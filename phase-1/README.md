# Phase 1 version

## Knowledge Graph (KG)

### 1. Data collection

This process requires gathering clinical, environmental and geometry data. Sample data is provided in `data/raw/` of this repository to reproduce a minimal example of the KG component:

* Clinical data: simulated events within the Republic of Ireland
* Environmental data: weather and pollution sample data from [Met Éireann](https://www.met.ie//climate/available-data/historical-data) and [Environmental Protection Agency (EPA)](http://www.epa.ie/)
* Geometry data: counties and electoral district geometries for the Republic of Ireland

### 2. Semantic Uplift

This process designs a mapping to uplift the data gathered from the data collection process into the Knowledge Graph.

* Mappings: R2RML mappings for the data sources are stored in `data/mapping/`. The R2RML-F engine used in this paper was provided by [chrdebru](https://github.com/chrdebru/r2rml)
* Uplift data (convert CSV -> RDF): open a terminal in the `data` folder of the project and run `./GenerateRDF.sh` to uplift the tabular data to RDF. This script will generate approximately 1GB of data, please make sure you have enough space available.
* Download triplestore: register to GraphDB and download the free version **standalone server** from their [website](https://www.ontotext.com/products/graphdb/graphdb-free/) (e.g. graphdb-free-9.7.0-dist.zip file)
* Locate the triplestore: unzip the .zip into the project's main folder (e.g. graphdb-free-9.7.0/)
* Open a terminal in the project's main folder
* Preload repository with generated RDF: run

`graphdb-free-9.7.0/bin/preload -f -c preloadSerdifToy.ttl data/rdf/EpaAirQDataHly.trig data/rdf/EpaAirQMetadata.trig data/rdf/MetDataHly.trig data/rdf/MetMetadata.trig data/rdf/rndEvIre.trig data/rdf/NGraph_GeohiveData.trig`

(NB: this is an example for graphdb-free-9.4.1, please edit according to the downloaded version)
* Run triplestore to load files: `graphdb-free-9.7.0/bin/graphdb` (NB: edit the version of the triplestore as in the previous step)
* Leave the triplestore running: open you browser and type in `http://localhost:7200/` to check if it is running

### 3. Data querying and filtering

This process defines a spatio-temporal query as a SPARQL template.
Optional: if you have expertise on SPARQL language, then you can inspect the content of the the `serdif_AppQueries.py` (otherwise skip this step)

## User interface (UI)

### 4. Data visualization
This process designs an initial visual tool to grant meaningful access to domain experts.
Run the following commands to install the necessary python libraries and deploy the SERDIF-UI:

`pip install -r requirements.txt`

`python serdif_App.py`

Then, type `http://0.0.0.0:5000/` in your browser to access the dashboard.

To explore the dashboard plese read the information on the main panel, proceed to input Query options from the left panel and then click the submit botton ad the end of the panel. Environmental-patient associated data is ready to be explored in the new generated tab 'Q1'!

### 5. Data exporting/downlift

This process exports combined and/or aggregated data from the Knowledge Graph in tabular format for analysis. The results from the SPARQL query can be exported as a table (CSV), which is the preferred input format for data analysis, through the dashboard.
