from SPARQLWrapper import SPARQLWrapper


def serdifSamplers(endpointURL, repoID):
    bodySamplers = '''
    PREFIX sosa: <http://www.w3.org/ns/sosa/>
    PREFIX geo: <http://www.opengis.net/ont/geosparql#>
    PREFIX geof: <http://www.opengis.net/def/function/geosparql/>
    PREFIX osi: <http://ontologies.geohive.ie/osi#>
    PREFIX serdif: <http://serdif.org/kg/datasource/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?LOI (COUNT(?sampler) AS ?samplerCount)
    WHERE{
        ?sampler a sosa:Sampler;
                 geo:hasGeometry ?splPointG.
        ?splPointG geo:asWKT ?splGeom.
        {
            SELECT ?cogeom ?LOI
            WHERE {
                #County geom
                ?county a osi:County, geo:Feature;
                        rdfs:label ?LOI;
                        geo:hasGeometry ?cogeomb.
                ?cogeomb a geo:Geometry;
                         geo:asWKT ?cogeom.
                FILTER (lang(?LOI) = 'en')
        
            }
        }
        FILTER(geof:sfWithin(?splGeom, ?cogeom))
    }
    GROUP BY ?LOI
    '''
    # 1.2.Query parameters
    SPARQLQuery = SPARQLWrapper(endpointURL + repoID)
    SPARQLQuery.setMethod('POST')
    SPARQLQuery.setQuery(bodySamplers)
    SPARQLQuery.setReturnFormat('json')
    # 1.3.Fire query and convert results to json (dictionary)
    qSamplers = SPARQLQuery.query().convert()
    # 1.4.Return results
    jSamplers = qSamplers['results']['bindings']
    tSamplers = {
        'LOI': [LocEv['LOI']['value'] for LocEv in jSamplers],
        'smp_Count': [eventD['samplerCount']['value'] for eventD in jSamplers]
    }
    return tSamplers


def serdifEOIdates(endpointURL, repoID, QPrefixes, eoiVal):
    # 1.Query to get all distinct RKD IDs
    # 1.1.Query body
    bodyLocEv = '''
    SELECT ?LOI (COUNT(?event) AS ?eoiCount)
    WHERE{
         GRAPH <http://serdif.org/kg/datasource/event> {
            ?event a event:Event;
                   event:place ?evgeomB;
                   event:sub_event ?evCat.
            ?evgeomB geo:asWKT ?evgeom.
            ''' + ' UNION '.join(['{ ?event event:sub_event <' + eoi + '> } ' for eoi in eoiVal]) + '''      
        }
    
        GRAPH <http://serdif.org/kg/datasource/GeohiveData> {  
            #County geom     
            ?county a osi:County, geo:Feature;
                    rdfs:label ?LOI;
                    geo:hasGeometry ?cogeomb.
            ?cogeomb a geo:Geometry;
                     geo:asWKT ?cogeom.
        }
        FILTER(geof:sfWithin(?evgeom, ?cogeom))
        FILTER (lang(?LOI) = 'en')
    }
    GROUP BY ?LOI
    ORDER BY ?LOI
    '''

    # 1.2.Query parameters
    SPARQLQuery = SPARQLWrapper(endpointURL + repoID)
    SPARQLQuery.setMethod('POST')
    SPARQLQuery.setQuery(QPrefixes + bodyLocEv)
    SPARQLQuery.setReturnFormat('json')
    # 1.3.Fire query and convert results to json (dictionary)
    qLocEv = SPARQLQuery.query().convert()
    # 1.4.Return results
    jLocEv = qLocEv['results']['bindings']
    tLocEv = {
        'LOI': [LocEv['LOI']['value'] for LocEv in jLocEv],
        'EOI_Count': [eventD['eoiCount']['value'] for eventD in jLocEv]
    }
    return tLocEv


def serdif_LOIs(endpointURL, repoID, QPrefixes):
    # 1.Query to get all distinct RKD IDs
    # 1.1.Query body
    bodyLOI = '''SELECT ?countyName
    WHERE{
    GRAPH <http://serdif.org/kg/datasource/GeohiveData> {  
    #County geom     
            ?county a osi:County, geo:Feature;
                    rdfs:label ?countyName;
                    geo:hasGeometry ?cogeomb.
            ?cogeomb a geo:Geometry;
                     geo:asWKT ?cogeom.
        }
        FILTER (lang(?countyName) = 'en')
    }  
    ORDER BY ASC(?countyName)
    '''

    # 1.2.Query parameters
    SPARQLQuery = SPARQLWrapper(endpointURL + repoID)
    SPARQLQuery.setMethod('POST')
    SPARQLQuery.setQuery(QPrefixes + bodyLOI)
    SPARQLQuery.setReturnFormat('json')
    # 1.3.Fire query and convert results to json (dictionary)
    qLOI = SPARQLQuery.query().convert()
    # 1.4.Return results
    jLOI = qLOI['results']['bindings']
    tLOI = [LOI['countyName']['value'] for LOI in jLOI]
    return tLOI


