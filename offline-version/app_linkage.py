import requests
from pprint import pprint
import pandas as pd
import xarray as xr
import numpy as np
import json
from datetime import datetime, timedelta
import time
import socket
from jinja2 import Environment, FileSystemLoader
from subprocess import call, Popen, PIPE, STDOUT, run, DEVNULL
import os
import shlex
import glob
import urllib
import shapely
import geopandas as gpd
from functools import partial
import pyproj
from shapely.ops import transform
from shapely.geometry import Point
import shutil
from string import Formatter
import plotly.graph_objects as go
import plotly.express as px
from bs4 import BeautifulSoup
import warnings
from tqdm import tqdm
warnings.filterwarnings("ignore")

# Function to check if a string is a valid url
def valid_url(url):
    try:
        request = requests.get(url)
        if request.status_code == 200:
            return True
        else:
            return False
    except:
        return False


# Function to print progress bar
def printProgressBar(iteration, prefix, suffix, decimals, length, fill, printEnd, total):
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + ' ' * (length - filledLength)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}\n', end=printEnd)


# Function to build serdif-geosparql server
def serdif_geosparql():
    # Path to the directory you want to delete
    db_path = 'data/serdif-geosparql'

    # Check if the directory exists
    if os.path.exists(db_path):
        # Remove the directory and its contents
        call(['rm', '-r', db_path], shell = True)
        print(f"Removed existing directory: {db_path}")
    else:
        print(f"Directory does not exist: {db_path}")
    # build serdif-geosparql SPARQL endpoint
    build_serdifstore = 'java -jar data/jena-fuseki-geosparql-4.7.0.jar -t "data/serdif-geosparql" -i'
    p_build_serdifstore = run(build_serdifstore, shell=True)
    # load dataset to serdif-geosparql SPARQL endpoint
    add_nutsgeo = 'data/apache-jena-4.7.0/bin/tdbloader --loc data/serdif-geosparql data/EU-nuts-rdf-geosparql.ttl'
    p_add_nuts = run(add_nutsgeo, shell=True)


# Function to load event data and metadata
def load_events(event_data, event_metadata):
    # read event data to dictionary
    # 
    if isinstance(event_data, pd.DataFrame):
        df_data = event_data.astype({
            'id': str,
            'group': str,
            'longitude': float,
            'latitude': float,
            'date': str,
            'length': int,
            'lag': int
        })
    else: 
        df_data = pd.read_csv(event_data, delimiter=',', dtype={'id': str, 'group': str, 'longitude': float,
                                                            'latitude': float, 'date': str, 'length': int, 'lag': int})

    # check if event data is empty
    if df_data.empty:
        print(f'Error: {event_data} is empty!')
        exit()
    # check if event data has the required columns
    if not set(['id', 'group', 'longitude', 'latitude', 'date', 'length', 'lag', 'spatial']).issubset(df_data.columns):
        print(f'Error: {event_data} does not contain the required columns!')
        exit()
    # check if there are missing values like empty strings or nan
    if '' in df_data.to_numpy().flatten() or df_data.isnull().values.any():
        print(f'Error: {event_data} contains missing values!')
        exit()
    # check if values in id are alphanumeric and dashed
    if not df_data['id'].str.match('[A-Za-z0-9\-_]+$').all():
        print('Error: values in column "id" need to be alphanumeric or dashed!')
        exit()
    # check if event data contains only valid values
    if not pd.to_numeric(df_data['longitude'], errors='coerce').notnull().all():
        print('Error: values in column "lon" need to be numeric!')
        exit()
    if not pd.to_numeric(df_data['latitude'], errors='coerce').notnull().all():
        print('Error: values in column "lat" need to be numeric!')
        exit()
    if pd.to_datetime(df_data['date'], errors='coerce').isnull().any():
        print('Error: values in column "date" need to be in the format YYYY-MM-DD!')
        exit()
    if not pd.to_numeric(df_data['length'], errors='coerce').notnull().all():
        print('Error: values in column "length" need to be integers!')
        exit()
    if not pd.to_numeric(df_data['lag'], errors='coerce').notnull().all():
        print('Error: values in column "lag" need to be integers!')
        exit()
    # check if the spatial column has a positive numeric value or a string 'NUTS-0', 'NUTS-1', 'NUTS-2', 'NUTS-3'
    if not (set(['NUTS-0', 'NUTS-1', 'NUTS-2', 'NUTS-3']).issubset(df_data['spatial']) or pd.to_numeric(df_data['spatial'], errors='coerce').notnull().all()):
        print('Error: values in column "spatial" need to be numeric or "NUTS-0", "NUTS-1", "NUTS-2", "NUTS-3"!')
        exit()

    print(f'{event_data} loaded successfully')
    printProgressBar(1, prefix='Progress:', suffix='Completed', decimals=1,
                     length=50, fill='=', printEnd="\r", total=8)
    
    if isinstance(event_metadata, pd.DataFrame):
        df_meta = event_metadata
    else:
        # read event metadata to dictionary
        df_meta = pd.read_csv(event_metadata, delimiter=',') # delimiter=','
    # check if event data is empty
    if df_meta.empty:
        print(f'Error: {event_metadata} is empty!')
        exit()
    # check if event data has the required columns
    if not set(['key', 'value']).issubset(df_meta.columns):
        print(f'Error: {event_metadata} does not contain the required columns!')
        exit()
    # check if there are missing values like empty strings or nan
    if '' in df_meta.to_numpy().flatten() or df_data.isnull().values.any():
        print(f'Error: {event_metadata} contains missing values!')
        exit()
    # check if the key column contains the following values only
    # 'context' 'publisher' 'license' 'dataController' 'dataProcessor' 'datasetURL'
    if not set(['context', 'publisher', 'license', 'dataController', 'dataProcessor', 'datasetURL']).issubset(
            df_meta['key']):
        print(f'Error: {event_metadata} contains invalid values in column "key"!')
        exit()
    # apply the valid_url function to the value column except for the first row
    # if not df_meta['value'][1:].apply(valid_url).all():
     #   print(f'Error: {event_metadata} contains URLs that do not exist on the Internet!')
     #   exit()

    # read event metadata and print table
    print(f'\n{event_metadata} loaded successfully')
    printProgressBar(2, prefix='Progress:', suffix='Completed', decimals=1,
                     length=50, fill='=', printEnd="\r", total=8)
    # follow with checking datasets folder in a new function
    print('\nthe end')


