# https://gist.githubusercontent.com/pnewall/9a122c05ba2865c3a58f15008548fbbd/raw/5bb4f84d918b871ee0e8b99f60dde976bb711d7c/ireland_counties.geojson

import plotly.express as px
from collections import Counter
import geojson
import pandas as pd
from SPARQLWrapper import SPARQLWrapper
from pprint import pprint


def mapSamplersFig(endpointURL, repoID):
    qMap = '''
        PREFIX sosa: <http://www.w3.org/ns/sosa/>
        PREFIX geo: <http://www.opengis.net/ont/geosparql#>
        PREFIX geof: <http://www.opengis.net/def/function/geosparql/>
        PREFIX osi: <http://ontologies.geohive.ie/osi#>
        PREFIX sceedr: <http://sceed.org/datasource/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT ?countyName (COUNT(?sampler) AS ?samplerCount) ?graphName
        WHERE{
        GRAPH ?graphName {
            ?sampler a sosa:Sampler;
                     geo:hasGeometry ?splPointG.
            ?splPointG geo:asWKT ?splGeom.
        }
        {
            SELECT ?cogeom ?countyName
            WHERE {
                #County geom
                ?county a osi:County, geo:Feature;
                        rdfs:label ?countyName;
                        geo:hasGeometry ?cogeomb.
                ?cogeomb a geo:Geometry;
                         geo:asWKT ?cogeom.
                FILTER (lang(?countyName) = 'en')

            }
        }
        FILTER(geof:sfWithin(?splGeom, ?cogeom))
        }
        GROUP BY ?countyName ?graphName
        '''
    # 1.2.Query parameters
    SPARQLQuery = SPARQLWrapper(endpointURL + repoID)
    SPARQLQuery.setMethod('POST')
    SPARQLQuery.setQuery(qMap)
    SPARQLQuery.setReturnFormat('json')
    # 1.3.Fire query and convert results to json (dictionary)
    qMapSamplers = SPARQLQuery.query().convert()

    # mapSColumns = qMapSamplers['head']['vars']
    mapSCounties = [cc['countyName']['value'].capitalize() for cc in qMapSamplers['results']['bindings']]
    mapSCount = [cc['samplerCount']['value'] for cc in qMapSamplers['results']['bindings']]
    mapSGraph = [cc['graphName']['value'].rsplit('/', 1)[-1] for cc in qMapSamplers['results']['bindings']]

    envMapDF = pd.DataFrame({'County': mapSCounties,
                             'DataPointsDensity': [int(i) for i in mapSCount],
                             'Graph': mapSGraph})

    envMapR = envMapDF.pivot(index='County', columns='Graph', values='DataPointsDensity')
    envMapR['DataPointsDensity'] = envMapR.weather.fillna(0) + envMapR.pollution.fillna(0)
    envMapR.reset_index(level=0, inplace=True)
    envMapR = envMapR.fillna(0)

    # Load Ireland geometries
    with open('IrelandCounties.geojson', 'r', encoding='utf-8') as f:
        geoIre = geojson.load(f)
    #pprint(geoIre)
    # Map figure with samplers data
    mapIreFig = px.choropleth_mapbox(
        envMapR, geojson=geoIre, locations='County', color='DataPointsDensity',
        color_continuous_scale=px.colors.sequential.Jet,
        mapbox_style='carto-positron',
        zoom=6, center={'lat': 53.425049, 'lon': -7.944620},
        opacity=0.5, hover_data=envMapR.columns,
    )
    mapIreFig.update_layout(margin={'r': 0, 't': 0, 'l': 0, 'b': 0})

    return mapIreFig


if __name__ == '__main__':
    mapSamplersFig()