# Data sources Named Graphs and variables
envDataSoDict = {
    'weather':
        {'namedGraph': 'http://serdif.org/kg/datasource/weather',
         'vars': ['rain', 'temp', 'wetb', 'rhum', 'vappr', 'msl', 'wdsp',
                  'wddir', 'sun', 'vis', 'clht', 'clamt']  # 'ww', 'w
         },
    'pollution':
        {'namedGraph': 'http://serdif.org/kg/datasource/pollution',
         'vars': ['pm10', 'pm2.5', 'no2', 'so2', 'o3', 'co']
         },
    'aerosol':
        {'namedGraph': 'http://sceed.org/datasource/aerosol',
         'vars': []
         },
    'soil':
        {'namedGraph': 'http://sceed.org/datasource/soil',
         'vars': []
         },
}

envDataList = ['rain', 'temp', 'wetb', 'rhum', 'vappr', 'msl', 'wdsp',
               'wddir', 'sun', 'vis', 'clht', 'clamt',
               # 'pm10', 'pm2.5',
               'no2', 'so2', 'o3', 'co']


# Function to get variables available based on selected data sources
def dataSourceSel(selDataSL):
    envVarSel = [envDataSoDict[selData]['vars'] for selData in selDataSL]
    envVars = [item.replace('.', '') for sublist in envVarSel for item in sublist]
    return envVars


# Function to build the select clause for the query (SELECT)
def selVars(envList, aggMethod):
    if aggMethod == 'AVG' or aggMethod == 'SUM':
        return ' '.join(['(IF (COUNT(?' + envVar.replace('.',
                                                         '') + ') = 0, ?undef, ' + aggMethod + '(?' + envVar.replace(
            '.', '') + ')) AS ?' + envVar.replace('.', '') + ')' for envVar in envList])
    else:
        return ' '.join(
            ['(' + aggMethod + '(?' + envVar.replace('.', '') + ') AS ?' + envVar.replace('.', '') + ')' for envVar in
             envList])


# Function to build the optional clauses in the query body (WHERE)
def qTextOptionalEnvVars(envList):
    return '\n'.join(
        ['OPTIONAL{?splPoint serdif:' + envVar + 'Value ?' + envVar.replace('.', '') + '.}' for envVar in envList])


# GROUP BY and ORDER BY ending
qGoEv = {'Hourly': 'GROUP BY ?hourT ?dayT ?monthT ?yearT ORDER BY ?yearT ?monthT ?dayT ?hourT',
         'Daily': 'GROUP BY ?dayT ?monthT ?yearT ORDER BY ?yearT ?monthT ?dayT',
         'Monthly': 'GROUP BY ?monthT ?yearT ORDER BY ?yearT ?monthT',
         'Yearly': 'GROUP BY ?yearT ORDER BY ?yearT',
         }
qSelTime = {'Hourly': '?hourT ?dayT ?monthT ?yearT',
            'Daily': '?dayT ?monthT ?yearT',
            'Monthly': '?monthT ?yearT',
            'Yearly': '?yearT',
            }
qGoTime = {'Hourly': 'GROUP BY ?dateEOI ?hourT ?dayT ?monthT ?yearT',
           'Daily': 'GROUP BY ?dateEOI ?dayT ?monthT ?yearT',
           'Monthly': 'GROUP BY ?dateEOI ?monthT ?yearT',
           'Yearly': 'GROUP BY ?dateEOI ?yearT',
           }


