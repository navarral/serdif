# Phase 2 version

## Knowledge Graph (KG)

The KG is made available in: https://serdif-example.adaptcentre.ie/

## User Interface (UI)

### 4. Data visualization
This process designs an initial visual tool to grant meaningful access to domain experts.
Run the following commands to install the necessary python libraries and deploy the SERDIF-UI:

`venv/bin/python3 app.py `

If the previous command does not work for you please use the following:

`source venv/bin/activate`

`pip install -r requirements.txt`

`python app.py`

Then, type http://0.0.0.0:5000/ in your browser to access the dashboard.

### 5. Data exporting/downlift

This process exports combined and/or aggregated data from the Knowledge Graph in tabular format for analysis. The results from the SPARQL query can be exported as a table (CSV), which is the preferred input format for data analysis, through the dashboard.
