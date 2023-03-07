from SPARQLWrapper import SPARQLWrapper
# from pprint import pprint
import requests
import json
import xmltodict
import io


# Function that returns the number of events grouped by type
def nEvents(referer, repo, username, password):
    qBody = '''
    PREFIX geo: <http://www.opengis.net/ont/geosparql#>
    PREFIX geof: <http://www.opengis.net/def/function/geosparql/>
    PREFIX prov: <http://www.w3.org/ns/prov#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    SELECT ?eventType (COUNT(?event) AS ?eventCount)
    WHERE {
        ?event
            a prov:Activity ;
            rdfs:label ?eventType .    
    }
    GROUP BY ?eventType
    '''

    # 1.2.Query parameters
    SPARQLQuery = SPARQLWrapper(referer + repo)
    SPARQLQuery.setMethod('POST')
    SPARQLQuery.setQuery(qBody)
    SPARQLQuery.setReturnFormat('json')
    SPARQLQuery.setCredentials(user=username, passwd=password)

    # 1.3.Fire query and convert results to json (dictionary)
    qEvNum_dict = SPARQLQuery.query().convert()
    # 1.4.Return results
    jEvNum = qEvNum_dict['results']['bindings']
    return jEvNum


# Function that returns the events filtered by type within specific regions
def evLoc(referer, repo, username, password):
    qBody = '''
    PREFIX geo: <http://www.opengis.net/ont/geosparql#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?LOI 
    WHERE { 
        ?county
            a geo:Feature, <http://ontologies.geohive.ie/osi#County> ;
            rdfs:label ?LOI ;
            geo:hasGeometry/geo:asWKT ?countyGeo .
        FILTER (lang(?LOI) = 'en')
    }
    '''

    # 1.2.Query parameters
    SPARQLQuery = SPARQLWrapper(referer + repo)
    SPARQLQuery.setMethod('POST')
    SPARQLQuery.setQuery(qBody)
    SPARQLQuery.setReturnFormat('json')
    SPARQLQuery.setCredentials(user=username, passwd=password)

    # 1.3.Fire query and convert results to json (dictionary)
    qEvLoc_dict = SPARQLQuery.query().convert()
    # 1.4.Return results
    jEvLoc = qEvLoc_dict['results']['bindings']
    return jEvLoc


# Function that returns the events filtered by type within specific regions
def envoLoc(referer, repo, envoLoc, username, password):
    qBody = '''
    PREFIX qb: <http://purl.org/linked-data/cube#>
    PREFIX geof: <http://www.opengis.net/def/function/geosparql/>
    PREFIX geo: <http://www.opengis.net/ont/geosparql#>
    PREFIX prov: <http://www.w3.org/ns/prov#>
    PREFIX dcat: <http://www.w3.org/ns/dcat#>
    PREFIX dct: <http://purl.org/dc/terms/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    SELECT ?LOI ?envoDataSet
    WHERE {
        # Filter environmental data within a region
        ?envoDataSet
            a qb:DataSet, geo:Feature, prov:Entity, dcat:Dataset ;
            dct:Location/geo:asWKT ?envoGeo .
        #County geom  
        VALUES ?LOI {''' + ''.join([' "' + envoLocVal + '"@en ' for envoLocVal in envoLoc]) + '''}
        ?county
            a geo:Feature, <http://ontologies.geohive.ie/osi#County> ;
            rdfs:label ?LOI ;
            geo:hasGeometry/geo:asWKT ?countyGeo .
        FILTER(geof:sfWithin(?envoGeo, ?countyGeo))  
    }
    '''

    # 1.2.Query parameters
    SPARQLQuery = SPARQLWrapper(referer + repo)
    SPARQLQuery.setMethod('POST')
    SPARQLQuery.setQuery(qBody)
    SPARQLQuery.setReturnFormat('json')
    SPARQLQuery.setCredentials(user=username, passwd=password)

    # 1.3.Fire query and convert results to json (dictionary)
    qEnvoLoc_dict = SPARQLQuery.query().convert()
    # 1.4.Return results
    jEnvoLoc = qEnvoLoc_dict['results']['bindings']
    return jEnvoLoc