# Fill query template with user options to retrieve environmental linked data
def serdif_EnvData(endpointURL, repoID, QPrefixes, eoiVal, sLOI, wLenVal, wLagVal, qGo, timeAgg, spatialAgg, eoiAgg):
    # 1.Query Environmental data related to specific patient ID
    # 1.1.Query body with input parameters
    bSmpEOIData = '''
    SELECT ''' + selVars(envList=envDataList, aggMethod=eoiAgg) + '''
    WHERE{
    {
        #Observation data temporal aggregation
        SELECT ?dateEOI ''' + qSelTime[qGo] + selVars(envList=envDataList, aggMethod=timeAgg) + '''
        WHERE{
            # String manipulation to order relative dates from EOI
            BIND(xsd:integer( STRAFTER( STRBEFORE( STR(?dateDf),"Y"),"P") ) AS ?yearT)
            BIND(xsd:integer( STRAFTER( STRBEFORE( STR(?dateDf),"M"),"Y") ) AS ?monthT)
            BIND(xsd:integer( STRAFTER( STRBEFORE( STR(?dateDf),"D"),"M") ) AS ?dayT)
            BIND(xsd:integer( STRAFTER( STRBEFORE( STR(?dateDf),"H"),"T") ) AS ?hourT)    
            #Subquery 1: Observation data time window and spatial aggregation
            {
                SELECT ?dateEOI ?dateDf ''' + selVars(envList=envDataList, aggMethod=spatialAgg) + '''
                WHERE{
                    ?sampler sosa:madeSampling ?splPoint .
                    ?splPoint sosa:resultTime ?dateT .
                    # Select variables
                    ''' + qTextOptionalEnvVars(envList=envDataList) + '''
                    # Lag from the EOI data
                    BIND(?dateEOI - "P''' + wLagVal + '''D"^^xsd:duration AS ?dateLag)
                    # Duration of the period
                    BIND(?dateLag - "P''' + wLenVal + '''D"^^xsd:duration AS ?dateStart)
                    # Filter environmental data for the selected dates
                    FILTER(?dateT > ?dateStart && ?dateT <= ?dateLag)
                    # Time difference from the event for ordering
                    BIND(?dateEOI - ?dateT as ?dateDf)
                    # Subquery 2: EOI dates in a LOI
                    {
                        SELECT ?dateEOI
                        WHERE{
                            # EOI location
                            GRAPH <http://serdif.org/kg/datasource/event> {
                                ?event a event:Event;
                                       event:place ?evgeomB;
                                       event:sub_event ?evCat;
                                       event:time ?dateEOI.
                                ?evgeomB geo:asWKT ?evgeom.
                                ''' + ' UNION '.join(['{ ?event event:sub_event <' + eoi + '> } ' for eoi in eoiVal]) + '''      
                            }
                        
                            GRAPH <http://serdif.org/kg/datasource/GeohiveData> {
                                #County geom    
                                ?county a osi:County, geo:Feature;
                                        rdfs:label ?countyName;
                                        geo:hasGeometry ?cogeomb.
                                ?cogeomb a geo:Geometry;
                                         geo:asWKT ?cogeom.
                                FILTER(''' + '|| '.join(['?countyName = "' + LOI + '" ' for LOI in sLOI]) + ''')
                            }
                            FILTER(geof:sfWithin(?evgeom, ?cogeom))
                        }  
                    }
                    # Subquery 3: Samplers in a LOI
                    {
                        SELECT ?sampler
                        WHERE{
                            ?sampler a sosa:Sampler;
                                     geo:hasGeometry ?splPointG.
                            ?splPointG geo:asWKT ?splGeom.
                            # Subquery 4: LOI geometries
                            {
                                SELECT ?cogeom
                                WHERE {            
                                    GRAPH <http://serdif.org/kg/datasource/GeohiveData> {  
                                        #County geom    
                                        ?county a osi:County, geo:Feature;
                                                rdfs:label ?countyName;
                                                geo:hasGeometry ?cogeomb.
                                        ?cogeomb a geo:Geometry;
                                                 geo:asWKT ?cogeom.
                                        FILTER(''' + '|| '.join(['?countyName = "' + LOI + '" ' for LOI in sLOI]) + ''')
                                    }
                                }
                            }
                            FILTER(geof:sfWithin(?splGeom, ?cogeom))                    
                        }
                    }
                }
                GROUP BY ?dateEOI ?dateDf
            } 
        }
        ''' + qGoTime[qGo] + '''
    }
}''' + qGoEv[qGo]
    # 1.2.Query parameters
    SPARQLQuery = SPARQLWrapper(endpointURL + repoID)
    SPARQLQuery.setMethod('POST')
    SPARQLQuery.setQuery(QPrefixes + bSmpEOIData)
    SPARQLQuery.setReturnFormat('json')
    # 1.3.Fire query and convert results to json (dictionary)
    qSmpEOIData = SPARQLQuery.query().convert()
    # 1.4.Return results
    print(QPrefixes + bSmpEOIData)
    return qSmpEOIData