# Function to uplift the datasets spatiotemporal information to RDF
def uplift_metadata(raw_folder, queryTimeStr):
    startTime = datetime.now()
    # make folder to store the output
    outfolder = './ee-output-QT_' + queryTimeStr
    if not os.path.exists(outfolder):
        os.makedirs(outfolder)

    # Step 1: Generate metadata from the datasets
    # identify datasets available in raw data folder
    raw_datasets = glob.glob(raw_folder + '/*')
    # iterate through datasets and merge the metadata results
    df_meta_list = []
    for ds in raw_datasets:
        # check the file type of each dataset
        if ds.endswith('.nc'):
            print('NetCDF file:', os.path.split(ds)[-1])
            # convert NetCDF to dataframe
            dnc = xr.open_dataset(ds)
            df_dnc = dnc.to_dataframe().dropna()
            # rename columns to merge index
            df_dnc.reset_index(inplace=True)
            # build a new dataframe with the necessary metadata
            # select unique lat-lon pairs
            df_info = df_dnc.groupby(['longitude', 'latitude'], sort=False, as_index=False)['time'].idxmin()
            df_info.reset_index(inplace=True)
            # add start and end dates
            df_info.insert(1, 'start', df_dnc['time'].min().strftime('%Y-%m-%dT%H:%M:%SZ'))
            df_info.insert(2, 'end', df_dnc['time'].max().strftime('%Y-%m-%dT%H:%M:%SZ'))
            # add time resolution in hours as xsd:duration from time variable
            df_info.insert(3, 'timeRes',
                           'PT' + str(int((df_dnc['time'][1] - df_dnc['time'][0]).total_seconds() / 3600)) + 'H')
            # add dataset size
            df_info.insert(4, 'size', os.stat(ds).st_size / len(df_dnc))
            # add dataset url
            df_info.insert(5, 'url','https://test.org')
            # add dataset license
            df_info.insert(6, 'license','https://test.org')
            # add dataset name
            df_info.insert(7, 'dsname', urllib.parse.quote(os.path.split(ds)[-1], safe='=?&'))
            # add dataset to metadata list
            df_meta_list.append(df_info)
        elif ds.endswith('.tsv') or ds.endswith('.csv'):
            if ds.endswith('.tsv'):
                ds_delimiter = '\t'
                print('TSV file:', ds)
            elif ds.endswith('.csv'):
                ds_delimiter = ';'
                print('CSV file:', ds)
            # build a new dataframe with the necessary metadata
            #df_read = pd.read_csv(ds, index_col=False, delimiter='\t',parse_dates=['time'])
            df_read = pd.read_csv(ds, index_col=False, delimiter=ds_delimiter,parse_dates=['time'])
            # select unique lat-lon pairs
            df_info = df_read.groupby(['longitude', 'latitude'], sort=False, as_index=False)['time'].idxmin()
            df_info.reset_index(inplace=True)
            # add start and end dates
            df_info.insert(1, 'start', df_read['time'].min().strftime('%Y-%m-%dT%H:%M:%SZ'))
            df_info.insert(2, 'end', df_read['time'].max().strftime('%Y-%m-%dT%H:%M:%SZ'))
            # add time resolution in hours as xsd:duration from time variable
            df_info.insert(3, 'timeres','P1D')
            # add dataset size
            df_info.insert(4, 'size', os.stat(ds).st_size / len(df_read))
            # add dataset url
            df_info.insert(5, 'url','https://test.org')
            # add dataset license
            df_info.insert(6, 'license','https://test.org')
            # add dataset name
            df_info.insert(7, 'dsname', urllib.parse.quote(os.path.split(ds)[-1], safe='=?&'))
            # add dataset to metadata list
            df_meta_list.append(df_info)
        elif ds.endswith('.grib'):
            print('GRIB file:', ds)
        else:
            print('Unknown file type.', ds, 'Supported files: .nc .csv')
            exit()

    # concat list of metadata dataframes
    df_meta = pd.concat(df_meta_list, ignore_index=True)
    # set metadata dataset name
    ds_name_meta = 'metadata_layer_sparql_' + queryTimeStr
    # Convert dataframe to a temporary csv file
    pd.DataFrame.to_csv(df_meta, outfolder + '/' + ds_name_meta + '.csv', sep=',', na_rep='', index=False)
    # load environment (directory) for jinja2 templates
    file_loader = FileSystemLoader('templates')
    env = Environment(loader=file_loader)
    # load dataset mapping template file
    tempMap_meta = env.get_template('dataset-metadata-map.ttl')

    # set data dictionary for input
    tempMap_meta_dict = {
        'dsName': ds_name_meta,
        'qTime': queryTimeStr,
        'outFolder': outfolder,
        # 'user': socket.gethostname()
    }
    outMap_meta = tempMap_meta.stream(data=tempMap_meta_dict)
    # export resulting mapping
    outMap_meta.dump(outfolder + '/' + ds_name_meta + '_map.ttl')
    # load .properties template file
    tempProp_meta = env.get_template('dataset-metadata.properties')
    # set data dictionary for input
    outProp_meta = tempProp_meta.stream(data=tempMap_meta_dict)
    # export resulting mapping properties file
    outPropName_meta = outfolder + '/' + ds_name_meta + '_map.properties'
    outProp_meta.dump(outPropName_meta)
    # uplift metadata file to rdf
    uplift_ds_meta = 'java -Xmx4112m -jar data/r2rml/r2rml-v1.2.3b/r2rml.jar ' + outfolder + '/' + ds_name_meta + '_map.properties',
    p_uplift_ds_meta = run(uplift_ds_meta, shell=True)
    # load dataset to serdif-geosparql SPARQL endpoint
    tdbloader_ds_meta = 'data/apache-jena-4.7.0/bin/tdbloader --loc data/serdif-geosparql ' + outfolder + '/' + ds_name_meta + '.trig',
    p_tdbloader_meta = run(tdbloader_ds_meta, shell=True)
    # wait for the endpoint to start
    # read event metadata and print table
    print('\nMetadata graph layer generated loaded successfully')
    printProgressBar(3, prefix='Progress:', suffix='Completed', decimals=1,
                     length=50, fill='=', printEnd="\r", total=8)
    return df_meta