# Function that returns the events filtered by type within specific regions
def evTypeLocDateT(referer, repo, evType, evLoc, wLen, wLag, username, password):
    qBody = '''
    PREFIX geo: <http://www.opengis.net/ont/geosparql#>
    PREFIX geof: <http://www.opengis.net/def/function/geosparql/>
    PREFIX prov: <http://www.w3.org/ns/prov#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    SELECT ?LOI ?event ?eventType ?evDateT ?dateLag ?dateStart
    WHERE {
        VALUES ?eventType {''' + ''.join([' "' + evTypeVal + '"@en ' for evTypeVal in evType]) + '''}      
        ?event
            a prov:Activity ;
            rdfs:label ?eventType ;
            prov:startedAtTime ?eventTime ;
            prov:atLocation/geo:asWKT ?eventGeo .
        #County geom    
        VALUES ?LOI {''' + ''.join([' "' + evLocVal + '"@en ' for evLocVal in evLoc]) + '''}
        ?county
            a geo:Feature, <http://ontologies.geohive.ie/osi#County> ;
            rdfs:label ?LOI ;
            geo:hasGeometry/geo:asWKT ?countyGeo .
        FILTER(geof:sfWithin(?eventGeo, ?countyGeo))    
        BIND(xsd:dateTime(?eventTime) AS ?evDateT)
        BIND(?evDateT - "P''' + str(wLag) + '''D"^^xsd:duration AS ?dateLag)
        BIND(?dateLag - "P''' + str(wLen) + '''D"^^xsd:duration AS ?dateStart)
    }
    '''
    # 1.2.Query parameters
    SPARQLQuery = SPARQLWrapper(referer + repo)
    SPARQLQuery.setMethod('POST')
    SPARQLQuery.setQuery(qBody)
    SPARQLQuery.setReturnFormat('json')
    SPARQLQuery.setCredentials(user=username, passwd=password)

    # 1.3.Fire query and convert results to json (dictionary)
    qEvTypeLocDateT_dict = SPARQLQuery.query().convert()
    # 1.4.Return results
    jEvTypeLocDateT = qEvTypeLocDateT_dict['results']['bindings']
    return jEvTypeLocDateT


# Function to check envo data is available for at least one event
def evEnvoDataAsk(referer, repo, evEnvoDict, username, password):
    # Build block per each event
    qBodyBlockList = []
    for ev in evEnvoDict.keys():
        qBodyBlock = '''
        {
            SELECT DISTINCT ?envoDataSet
            WHERE{
                VALUES ?envoDataSet {''' + ''.join([' <' + envoDS + '> ' for envoDS in evEnvoDict[ev]['envoDS']]) + '''}  
                ?obsData
                    a qb:Observation ;
                    qb:dataSet ?envoDataSet ;
                    sdmx-dimension:timePeriod ?obsTime .        
                FILTER(?obsTime > "''' + evEnvoDict[ev]['dateStart'] + '''"^^xsd:dateTime && ?obsTime <= "''' + \
                     evEnvoDict[ev]['dateLag'] + '''"^^xsd:dateTime)
            }
        }
        '''
        qBodyBlockList.append(qBodyBlock)

    qBodyBlockUnion = '  UNION  '.join(qBodyBlockList)

    qBody = '''
    PREFIX eg: <http://example.org/ns#>
    PREFIX qb: <http://purl.org/linked-data/cube#>
    PREFIX sdmx-dimension: <http://purl.org/linked-data/sdmx/2009/dimension#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    ASK
    WHERE{
    ''' + qBodyBlockUnion + '''   
    }
        '''
    # 1.2.Query parameters
    SPARQLQuery = SPARQLWrapper(referer + repo)
    SPARQLQuery.setMethod('POST')
    SPARQLQuery.setQuery(qBody)
    SPARQLQuery.setReturnFormat('json')
    SPARQLQuery.setCredentials(user=username, passwd=password)

    # 1.3.Fire query and convert results to json (dictionary)
    qEvEnvoAsk = SPARQLQuery.query().convert()
    # 1.4.Return results
    jEvEnvoAsk = qEvEnvoAsk['boolean']
    return jEvEnvoAsk