# Ask env data
# Fill query template with user options to retrieve environmental linked data
def serdif_EnvDataAsk(endpointURL, repoID, QPrefixes, eoiVal, sLOI, wLenVal, wLagVal):
    # ADD (COUNT(?sampler) AS ?samplerC)

    # 1.Query Environmental data related to specific LOI
    # 1.1.Query body with input parameters
    bAskSub = '''
    ASK
    WHERE{
        ?sampler a sosa:Sampler ;
                 sosa:madeSampling ?splPoint ;
                 geo:hasGeometry ?splPointG .
        ?splPointG geo:asWKT ?splGeom.
        ?splPoint sosa:resultTime ?dateT .
        # Select variables
        #OPTIONAL{?splPoint serdif:tempValue ?temp.}
        # Lag from the EOI data
        BIND(?dateEOI - "P''' + wLagVal + '''D"^^xsd:duration AS ?dateLag)
        # Duration of the period
        BIND(?dateLag - "P''' + wLenVal + '''D"^^xsd:duration AS ?dateStart)
        # Filter environmental data for the selected dates
        FILTER(?dateT > ?dateStart && ?dateT <= ?dateLag)
        # Time difference from the event for ordering
        BIND(?dateEOI - ?dateT as ?dateDf)
        # Subquery 2: EOI dates in a LOI
        {
            SELECT ?dateEOI
            WHERE{
                # EOI location
                GRAPH <http://serdif.org/kg/datasource/event> {
                            ?event a event:Event;
                                   event:place ?evgeomB;
                                   event:sub_event ?evCat;
                                   event:time ?dateEOI.
                            ?evgeomB geo:asWKT ?evgeom.
                            ''' + ' UNION '.join(['{ ?event event:sub_event <' + eoi + '> } ' for eoi in eoiVal]) + '''      
                        }
                    
                GRAPH <http://serdif.org/kg/datasource/GeohiveData> { 
                    #County geom    
                    ?county a osi:County, geo:Feature;
                            rdfs:label ?countyName;
                            geo:hasGeometry ?cogeomb.
                    ?cogeomb a geo:Geometry;
                             geo:asWKT ?cogeom.
                    FILTER(''' + '|| '.join(['?countyName = "' + LOI + '" ' for LOI in sLOI]) + ''')
                }
                FILTER(geof:sfWithin(?evgeom, ?cogeom))
            }  
        }
        # Subquery 3: Samplers in a LOI
        {
            SELECT ?sampler
            WHERE{
                ?sampler a sosa:Sampler;
                         geo:hasGeometry ?splPointG.
                ?splPointG geo:asWKT ?splGeom.
                # Subquery 4: LOI geometries
                {
                    SELECT ?cogeom
                    WHERE {            
                        GRAPH <http://serdif.org/kg/datasource/GeohiveData> {  
                            #County geom    
                            ?county a osi:County, geo:Feature;
                                    rdfs:label ?countyName;
                                    geo:hasGeometry ?cogeomb.
                            ?cogeomb a geo:Geometry;
                                     geo:asWKT ?cogeom.
                            FILTER(''' + '|| '.join(['?countyName = "' + LOI + '" ' for LOI in sLOI]) + ''')
                        }
                    }
                }
                FILTER(geof:sfWithin(?splGeom, ?cogeom))                    
            }
        }
    }
    '''
    # 1.2.Query parameters
    SPARQLQuery = SPARQLWrapper(endpointURL + repoID)
    SPARQLQuery.setMethod('POST')
    SPARQLQuery.setQuery(QPrefixes + bAskSub)
    SPARQLQuery.setReturnFormat('json')
    # 1.3.Fire query and convert results to json (dictionary)
    qAskSub = SPARQLQuery.query().convert()
    # 1.4.Return results
    return qAskSub


# Function to get variable descriptions
def serdif_EnvDesc(endpointURL, repoID):
    qEnvDesc = '''
    PREFIX qudt: <http://qudt.org/schema/qudt/>
    PREFIX serdif: <http://serdif.org/kg/datasource/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT ?varAbb ?varName ?varUnit
    WHERE { 
        ?var qudt:abbreviation ?varAbb;
             qudt:symbol ?varUnit;
             rdfs:label ?varName.
    }
    '''

    # 1.2.Query parameters
    SPARQLQuery = SPARQLWrapper(endpointURL + repoID)
    SPARQLQuery.setMethod('POST')
    SPARQLQuery.setQuery(qEnvDesc)
    SPARQLQuery.setReturnFormat('json')
    # 1.3.Fire query and convert results to json (dictionary)
    jEnvDesc = SPARQLQuery.query().convert()
    # 1.4.Return results formatted for tooltip_header
    varAbb = [cc['varAbb']['value'] for cc in jEnvDesc['results']['bindings']]
    varDesc = [cc['varName']['value'] + ' [' + cc['varUnit']['value'] + ']' for cc in jEnvDesc['results']['bindings']]

    tooltipEnvDesc = dict(zip(varAbb, varDesc))

    return tooltipEnvDesc


if __name__ == '__main__':
    serdifSamplers()
    serdifEOIdates()
    serdif_LOIs()
    serdif_EnvData()
    serdif_EnvDataAsk()
    serdif_EnvDesc()
    dataSourceSel()