# Function to link health events with environmental data
def link_data(raw_folder, df_input_path, df_info_path, queryTimeStr, agg_method, time_Unit):
    # Export process
    startTime = datetime.now()
    # current version
    version = 'v20230530'
    prefixes_serdif = prefixes_serdif = '''
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
PREFIX geosparql: <http://www.opengis.net/ont/geosparql#>
PREFIX geof: <http://www.opengis.net/def/function/geosparql/>
PREFIX ramon: <http://rdfdata.eionet.europa.eu/ramon/ontology/>
PREFIX dcat: <http://www.w3.org/ns/dcat#>
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX qb: <http://purl.org/linked-data/cube#>
PREFIX locn: <http://www.w3.org/ns/locn#>
PREFIX serdif: <https://serdif.adaptcentre.ie/kg/2023/dataset/>
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX sdmx-dimension: <http://purl.org/linked-data/sdmx/2009/dimension#>
PREFIX serdif-dataset: <https://serdif.adaptcentre.ie/kg/2023/dataset#>
PREFIX serdif-measure: <https://serdif.adaptcentre.ie/kg/2023/measure#>
PREFIX serdif-dimension: <https://serdif.adaptcentre.ie/kg/2023/dimension#>
PREFIX serdif-slice: <https://serdif.adaptcentre.ie/kg/2023/slice#>
PREFIX greg: <http://www.w3.org/ns/time/gregorian#>
PREFIX time: <http://www.w3.org/2006/time#>
    '''
    # set endpoint URL for GeoSPARQL server
    endpointURL = 'http://localhost:3030/ds'
    
    if isinstance(df_input_path, pd.DataFrame):
        df_input = df_input_path.astype({
            'id': str,
            'group': str,
            'longitude': float,
            'latitude': float,
            'date': str,
            'length': int,
            'lag': int
        })
    else:
        # Read events data
        df_input = pd.read_csv(df_input_path, delimiter=',', dtype={'id': str, 'group': str, 'longitude': float,
                                                            'latitude': float, 'date': str, 'length': int, 'lag': int})
    if isinstance(df_info_path, pd.DataFrame):
        df_info = df_info_path
    else:
        # Read metadata information
        df_info = pd.read_csv(df_info_path, delimiter=',')
    # function that returns the start and end dates of the time window
    def evTimeWindow(endpoint, date, lag, length):
        print(endpoint, date, lag, length)
        qBody = '''
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            SELECT ?dateLag ?dateStart
            WHERE {
                BIND(xsd:dateTime("''' + str(date) + 'T23:59:59Z' + '''") AS ?evDateT)
                BIND(?evDateT - "P''' + str(lag) + '''D"^^xsd:duration AS ?dateLag)
                BIND(?dateLag - "P''' + str(length) + '''D"^^xsd:duration AS ?dateStart)
            }
            '''
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
            'queryBodyTime': qBody
        }
        return dEvTW

    # function that returns the datasets within a given geographical area
    def envoDataLoc(endpoint, lat, lon, level, queryTimeStr, dateStart, dateEnd):
        # generate point from lat and lon that conforms with SPARQL syntax
        point = 'POINT(' + str(lon) + ' ' + str(lat) + ')'
        # ?point ?area ?geo ?areaName
        qBody = '''
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            PREFIX geosparql: <http://www.opengis.net/ont/geosparql#>
            PREFIX geof: <http://www.opengis.net/def/function/geosparql/>
            PREFIX ramon: <http://rdfdata.eionet.europa.eu/ramon/ontology/>
            PREFIX dcat: <http://www.w3.org/ns/dcat#>
            PREFIX dct: <http://purl.org/dc/terms/>
            PREFIX qb: <http://purl.org/linked-data/cube#>
            PREFIX locn: <http://www.w3.org/ns/locn#>
            PREFIX serdif: <https://serdif.adaptcentre.ie/kg/2023/dataset/>
            SELECT ?ds ?dsTitle ?dsGeo ?geo ?areaName
            WHERE {
                # select geographical area relevant to a particular event
                {
                    SELECT ?point ?area ?geo ?areaName
                    WHERE { 
                      # event location
                      BIND( "''' + point + '''"^^geosparql:wktLiteral AS ?point)
                      ?area a geosparql:Feature ;
                        rdfs:label ?areaName ;
                        geosparql:hasGeometry/geosparql:asWKT ?geo ;
                        ramon:level ''' + str(level) + ''' .
                      # geographical area that contains the event location
                      FILTER(geof:sfWithin(?point, ?geo))
                    }
                }
                # select datasets within the geographical area
                GRAPH <https://serdif.adaptcentre.ie/kg/2023/dataset/metadata/metadata_layer_sparql_''' + queryTimeStr + '''> {
                    ?ds a dcat:Distribution ;
                        dct:title ?dsTitle ;
                        dcat:spatial/locn:geometry ?dsGeo ;
                        dcat:temporal/dcat:startDate ?dsStartDate ;
    		            dcat:temporal/dcat:endDate ?dsEndDate .
                }
                # spatial filter
                FILTER(geof:sfWithin(?dsGeo, ?geo))
                # temporal filter
                FILTER(?dsStartDate <= "''' + dateStart + '''"^^xsd:dateTime && ?dsEndDate >= "''' + dateEnd + '''"^^xsd:dateTime)
            }
            '''
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
        dEvLoc = {  # ?ds ?dsTitle ?dsGeo
            'dsURL': [ds['ds']['value'] for ds in rEvLoc],
            'file': [ds['dsTitle']['value'] for ds in rEvLoc],
            'lat': [ds['dsGeo']['value'].strip('POINT()').split(' ')[1] for ds in rEvLoc],
            'lon': [ds['dsGeo']['value'].strip('POINT()').split(' ')[0] for ds in rEvLoc],
            'areaGeo': [ds['geo']['value'] for ds in rEvLoc],
            'queryBodyGeo': qBody
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

    def envoDataLocBuffer(endpoint, buffer, prefixes, queryTimeStr, dateStart, dateEnd):
        qBody = prefixes + '''
        SELECT ?ds ?dsTitle ?dsGeo ?buffer
        WHERE { 
            BIND( "''' + buffer + '''"^^geosparql:wktLiteral AS ?buffer)
            GRAPH <https://serdif.adaptcentre.ie/kg/2023/dataset/metadata/metadata_layer_sparql_''' + queryTimeStr + '''> {
                ?ds a dcat:Distribution ;
                    dct:title ?dsTitle ;
                    dcat:spatial/locn:geometry ?dsGeo ;
                    dcat:temporal/dcat:startDate ?dsStartDate ;
                    dcat:temporal/dcat:endDate ?dsEndDate .
            }
            # spatial filter     
            FILTER(geof:sfWithin(?dsGeo, ?buffer))
            # temporal filter
            FILTER(?dsStartDate <= "''' + dateStart + '''"^^xsd:dateTime && ?dsEndDate >= "''' + dateEnd + '''"^^xsd:dateTime)
        }
            '''

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
        dEvLoc = {  # ?ds ?dsTitle ?dsGeo
            'dsURL': [ds['ds']['value'] for ds in rEvLoc],
            'file': [ds['dsTitle']['value'] for ds in rEvLoc],
            'lat': [ds['dsGeo']['value'].strip('POINT()').split(' ')[1] for ds in rEvLoc],
            'lon': [ds['dsGeo']['value'].strip('POINT()').split(' ')[0] for ds in rEvLoc],
            'areaGeo': [ds['buffer']['value'] for ds in rEvLoc],
            'queryBodyGeo': qBody
        }

        
        return dEvLoc

    # Function that returns the season-alike events from input
    def evSeasonAlike(endpoint, date, daysBefore, daysAfter, prefixes):
        qBody = prefixes + '''
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

    def strfdelta(tdelta, fmt='{D:02}d {H:02}h {M:02}m {S:02}s', inputtype='timedelta'):
        """Convert a datetime.timedelta object or a regular number to a custom-
        formated string, just like the stftime() method does for datetime.datetime
        objects.

        The fmt argument allows custom formatting to be specified.  Fields can
        include seconds, minutes, hours, days, and weeks.  Each field is optional.

        Some examples:
            '{D:02}d {H:02}h {M:02}m {S:02}s' --> '05d 08h 04m 02s' (default)
            '{W}w {D}d {H}:{M:02}:{S:02}'     --> '4w 5d 8:04:02'
            '{D:2}d {H:2}:{M:02}:{S:02}'      --> ' 5d  8:04:02'
            '{H}h {S}s'                       --> '72h 800s'

        The inputtype argument allows tdelta to be a regular number instead of the
        default, which is a datetime.timedelta object.  Valid inputtype strings:
            's', 'seconds',
            'm', 'minutes',
            'h', 'hours',
            'd', 'days',
            'w', 'weeks'
        """

        # Convert tdelta to integer seconds.
        if inputtype == 'timedelta':
            remainder = int(tdelta.total_seconds())
        elif inputtype in ['s', 'seconds']:
            remainder = int(tdelta)
        elif inputtype in ['m', 'minutes']:
            remainder = int(tdelta) * 60
        elif inputtype in ['h', 'hours']:
            remainder = int(tdelta) * 3600
        elif inputtype in ['d', 'days']:
            remainder = int(tdelta) * 86400
        elif inputtype in ['w', 'weeks']:
            remainder = int(tdelta) * 604800

        f = Formatter()
        desired_fields = [field_tuple[1] for field_tuple in f.parse(fmt)]
        possible_fields = ('W', 'D', 'H', 'M', 'S')
        constants = {'W': 604800, 'D': 86400, 'H': 3600, 'M': 60, 'S': 1}
        values = {}
        for field in possible_fields:
            if field in desired_fields and field in constants:
                values[field], remainder = divmod(remainder, constants[field])
        return f.format(fmt, **values)

    # String to iri
    def strToIri(stringL):
        return ['<' + string + '>' for string in stringL]

    # Select values for a specific key
    def selectValueKey(df, keyN):
        return df.loc[df['key'] == keyN, 'value'].iloc[0]

    # Flatten list
    def flatten(d):
        return [i for b in [[i] if not isinstance(i, list) else flatten(i) for i in d] for i in b]

    # read user input data
    # df_input = pd.read_csv(df_input_file)
    # start serdif-geosparql SPARQL endpoint
    start_geosparql = 'java -jar data/jena-fuseki-geosparql-4.7.0.jar -t data/serdif-geosparql -i'
    # run start_geosparql command in shell in the background and continue with the code while printing the output
    p_geosparql = Popen(shlex.split(start_geosparql), start_new_session=True,
                        shell=False, stdout=DEVNULL,
    stderr=STDOUT)  # , stdout=PIPE) #, stderr=STDOUT, text=True)  # preexec_fn=os.setsid,
    # wait for the endpoint to start
    print('\nWaiting 10s for the endpoint to start...')
    time.sleep(10)
    # p_geosparql.wait()
    # iterate over each row of the df_input to build a list of dataframes
    df_list_0 = []
    df_geo_list = []
    df_tw_list = []
    ds_used = {
        'obs': [],
        'evName': [],
        'evGroup': [],
        'evDatetime': [],
        'evPoint': [],
        'evStart': [],
        'evLag': [],
        'evArea': [],
        'datasetsL': [],
        'datasets': [],
        'file_name': [],
        'file_ext': [],
        'file_size': [],
        'file_ext_url': [],
    }
    # make the event column in df_input unique based on index
    # df_input['id'].astype(str) + '_' + df_input['group'].astype(str) +

    df_input['obs'] = 'obs_' + df_input.index.astype(str)
    for index, row in tqdm(df_input.iterrows()):
        # print('\nEvent: ' + row['event'])
        # get the time window for each event
        dic_tw = evTimeWindow(
            endpoint=endpointURL, date=row['date'],
            lag=row['lag'], length=row['length']
        )
        #print(dic_tw)
        dic_tw['obs'] = row['obs']
        dic_tw['id'] = row['id']
        dic_tw['group'] = row['group']
        # convert dictionary to dataframe
        df_tw_dic = pd.DataFrame(dic_tw, index=[index])
        df_tw_list.append(df_tw_dic)
        # print('\nTime window: ' + str(dic_tw['dateStart']) + ' - ' + str(dic_tw['dateLag']))
        # check if the input is numeric (radius) or an area and link the data accordingly
        try:
            sp_var = row['spatial'] + 42
            # get the datasets within a geographical area and time window
            buffer_geo = geodesic_point_buffer(lat=row['latitude'], lon=row['longitude'], km=row['spatial'])
            dic_ds = envoDataLocBuffer(
                endpoint=endpointURL, buffer=buffer_geo,
                dateStart=dic_tw['dateStart'], dateEnd=dic_tw['dateLag'],
                prefixes=prefixes_serdif, queryTimeStr=queryTimeStr
            )
    
            spatialLink_var = str(row['spatial']) + 'km'
        except TypeError:
            # get the datasets within a geographical area and time window
            dic_ds = envoDataLoc(
                endpoint=endpointURL,
                lat=row['lat'], lon=row['lon'], level=row['spatial'][-1],
                dateStart=dic_tw['dateStart'], dateEnd=dic_tw['dateLag'],
                queryTimeStr=queryTimeStr,
            )
            spatialLink_var = str(row['spatial'])


        # print('\nDatasets: ' + str(dic_ds['file']))
        # add event information to dictionary for provenance

        # iterate over each row (event) of the df_ds to build a list of dataframes
        df_list_1 = []
        # convert dictionary to dataframe
        df_ds = pd.DataFrame(dic_ds)
        df_geo_list.append(df_ds)
        #print(df_ds.head())
        # if no datasets have been linked to the event, add empty dataframe to list_1
        if df_ds.empty:
            # add empty dataframe to list_1
            df_ev = pd.DataFrame()
            df_list_1.append(df_ev)
        else:
            ds_used['obs'].append(row['obs'])
            ds_used['evName'].append(row['id'])
            ds_used['evGroup'].append(row['group'])
            ds_used['evDatetime'].append(row['date'] + 'T00:00:00Z')
            ds_used['evPoint'].append('POINT(' + str(row['longitude']) + ' ' + str(row['latitude']) + ')')
            ds_used['evStart'].append(dic_tw['dateStart'])
            ds_used['evLag'].append(dic_tw['dateLag'])
            ds_used['evArea'].append(dic_ds['areaGeo'])
            ds_used['file_name'].append([os.path.splitext(file)[0] for file in dic_ds['file']])
            ds_used['file_ext'].append([os.path.splitext(file)[1][1:] for file in dic_ds['file']])
            ds_used['file_size'].append([os.path.getsize(raw_folder + '/' + file) for file in dic_ds['file']])

            for filename in dic_ds['file']:
                if filename.endswith('.csv'):
                    ds_used['file_ext_url'].append('<https://www.iana.org/assignments/media-types/text/csv>')
                elif filename.endswith('.nc'):
                    ds_used['file_ext_url'].append('<https://www.iana.org/assignments/media-types/application/netcdf>')

        for index2, row2 in df_ds.iterrows():
            # select dataset file
            filename = row2['file']
            # open netcdf file and convert to pandas dataframe
            if filename.endswith('.nc'):
                dnc = xr.open_dataset(raw_folder + '/' + filename)
                df_dnc = dnc.to_dataframe()
                # convert multiindex to columns
                df_dnc.reset_index(inplace=True)
            if filename.endswith('.tsv'):
                df_dnc = pd.read_csv(filename, index_col=False, delimiter='\t', parse_dates=['time'])
                
            # subset dataset by specific lon/lat and time window
            startDate_dt = datetime.strptime(dic_tw['dateStart'][:-1], '%Y-%m-%dT%H:%M:%S')
            endDate_dt = datetime.strptime(dic_tw['dateLag'][:-1], '%Y-%m-%dT%H:%M:%S')
            # df_ev = df_dnc[(df_dnc['longitude'] == row2['lon']) & (df_dnc['latitude'] == row2['lat']) & \
            #               (df_dnc['time'] >= startDate_dt) & (df_dnc['time'] <= endDate_dt)
            #               ]
            df_ev = df_dnc[
                np.isclose(df_dnc['longitude'], float(row2['lon']), atol=1e-6) & 
                np.isclose(df_dnc['latitude'], float(row2['lat']), atol=1e-6) & 
                (df_dnc['time'] >= startDate_dt) & (df_dnc['time'] <= endDate_dt)
            ]
        
            # convert dataframe to long format
            df_ev = pd.melt(df_ev, id_vars=['longitude', 'latitude', 'time'], value_vars=list(dnc.keys()))
            # convert variable column to all capital letters
            df_ev['variable'] = df_ev['variable'].str.upper()
            df_ev['obs'] = row['obs']
            df_ev['id'] = row['id']
            df_ev['group'] = row['group']
            # add filename column to df_ev with the name of the dataset + longitude and latitude
            df_ev.insert(1, 'prov', os.path.splitext(filename)[0])
            
            df_list_1.append(df_ev)
            # print('\nDataset: ' + filename + ' - ' + row['id'])

        # concat list of dataframes
        df_temp_1 = pd.concat(df_list_1, ignore_index=True)
        # add dataframe to list_1
        df_list_0.append(df_temp_1)

    print('\nEvent and health data linked successfully')
    printProgressBar(4, prefix='Progress:', suffix='Completed', decimals=1,
                     length=50, fill='=', printEnd="\r", total=8)
    # concat list of geo dataframes
    df_geo = pd.concat(df_geo_list, ignore_index=True)
    df_tw = pd.concat(df_tw_list, ignore_index=True)
    # concat each of the elements in the list of lists of file_name and file_ext into a nested list of strings
    new_ds = []
    for nameL, extL in zip(ds_used['file_name'], ds_used['file_ext']):
        new_ds.append(['serdif-dataset:' + name + '-' + ext for name, ext in zip(nameL, extL)])
    ds_used['datasetsL'] = list(set(flatten(new_ds)))
    ds_used['datasets'] = [', '.join(dsL) for dsL in new_ds]
    # kill serdif-geosparql SPARQL endpoint for offline import
    p_geosparql.terminate()
    # p_geosparql.wait()
    # os.kill(os.getpgid(p_geosparql.pid), signal.SIGKILL)
    # concat list of dataframes
    df_temp_0 = pd.concat(df_list_0, ignore_index=True)
    #print(df_temp_0.head())

    
    # add lag column based on input events and merged data
    # convert date and time columns to datetime
    # add 23h to the date column to fix lag issue
    df_input['date'] = pd.to_datetime(df_input['date']) + timedelta(hours=23, minutes=59, seconds=59)
    # df_input['date'] = pd.to_datetime(df_input['date'])
    df_temp_0['time'] = pd.to_datetime(df_temp_0['time'])

    # iterate over df_event
    lag_list = []
    for index, row in df_input.iterrows():
        # get the event
        event = row['obs']
        # get the date
        date = row['date']
        # add a lag column in the df_data
        df_time = df_temp_0.loc[df_temp_0['obs'] == event, 'time']
        # compute the lag
        lag = df_time - date
        # print the lag
        lag_list.append(lag)

    # concat series in lag_list
    lag_conc = pd.concat(lag_list)
    df_temp_0['lag'] = [str(strfdelta(abs(lag), '{D:2}{H:02}{M:02}{S:02}')) for lag in lag_conc]
    # reorder df_temp_0 columns
    df_temp_0 = df_temp_0[['obs','id', 'group', 'prov', 'longitude', 'latitude', 'time', 'lag', 'variable', 'value']]

    # save dataframe to csv
    # make folder to store the output
    outfolder = './ee-output-QT_' + queryTimeStr
    df_temp_0.to_csv(outfolder + '/ds_' + queryTimeStr + '_raw.csv', index=False)
    # compute the maximum and minimum dates for the raw dataset
    min_dateTime = df_temp_0['time'].min().strftime('%Y-%m-%dT%H:%M:%SZ')
    max_dateTime = df_temp_0['time'].max().strftime('%Y-%m-%dT%H:%M:%SZ')

    # load environment (directory) for jinja2 templates
    file_loader = FileSystemLoader('templates')
    env = Environment(loader=file_loader)
    # load dataset mapping template file
    tempMap = env.get_template('dataset-qb-map-template.ttl')
    # set dataset name
    ds_name = 'ds_' + queryTimeStr
    # set data dictionary for input
    tempMap_dict = {'dsName': ds_name,
                    'dsNameCSV': ds_name + '_raw',
                    'qTime': queryTimeStr,
                    'user': socket.gethostname(),
                    'outFolder': outfolder}
    outMap = tempMap.stream(data=tempMap_dict)
    # export resulting mapping
    outMap.dump(outfolder + '/' + ds_name + '_map.ttl')
    # load .properties template file
    tempProp = env.get_template('dataset-qb-template.properties')
    # set data dictionary for input
    outProp = tempProp.stream(data=tempMap_dict)
    # export resulting mapping properties file
    outPropName = outfolder + '/' + ds_name + '_map.properties'
    outProp.dump(outPropName)
    # uplift metadata file to rdf
    uplift_ds = 'java -Xmx4112m -jar data/r2rml/r2rml-v1.2.3b/r2rml.jar ' + outfolder + '/' + ds_name + '_map.properties',
    p_uplift_ds = run(uplift_ds, shell=True)
    # wait for the endpoint to start
    print('\nLinked data uplifted to RDF successfully')
    printProgressBar(5, prefix='Progress:', suffix='Completed', decimals=1,
                     length=50, fill='=', printEnd="\r", total=8)
    print('\nData sources uplifted to RDF in ', datetime.now() - startTime)

    # Build html
    # aggregate the values in df_temp_0 by unit of time based on time_Unit input
    if time_Unit == 'hour':
        df_temp_0['time'] = df_temp_0['time'].dt.to_period('H').dt.to_timestamp()
    if time_Unit == 'day':
        df_temp_0['time'] = df_temp_0['time'].dt.to_period('D').dt.to_timestamp()
        df_temp_0['lag'] = (df_temp_0['lag'].astype(float) / 1000000).astype(int)
    if time_Unit == 'month':
        df_temp_0['time'] = df_temp_0['time'].dt.to_period('M').dt.to_timestamp()
        df_temp_0['lag'] = df_temp_0['lag'].astype(float) / 1000000
    if time_Unit == 'year':
        df_temp_0['time'] = df_temp_0['time'].dt.to_period('Y').dt.to_timestamp()
        df_temp_0['lag'] = df_temp_0['lag'].astype(float) / 1000000
    # compute the mean of the variables per event at a monthly frequency from time column and
    # add a column with the first lag based on event, time and variable
    if agg_method == 'avg':
        df_agg = df_temp_0.groupby(['obs','id', 'group', 'time', 'variable'])['value'].mean().reset_index()
        df_agg.insert(2, 'lag',
                      df_temp_0.groupby(['obs','id', 'group', 'time', 'variable'])['lag'].first().reset_index()['lag'])
    if agg_method == 'sum':
        df_agg = df_temp_0.groupby(['obs','id', 'group', 'time', 'variable'])['value'].sum().reset_index()
        df_agg.insert(2, 'lag',
                      df_temp_0.groupby(['obs','id', 'group', 'time', 'variable'])['lag'].first().reset_index()['lag'])
    if agg_method == 'min':
        df_agg = df_temp_0.groupby(['obs','id', 'group', 'time', 'variable'])['value'].min().reset_index()
        df_agg.insert(2, 'lag',
                      df_temp_0.groupby(['obs','id', 'group', 'time', 'variable'])['lag'].first().reset_index()['lag'])
    if agg_method == 'max':
        df_agg = df_temp_0.groupby(['obs','id', 'group', 'time', 'variable'])['value'].max().reset_index()
        df_agg.insert(2, 'lag',
                      df_temp_0.groupby(['obs','id', 'group', 'time', 'variable'])['lag'].first().reset_index()['lag'])
    # reshape df_agg from long to wide
    df_agg_wide = pd.pivot(df_agg, index=['obs', 'id', 'group', 'time', 'lag'], columns='variable', values='value')
    df_agg_wide.reset_index(inplace=True)
    df_agg_wide = df_agg_wide.sort_values(by=['obs', 'lag'])
    df_agg_wide.to_csv(outfolder + '/ds_' + queryTimeStr + '_obs_' + agg_method + '.csv', index=False)
    # summarize the data in df_agg by event, group and variable and create a new mean, std, median, sum,
    # min and max columns
    df_agg_sum = df_agg.groupby(['obs', 'id', 'group', 'variable']). \
        agg({'value': ['mean', 'std', 'median', 'sum', 'min', 'max']}).reset_index()
    # flatten the multi-index columns
    df_agg_sum.columns = [''.join(col).strip().replace('value', '') for col in df_agg_sum.columns.values]
    # add date, length and lag columns from df_input to df_agg_sum by matching event and group
    df_agg_sum = df_agg_sum.merge(df_input[['obs','id', 'group', 'date', 'length', 'lag']], on=['obs', 'id', 'group'])
    # reorder columns in df_agg_sum
    df_agg_sum = df_agg_sum[
        ['obs', 'id', 'group', 'date', 'length', 'lag', 'variable', 'mean', 'std', 'median', 'sum', 'min', 'max']]
    df_agg_sum['date'] = df_agg_sum['date'].dt.date
    # save df_agg_sum as csv
    df_agg_sum.to_csv(outfolder + '/ds_' + queryTimeStr + '_summary.csv', index=False)
    print('\nLinked data stored as CSV files successfully')
    printProgressBar(6, prefix='Progress:', suffix='Completed', decimals=1,
                     length=50, fill='=', printEnd="\r", total=8)
    # select variables to plot
    col_vars = df_agg_wide.columns[5:].values.tolist()

    # drop event and time columns from df_agg_wide
    df_agg_wide.drop(columns=['obs', 'id', 'time'], inplace=True)
    df_agg_wide = df_agg_wide.sort_values(by=['group', 'lag'])
    df_agg_wide_lag = df_agg_wide.groupby(['group', 'lag']).mean().reset_index()

    # plot lineplot of lag per variable
    # Define buttons to select variables while respecting the groups (events)
    fig = go.Figure()
    for col in col_vars:
        figpx = px.line(
            data_frame=df_agg_wide_lag.assign(Plot=col),
            x='lag', y=col,
            color='group',
            hover_data=['Plot'],
            color_discrete_sequence=px.colors.qualitative.G10).update_traces(visible=False)
        fig.add_traces(figpx.data)
        figbox = px.box(
            data_frame=df_agg_wide.assign(Plot=col + '_box'),
            x='lag', y=col,
            color='group',
            hover_data=['Plot'],
            color_discrete_sequence=px.colors.qualitative.G10).update_traces(visible=False)
        fig.add_traces(figbox.data)

    # for every trace that represents a line set visible to True, and for a boxplot set the visible to legendonly
    def get_visibility(trace, var_name):
        if trace == var_name:
            return True
        elif trace == var_name + '_box':
            return 'legendonly'
        else:
            return False

    fig.update_layout(
        updatemenus=[
            {
                'buttons':
                    [
                        {
                            'label': f'Variable - {k}',
                            'method': 'update',
                            'args':
                                [
                                    {'visible': [get_visibility(trace=t.customdata[0][0], var_name=k) for t in
                                                 fig.data]},
                                    {
                                        'yaxis': {
                                            'title': k,
                                            'showline': True, 'linewidth': 1.5,
                                            'linecolor': 'black', 'mirror': True, 'ticks': 'outside'
                                        },
                                    },

                                ],
                        }
                        for k in col_vars
                    ],
                'y': 1.15,
                'x': 0.1,
            }
        ],
        font=dict(size=20),
        plot_bgcolor='rgba(0,0,0,0)',
        height=400,
        legend=dict(title='group', groupclick='toggleitem'),
        hovermode='x unified',
        margin={'l': 5, 'r': 5, 't': 5, 'b': 0},

    ).update_traces(visible=True, selector=lambda t: t.customdata[0][0] == col_vars[0]). \
        update_traces(visible='legendonly', selector=lambda t: t.customdata[0][0] == col_vars[0] + '_box')
    if time_Unit == 'raw':
        lagtitle = 'Lag [{D:2}{H:02}{M:02}{S:02}]'
    else:
        lagtitle = 'Lag [days]'

    fig.update_xaxes(showline=True, linewidth=1.5, autorange='reversed', title=lagtitle,
                     linecolor='black', mirror=True, ticks='outside')

    fig_dist = go.Figure()
    for col in col_vars:
        figdist = px.histogram(
            data_frame=df_agg_wide.assign(Plot=col),
            x=col,
            color='group',
            hover_name='group',
            barmode='overlay',
            color_discrete_sequence=px.colors.qualitative.G10).update_traces(visible=False)
        fig_dist.add_traces(figdist.data)
    fig_dist.update_layout(
        updatemenus=[
            {
                'buttons':
                    [
                        {
                            'label': f'Variable - {k}',
                            'method': 'update',
                            'args':
                                [
                                    {'visible': [col_vars[0] in t.hovertemplate for t in
                                                 fig_dist.data]},
                                    {
                                        'xaxis': {
                                            'title': k,
                                            'showline': True, 'linewidth': 1.5,
                                            'linecolor': 'black', 'mirror': True, 'ticks': 'outside'
                                        }
                                    },

                                ],
                        }
                        for k in col_vars
                    ],
                'y': 1.15,
                'x': 0.1,
            }
        ],
        font=dict(size=20),
        plot_bgcolor='rgba(0,0,0,0)',
        height=400,
        # legend=dict(title='group', groupclick='toggleitem'),
        # hovermode='x unified',
        margin={'l': 5, 'r': 5, 't': 5, 'b': 0},
        barmode='overlay',

    ).update_traces(visible=True, selector=lambda t: col_vars[0] in t.hovertemplate)

    fig_dist.update_xaxes(showline=True, linewidth=1.5, title=col_vars[0],
                          linecolor='black', mirror=True, ticks='outside')
    fig_dist.update_yaxes(showline=True, linewidth=1.5, title='Count',
                          linecolor='black', mirror=True, ticks='outside')

    # import serdif html report template
    htmlMap = env.get_template('serdif-report-templates-sum.html')
    # convert df_input to html
    df_input_html = df_input.to_html(
        classes='table',
        justify='center', table_id='evTable')
    # convert df_input to html
    df_agg_sum.drop(columns=['obs', 'id', 'date', 'length', 'lag'], inplace=True)
    df_agg_html = df_agg_sum.groupby(['group', 'variable']).mean().reset_index()
    #print(df_agg_html.head())

    html_table = df_agg_html.to_html(
        classes='table',
        na_rep='', justify='center', table_id='sortTable',
    ).replace('<tbody>', '<tbody id="myTable">')

    # Parse html to enable tag selection
    soup_v = BeautifulSoup(html_table, 'html.parser')

    # Add tooltip to column headers
    # table_header = ['row_id', 'event ID', 'group', 'event datetime', 'time between the data and the event [days]'] + col_vars
    table_header = ['id', 'group', 'variable', 'mean', 'std', 'median', 'sum', 'min', 'max']
    table_header_loop = table_header[1:]
    for h in soup_v.select('thead'):
        for num, th in enumerate(h.find_all('th')):
            th['title'] = table_header[num]

    for h in soup_v.select('tbody'):
        for num, td in enumerate(h.find_all('td')):
            idx = num % len(table_header_loop) if num else 0
            td['data-cell'] = table_header_loop[idx]
    # Count percentage of missing values without "event", "date" and "lag" columns
    df_miss = df_agg_wide.drop(['group'], axis=1)
    #print(df_miss.head())
    miss_count = df_miss.isnull().values.sum()
    notmiss_count = df_miss.notnull().values.sum()
    miss_ratio = (miss_count / (miss_count + notmiss_count)) * 100
    # convert queryTimeStr to valid SPARQL datetime
    queryTime = datetime.strptime(queryTimeStr + 'Z', '%Y%m%dT%H%M%SZ').strftime('%Y-%m-%dT%H:%M:%SZ')
    # identify datasets available in raw data folder
    raw_datasets = glob.glob(raw_folder + '/*')
    # join raw_datasets names to a string
    raw_datasets_join = ', '.join(raw_datasets)
    # plot the spatial link between datasets and input events
    # select unique lat-lon pairs
    df_evds_latlon = df_temp_0.groupby(['obs','id', 'group', 'prov', 'longitude', 'latitude'], sort=False, as_index=False)[
        'time'].idxmin()
    df_evds_latlon.reset_index(inplace=True)
    df_evds_latlon['longitude'] = df_evds_latlon['longitude']  # .apply(lambda x: x.split('point(')[1].split('_')[0])
    df_evds_latlon['latitude'] = df_evds_latlon[
        'latitude']  # .apply(lambda x: x.split('point(')[1].split('_')[1].split(')')[0])
    # compute the mean event location to center the map
    lat_zoom = df_input['latitude'].mean()
    lon_zoom = df_input['longitude'].mean()
    df_geod = df_geo.drop_duplicates(subset=['areaGeo'], keep='first')
    fig_map = px.choropleth_mapbox(
        df_geo,
        geojson=gpd.GeoSeries(df_geod['areaGeo'].apply(shapely.wkt.loads)).__geo_interface__,
        locations=df_geod.index,
        color_discrete_map={'area': '#1f618d'},
        color=['area'] * len(df_geod['areaGeo']),
        opacity=0.4,
    ).update_layout(
        mapbox={'style': 'carto-positron',
                'center': {'lat': lat_zoom, 'lon': lon_zoom},
                'zoom': 5,
                },
        autosize=True,
        hovermode='closest',
        margin={'r': 0, 't': 0, 'l': 0, 'b': 0},
        legend={
            'orientation': 'h',
            'yanchor': 'bottom',
            'y': 1.02,
            'xanchor': 'left',
            'x': 0},
    )
    fig_map.add_scattermapbox(
        lat=df_input['latitude'],
        lon=df_input['longitude'],
        mode='markers+text',
        text=df_input['obs'] + '_' + df_input['id'],
        marker_size=20,
        marker_color='#d35400',
        name='id',
    )
    fig_map.add_scattermapbox(
        lat=df_evds_latlon['latitude'],
        lon=df_evds_latlon['longitude'],
        mode='markers+text',
        text=df_evds_latlon['id'],
        marker_size=12,
        marker_color='#1e8449',
        name='datasets',
    )
    # Generate timeline figure for input events
    fig_timeline = px.timeline(
        df_tw, x_start='dateStart', x_end='dateLag',
        y='group', color='group', opacity=0.6)
    fig_timeline.update_xaxes(
        showline=True, linewidth=1.5,
        linecolor='black', mirror=True, ticks='outside')
    fig_timeline.update_yaxes(
        showline=True, linewidth=1.5, title='',
        linecolor='black', mirror=True, ticks='outside')
    fig_timeline.update_layout(
        font=dict(size=20),
        plot_bgcolor='rgba(0,0,0,0)',
        # shapes=shapesList,
        height=400,
        # width=800,
    )
    # Build dictionary for html template
    htmldata_dict = {
        'date': datetime.strftime(datetime.now(), '%b %-d, %Y'),
        # 'dsraw': raw_datasets_join,
        'spOption1': spatialLink_var,
        # 'areaText': spatialLink_sel['text'],
        'datasetmap': fig_map.to_html(full_html=False, include_plotlyjs='cdn'),
        'timeline': fig_timeline.to_html(full_html=False, include_plotlyjs='cdn'),
        'aggMethod': agg_method,
        'timeUnit': time_Unit,
        # 'eventTable': df_input_html,
        # 'context': selectValueKey(df=df_info, keyN='eventName'),
        # 'version': version,
        # 'queryDateTime': queryTime,
        'publisher': selectValueKey(df=df_info, keyN='publisher'),
        'dataController': selectValueKey(df=df_info, keyN='dataController'),
        'orcid': selectValueKey(df=df_info, keyN='dataProcessor'),
        'license': selectValueKey(df=df_info, keyN='license'),
        'dataTableMissing': miss_ratio.round(0),
        'dataTable': soup_v,
        'tsFigure': fig.to_html(full_html=False, include_plotlyjs='cdn'),
        'distFigure': fig_dist.to_html(full_html=False, include_plotlyjs='cdn'),
        'queryTimeStr': queryTimeStr,

    }

    outMap = htmlMap.stream(data=htmldata_dict)
    # Export resulting html report
    outMap.dump(outfolder + '/' + ds_name + '_report.html')
    print('\nLinked data summary report generated successfully')
    printProgressBar(7, prefix='Progress:', suffix='Completed', decimals=1,
                     length=50, fill='=', printEnd="\r", total=8)
    # Metadata information for the generated linked data
    # 1. Generate mapping file from template
    # Load eea template file
    metaMap = env.get_template('serdif-dataset-metadata-template.ttl')

    # convert time unit input to xsd:duration
    selTimeRes = {'raw': '', 'hour': 'PT1H', 'day': 'P1D', 'month': 'P1M', 'year': 'P1Y'}

    metaMap_dict = {
        # -- Data Set ----------------------------------------------------------
        'queryTimeStr': queryTimeStr,
        'context': selectValueKey(df=df_info, keyN='context'),
        'timeUnit': time_Unit,
        'version': version,
        'queryDateTime': queryTime,
        'publisher': '<' + selectValueKey(df=df_info, keyN='publisher') + '>',
        'license': '<' + selectValueKey(df=df_info, keyN='license') + '>',
        'timeRes': selTimeRes[time_Unit],
        'eventNameList': df_input['id'].values.tolist(),
        'dataController': '<' + selectValueKey(df=df_info, keyN='dataController') + '>',
        'orcid': '<' + selectValueKey(df=df_info, keyN='dataProcessor') + '>',
        # -- Distribution -------------------------------------------------------
        'fileSizeTRIG': os.path.getsize(outfolder + '/' + ds_name + '.trig'),
        'fileSizeCSV': os.path.getsize(outfolder + '/' + ds_name + '_raw.csv'),
        'fileSizeMap': os.path.getsize(outfolder + '/' + ds_name + '_map.ttl'),
        # -- Datasets used ---------------------------------------------------
        'extDataSetsUsedDict': zip(*[flatten(ds_used['file_name']), flatten(ds_used['file_ext']),
                                     flatten(ds_used['file_ext_url']), flatten(ds_used['file_size'])]),
        # -- Period of time included in the data set ---------------------------
        'startDateTime': min_dateTime,
        'endDateTime': max_dateTime,
        # -- Region geometries -------------------------------------------------
        'dsgeo': ', '.join(['"' + area + '"^^<http://www.opengis.net/ont/geosparql#wktLiteral>'
                            for area in df_geo['areaGeo'].values.tolist()]),
        # -- Data provenance and lineage ---------------------------------------
        'extDataSetsUsedDictL': ds_used['datasetsL'],
        'queryTextSelect': df_geo['queryBodyGeo'].values.tolist(),
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
        'eeVarsL': col_vars,
        'eeVarsText': col_vars,
        # -- Event Description -----------------------------------------------
        'eventDict': zip(*[
            ds_used['evName'], ds_used['evDatetime'], ds_used['evPoint'],
            ds_used['evStart'], ds_used['evLag'], flatten(ds_used['evArea']),
            ds_used['datasets']
        ]),
    }
    # pprint(metaMap_dict['eventDict'])
    outMap = metaMap.stream(data=metaMap_dict)
    # Export resulting mapping
    outMap.dump(outfolder + '/metadata_' + ds_name + '.ttl')

    # Zip output folder to send
    shutil.make_archive(
        'linked-ee-pack-' + version + '-QT_' + queryTimeStr,
        'zip',
        outfolder,
    )
    queryLogLine = 'Query: ' + queryTime + '\tLinking time: ' + str(datetime.now() - startTime) + '\n'
    print(queryLogLine)
    # Remove folder after sending the zip file
    if os.path.exists(outfolder):
        shutil.rmtree(outfolder, ignore_errors=True)
    #
    # call(['rm -r data/serdif-geosparql'], shell=True) 
    call(['find . -maxdepth 1 -name "*.zip" -type f -mtime +1 -exec rm -f {} +', ], shell=True)
    print('\nLinked data zip file ready in your local folder')
    printProgressBar(8, prefix='Progress:', suffix='Completed', decimals=1,
                     length=50, fill='=', printEnd="\r", total=8)
    return './linked-ee-pack-' + version + '-QT_' + queryTimeStr + '.zip'