# Function to check envo data is available for at least one event
def evEnvoDataSet(referer, repo, evEnvoDict, timeUnit, spAgg, username, password):
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
            SELECT ?event ''' + selTimeUnitRev[timeUnit] + ''' ?envProp (''' + spAgg + '''(?envVar) AS ?envVar)
            WHERE {
                {
                    SELECT ?obsData ?obsTime
                    WHERE{
                        VALUES ?envoDataSet {''' + ''.join(
            [' <' + envoDS + '> ' for envoDS in evEnvoDict[ev]['envoDS']]) + '''}  
                        ?obsData
                            a qb:Observation ;
                            qb:dataSet ?envoDataSet ;
                            sdmx-dimension:timePeriod ?obsTime .        
                        FILTER(?obsTime > "''' + evEnvoDict[ev]['dateStart'] + '''"^^xsd:dateTime && ?obsTime <= "''' + \
                     evEnvoDict[ev]['dateLag'] + '''"^^xsd:dateTime)
                    }
                }
                ?obsData ?envProp ?envVar .
                FILTER(datatype(?envVar) = xsd:float)    
                # String manipulation to aggregate observations per time unit
                BIND(YEAR(?obsTime) AS ?yearT)
                BIND(MONTH(?obsTime) AS ?monthT)
                BIND(DAY(?obsTime) AS ?dayT)
                BIND(HOURS(?obsTime) AS ?hourT)
                BIND("''' + ev.split('/ns#')[1] + '''" AS ?event)
            }
            GROUP BY ?event ?envProp ''' + selTimeUnit[timeUnit] + '''
        }
        '''
        qBodyBlockList.append(qBodyBlock)

    qBodyBlockUnion = '  UNION  '.join(qBodyBlockList)

    qBody = '''
    PREFIX qb: <http://purl.org/linked-data/cube#>
    PREFIX eg: <http://example.org/ns#>
    PREFIX geohive-county-geo: <http://data.geohive.ie/pathpage/geo:hasGeometry/county/>
    PREFIX sdmx-dimension: <http://purl.org/linked-data/sdmx/2009/dimension#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    PREFIX geo:	<http://www.opengis.net/ont/geosparql#>
    PREFIX prov: <http://www.w3.org/ns/prov#>
    CONSTRUCT{
        ?eventRef ?evP ?evO ;
                  prov:atLocation ?evGeoUri .
        ?evGeoUri geo:asWKT ?evGeo .
        ?evI ?evIP ?evIO .
        
        ?sliceName
            a qb:Slice;
            qb:sliceStructure 			eg:sliceByTime ;
            eg:refArea 					?evGeoUri ;
            eg:refEvent        			?eventRef ;
            qb:observation   			?obsName ;
            .
    
        ?obsName
            a qb:Observation ;
            qb:dataSet 					?datasetName ;
            sdmx-dimension:timePeriod 	?obsTimePeriod ;
            ?envProp 					?envVar ;
            .
    }
    WHERE {
    ''' + qBodyBlockUnion + '''   
        # Fix single digits when using SPARQL temporal functions
        BIND( IF( BOUND(?monthT), IF(STRLEN( STR(?monthT) ) = 2, STR(?monthT), CONCAT("0", STR(?monthT)) ), "01") AS ?monthTF )
        BIND( IF( BOUND(?dayT), IF( STRLEN( STR(?dayT) ) = 2, STR(?dayT), CONCAT("0", STR(?dayT)) ), "01" ) AS ?dayTF )
        BIND( IF( BOUND(?hourT) , IF( STRLEN( STR(?hourT) ) = 2, STR(?hourT), CONCAT("0", STR(?hourT)) ), "00" ) AS ?hourTF )
        # Build dateTime values 
        BIND(CONCAT(str(?yearT),"-",?monthTF,"-",?dayTF,"T",?hourTF,":00:00Z") AS ?obsTimePeriod)
        # Build IRI for the CONSTRUCT
        BIND(IRI(CONCAT("http://example.org/ns#dataset-ee-20211012T120000-IE-QT_", ENCODE_FOR_URI(STR(NOW())))) AS ?datasetName)
        BIND(IRI(CONCAT(STR(?datasetName),"-", ?event ,"-obs-", str(?yearT),?monthTF,?dayTF,"T",?hourTF,"0000Z")) AS ?obsName)
        BIND(IRI(CONCAT(STR(?datasetName),"-", ?event ,"-slice")) AS ?sliceName)
        
        # Gather events description
        SERVICE <repository:repo-serdif-events-ie>{
            VALUES ?eventRef {''' + ''.join([' <' + ev + '> ' for ev in evEnvoDict.keys()]) + '''}
            ?eventRef ?evP ?evO ;
                      prov:wasAssociatedWith	?evI ;
                      prov:atLocation/geo:asWKT ?evGeo .
            ?evI ?evIP ?evIO .
            BIND(IRI(CONCAT(str(?eventRef), "-geo")) AS ?evGeoUri)
        }
    }
    '''
    # print(evEnvoDict)
    # 1.2.Query parameters
    rQuery = requests.post(
        referer + repo,
        # data={'query': 'SELECT ?s ?p ?o { ?s ?p ?o . } LIMIT 4'},
        data={'query': qBody},
        auth=(username, password),
        headers={
            'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:93.0) Gecko/20100101 Firefox/93.0',
            'Referer': 'https://serdif-example.adaptcentre.ie/sparql',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        }
    )

    return {'queryContent': rQuery.content, 'queryBody': qBody}  # qEvEnvo_dict


# Function that returns the number of events grouped by type
def envoVarNameUnit(referer, repo, username, password):
    qBody = '''
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX owl: <http://www.w3.org/2002/07/owl#>
    PREFIX qb: <http://purl.org/linked-data/cube#>
    SELECT ?envoVar ?envoVarName
    WHERE { 
        ?envoVar a owl:DatatypeProperty , qb:MeasureProperty ; 
                 rdfs:comment ?envoVarName.
    }
    '''

    # 1.2.Query parameters
    SPARQLQuery = SPARQLWrapper(referer + repo)
    SPARQLQuery.setMethod('POST')
    SPARQLQuery.setQuery(qBody)
    SPARQLQuery.setReturnFormat('json')
    SPARQLQuery.setCredentials(user=username, passwd=password)

    # 1.3.Fire query and convert results to json (dictionary)
    qVarNameUnit_dict = SPARQLQuery.query().convert()
    # 1.4.Return results
    jVarNameUnit = qVarNameUnit_dict['results']['bindings']
    # 1.5.Return results formatted for tooltip_header
    varAbb = [cc['envoVar']['value'].split('http://example.org/ns#has')[1] for cc in jVarNameUnit]
    varDesc = [cc['envoVarName']['value'] for cc in jVarNameUnit]
    tooltipEnvDesc = dict(zip(varAbb, varDesc))

    return tooltipEnvDesc


if __name__ == '__main__':
    nEvents()
    evLoc()
    envoLoc()
    evTypeLocDateT()
    evEnvoDataAsk()
    evEnvoDataSet()
    envoVarNameUnit()
