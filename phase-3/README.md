# Phase 3

## Knowledge Graph (KG)

The KG is made available at: [https://serdif-kg.adaptcentre.ie/](https://serdif-kg.adaptcentre.ie/)

## User Interface (UI)

The serdif-ui is available at [https://serdif-ui.adaptcentre.ie/](https://serdif-ui.adaptcentre.ie/)

### Key Concepts

* **Event**: something that occurs in a certain place during a particular time.

* **Data linkage**: result of a semantic query that integrates environmental data **within the region of the event** and 
selects a **period of data before the event**.

<p align="center">
  <img src="assets/environmental_data_before_event.png" />
</p>

###  How does it work?

#### Step 1: Upload Event Dataset to Link

The event data set only requires location and time for each event as the following example dataset:

| event | lon    | lat     | date       | length | lag |
|-------|--------|---------|------------|--------|-----|
| A     | 8.549  | 47.366  | 2011-02-05 | 14     | 0   |
| B     | 9.3852 | 47.431  | 2011-08-20 | 14     | 7   |
| C     | 7.4218 | 46.926  | 2011-11-01 | 14     | 14  |
| D     | 8.3007 | 47.0156 | 2011-04-30 | 14     | 0   |

* **event**: Name of the event (only letters, numbers and dashed without spaces)
* **lon**: Longitude coordinate of the event's location (numeric)
* **lat**: Latitude coordinate of the event's location (numeric)
* **date**: Date of the event (YYYY-MM-DD)
* **length**: Time interval to gather data (days)
* **lag**: Time between the data and the event (days)

Environmental data available:


| **Data type** | **Data source** | **Period** | **Time resolution** | **Country**                                                 |
|---------------|-----------------|------------|---------------------|-------------------------------------------------------------|
| Climate       | [Copernicus](https://cds.climate.copernicus.eu/cdsapp#!/dataset/insitu-gridded-observations-europe?tab=overview)      | 2011-2020  | Daily               | Europe                                                      |
| Air Pollution | [EEA](https://www.eea.europa.eu/data-and-maps/data/aqereporting-9)             | 2011-2020  | Daily               | Czech Republic, Ireland, Switzerland, United Kingdom, Italy |

Example of environmental data uplifted to RDF:

* Albert Navarro-Gallinad. (2021). Weather and Air Quality data for Ireland as RDF data cube (20211012T120000) [Data set]. Zenodo. https://doi.org/10.5281/zenodo.5668287

#### Step 2: Select Data Linkage Options

Select from the linkage options that are more relevant to your particular use case. Once the linkage options have been selected, the options will be substituted into a SPARQL query template and run against the [https://serdif-kg.adaptcentre.ie/](https://serdif-kg.adaptcentre.ie/) endpoint 
hosted in a [Ontotext GraphDB Free](https://graphdb.ontotext.com/) triplestore within
the [ADAPT centre](https://www.adaptcentre.ie/) at [Trinity College Dublin](https://www.tcd.ie/).

#### Step 3: Export the Output
The resulting event-environmental linked data is compressed in a zip file that contains:

1. The data for analysis as a data table and/or graph
2. The metadata for research or publication
3. The interactive report to explore the (meta)data 

### Setup

This process designs an initial visual tool to grant meaningful access to domain experts.
Run the following commands to install the necessary python libraries and deploy the SERDIF-UI:

`pip install -r requirements.txt`

`python app.py`

Then, type http://0.0.0.0:5000/ in your browser to access the dashboard.
