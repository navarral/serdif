from pprint import pprint
import requests
import json
import io
import sys
import os
import pandas as pd
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from collections import defaultdict
import urllib.parse
from rdflib import Graph
import shutil
import numpy as np
from bs4 import BeautifulSoup
from plotly.subplots import make_subplots
import plotly.express as px
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import matplotlib
import shapely
import geopandas as gpd
from functools import partial
import pyproj
from shapely.ops import transform
from shapely.geometry import Point
from subprocess import call


def serdifLinkage(df, evEnvoMetaDf, referer, repo, endpoint, spatialLink_sel,
                  timeUnit_sel, aggMethod_sel, evType, metadataType):
    # Delete zip files older than
    df_input_html = df.to_html(
        classes='table text-center table-borderless table-striped table-hover table-responsive table-sm',
        justify='center', table_id='evTable')
    # Define location from longitude and latitude coordinates as a GeoSPARQL point
    df['point'] = 'POINT(' + df['lon'].astype(str) + ' ' + df['lat'].astype(str) + ')'

    # Get query time to use as index for file names
    startTime = datetime.now()
    queryTimeStr = str(startTime)
    queryTime = urllib.parse.quote(queryTimeStr, safe='')

    # Make folder to store the output
    outfolder = './ee-output-QT_' + queryTimeStr
    if not os.path.exists(outfolder):
        os.makedirs(outfolder)

    areaLevel = spatialLink_sel['level']

    # -------------------------------------------------------------------------------------------------------------------
    #   Function definition
    # -------------------------------------------------------------------------------------------------------------------

    # Function that returns datasets within a specific region or close by it
    def envoDataLoc(referer, repo, point, level):
        qBody = '''
    PREFIX geosparql: <http://www.opengis.net/ont/geosparql#>
    PREFIX geof: <http://www.opengis.net/def/function/geosparql/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX ramon: <http://rdfdata.eionet.europa.eu/ramon/ontology/>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    PREFIX qb: <http://purl.org/linked-data/cube#>
    PREFIX prov: <http://www.w3.org/ns/prov#>
    PREFIX dcat: <http://www.w3.org/ns/dcat#>
    PREFIX dct: <http://purl.org/dc/terms/>
    PREFIX geo: <http://www.opengis.net/ont/geosparql#>
    PREFIX locn: <http://www.w3.org/ns/locn#>
    PREFIX serdif: <https://serdif.adaptcentre.ie/kg/2022/>
    SELECT ?point ?qbDataSet ?areaName	 
    WHERE { 
        {
            SELECT ?point ?area ?geo ?areaName
            WHERE{
                BIND( "''' + point + '''"^^geosparql:wktLiteral AS ?point)
                ?area a geosparql:Feature ;
                      rdfs:label ?areaName ;
                      geosparql:hasGeometry/geosparql:asWKT ?geo ;
                                           ramon:level ''' + str(level) + ''' .
                FILTER(geof:sfWithin(?point, ?geo))
            }
        }
        GRAPH serdif:metadata {
            ?qbDataSet a qb:DataSet, geosparql:Feature ;
                       locn:geometry ?qbGeoB .
            ?qbGeoB geo:asWKT ?qbGeo.
        }
        FILTER(geof:sfWithin(?qbGeo, ?geo))
    }
        '''
        endpoint = ''.join(referer + repo)
        # 1.3.Fire query and convert results to json (dictionary)
        qEvLoc = requests.post(
            endpoint,
            data={'query': qBody},
            headers={
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:101.0) Gecko/20100101 Firefox/101.0',
                # 'Referer': 'http://localhost:7200/sparql',
                'Accept': 'application/sparql-results+json',
            }
        )
        jEvLoc = json.loads(qEvLoc.text)
        # 1.4.Return results
        rEvLoc = jEvLoc['results']['bindings']
        dEvLoc = {
            'dataset': [ds['qbDataSet']['value'] for ds in rEvLoc],
            'queryBody': qBody
        }
        return dEvLoc

    # Function that returns the area name and geometry for a given point
    def provArea(referer, repo, point, level):
        qBody = '''
    PREFIX geosparql: <http://www.opengis.net/ont/geosparql#>
    PREFIX geof: <http://www.opengis.net/def/function/geosparql/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX ramon: <http://rdfdata.eionet.europa.eu/ramon/ontology/>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    PREFIX qb: <http://purl.org/linked-data/cube#>
    PREFIX prov: <http://www.w3.org/ns/prov#>
    PREFIX dcat: <http://www.w3.org/ns/dcat#>
    PREFIX dct: <http://purl.org/dc/terms/>
    PREFIX geo: <http://www.opengis.net/ont/geosparql#>
    PREFIX locn: <http://www.w3.org/ns/locn#>
    PREFIX serdif: <https://serdif.adaptcentre.ie/kg/2022/>
    SELECT ?point ?area ?geo ?areaName
    WHERE{
        BIND( "''' + point + '''"^^geosparql:wktLiteral AS ?point)
        ?area a geosparql:Feature ;
              rdfs:label ?areaName ;
              geosparql:hasGeometry/geosparql:asWKT ?geo ;
                                   ramon:level ''' + str(level) + ''' .
        FILTER(geof:sfWithin(?point, ?geo))
    }
        '''
        endpoint = ''.join(referer + repo)
        # 1.3.Fire query and convert results to json (dictionary)
        qEvLoc = requests.post(
            endpoint,
            data={'query': qBody},
            headers={
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:101.0) Gecko/20100101 Firefox/101.0',
                # 'Referer': 'http://localhost:7200/sparql',
                'Accept': 'application/sparql-results+json',
            }
        )
        jEvLoc = json.loads(qEvLoc.text)
        # 1.4.Return results
        rEvLoc = jEvLoc['results']['bindings']
        dEvLoc = {
            'areaName': rEvLoc[0]['areaName']['value'],
            'areaGeo': rEvLoc[0]['geo']['value'],
            'queryBody': qBody
        }
        return dEvLoc

    # Function to define a buffer around a point and return a wkt geometry
    proj_wgs84 = pyproj.Proj('+proj=longlat +datum=WGS84')

    def geodesic_point_buffer(lat, lon, km):
        # Azimuthal equidistant projection
        aeqd_proj = '+proj=aeqd +lat_0={lat} +lon_0={lon} +x_0=0 +y_0=0'
        project = partial(
            pyproj.transform,
            pyproj.Proj(aeqd_proj.format(lat=lat, lon=lon)),
            proj_wgs84)
        buf = Point(0, 0).buffer(km * 1000)  # distance in metres
        polyTupleList = transform(project, buf).exterior.coords[:]
        polyGeo = 'POLYGON (' + ''.join(str(x) for x in polyTupleList).replace(', ', ' ').replace(')(', ', ') + ')'
        return polyGeo

    def envoDataLocBuffer(referer, repo, buffer):
        qBody = '''
    PREFIX geosparql: <http://www.opengis.net/ont/geosparql#>
    PREFIX geof: <http://www.opengis.net/def/function/geosparql/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX ramon: <http://rdfdata.eionet.europa.eu/ramon/ontology/>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    PREFIX qb: <http://purl.org/linked-data/cube#>
    PREFIX prov: <http://www.w3.org/ns/prov#>
    PREFIX dcat: <http://www.w3.org/ns/dcat#>
    PREFIX dct: <http://purl.org/dc/terms/>
    PREFIX geo: <http://www.opengis.net/ont/geosparql#>
    PREFIX locn: <http://www.w3.org/ns/locn#>
    PREFIX serdif: <https://serdif.adaptcentre.ie/kg/2022/>
    SELECT ?buffer ?qbDataSet
    WHERE { 
        BIND( "''' + buffer + '''"^^geosparql:wktLiteral AS ?buffer)
        GRAPH serdif:metadata {
            ?qbDataSet a qb:DataSet, geosparql:Feature ;
                       locn:geometry ?qbGeoB .
            ?qbGeoB geo:asWKT ?qbGeo.
        }
        FILTER(geof:sfWithin(?qbGeo, ?buffer))
    }
        '''
        endpoint = ''.join(referer + repo)
        # 1.3.Fire query and convert results to json (dictionary)
        qEvLoc = requests.post(
            endpoint,
            data={'query': qBody},
            headers={
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:101.0) Gecko/20100101 Firefox/101.0',
                # 'Referer': 'http://localhost:7200/sparql',
                'Accept': 'application/sparql-results+json',
            }
        )
        jEvLoc = json.loads(qEvLoc.text)
        # 1.4.Return results
        rEvLoc = jEvLoc['results']['bindings']
        dEvLoc = {
            'dataset': [ds['qbDataSet']['value'] for ds in rEvLoc],
            'queryBody': qBody
        }
        return dEvLoc

    # Function that returns the season-alike events from input
    def evSeasonAlike(referer, repo, date, daysBefore, daysAfter):
        qBody = '''
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
PREFIX qb: <http://purl.org/linked-data/cube#>
PREFIX sdmx-dimension: <http://purl.org/linked-data/sdmx/2009/dimension#>
PREFIX serdif-dataset: <https://serdif.adaptcentre.ie/kg/2022/dataset#>
PREFIX serdif-measure: <https://serdif.adaptcentre.ie/kg/2022/measure#>
# Query to select random season-alike event dates
SELECT ?obsTime
WHERE{
    # Step 1: select years from all dates available
    {
        SELECT DISTINCT ?years
        WHERE{
            # Step 1.1: get all dates available
            ?obsData a qb:Observation ;
                     qb:dataSet  <https://serdif.adaptcentre.ie/kg/2022/dataset#type=airquality&source=eea&version=vE1a&point=8.6134_47.4028999994652> ;
                     sdmx-dimension:timePeriod ?obsTime .
            # Step 1.2: select years from dates available
            BIND(YEAR(?obsTime) AS ?years)
        }
    }
    # Step 2: define the date of the event
    BIND(xsd:dateTime("''' + str(date) + 'T00:00:00Z' + '''") AS ?evDateT)
    # Step 3: select the month and day from the event date    
    BIND(MONTH(?evDateT) as ?evMonth)
    BIND(DAY(?evDateT) as ?evDay)
    # Step 4: fix single digits when using SPARQL temporal functions
    BIND(IF(STRLEN( STR(?evMonth) ) = 1, CONCAT("0", STR(?evMonth)), STR(?evMonth)) AS ?evMonthS)
    BIND(IF(STRLEN( STR(?evDay) ) = 1, CONCAT("0", STR(?evDay)), STR(?evDay)) AS ?evDayS)
    # Step 5: build an event date for all the years available
    BIND(xsd:dateTime(CONCAT(STR(?years),"-", ?evMonthS, "-", ?evDayS, "T00:00:00Z")) AS ?eventYear)
    # Step 6: generate an interval around the event date across years
    BIND(?eventYear - "P''' + str(daysBefore) + '''D"^^xsd:duration AS ?dateLag)
    BIND(?dateLag - "P''' + str(daysAfter) + '''D"^^xsd:duration AS ?dateStart)
    # Step 7: get all dates available
    ?obsData a qb:Observation ;
             qb:dataSet <https://serdif.adaptcentre.ie/kg/2022/dataset#type=airquality&source=eea&version=vE1a&point=8.6134_47.4028999994652> ;
             sdmx-dimension:timePeriod ?obsTime .
    # Step 8: filter all dates available within the defined intervals
    FILTER(?obsTime > ?dateStart && ?obsTime < ?dateLag)

}
ORDER BY RAND()
LIMIT 1
'''
        endpoint = ''.join(referer + repo)
        qEvTW = requests.post(
            endpoint,
            data={'query': qBody},
            headers={
                'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:93.0) Gecko/20100101 Firefox/93.0',
                # 'Referer': 'https://serdif-example.adaptcentre.ie/sparql',
                'Accept': 'application/sparql-results+json',
            }
        )
        jEvTW = json.loads(qEvTW.text)
        # 1.4.Return results
        rEvTW = jEvTW['results']['bindings']
        dEvTW = rEvTW[0]['obsTime']['value'].split('T')[0]
        return dEvTW

    # Function that returns the start and end dates of the time window
    def evTimeWindow(referer, repo, date, lag, length):
        qBody = '''
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        SELECT ?dateLag ?dateStart
        WHERE { 
            BIND(xsd:dateTime("''' + str(date) + 'T00:00:00Z' + '''") AS ?evDateT)
            BIND(?evDateT - "P''' + str(lag) + '''D"^^xsd:duration AS ?dateLag)
            BIND(?dateLag - "P''' + str(length) + '''D"^^xsd:duration AS ?dateStart)
        }
        '''
        endpoint = ''.join(referer + repo)
        qEvTW = requests.post(
            endpoint,
            data={'query': qBody},
            headers={
                'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:93.0) Gecko/20100101 Firefox/93.0',
                # 'Referer': 'https://serdif-example.adaptcentre.ie/sparql',
                'Accept': 'application/sparql-results+json',
            }
        )
        jEvTW = json.loads(qEvTW.text)
        # 1.4.Return results
        rEvTW = jEvTW['results']['bindings']
        dEvTW = {
            'dateLag': rEvTW[0]['dateLag']['value'],
            'dateStart': rEvTW[0]['dateStart']['value'],
            'queryBody': qBody
        }
        return dEvTW

    # Query to generate an event-environmental graph
    def evEnvoDataSetValue(referer, repo, evEnvoDict, timeUnit, spAgg):
        # Dictionaries to translate timeUnit to query SPARQL query parameters
        selTimeUnit = {'hour': '?hourT ?dayT ?monthT ?yearT',
                       'day': '?dayT ?monthT ?yearT',
                       'month': '?monthT ?yearT',
                       'year': '?yearT',
                       }
        selTimeUnitRev = {'hour': '?yearT ?monthT ?dayT ?hourT',
                          'day': '?yearT ?monthT ?dayT',
                          'month': '?yearT ?monthT',
                          'year': '?yearT',
                          }

        # Build block per each event
        qBodyBlockList = []
        for ev in evEnvoDict.keys():
            qBodyBlock = '''
            {
                SELECT ?event ''' + selTimeUnitRev[timeUnit] + ''' ?envProp ?lag (''' + spAgg + '''(?envVar) AS ?envVarV)
                WHERE {
                    {
                        SELECT ?obsData ?obsTime
                        WHERE{
                            VALUES ?envoDataSet {''' + ''.join(
                [' <' + envoDS + '> ' for envoDS in evEnvoDict[ev]['datasets-used']]) + '''}  
                            GRAPH ?envoDataSet {
                                ?obsData
                                    a qb:Observation ;
                                    qb:dataSet ?envoDataSet ;
                                    sdmx-dimension:timePeriod ?obsTime .
                            }        
                            FILTER(?obsTime > "''' + evEnvoDict[ev][
                             'dateStart'] + '''"^^xsd:dateTime && ?obsTime < "''' + \
                         evEnvoDict[ev]['dateLag'] + '''"^^xsd:dateTime)
                        }
                    }
                    ?obsData ?envProp ?envVar .
                    FILTER(datatype(?envVar) = xsd:float)  
                    # FILTER(?envProp != <http://purl.org/linked-data/sdmx/2009/measure#obsValue>)  
                    # String manipulation to aggregate observations per time unit
                    BIND(YEAR(?obsTime) AS ?yearT)
                    BIND(MONTH(?obsTime) AS ?monthT)
                    BIND(DAY(?obsTime) AS ?dayT)
                    BIND(xsd:decimal(ofn:asDays("''' + evEnvoDict[ev]['date'] + '''T00:00:00Z"^^xsd:dateTime - ?obsTime - "P1D"^^xsd:duration )) AS ?lag)
                    BIND("''' + ev.split('event#')[1] + '''" AS ?event)
                }
                GROUP BY ?event ?envProp ?lag ''' + selTimeUnit[timeUnit] + '''
            }
            '''
            qBodyBlockList.append(qBodyBlock)

        qBodyBlockUnion = '  UNION  '.join(qBodyBlockList)

        qBody = '''
    PREFIX qb: <http://purl.org/linked-data/cube#>
    PREFIX sdmx-dimension: <http://purl.org/linked-data/sdmx/2009/dimension#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    PREFIX geo:	<http://www.opengis.net/ont/geosparql#>
    PREFIX prov: <http://www.w3.org/ns/prov#>
    PREFIX serdif-dataset: <https://serdif.adaptcentre.ie/kg/2022/dataset#>
    PREFIX serdif-measure: <https://serdif.adaptcentre.ie/kg/2022/measure#>
    PREFIX serdif-dimension: <https://serdif.adaptcentre.ie/kg/2022/dimension#>
    PREFIX serdif-slice: <https://serdif.adaptcentre.ie/kg/2022/slice#>
    PREFIX greg: <http://www.w3.org/ns/time/gregorian#>
    PREFIX time: <http://www.w3.org/2006/time#>
    PREFIX ofn: <http://www.ontotext.com/sparql/functions/>
    CONSTRUCT{       
        ?sliceName
            a qb:Slice;
            qb:sliceStructure 				serdif-slice:sliceByTime ;
            serdif-dimension:event		   	?eventRef ;
            serdif-dimension:measureType 	?measureTypeUri ;
            qb:observation   				?obsName ;
            .
    
        ?obsName
            a qb:Observation, time:TimePosition ;
            qb:dataSet 					?datasetName ;
            sdmx-dimension:timePeriod 	?obsTimePeriod ;
            time:numericPosition		?lag ;
            ?envProp 					?envVarV ;
            .
    }
        WHERE {
        ''' + qBodyBlockUnion + '''   
            # Slice
            BIND(IRI(CONCAT(STR("https://serdif.adaptcentre.ie/kg/2022/event#"), ?event)) AS ?eventRef)
            # Measure Type
            BIND(IRI("https://serdif.adaptcentre.ie/kg/2022/measureType#value") AS ?measureTypeUri)
            # Environmental property
            # BIND(IRI(CONCAT(STR(?envProp), "Value")) AS ?envPropV)
            # Dataset name
            BIND(IRI("https://serdif.adaptcentre.ie/kg/2022/dataset#linked-ee-dataset-v20220524-QT_''' + queryTime + '''") AS ?datasetName)
            # Observation Name
            # Fix single digits when using SPARQL temporal functions
            BIND( IF( BOUND(?monthT), IF(STRLEN( STR(?monthT) ) = 2, STR(?monthT), CONCAT("0", STR(?monthT)) ), "01") AS ?monthTF )
            BIND( IF( BOUND(?dayT), IF( STRLEN( STR(?dayT) ) = 2, STR(?dayT), CONCAT("0", STR(?dayT)) ), "01" ) AS ?dayTF )
            BIND( "00"  AS ?hourTF )    
            BIND(IRI(CONCAT(STR(?datasetName),"-obs-", ?event ,"-value-", str(?yearT),?monthTF,?dayTF,"T",?hourTF,"0000Z")) AS ?obsName)
            # Build dateTime values 
            BIND(xsd:dateTime(CONCAT(str(?yearT),"-",?monthTF,"-",?dayTF,"T",?hourTF,":00:00Z")) AS ?obsTimePeriod)
            # Build IRI for the CONSTRUCT
            BIND(IRI(CONCAT(STR(?datasetName),"-slice-", ?event, "-value")) AS ?sliceName)
    
        }
        '''
        endpoint = ''.join(referer + repo)
        # 1.2.Query parameters
        rQuery = requests.post(
            endpoint,
            data={'query': qBody},
            headers={
                'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:93.0) Gecko/20100101 Firefox/93.0',
                # 'Referer': 'https://serdif-example.adaptcentre.ie/sparql',
                'Accept': 'text/turtle',
            }
        )

        return {'queryContent': rQuery.content, 'queryBody': qBody}

    def evEnvoDataSetNormal(referer, repo, evEnvoDict):
        # Build block per each event
        qBodyBlockList = []
        for ev in evEnvoDict.keys():
            # Select months within the time interval of the selected data
            dates_ev = [datetime.strptime(evEnvoDict[ev][dd],
                                          '%Y-%m-%dT%H:%M:%S%z').month for dd in ['dateLag', 'dateStart']]
            month_ev = list(set(dates_ev))

            qBodyBlock = '''
            {
                SELECT ?event ?monthN ?envPropN (AVG(?envVar) AS ?envVarN)
                WHERE {
                    {
                        SELECT ?obsData ?obsTime ?monthN
                        WHERE{
                            VALUES ?envoDataSet {''' + ''.join(
                [' <' + envoDS + '> ' for envoDS in evEnvoDict[ev]['datasets-used']]) + '''}  
                            GRAPH ?envoDataSet {
                                ?obsData
                                    a qb:Observation ;
                                    qb:dataSet ?envoDataSet ;
                                    sdmx-dimension:timePeriod ?obsTime .
                            }       
                            BIND(MONTH(?obsTime) AS ?monthN)
                            FILTER(''' + '||'.join(
                [' ?monthN = "' + str(mev) + '"^^xsd:integer ' for mev in month_ev]) + ''')
                        }
                    }
                    ?obsData ?envProp ?envVar .
                    FILTER(datatype(?envVar) = xsd:float)  
                    # FILTER(?envProp != <http://purl.org/linked-data/sdmx/2009/measure#obsValue>)  
                    # String manipulation to aggregate observations per time unit
                    BIND(IRI(CONCAT(STR(?envProp),"Normal")) AS ?envPropN)
                    BIND("''' + ev.split('event#')[1] + '''" AS ?event)
                }
                GROUP BY ?event ?envPropN ?monthN
            }
            '''
            qBodyBlockList.append(qBodyBlock)

        qBodyBlockUnion = '  UNION  '.join(qBodyBlockList)

        qBody = '''
    PREFIX qb: <http://purl.org/linked-data/cube#>
    PREFIX sdmx-dimension: <http://purl.org/linked-data/sdmx/2009/dimension#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    PREFIX geo:	<http://www.opengis.net/ont/geosparql#>
    PREFIX prov: <http://www.w3.org/ns/prov#>
    PREFIX serdif-dataset: <https://serdif.adaptcentre.ie/kg/2022/dataset#>
    PREFIX serdif-measure: <https://serdif.adaptcentre.ie/kg/2022/measure#>
    PREFIX serdif-dimension: <https://serdif.adaptcentre.ie/kg/2022/dimension#>
    PREFIX serdif-slice: <https://serdif.adaptcentre.ie/kg/2022/slice#>
    PREFIX greg: <http://www.w3.org/ns/time/gregorian#>
    PREFIX time: <http://www.w3.org/2006/time#>
    PREFIX ofn: <http://www.ontotext.com/sparql/functions/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    CONSTRUCT{       
        ?sliceName
            a qb:Slice;
            qb:sliceStructure 				serdif-slice:sliceByTime ;
            serdif-dimension:event		   	?eventRef ;
            serdif-dimension:measureType 	?measureTypeUri ;
            qb:observation   				?obsName ;
            .
    
        ?obsName
            a qb:Observation, time:GeneralDateTimeDescription ;
            qb:dataSet 					?datasetName ;
            time:unitType				time:unitMonth ;
            time:monthOfYear		 	?obsMonth ;
            ?envPropN 					?envVarN ;
            .
    }
        WHERE {
        ''' + qBodyBlockUnion + '''   
            # Slice
            BIND(IRI(CONCAT(STR("https://serdif.adaptcentre.ie/kg/2022/event#"), ?event)) AS ?eventRef)
            # Measure Type
            BIND(IRI("https://serdif.adaptcentre.ie/kg/2022/measureType#normal") AS ?measureTypeUri)
            # Dataset name
            BIND(IRI("https://serdif.adaptcentre.ie/kg/2022/dataset#linked-ee-dataset-v20220524-QT_''' + queryTime + '''") AS ?datasetName)
            # Normals month
            BIND(IF(STRLEN( STR(?monthN) ) = 1, CONCAT("--0", STR(?monthN)), CONCAT("--", STR(?monthN))) AS ?obsMonthN)
            ?obsMonth time:month ?refMonth ;
                      rdfs:label ?obsMonthLabel .
            FILTER(STR(?refMonth) = ?obsMonthN)   
            # Observation Name  
            BIND(IRI(CONCAT(STR(?datasetName),"-obs-", ?event ,"-normal-", ?obsMonthLabel)) AS ?obsName)
            # Build IRI for the CONSTRUCT
            BIND(IRI(CONCAT(STR(?datasetName),"-slice-", ?event, "-normal")) AS ?sliceName)
        }
        '''
        endpoint = ''.join(referer + repo)
        # 1.2.Query parameters
        rQuery = requests.post(
            endpoint,
            data={'query': qBody},
            headers={
                'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:93.0) Gecko/20100101 Firefox/93.0',
                # 'Referer': 'https://serdif-example.adaptcentre.ie/sparql',
                'Accept': 'text/turtle',
            }
        )

        return {'queryContent': rQuery.content, 'queryBody': qBody}

    def evEnvoDataSetSdev(referer, repo, evEnvoDict):
        # Build block per each event
        qBodyBlockList = []
        for ev in evEnvoDict.keys():
            # Select months within the time interval of the selected data
            dates_ev = [datetime.strptime(evEnvoDict[ev][dd],
                                          '%Y-%m-%dT%H:%M:%S%z').month for dd in ['dateLag', 'dateStart']]
            month_ev = list(set(dates_ev))

            qBodyBlock = '''
            {
                SELECT ?event ?monthN ?envPropC (xsd:float(ofn:sqrt(SUM(?envVarNmean)/(?envVarC - 1))) AS ?sdev) 
                WHERE{
                    {
                        SELECT ?monthN ?envProp ?envVarC ((?envVar - ?envVarN)*(?envVar - ?envVarN) AS ?envVarNmean) 
                        WHERE {
                            {
                                SELECT ?monthN ?envProp ?envVar
                                WHERE{
                                    {
                                        SELECT ?obsData ?obsTime ?monthN
                                        WHERE{
                                            VALUES ?envoDataSet { ''' + ''.join(
                [' <' + envoDS + '> ' for envoDS in evEnvoDict[ev]['datasets-used']]) + ''' }
                                            GRAPH ?envoDataSet {
                                                ?obsData
                                                    a qb:Observation ;
                                                    qb:dataSet ?envoDataSet ;
                                                    sdmx-dimension:timePeriod ?obsTime .
                                            }
                                            BIND(MONTH(?obsTime) AS ?monthN)
                                            FILTER(''' + '||'.join(
                [' ?monthN = "' + str(mev) + '"^^xsd:integer ' for mev in month_ev]) + ''')
    
                                        }
                                    }
                                    ?obsData ?envProp ?envVar .
                                    FILTER(datatype(?envVar) = xsd:float)  
                                }
                            }
    
                            {
                                SELECT ?monthN ?envProp (AVG(?envVar) AS ?envVarN) (COUNT(?envVar) AS ?envVarC)
                                WHERE {
                                    {
                                        SELECT ?obsData ?obsTime ?monthN
                                        WHERE{
                                            VALUES ?envoDataSet { ''' + ''.join(
                [' <' + envoDS + '> ' for envoDS in evEnvoDict[ev]['datasets-used']]) + ''' }
                                            GRAPH ?envoDataSet {
                                                ?obsData
                                                    a qb:Observation ;
                                                    qb:dataSet ?envoDataSet ;
                                                    sdmx-dimension:timePeriod ?obsTime .
                                            }
                                            BIND(MONTH(?obsTime) AS ?monthN)
                                            FILTER(''' + '||'.join(
                [' ?monthN = "' + str(mev) + '"^^xsd:integer ' for mev in month_ev]) + ''')
    
                                        }
                                    }
                                    ?obsData ?envProp ?envVar .
                                    FILTER(datatype(?envVar) = xsd:float)   
                                }
                                GROUP BY ?envProp ?monthN
                            }
                        }
                    }
                # String manipulation to aggregate observations per time unit
                BIND(IRI(CONCAT(STR(?envProp),"Sdev")) AS ?envPropC)
                BIND("''' + ev.split('event#')[1] + '''" AS ?event)    
    
                }
                GROUP BY ?event ?envPropC ?monthN ?envVarC
            }
            '''
            qBodyBlockList.append(qBodyBlock)

        qBodyBlockUnion = '  UNION  '.join(qBodyBlockList)

        qBody = '''
    PREFIX qb: <http://purl.org/linked-data/cube#>
    PREFIX sdmx-dimension: <http://purl.org/linked-data/sdmx/2009/dimension#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    PREFIX geo:	<http://www.opengis.net/ont/geosparql#>
    PREFIX prov: <http://www.w3.org/ns/prov#>
    PREFIX serdif-dataset: <https://serdif.adaptcentre.ie/kg/2022/dataset#>
    PREFIX serdif-measure: <https://serdif.adaptcentre.ie/kg/2022/measure#>
    PREFIX serdif-dimension: <https://serdif.adaptcentre.ie/kg/2022/dimension#>
    PREFIX serdif-slice: <https://serdif.adaptcentre.ie/kg/2022/slice#>
    PREFIX greg: <http://www.w3.org/ns/time/gregorian#>
    PREFIX time: <http://www.w3.org/2006/time#>
    PREFIX ofn: <http://www.ontotext.com/sparql/functions/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    CONSTRUCT{       
        ?sliceName
            a qb:Slice;
            qb:sliceStructure 				serdif-slice:sliceByTime ;
            serdif-dimension:event		   	?eventRef ;
            serdif-dimension:measureType 	?measureTypeUri ;
            qb:observation   				?obsName ;
            .
    
        ?obsName
            a qb:Observation, time:GeneralDateTimeDescription ;
            qb:dataSet 					?datasetName ;
            time:unitType				time:unitMonth ;
            time:monthOfYear		 	?obsMonth ;
            ?envPropC 					?sdev ;
            .
    }
        WHERE {
        ''' + qBodyBlockUnion + '''   
            # Slice
            BIND(IRI(CONCAT(STR("https://serdif.adaptcentre.ie/kg/2022/event#"), ?event)) AS ?eventRef)
            # Measure Type
            BIND(IRI("https://serdif.adaptcentre.ie/kg/2022/measureType#sdev") AS ?measureTypeUri)
            # Dataset name
            BIND(IRI("https://serdif.adaptcentre.ie/kg/2022/dataset#linked-ee-dataset-v20220524-QT_''' + queryTime + '''") AS ?datasetName)
            # Normals month
            BIND(IF(STRLEN( STR(?monthN) ) = 1, CONCAT("--0", STR(?monthN)), CONCAT("--", STR(?monthN))) AS ?obsMonthN)
            ?obsMonth time:month ?refMonth ;
                      rdfs:label ?obsMonthLabel .
            FILTER(STR(?refMonth) = ?obsMonthN)   
            # Observation Name  
            BIND(IRI(CONCAT(STR(?datasetName),"-obs-", ?event ,"-sdev-", ?obsMonthLabel)) AS ?obsName)
            # Build IRI for the CONSTRUCT
            BIND(IRI(CONCAT(STR(?datasetName),"-slice-", ?event, "-sdev")) AS ?sliceName)
        }
        '''
        endpoint = ''.join(referer + repo)
        # 1.2.Query parameters
        rQuery = requests.post(
            endpoint,
            data={'query': qBody},
            headers={
                'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:93.0) Gecko/20100101 Firefox/93.0',
                # 'Referer': 'https://serdif-example.adaptcentre.ie/sparql',
                'Accept': 'text/turtle',
            }
        )

        return {'queryContent': rQuery.content, 'queryBody': qBody}

    # String to iri
    def strToIri(stringL):
        return ['<' + string + '>' for string in stringL]

    # Select values for a specific key
    def selectValueKey(df, keyN):
        return df.loc[df['key'] == keyN, 'value'].iloc[0]

    # selectValueKey and separate list
    def selectValueKeyL(df, keyN):
        return df.loc[df['key'] == keyN, 'value'].iloc[0].split(' ')

    # Flatten list
    def flatten(d):
        return [i for b in [[i] if not isinstance(i, list) else flatten(i) for i in d] for i in b]

    # -------------------------------------------------------------------------------------------------------------------
    #   Event journey
    # -------------------------------------------------------------------------------------------------------------------

    # Define the event journey from input events and queries
    if evType['evType'] == 'random':
        df['date'] = [evSeasonAlike(
            referer=referer, repo=repo, date=d,
            daysBefore=evType['before'], daysAfter=evType['after'], ) for d in df['date']]

    # Query results and query bodies for provenance
    eventTimeInfo = [evTimeWindow(referer=referer, repo=repo, date=d, lag=lg, length=ln) for d, lg, ln in
                     zip(df['date'], df['lag'], df['length'])]
    # Spatial link
    if spatialLink_sel['spatial'] == 'area':
        eventDatasetLoc = [envoDataLoc(referer=referer, repo=repo, point=p, level=areaLevel) for p in df['point']]
        eventArea = [provArea(referer=referer, repo=repo, point=p, level=areaLevel) for p in df['point']]
        # Datasets used
        df['datasets-used'] = [d['dataset'] for d in eventDatasetLoc]
        # Area
        df['queryLoc'] = [d['queryBody'] for d in eventDatasetLoc]
        df['evAreaName'] = [d['areaName'] for d in eventArea]
        df['evArea'] = [d['areaGeo'] for d in eventArea]
        df['queryEvArea'] = [d['queryBody'] for d in eventArea]
    elif spatialLink_sel['spatial'] == 'distance':
        bufferList = [geodesic_point_buffer(lat=lat, lon=lon, km=spatialLink_sel['level']) for lat, lon in
                      zip(df['lat'], df['lon'])]
        eventDatasetLoc = [envoDataLocBuffer(referer=referer, repo=repo, buffer=b) for b in bufferList]
        # Datasets used
        df['datasets-used'] = [d['dataset'] for d in eventDatasetLoc]
        # Area
        df['queryLoc'] = [d['queryBody'] for d in eventDatasetLoc]
        df['evAreaName'] = [ev + '-buffer-' + str(spatialLink_sel['level']) + 'km' for ev in df['event']]
        df['evArea'] = bufferList
        df['queryEvArea'] = [d['queryBody'] for d in eventDatasetLoc]

    # Store event journey results in the event dataframe
    df['evName'] = df['event']
    # Time window
    df['qTimeWindow'] = [dlag['queryBody'] for dlag in eventTimeInfo]
    df['evDatetime'] = df['date'] + 'T00:00:00Z'
    df['dateLag'] = [dlag['dateLag'] for dlag in eventTimeInfo]
    df['dateStart'] = [dlag['dateStart'] for dlag in eventTimeInfo]

    # Save event journey table as a csv
    df.to_csv(outfolder + '/linked-ee-journey-v20220524-QT_' + queryTimeStr + '.csv', index=False)
    # Generate timeline figure for input events
    fig_timeline = px.timeline(
        df, x_start='dateStart', x_end='dateLag',
        y='evName', color='event', opacity=0.6)
    shapesList = list()
    for i in range(len(df['date'])):
        shapesList.append(
            dict(
                type='line', yref='paper',
                y0=(1 / len(df['date'])) * i,
                y1=(1 / len(df['date'])) * i + (1 / len(df['date'])),
                # y0='event-A',
                # y1='event-B',
                xref='x',
                x0=df['date'][i],
                x1=df['date'][i],
                line=dict(color='black', width=2),

            )
        )

    fig_timeline.update_xaxes(
        showline=True, linewidth=1.5,
        linecolor='black', mirror=True, ticks='outside')
    fig_timeline.update_yaxes(
        showline=True, linewidth=1.5,
        linecolor='black', mirror=True, ticks='outside')
    fig_timeline.update_layout(
        font=dict(size=20),
        plot_bgcolor='rgba(0,0,0,0)',
        shapes=shapesList,
        height=600,
        width=800,
    )

    # Map Figure to represent the provenance of the linked data
    centrePolygons = [list(shapely.wkt.loads(polygon).centroid.coords[0]) for polygon in df['evArea']]
    centreMap = [float(sum(col)) / len(col) for col in zip(*centrePolygons)]

    # Generate map figure for processing steps
    fig_map = px.choropleth_mapbox(
        df,
        geojson=gpd.GeoSeries(df['evArea'].apply(shapely.wkt.loads)).__geo_interface__,
        locations=df.index,
        color_discrete_map={'area': '#1f618d'},  # , 'Moderate':'Yellow','Low':'Green'},
        color=['area'] * len(df['evArea']),
        opacity=0.4,
        height=600,
        #width=800,
        # df['evArea'].apply(shapely.wkt.loads).apply(lambda p: len(p.exterior.coords)),
    ).update_layout(
        mapbox={'style': 'carto-positron',
                'center': {'lat': centreMap[1], 'lon': centreMap[0]},
                #'zoom': 6,
                },
        autosize=True,
        hovermode='closest',
        margin={"r":0,"t":0,"l":0,"b":0}
    )
    fig_map.add_scattermapbox(
        lat=df['lat'],
        lon=df['lon'],
        mode='markers+text',
        text=df['evName'],
        marker_size=20,
        marker_color='#d35400',
        name='event',
    )
    # Dataset lat, lon and names for the map
    dsLon = [envDS.split('&point=')[1].split('_')[0] for envDS in set(flatten(df['datasets-used']))]
    dsLat = [envDS.split('&point=')[1].split('_')[1].split('>')[0] for envDS in set(flatten(df['datasets-used']))]
    dsSource = [envDS.split('#')[1].split('&version')[0].split('>')[0] for envDS in set(flatten(df['datasets-used']))]
    dsNames = []
    for lon, lat, s in zip(dsLon, dsLat, dsSource):
        dsName = 'dataset-' + s + '&point=' + lon + '_' + 'lat'
        dsNames.append(dsName)

    fig_map.add_scattermapbox(
        lat=dsLat,
        lon=dsLon,
        mode='markers+text',
        text=flatten(dsNames),
        marker_size=12,
        marker_color='#1e8449',
        name='datasets',
    )
    fig_map.update_layout(
        font=dict(size=20),
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.1,
            xanchor='left',
            x=0,
        ),
    )

    # Convert dataframe to dictionary with events as keys
    df['event'] = 'https://serdif.adaptcentre.ie/kg/2022/event#' + df['event']
    df.index = df['event']
    evEnvoDict = df.transpose().to_dict()

    ###########################################
    ###  Event-Environmental linked data    ###
    ###########################################

    # Query to link environmental data to particular events
    qr_ee_graph_value = evEnvoDataSetValue(referer=referer, repo=repo, evEnvoDict=evEnvoDict, timeUnit=timeUnit_sel,
                                           spAgg=aggMethod_sel)
    # Query to generate event specific monthly normals and sdev
    qr_ee_graph_normal = evEnvoDataSetNormal(referer=referer, repo=repo, evEnvoDict=evEnvoDict)
    qr_ee_graph_sdev = evEnvoDataSetSdev(referer=referer, repo=repo, evEnvoDict=evEnvoDict)

    # Decode results to concat in the same rdf data file
    qr_ee_graph_value_qc = qr_ee_graph_value['queryContent'].decode('utf-8')
    qr_ee_graph_normal_qc = qr_ee_graph_normal['queryContent'].decode('utf-8')
    qr_ee_graph_count_qc = qr_ee_graph_sdev['queryContent'].decode('utf-8')
    # Event-environmental linked data save as a ttl file
    f = open(outfolder + '/linked-ee-dataset-v20220524-QT_' + queryTime + '.ttl', 'w')
    f.write('#-- Value environmental observations slice ----------\n')
    f.write(qr_ee_graph_value_qc)
    f.write('\n#-- Normal environmental observations slice ----------\n')
    f.write(qr_ee_graph_normal_qc[qr_ee_graph_normal_qc.find('\n\n'):])
    f.write('\n#-- Sdev environmental observations slice ----------\n')
    f.write(qr_ee_graph_count_qc[qr_ee_graph_count_qc.find('\n\n'):])
    f.close()

    ############################################
    ### Graph to CSV (values, normals, sdev) ###
    ############################################
    # Parse rdf file as a rdflib graph
    g = Graph()
    g.parse(outfolder + '/linked-ee-dataset-v20220524-QT_' + queryTime + '.ttl', format='turtle')

    # Query the data in g using SPARQL
    qres = g.query(
        '''
    SELECT ?event ?lag ?date ?variable ?value
    WHERE {
        ?slice a qb:Slice ;
               serdif-dimension:event ?eventU ;
               serdif-dimension:measureType <https://serdif.adaptcentre.ie/kg/2022/measureType#value> ;
               qb:observation ?obs .
        ?obs a qb:Observation, time:TimePosition ;
            qb:dataSet ?dataset ;
            sdmx-dimension:timePeriod ?dateTimeU ;
            time:numericPosition ?lag ;
            ?variableU ?value
        FILTER(datatype(?value) = xsd:float)
        # Format output to be more human friendly: uri -> simplified string
        BIND(STRAFTER(STR(?eventU), "#") AS ?event)
        BIND(STRBEFORE(STR(?dateTimeU), "T") AS ?date)
        BIND(STRBEFORE(STRAFTER(STR(?variableU), "has"),"Value") AS ?variable)
    }
    ORDER BY ?event DESC(?lag) ?variable
        '''
    )

    df_qr = pd.DataFrame(qres, columns=qres.vars)

    # Format column names from rdf variable format to string
    df_qr.columns = [str(col) for col in df_qr.columns.tolist()]
    # Pivot variable column from long to wide as preferred by the researchers
    df_qr_csv = df_qr.pivot(
        index=['event', 'date', 'lag'],
        columns='variable', values='value').reset_index().sort_values(by=['event', 'lag'])
    df_qr_csv.index.names = ['index']
    df_qr_csv.columns = [str(col) for col in df_qr_csv.columns.tolist()]
    df_qr_csv.to_csv(outfolder + '/linked-ee-dataset-v20220524-QT_' + queryTime + '-values.csv', index=False)
    df_qr_csv = df_qr_csv.to_csv(index=False)
    # 2.ReParse CSV object as text and then read as CSV. This process will
    # format the columns of the data frame to data types instead of objects.
    df_qr_csv_r = pd.read_csv(io.StringIO(df_qr_csv)).round(decimals=2)
    pd.set_option('display.max_rows', 500)
    pd.set_option('display.max_columns', 500)
    pd.set_option('display.width', 1000)

    # Query the normals
    qnormal = g.query(
        '''
    SELECT ?event ?month ?variable ?value
    WHERE {
        ?slice a qb:Slice ;
               serdif-dimension:event ?eventU ;
               serdif-dimension:measureType <https://serdif.adaptcentre.ie/kg/2022/measureType#normal> ;
               qb:observation ?obs .
        ?obs a qb:Observation, time:GeneralDateTimeDescription ;
            qb:dataSet ?dataset ;
            time:monthOfYear ?monthU ;
            ?variableU ?value
        FILTER(datatype(?value) = xsd:float)
        # Format output to be more human friendly: uri -> simplified string
        BIND(STRAFTER(STR(?eventU), "#") AS ?event)
        BIND(STRAFTER(STR(?monthU), "gregorian/") AS ?month)
        BIND(STRBEFORE(STRAFTER(STR(?variableU), "has"),"Normal") AS ?variable)
    }
    ORDER BY ?event ?month ?variable
        '''
    )
    df_normal = pd.DataFrame(qnormal, columns=qnormal.vars)
    # Format column names from rdf variable format to string
    df_normal.columns = [str(col) for col in df_normal.columns.tolist()]
    # Pivot variable column from long to wide as preferred by the researchers
    df_normal_csv = df_normal.pivot(
        index=['event', 'month'],
        columns='variable', values='value').reset_index()
    df_normal_csv.columns = [str(col).replace('Value', '') for col in df_normal_csv.columns.tolist()]
    df_normal_csv.index.names = ['index']
    df_normal_csv.to_csv(outfolder + '/linked-ee-dataset-v20220524-QT_' + queryTime + '-normals.csv', index=False)
    df_normal_csv = df_normal_csv.to_csv(index=False)
    df_normal_csv_r = pd.read_csv(io.StringIO(df_normal_csv))  # .round(decimals=2)
    # Query the sdev
    qsdev = g.query(
        '''
    SELECT ?event ?month ?variable ?value
    WHERE {
        ?slice a qb:Slice ;
               serdif-dimension:event ?eventU ;
               serdif-dimension:measureType <https://serdif.adaptcentre.ie/kg/2022/measureType#sdev> ;
               qb:observation ?obs .
        ?obs a qb:Observation, time:GeneralDateTimeDescription ;
            qb:dataSet ?dataset ;
            time:monthOfYear ?monthU ;
            ?variableU ?value
        FILTER(datatype(?value) = xsd:float)
        # Format output to be more human friendly: uri -> simplified string
        BIND(STRAFTER(STR(?eventU), "#") AS ?event)
        BIND(STRAFTER(STR(?monthU), "gregorian/") AS ?month)
        BIND(STRBEFORE(STRAFTER(STR(?variableU), "has"),"Sdev") AS ?variable)
    }
    ORDER BY ?event ?month ?variable
        '''
    )
    df_sdev = pd.DataFrame(qsdev, columns=qsdev.vars)
    # Format column names from rdf variable format to string
    df_sdev.columns = [str(col) for col in df_sdev.columns.tolist()]
    # Pivot variable column from long to wide as preferred by the researchers
    df_sdev_csv = df_sdev.pivot(
        index=['event', 'month'],
        columns='variable', values='value').reset_index()
    df_sdev_csv.columns = [str(col).replace('Value', '') for col in df_sdev_csv.columns.tolist()]
    df_sdev_csv.index.names = ['index']
    df_sdev_csv.to_csv(outfolder + '/linked-ee-dataset-v20220524-QT_' + queryTime + '-sdev.csv', index=False)
    df_sdev_csv = df_sdev_csv.to_csv(index=False)
    df_sdev_csv_r = pd.read_csv(io.StringIO(df_sdev_csv))  # .round(decimals=2)

    ###############################################
    ###  Event-Environmental linked metadata    ###
    ###############################################

    # Load environment for jinja2 templates
    file_loader = FileSystemLoader('templates')
    env = Environment(loader=file_loader)
    # 1. Generate mapping file from template
    # Load eea template file
    metaMap = env.get_template('serdif-metadata-template.ttl')

    # Edit evEnvoDict input
    dd = defaultdict(list)

    for k in evEnvoDict.keys():
        tt = evEnvoDict[k]
        for key, val in tt.items():
            dd[key].append(val)

    evEnvoDict_e = dict(dd)

    # Dictionaries to translate timeUnit to query SPARQL query parameters
    selTimeUnit = {'hour': 'HOURS',
                   'day': 'DAYS',
                   'month': 'MONTHS',
                   'year': 'YEARS',
                   }
    selTimeRes = {'hour': 'PT1H',
                  'day': 'P1D',
                  'month': 'P1M',
                  'year': 'P1Y',
                  }

    # Environmental variables available in the data
    eeVars = df_qr_csv_r.columns.tolist()[3:]

    qEnvInfo = requests.post(
        endpoint,
        data={'query': '''              
    PREFIX owl: <http://www.w3.org/2002/07/owl#>
    PREFIX qb: <http://purl.org/linked-data/cube#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX unit: <http://qudt.org/vocab/unit/>
    PREFIX serdif-measure: <https://serdif.adaptcentre.ie/kg/2022/measure#>
    SELECT ?envoVar ?label ?name ?abb (GROUP_CONCAT(?infoS;separator=", ") AS ?infoG)
    WHERE { 
        VALUES ?envoVar {''' + ' '.join(['serdif-measure:has' + eeVar + 'Value' for eeVar in eeVars]) + '''}
        ?envoVar a owl:DatatypeProperty , qb:MeasureProperty ; 
                 rdfs:label ?label ;
                 rdfs:comment ?name ;
                 unit:abbreviation ?abb ;
                 rdfs:seeAlso ?info ;
        .
        BIND(CONCAT("<",STR(?info),">") AS ?infoS)
    }
    GROUP BY ?envoVar ?label ?name ?abb
    '''
              },
        headers={'Accept': 'application/sparql-results+json'}
    ).text
    # 1.4.Return results
    jEnvInfo = json.loads(qEnvInfo)['results']['bindings']
    rEnvInfo_envIRI = ['serdif:has' + envI['envoVar']['value'].split('#has')[1] for envI in jEnvInfo]
    rEnvInfo_label = [envI['envoVar']['value'].split('#has')[1] for envI in jEnvInfo]
    rEnvInfo_name = [envI['name']['value'] for envI in jEnvInfo]
    rEnvInfo_abb = ['<' + envI['abb']['value'] + '>' for envI in jEnvInfo]
    rEnvInfo_info = [envI['infoG']['value'] for envI in jEnvInfo]

    # External data sets used to construct the query
    extDataUsed = ['<' + envDS + '>' for envDS in set(flatten(evEnvoDict_e['datasets-used']))]
    # datasets per event
    dsUsedEvent = [', '.join(dsL).replace(', ', '>, <') for dsL in evEnvoDict_e['datasets-used']]
    # Build metadata template dictionary
    if metadataType == 'recommended':
        metaMap_dict = {
            'version': '20220524',
            'queryTime': queryTime,
            'queryDateTime': queryTimeStr.replace(' ', 'T') + 'Z',
            'timeUnit': selTimeUnit[timeUnit_sel],
            'aggMethod': aggMethod_sel,
            'timeRes': selTimeRes[timeUnit_sel],
            'startDateTime': '2011-01-01T00:00:00Z',
            'endDateTime': '2021-01-01T00:00:00Z',
            'eeVars': rEnvInfo_label,
            'eeVarsD': zip(*[rEnvInfo_name, rEnvInfo_envIRI, rEnvInfo_label,
                             rEnvInfo_abb, rEnvInfo_info]),
            # From metadata csv
            'context': selectValueKey(df=evEnvoMetaDf, keyN='eventName'),
            'publisher': ', '.join(strToIri(selectValueKeyL(df=evEnvoMetaDf, keyN='publisher'))),
            'publisherL': strToIri(selectValueKeyL(df=evEnvoMetaDf, keyN='publisher')),
            'license': selectValueKey(df=evEnvoMetaDf, keyN='license'),
            'dataController': ', '.join(strToIri(selectValueKeyL(df=evEnvoMetaDf, keyN='dataController'))),
            'orcid': ', '.join(strToIri(selectValueKeyL(df=evEnvoMetaDf, keyN='dataProcessor'))),
            'orcidL': strToIri(selectValueKeyL(df=evEnvoMetaDf, keyN='dataProcessor')),
            # -- Data Subject -------------------------------------------------------
            'DataSubjectLabel': selectValueKey(df=evEnvoMetaDf, keyN='dataSubjectLabel'),
            'DataSubjectComment': selectValueKey(df=evEnvoMetaDf, keyN='dataSubjectComment'),
            'DataSubjectUrl': selectValueKey(df=evEnvoMetaDf, keyN='dataSubjectUrl'),
            # -- Legal Basis --------------------------------------------------------
            'LegalBasisLabel': selectValueKey(df=evEnvoMetaDf, keyN='legalBasisLabel'),
            'LegalBasisComment': selectValueKey(df=evEnvoMetaDf, keyN='legalBasisComment'),
            'LegalBasisUrl': selectValueKey(df=evEnvoMetaDf, keyN='legalBasisUrl'),
            # -- Personal Data Category ---------------------------------------------
            'PersonalDataCategoryComment': selectValueKey(df=evEnvoMetaDf, keyN='personalDataCategoryComment'),
            'PersonalDataCategoryUrl': selectValueKey(df=evEnvoMetaDf, keyN='personalDataCategoryUrl'),
            # -- ProcessingPurpose --------------------------------------------------
            'ProcessingPurposeComment': selectValueKey(df=evEnvoMetaDf, keyN='processingPurposeComment'),
            'ProcessingPurposeUrl': selectValueKey(df=evEnvoMetaDf, keyN='processingPurposeUrl'),
            # -- Right --------------------------------------------------------------
            'RightClass': ', '.join(selectValueKeyL(df=evEnvoMetaDf, keyN='rightClass')),
            'RightComment': selectValueKey(df=evEnvoMetaDf, keyN='rightComment'),
            'RightUrl': selectValueKey(df=evEnvoMetaDf, keyN='rightUrl'),
            # -- Identification Risk ------------------------------------------------
            'IdentificationRiskComment': selectValueKey(df=evEnvoMetaDf, keyN='identificationRiskComment'),
            # -- Data Set Storage ---------------------------------------------------
            'DataSetStorageStorage': selectValueKey(df=evEnvoMetaDf, keyN='dataSetStorageStorage'),
            'DataSetStorageLocation': selectValueKey(df=evEnvoMetaDf, keyN='dataSetStorageLocation'),
            'DataSetStorageDuration': selectValueKey(df=evEnvoMetaDf, keyN='dataSetStorageDuration'),
            'DataSetStorageComment': selectValueKey(df=evEnvoMetaDf, keyN='dataSetStorageComment'),
            # -- Health Data Access Control -----------------------------------------
            'HealthDataAccessControlComment': selectValueKey(df=evEnvoMetaDf, keyN='healthDataAccessControlComment'),
            # -- Health Data Pseudonymisation ---------------------------------------
            'HealthDataPseudonymisationComment': selectValueKey(df=evEnvoMetaDf,
                                                                keyN='healthDataPseudonymisationComment'),
            # -- DPIA ---------------------------------------------------------------
            'dpiaComment': selectValueKey(df=evEnvoMetaDf, keyN='dpiaComment'),
            'dpiaUrl': selectValueKey(df=evEnvoMetaDf, keyN='dpiaUrl'),
            # -- Health Data Access Control -----------------------------------------
            'HealthDataAuthorisationComment': selectValueKey(df=evEnvoMetaDf, keyN='healthDataAuthorisationComment'),
            # -- Certification ------------------------------------------------------
            'CertificationComment': selectValueKey(df=evEnvoMetaDf, keyN='certificationComment'),
            # -- Consultation -------------------------------------------------------
            'ConsultationComment': selectValueKey(df=evEnvoMetaDf, keyN='consultationComment'),
            # -- Research Contract --------------------------------------------------
            'ResearchContractDuration': selectValueKey(df=evEnvoMetaDf, keyN='researchContractDuration'),
            'ResearchContractComment': selectValueKey(df=evEnvoMetaDf, keyN='researchContractComment'),
            # -- Research Code Of Conduct -------------------------------------------
            'ResearchCodeOfConductComment': selectValueKey(df=evEnvoMetaDf, keyN='researchCodeOfConductComment'),
            # -- Privacy Notice Comment ---------------------------------------------
            'PrivacyNoticeComment': selectValueKey(df=evEnvoMetaDf, keyN='privacyNoticeComment'),
            # -- Data Policy --------------------------------------------------------
            'DataPolicyComment': selectValueKey(df=evEnvoMetaDf, keyN='dataPolicyComment'),
            # -- Research Risk Management Procedure ---------------------------------
            'ResearchRiskManagementProcedureComment': selectValueKey(df=evEnvoMetaDf,
                                                                     keyN='researchRiskManagementProcedureComment'),
            # -- Research Safeguard -------------------------------------------------
            'ResearchSafeguardComment': selectValueKey(df=evEnvoMetaDf, keyN='researchSafeguardComment'),
            # -- Data Use --------------------------------------------------------
            'DataUseClass': ', '.join(selectValueKeyL(df=evEnvoMetaDf, keyN='dataUseClass')),
            'DataUseComment': selectValueKey(df=evEnvoMetaDf, keyN='dataUseComment'),
            # Extra for open ready
            'extDataSetsUsed': ', '.join(set(extDataUsed)),
            'fileSize': os.path.getsize(outfolder + '/linked-ee-dataset-v20220524-QT_' + queryTime + '.ttl'),
            # -- Event Description -----------------------------------------------
            'eventDict': zip(*[
                evEnvoDict_e['evName'], evEnvoDict_e['evDatetime'], evEnvoDict_e['point'],
                evEnvoDict_e['dateStart'], evEnvoDict_e['dateLag'], evEnvoDict_e['evArea'],
                evEnvoDict_e['evAreaName'], evEnvoDict_e['queryLoc'], evEnvoDict_e['qTimeWindow'],
                evEnvoDict_e['queryEvArea'], dsUsedEvent,
            ]),
            'eventNameList': evEnvoDict_e['evName'],
            'dsgeo': ', '.join(['"' + geo + '"^^geo:wktLiteral' for geo in evEnvoDict_e['evArea']]),
            'eeVarsIRI': rEnvInfo_envIRI,
            'queryTextV': qr_ee_graph_value['queryBody'],
            'queryTextN': qr_ee_graph_normal['queryBody'],
            'queryTextSdev': qr_ee_graph_sdev['queryBody'],
        }
    elif metadataType == 'minimum':
        metaMap_dict = {
            'version': '20220524',
            'queryTime': queryTime,
            'queryDateTime': queryTimeStr.replace(' ', 'T') + 'Z',
            'timeUnit': selTimeUnit[timeUnit_sel],
            'aggMethod': aggMethod_sel,
            'timeRes': selTimeRes[timeUnit_sel],
            'startDateTime': '2011-01-01T00:00:00Z',
            'endDateTime': '2021-01-01T00:00:00Z',
            'eeVars': rEnvInfo_label,
            'eeVarsD': zip(*[rEnvInfo_name, rEnvInfo_envIRI, rEnvInfo_label,
                             rEnvInfo_abb, rEnvInfo_info]),
            # From metadata csv
            'context': selectValueKey(df=evEnvoMetaDf, keyN='eventName'),
            'publisher': ', '.join(strToIri(selectValueKeyL(df=evEnvoMetaDf, keyN='publisher'))),
            'publisherL': strToIri(selectValueKeyL(df=evEnvoMetaDf, keyN='publisher')),
            'license': selectValueKey(df=evEnvoMetaDf, keyN='license'),
            'dataController': ', '.join(strToIri(selectValueKeyL(df=evEnvoMetaDf, keyN='dataController'))),
            'orcid': ', '.join(strToIri(selectValueKeyL(df=evEnvoMetaDf, keyN='dataProcessor'))),
            'orcidL': strToIri(selectValueKeyL(df=evEnvoMetaDf, keyN='dataProcessor')),
            # -- Right --------------------------------------------------------------
            'RightClass': 'dpv-gdpr:A15',
            # 'RightComment': selectValueKey(df=evEnvoMetaDf, keyN='rightComment'),
            # 'RightUrl': selectValueKey(df=evEnvoMetaDf, keyN='rightUrl'),
            # -- Identification Risk ------------------------------------------------
            'IdentificationRiskComment': 'The dataset is considered pseudonymised since effective anonymisation was '
                                         'not possible without losing value of the data for research. Identification '
                                         'risks: (1) singling out of individual subjects, (2) linking of records or '
                                         'matching of data between data sets, and (3) inference of any information '
                                         'about individuals from the data set. (1) Individual patient dates are used '
                                         'to associate environmental data; which in a hospital context the hospital, '
                                         'the individuals could be identified due to the rare disease condition of '
                                         'the patients. (2) Individual patient dates could be linked to hospital '
                                         'attendance registries in the area, public registries, social media data and '
                                         'other sources. (3) The rare condition of the patients, the pseudonymised '
                                         'category of the data together with the location and time expressed in the '
                                         'environmental data could potentially lead to inferring a link even though '
                                         'the information is not expressly linked.',
            # -- Data Use --------------------------------------------------------
            'DataUseClass': 'obo:DUO_0000012, obo:DUO_0000007, obo:DUO_0000046',
            # 'DataUseComment': selectValueKey(df=evEnvoMetaDf, keyN='dataUseComment'),
            # Extra for open ready
            'extDataSetsUsed': ', '.join(set(extDataUsed)),
            'fileSize': os.path.getsize(outfolder + '/linked-ee-dataset-v20220524-QT_' + queryTime + '.ttl'),
            # -- Event Description -----------------------------------------------
            'eventDict': zip(*[
                evEnvoDict_e['evName'], evEnvoDict_e['evDatetime'], evEnvoDict_e['point'],
                evEnvoDict_e['dateStart'], evEnvoDict_e['dateLag'], evEnvoDict_e['evArea'],
                evEnvoDict_e['evAreaName'], evEnvoDict_e['queryLoc'], evEnvoDict_e['qTimeWindow'],
                evEnvoDict_e['queryEvArea'], dsUsedEvent,
            ]),
            'eventNameList': evEnvoDict_e['evName'],
            'dsgeo': ', '.join(['"' + geo + '"^^geo:wktLiteral' for geo in evEnvoDict_e['evArea']]),
            'eeVarsIRI': rEnvInfo_envIRI,
            'queryTextV': qr_ee_graph_value['queryBody'],
            'queryTextN': qr_ee_graph_normal['queryBody'],
            'queryTextSdev': qr_ee_graph_sdev['queryBody'],
        }
    outMap = metaMap.stream(data=metaMap_dict)
    # Export resulting mapping
    outMap.dump(outfolder + '/linked-ee-metadata-v20220524-QT_' + queryTime + '.ttl')

    ###############################################
    ###  Event-Environmental linked html report ###
    ###############################################

    # Add month column to align the data with the normals and sdev
    df_qr_csv_r['dateT'] = pd.to_datetime(df_qr_csv_r['date'])
    df_qr_csv_r['month'] = df_qr_csv_r['dateT'].dt.month_name()

    # Compute z-score dataset
    df_z = df_qr_csv_r.set_index(['event', 'month'])[df_qr_csv_r.select_dtypes('number').columns]. \
        subtract(df_normal_csv_r.set_index(['event', 'month'])[df_normal_csv_r.select_dtypes('number').columns],
                 fill_value=np.nan). \
        div(df_sdev_csv_r.set_index(['event', 'month'])[df_sdev_csv_r.select_dtypes('number').columns],
            fill_value=np.nan). \
        reset_index().round(2)

    df_z.insert(loc=1, column='date', value=df_qr_csv_r['date'])
    df_z.drop(columns=['lag', 'month'], axis=1, inplace=True)
    df_z.insert(loc=2, column='lag', value=df_qr_csv_r['lag'])
    df_z = df_z.sort_values(by=['event', 'lag'])
    df_qr_csv_r.drop(columns=['dateT', 'month'], axis=1, inplace=True)

    # Data values pandas dataframe to html table
    html_table = df_qr_csv_r.to_html(
        classes='sortable text-center table-bordered table-striped table-hover table-responsive table-sm',
        na_rep='', justify='center', table_id='sortTable',
    ).replace('<tbody>', '<tbody id="myTable">')

    # .replace('</th>',' <i class="fa fa-fw fa-info-circle"></i></th>')

    # Z-score pandas dataframe to html table
    html_table_z = df_z.to_html(na_rep='')

    # Parse html to enable tag selection
    soup_v = BeautifulSoup(html_table, 'html.parser')
    soup_z = BeautifulSoup(html_table_z, 'html.parser')

    df_num = list(range(len(eeVars)))[3:]
    # Add background color to cells with a z-score higher than +2 (red) and lower than -2 (blue).
    for row_v, row_z in zip(soup_v.select('tbody tr'), soup_z.select('tbody tr')):
        tds_v = row_v.find_all('td')
        tds_z = row_z.find_all('td')
        for i in df_num:
            if tds_z[i].text:
                if float(tds_z[i].text) < -2:
                    tds_v[i]['class'] = 'table-primary'
                if float(tds_z[i].text) > 2:
                    tds_v[i]['class'] = 'table-danger'

    # Add tooltip to column headers
    table_header = ['row_id', 'event ID', 'event date', 'time between the data and the event [days]'] + rEnvInfo_name

    for h in soup_v.select('thead'):
        for num, th in enumerate(h.find_all('th')):
            th['title'] = table_header[num]

    # Environmental variables links
    envVarInfo = {label.replace('Value', ''): {'name': name, 'info': info.replace('<', '').replace('>', '')} for
                  label, name, info in zip(*[rEnvInfo_label, rEnvInfo_name, rEnvInfo_info])}

    # Weather variables are constant across the dataset so it is save to remove from the total environmental variables available
    wVars = ['MaximumTemperature', 'MeanTemperature', 'MinimumTemperature',
             'PrecipitationAmount', 'RelativeHumidity', 'SeaLevelPressure',
             'SolarRadiation', 'WindSpeed']
    apVars = list(set(eeVars) - set(wVars))
    wVarsLinks = ', '.join(
        [
            '<a href="' + 'https://cds.climate.copernicus.eu/cdsapp#!/dataset/10.24381/cds.151d3ec6' + '" target="_blank">' +
            envVarInfo[i]['name'] + '</a>' for i in wVars])
    apVarsLinks = ', '.join(
        ['<a href="' + envVarInfo[i]['info'] + '" target="_blank">' + envVarInfo[i]['name'] + '</a>' for i in apVars])

    df_mean = df_qr_csv_r.groupby(['lag'])[eeVars].mean().reset_index()

    # Plot colors
    # colorsL = px.colors.qualitative.Plotly*10
    cMap = plt.cm.get_cmap('jet', lut=len(eeVars))
    cMap._init()
    # tt = list(set([cMap(a) for a in np.linspace(0,1,1000)]))
    # colorsL = list(set([matplotlib.colors.rgb2hex(x) for x in cMap._lut]))
    colorsL = ['#000000', '#AFAEAE', '#648fff', '#785ef0', '#dc267f', '#fe6100', '#ffb000'] * 4
    fig_apw = make_subplots(specs=[[{'secondary_y': True}]])
    # Add traces
    fig_apw.add_trace(
        go.Heatmap(
            z=df_mean['WindSpeed'].tolist(),
            y=np.linspace(1, 1, 21),
            x=df_mean['lag'].tolist(),
            colorscale='blues',
            opacity=0.3,
            colorbar={'title': 'Wind speed [m/s]',
                      'orientation': 'v',
                      'titleside': 'right',
                      'xanchor': 'center'},
            hovertemplate='%{z}',
            name='WindSpeed',
            # zmin=0
        ),
        secondary_y=True,

    )

    for i, aqv in enumerate(apVars):
        fig_apw.add_trace(
            go.Scatter(x=df_mean['lag'], y=df_mean[aqv], name=aqv,
                       marker=dict(color=colorsL[i]),
                       # legendgroup='meanValues', legendgrouptitle=dict(text='<b>Mean values</b>')
                       ),
            secondary_y=False,
        )

    for i, aqv in enumerate(apVars):
        fig_apw.add_trace(
            go.Box(x=df_qr_csv_r['lag'], y=df_qr_csv_r[aqv], name=aqv, visible='legendonly',
                   marker=dict(color=colorsL[i]),
                   # legendgroup='boxPlots', legendgrouptitle=dict(text='<b>Sample variability</b>')
                   ),
            secondary_y=False,
        )

    fig_apw.layout.xaxis.title = 'Lag [days]'
    fig_apw.layout.yaxis.title = 'Concentration [ug/m3]'
    fig_apw.layout.yaxis2.title = ''
    fig_apw.layout.yaxis2.visible = False

    # Menu to update the background weather variable
    # Define buttons to select variables while respecting the groups (events)
    buttons_bgw = []
    for wvar in wVars:
        fig_dict_ev = {
            'label': f'Background - {wvar}',
            'method': 'restyle',
            # 'visible': True,
            'args': [
                # 1. updates to the traces
                {
                    'y': [np.linspace(1, 1, 21)],
                    'x': [df_mean['lag'].tolist()],
                    'z': [df_mean[wvar].tolist()],
                    'colorbar': {
                        'title': {'text': envVarInfo[wvar]['name'],
                                  'side': 'right'},
                        'orientation': 'v',
                        'xanchor': 'center'
                    },
                    'name': wvar,
                },
                # 3. which traces are affected
                [0],
            ]
        }

        buttons_bgw.append(fig_dict_ev)

    # Define buttons to convert scatter plots to box plots
    fig_apw.update_layout(showlegend=True, )
    fig_apw.update_layout(
        font=dict(size=20),
        plot_bgcolor='rgba(0,0,0,0)',
        height=600,
        # boxmode='group',
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=-0.55,
            xanchor='left',
            x=-0.1,
            # groupclick='toggleitem'

        ),
        hovermode='x unified',
        updatemenus=[
            {
                'buttons': buttons_bgw,
                'y': 1.12,
                'x': 0.3,
            },
        ],
        margin={'l': 5, 'r': 5, 't': 1, 'b': 0},
    )
    fig_apw.update_xaxes(showline=True, linewidth=1.5, autorange='reversed',
                         linecolor='black', mirror=True, ticks='outside')
    fig_apw.update_yaxes(showline=True, linewidth=1.5,
                         linecolor='black', mirror=True, ticks='outside')

    # Z-score figure
    df_mean_z = df_z.groupby(['lag'])[eeVars].mean().reset_index()
    zMaxAbs = max(df_mean_z[eeVars].abs().max()) + 0.2

    fig_z = make_subplots(specs=[[{'secondary_y': True}]])
    # Add traces
    fig_z.add_trace(
        go.Heatmap(
            z=df_mean_z['WindSpeed'].tolist(),
            y=np.linspace(1, 1, 21),
            x=df_mean_z['lag'].tolist(),
            colorscale='RdBu',
            reversescale=True,
            opacity=0.3,
            colorbar={'title': 'Wind speed [sdev]',
                      'orientation': 'v',
                      'titleside': 'right',
                      'xanchor': 'center'},
            hovertemplate='%{z}',
            name='WindSpeed',
            zmin=-zMaxAbs,
            zmax=zMaxAbs,
        ),
        secondary_y=True,

    )

    for i, aqv in enumerate(apVars):
        fig_z.add_trace(
            go.Scatter(x=df_mean_z['lag'], y=df_mean_z[aqv], name=aqv,
                       marker=dict(color=colorsL[i]),
                       # legendgroup='meanValues', legendgrouptitle=dict(text='<b>Mean values</b>')
                       ),
            secondary_y=False,
        )

    for i, aqv in enumerate(apVars):
        fig_z.add_trace(
            go.Box(x=df_z['lag'], y=df_z[aqv], name=aqv, visible='legendonly',
                   marker=dict(color=colorsL[i]),
                   # legendgroup='boxPlots', legendgrouptitle=dict(text='<b>Sample variability</b>')
                   ),
            secondary_y=False,
        )

    fig_z.layout.xaxis.title = 'Lag [days]'
    fig_z.layout.yaxis.title = 'z-score [sdev]'
    fig_z.layout.yaxis.range = [-zMaxAbs, zMaxAbs]
    fig_z.layout.yaxis2.title = ''
    fig_z.layout.yaxis2.visible = False
    # fig_z.layout.yaxis2.range = [-zMaxAbs,zMaxAbs]
    fig_z.add_hline(y=2, line_dash='dash', line_color='#a93226')
    fig_z.add_hline(y=-2, line_dash='dash', line_color='#03a9f4')

    # Menu to update the background weather variable
    # Define buttons to select variables while respecting the groups (events)
    buttons_bgw_z = []
    for wvar in wVars:
        fig_dict_ev = {
            'label': f'Background - {wvar}',
            'method': 'restyle',
            # 'visible': True,
            'args': [
                # 1. updates to the traces
                {
                    'y': [np.linspace(1, 1, 21)],
                    'x': [df_mean_z['lag'].tolist()],
                    'z': [df_mean_z[wvar].tolist()],
                    'colorbar': {
                        'title': {'text': wvar + ' [sdev]',
                                  'side': 'right'},
                        'orientation': 'v',
                        'xanchor': 'center'
                    },
                    'name': wvar,
                },
                # 3. which traces are affected
                [0],
            ]
        }

        buttons_bgw_z.append(fig_dict_ev)

    # Define buttons to convert scatter plots to box plots
    fig_z.update_layout(showlegend=True, )
    fig_z.update_layout(
        font=dict(size=20),
        plot_bgcolor='rgba(0,0,0,0)',
        height=600,
        # boxmode='group',
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=-0.55,
            xanchor='left',
            x=-0.1,
            # groupclick='toggleitem'

        ),
        hovermode='x unified',
        updatemenus=[
            {
                'buttons': buttons_bgw_z,
                'y': 1.12,
                'x': 0.3,
            },
        ],
        margin={'l': 5, 'r': 5, 't': 1, 'b': 0},
    )

    fig_z.update_xaxes(showline=True, linewidth=1.5, autorange='reversed',
                       linecolor='black', mirror=True, ticks='outside')
    fig_z.update_yaxes(showline=True, linewidth=1.5,
                       linecolor='black', mirror=True, ticks='outside')

    # Load environment for jinja2 templates
    file_loader = FileSystemLoader('templates')
    env = Environment(loader=file_loader)
    # 1. Generate mapping file from template
    # Load eea template file
    metaMap = env.get_template('serdif-report-templates.html')

    # Generate individual figures for each event
    evFigList = []
    for ev in df['evName']:
        # event plots
        fig_apw_evA = make_subplots(specs=[[{'secondary_y': True}]])
        # Add traces
        df_evA = df_qr_csv_r.loc[df_qr_csv_r['event'] == ev]
        fig_apw_evA.add_trace(
            go.Heatmap(
                z=df_evA['WindSpeed'].tolist(),
                y=np.linspace(1, 1, 21),  # what does 21 mean?
                x=df_evA['lag'].tolist(),
                colorscale='blues',
                opacity=0.3,
                colorbar={'title': 'Wind speed [m/s]',
                          'orientation': 'v',
                          'titleside': 'right',
                          'xanchor': 'center'},
                hovertemplate='%{z}',
                name='WindSpeed',
                # zmin=0
            ),
            secondary_y=True,

        )

        for i, aqv in enumerate(apVars):
            fig_apw_evA.add_trace(
                go.Scatter(x=df_evA['lag'], y=df_evA[aqv], name=aqv, marker=dict(color=colorsL[i]), ),
                secondary_y=False,
            )

        fig_apw_evA.layout.xaxis.title = 'Lag [days]'
        fig_apw_evA.layout.yaxis.title = 'Concentration [ug/m3]'
        fig_apw_evA.layout.yaxis2.title = ''
        fig_apw_evA.layout.yaxis2.visible = False

        # Define buttons to select variables while respecting the groups (events)
        buttons_bgw = []
        for wvar in wVars:
            fig_dict_ev = {
                'label': f'Background - {wvar}',
                'method': 'restyle',
                # 'visible': True,
                'args': [
                    # 1. updates to the traces
                    {
                        'y': [np.linspace(1, 1, 21)],
                        'x': [df_evA['lag'].tolist()],
                        'z': [df_evA[wvar].tolist()],
                        'colorbar': {
                            'title': {'text': envVarInfo[wvar]['name'],
                                      'side': 'right'},
                            'orientation': 'v',
                            'xanchor': 'center'
                        },
                        'name': wvar,
                    },
                    # 3. which traces are affected
                    [0],
                ]
            }

            buttons_bgw.append(fig_dict_ev)

        # Define buttons to convert scatter plots to box plots
        fig_apw_evA.update_layout(showlegend=True, )
        fig_apw_evA.update_layout(
            font=dict(size=20),
            plot_bgcolor='rgba(0,0,0,0)',
            height=600,
            width=1000,
            # boxmode='group',
            legend=dict(
                orientation='h',
                yanchor='bottom',
                y=-0.5,
                xanchor='left',
                x=-0.1,
                # groupclick='toggleitem'

            ),
            hovermode='x unified',
            updatemenus=[
                {
                    'buttons': buttons_bgw,
                    'y': 1.15,
                    'x': 0.3,
                },
            ],
            margin={'l': 5, 'r': 5, 't': 1, 'b': 0},
        )
        fig_apw_evA.update_xaxes(showline=True, linewidth=1.5, autorange='reversed',
                                 linecolor='black', mirror=True, ticks='outside')
        fig_apw_evA.update_yaxes(showline=True, linewidth=1.5,
                                 linecolor='black', mirror=True, ticks='outside')

        evFigList.append(fig_apw_evA.to_html(full_html=False, include_plotlyjs='cdn'))

    # Build dictionary for html template
    htmldata_dict = {
        'date': datetime.strftime(datetime.now(), '%b %-d, %Y'),
        'eventTable': df_input_html,
        'dataTable': soup_v,
        'overviewFigure': fig_apw.to_html(full_html=False, include_plotlyjs='cdn'),
        'zscoreFigure': fig_z.to_html(full_html=False, include_plotlyjs='cdn'),
        'datasetmap': fig_map.to_html(full_html=False, include_plotlyjs='cdn'),
        'timeline': fig_timeline.to_html(full_html=False, include_plotlyjs='cdn'),
        'weatherLinks': wVarsLinks,
        'pollutionLinks': apVarsLinks,
        'context': selectValueKey(df=evEnvoMetaDf, keyN='eventName'),
        'timeUnit': selTimeUnit[timeUnit_sel],
        'aggMethod': aggMethod_sel,
        'version': '20220524',
        'queryDateTime': queryTimeStr.replace(' ', 'T') + 'Z',
        'publisher': ', '.join(['<a href="' + p + '" target="_blank">' + p + '</a>' for p in
                                selectValueKeyL(df=evEnvoMetaDf, keyN='publisher')]),
        'dataController': ', '.join(['<a href="' + p + '" target="_blank">' + p + '</a>' for p in
                                     selectValueKeyL(df=evEnvoMetaDf, keyN='dataController')]),
        'orcid': ', '.join(
            ['<a href="' + p + '" target="_blank">' + p + '</a>' for p in
             selectValueKeyL(df=evEnvoMetaDf, keyN='dataProcessor')]),
        'eventNameList': df['evName'],
        'eventFigures': zip(df['evName'], evFigList),
        'areaText': spatialLink_sel['text'],
        'spOption1': spatialLink_sel['spatial'],
        'spOption2': spatialLink_sel['qOpt'],
    }
    outMap = metaMap.stream(data=htmldata_dict)
    # Export resulting mapping
    outMap.dump(outfolder + '/linked-ee-report-v20220524-QT_' + queryTime + '.html')
    # Zip output folder to send
    shutil.make_archive('linked-ee-pack-v20220524-QT_' + queryTime, 'zip', outfolder)
    queryLogLine = 'Query: ' + queryTimeStr + '\tLinking time: ' + str(datetime.now() - startTime) + '\n'
    print(queryLogLine)
    with open('queryLog.txt', 'a') as file:
        file.write(queryLogLine)
    # Remove folder after sending the zip file
    if os.path.exists(outfolder):
        shutil.rmtree(outfolder, ignore_errors=True)
    #
    call(['find . -maxdepth 1 -name "*.zip" -type f -mtime +1 -exec rm -f {} +',], shell=True)

    return './linked-ee-pack-v20220524-QT_' + queryTime + '.zip'
