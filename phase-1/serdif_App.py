# -*- coding: utf-8 -*-
import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import dash_table
from dash.dependencies import Input, Output, State, MATCH, ALL
from dash.exceptions import PreventUpdate
import pandas as pd
from scipy import stats
from collections import defaultdict
import json
import io
import copy
import numpy as np
import plotly.express as px
from datetime import datetime
# Libraries to set paths and download/upload files
from pathlib import Path
from flask import Flask, send_from_directory, send_file
# Functions to send queries
from serdif_AppQueries import serdifSamplers, serdifEOIdates, serdif_EnvData, serdif_EnvDesc, serdif_LOIs, \
    serdif_EnvDataAsk, \
    dataSourceSel
from serdif_SamplerMap import mapSamplersFig
import pytz
import plotly.figure_factory as ff
import zipfile

# Directory to save files locally, need to fix to make it portable
queryStoreDir = 'appFiles'
Path(queryStoreDir).mkdir(parents=True, exist_ok=True)

# Normally, Dash creates its own Flask server internally. By creating our own,
# we can create a route for downloading files directly:
server = Flask(__name__)


@server.route('/download/<path:path>')
def download(path):
    """Serve a file from the upload directory."""
    return send_from_directory(queryStoreDir, path, as_attachment=True)


# Set query parameters
#localHost = 'http://db:7200/'
localHost = 'http://localhost:7200/'
serdifRepoID = 'repositories/serdifToy'
queryVar = '?query='
QPrefixes = '''PREFIX sosa: <http://www.w3.org/ns/sosa/>
    PREFIX geo: <http://www.opengis.net/ont/geosparql#>
    PREFIX geof: <http://www.opengis.net/def/function/geosparql/>
    PREFIX osi: <http://ontologies.geohive.ie/osi#>
    PREFIX time: <http://www.w3.org/2006/time#>
    PREFIX dc: <http://purl.org/dc/terms/>
    PREFIX uom: <http://www.opengis.net/def/uom/OGC/1.0/>
    PREFIX unit: <http://qudt.org/vocab/unit#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    PREFIX qudt: <http://qudt.org/schema/qudt/>
    PREFIX dcat: <http://www.w3.org/ns/dcat#>
    PREFIX event: <http://purl.org/NET/c4dm/event.owl#> 
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX serdif: <http://serdif.org/kg/datasource/>
    '''


def listToOptions(optDM):
    listOpt = []
    for entry in optDM:
        dictID = {'label': entry, 'value': entry}
        listOpt.append(dictID)
    return listOpt


topNavbarHelical = dbc.NavbarSimple(
    children=[
        dbc.NavItem(dbc.NavLink("Helical", href="http://helical-itn.eu/")),
        dbc.DropdownMenu(
            nav=True,
            in_navbar=True,
            label="Analysis",
            children=[
                dbc.DropdownMenuItem("AVERT/HELICAL"),
                dbc.DropdownMenuItem("WINDBIOME"),
                dbc.DropdownMenuItem("FAIRVASC"),
            ],
        )
    ],
    brand='SERDIF - Semantic Environmental and Rare Disease data Integration Framework',
    brand_href='#',
    sticky='top',
)

tabQuery = dbc.Card([
    dbc.CardHeader('Input Options',
                   style={'fontWeight': 'bold'}
                   ),
    dbc.CardBody([
        html.Label('Rare Disease:', style={'fontWeight': 'bold'}),

        dcc.Dropdown(
            id='rareDisease',
            options=listToOptions(['ANCA vasculitis - Ireland']),
        ),
        # Store sampler data
        dbc.Spinner([
            dcc.Store(id='smpDataS'),
        ], color='info'),
        html.Div([
            html.Label('Event Of Interest (EOI): Flare   ', style={'fontWeight': 'bold'}),
            dbc.Button('i', id='eoiPopover', color='info',
                       style={'fontWeight': 'bold',
                              'margin-left': '1em',
                              'margin-top': '1em',
                              'margin-bottom': '1em',
                              'height': '25px',
                              'width': '25px',
                              'border-radius': '70%',
                              'text-align': 'center',
                              'padding': '0',
                              },
                       size='sm'),
            dbc.Popover(
                [
                    dbc.PopoverHeader('Definite'),
                    dbc.PopoverBody('''Active vasculitis with histopathological confirmation, treated with 
                    immunosuppression escalation, and clinical response to same.'''),
                    dbc.PopoverHeader('High probability'),
                    dbc.PopoverBody('''Active vasculitis supported by suggestive clinical features, biochemistry 
                    (c-reactive protein, creatinine, proteinuria, ANCA serology), urinalysis (red cells and casts) and/or
                    radiological investigation, treated with immunosuppression escalation, and clinical response to same,
                    but without histopathological confirmation.'''),
                    dbc.PopoverHeader('Possible'),
                    dbc.PopoverBody('''Active vasculitis on physician assessment, but limited supporting 
                    laboratory/radiological evidence, treated with immunosuppression escalation, and clinical response to same'''
                                    ),

                ],
                id='eoiPopoverText',
                is_open=False,
                target='eoiPopover',
            ),
        ]),

        dcc.Dropdown(
            id='eoi',
            options=[
                {'label': ' Definite', 'value': 'http://serdif.org/kg/datasource/event/RndEvIre/Definite'},
                {'label': ' High Probability',
                 'value': 'http://serdif.org/kg/datasource/event/RndEvIre/High%20Probability'},
                {'label': ' Possible', 'value': 'http://serdif.org/kg/datasource/event/RndEvIre/Possible'},
                {'label': ' No', 'value': 'http://serdif.org/kg/datasource/event/RndEvIre/No'}
            ],
            multi=True,
        ),
        html.Div([], style={'marginBottom': '0.5em'}),
        # Store EOI sum table
        dbc.Spinner([
            dcc.Store(id='eoiTable'),
        ], color='info'),
        # html.Label('EOI dates:', style={'fontWeight': 'bold'}),
        dash_table.DataTable(
            id='loiDate',
            page_size=3,
            column_selectable='single',
            style_cell={
                'overflow': 'hidden',
                'textOverflow': 'ellipsis',
                'maxWidth': 0,
                'textAlign': 'center',
                'whiteSpace': 'normal',
                'lineHeight': '15px'
                # 'height': 4,
            },
            style_header={
                'backgroundColor': 'whitesmoke',
                'fontWeight': 'bold',
                'color': 'black',
                'textDecoration': 'underline',
                'textDecorationStyle': 'dotted',
            },
            tooltip_duration=None,
            tooltip_header={'LOI': 'Location Of Interest',
                            'EOI_Count': 'Number of EOIs dates',
                            'smp_Count': 'Number of samplers available'},
            css=[{
                'selector': '.dash-table-tooltip',
                'rule': 'background-color: #A4DCD1'
            }],
            # row_deletable=True,
            # editable=True
        ),
        html.Div([], style={'marginBottom': '1em'}),
        html.Label('Location Of Interest (LOI):', style={'fontWeight': 'bold'}),
        dcc.Dropdown(
            id='loi',
            options=listToOptions(
                serdif_LOIs(endpointURL=localHost,
                            repoID=serdifRepoID,
                            QPrefixes=QPrefixes
                            )
            ),
            multi=True
        ),
        dcc.Checklist(
            id='allLOI',
            labelStyle={'display': 'none', 'margin-right': '20px'},
            # labelStyle={'display': 'inline-block', 'margin-right': '20px'},
            options=[{'label': '  Select all LOIs', 'value': 'GetAll'}],
            # value='G',
        ),

        # Flare options liked to Patient ID
        html.Div([
            html.Label('Time-window length [days]:', style={'fontWeight': 'bold'}),
            dcc.Input(
                id='wLength',
                type='number',
                min=1,
                # value=10,
                # step=10,
                style={'width': '5em', 'margin-left': '1em'},
            ),
        ], style={'marginTop': '1em', 'display': 'inline-block', 'margin-right': '2em'}),

        html.Div([
            html.Label('Time-window lag [days]:', style={'fontWeight': 'bold'}),
            dcc.Input(
                id='wLag',
                type='number',
                min=0,
                # value=10,
                # step=10,
                style={'width': '5em', 'margin-left': '1em'},
            ),
        ], style={'marginTop': '1em', 'display': 'inline-block', 'margin-right': '2em'}),

        html.Div([], style={'marginBottom': '0.5em'}),
        dcc.ConfirmDialog(
            id='checkDataQuery',
            message='''There is no data for the selected options\n
                    Please refer to the Data Point Density Map at the bottom of the home 
                    tab to check for a valid inputs''',
        ),
        html.Label(
            html.Div([
                'Temporal Units:  (',
                html.Span(' i ',
                          id='timeUnitTooltip',
                          style={'fontWeight': 'bold',
                                 'textDecoration': 'underline',
                                 'cursor': 'pointer'}
                          ), ')'
            ], style={'fontWeight': 'bold'}
            )
        ),
        dbc.Tooltip(
            dcc.Markdown(
                '''Data will be combined and aggregated at the following temporal unit'''
            ), target='timeUnitTooltip'
        ),
        dcc.RadioItems(id='timeUnit',
                       # labelStyle={'display': 'inline-block', 'margin-right': '20px'},
                       options=[
                           {'label': ' Hour ', 'value': 'Hourly'},
                           {'label': ' Day ', 'value': 'Daily'},
                           {'label': ' Month ', 'value': 'Monthly'},
                           {'label': ' Year ', 'value': 'Yearly'}
                       ],
                       # value='Hourly'
                       ),
        html.Label('Aggregations:', style={'fontWeight': 'bold'}),
        html.Div([], style={'marginBottom': '0.2em'}),
        html.Label(
            html.Div([
                '1. Spatial:  (',
                html.Span(' i ',
                          id='spatialAggTooltip',
                          style={'fontWeight': 'bold',
                                 'textDecoration': 'underline',
                                 'cursor': 'pointer'}
                          ), ')'
            ], style={'fontWeight': 'bold'}
            )
        ),
        dbc.Tooltip(
            dcc.Markdown(
                '''Spatial aggregation method for the samplers time series data within the LOI'''
            ), target='spatialAggTooltip'
        ),
        dcc.RadioItems(id='spatialAgg',
                       # labelStyle={'display': 'inline-block', 'margin-right': '20px'},
                       options=[
                           {'label': ' Mean ', 'value': 'AVG'},
                           {'label': ' Sum ', 'value': 'SUM'},
                           {'label': ' Min ', 'value': 'MIN'},
                           {'label': ' Max ', 'value': 'MAX'},
                       ],
                       ),
        html.Label(
            html.Div([
                '2. Temporal:  (',
                html.Span(' i ',
                          id='timeAggTooltip',
                          style={'fontWeight': 'bold',
                                 'textDecoration': 'underline',
                                 'cursor': 'pointer'}
                          ), ')'
            ], style={'fontWeight': 'bold'}
            )
        ),
        dbc.Tooltip(
            dcc.Markdown(
                '''Temporal method to aggregate the sampling data points for the selected temporal unit'''
            ), target='timeAggTooltip'
        ),
        dcc.RadioItems(id='timeAgg',
                       # labelStyle={'display': 'inline-block', 'margin-right': '20px'},
                       options=[
                           {'label': ' Mean ', 'value': 'AVG'},
                           {'label': ' Sum ', 'value': 'SUM'},
                           {'label': ' Min ', 'value': 'MIN'},
                           {'label': ' Max ', 'value': 'MAX'},
                       ],
                       ),
        html.Label(
            html.Div([
                '3. EOI records:  (',
                html.Span(' i ',
                          id='eoiAggTooltip',
                          style={'fontWeight': 'bold',
                                 'textDecoration': 'underline',
                                 'cursor': 'pointer'}
                          ), ')'
            ], style={'fontWeight': 'bold'}
            )
        ),
        dbc.Tooltip(
            dcc.Markdown(
                '''Method to aggregate environmental records associated to each EOI'''
            ), target='spatialAggTooltip'
        ),
        dcc.RadioItems(id='eoiAgg',
                       #labelStyle={'display': 'inline-block', 'margin-right': '20px'},
                       options=[
                           {'label': ' Mean ', 'value': 'AVG'},
                           {'label': ' Sum ', 'value': 'SUM'},
                           {'label': ' Min ', 'value': 'MIN'},
                           {'label': ' Max ', 'value': 'MAX'},
                       ],
                       ),
        html.Div(),

        # Submit button to display Table Output
        dbc.Spinner([
            html.Button(children='Submit', id='submitData', n_clicks=0, disabled=True),
        ], color='info'),

        html.Div(),
        # Tell the user to wait until is done uploading (confirm dialog?)
        # dcc.Markdown('''
        # Wait until the query is processed
        # '''),
        # Hidden div inside the app that stores the table resulting from queries
        html.Div(id='envVarsDf', style={'display': 'none'}),

        # Hidden div inside the app that stores all queries
        html.Div(id='envVarsDfAll', style={'display': 'none'}),

        # Default storage is memory, lost on page reload.
        # dcc.Store(id='infoQuery', storage_type='local'),  # clear_data=True

        # session storage_type is cleared when the browser exit.
        # dcc.Store(id='infoQuery', storage_type='session'),
        html.Div(id='numberQuery'),

        # The local store will take the initial data
        # only the first time the page is loaded
        # and keep it until it is cleared.
        dcc.Store(id='infoQuery', storage_type='local'),
    ])
],
    className="mt-3"
)

tabDownl = dbc.Card([
    dbc.CardHeader('Queries Datatable', style={'fontWeight': 'bold'}),
    dbc.CardBody([
        html.Div([
            dbc.Button(
                'Download Zip with all datatables',
                id='qDatatableZip',
                color='info',
                style={'fontWeight': 'bold',
                       'margin-left': '1em',
                       'text-align': 'center',
                       },
                size='sm'
            ),
        ], style={'display': 'block', 'margin-bottom': '1em'}),
        html.Div([], id='zipCheck')

    ])

], className='mt-3')

inputTabs = dcc.Tabs(
    [
        dcc.Tab(tabQuery, label='Query'),
        dcc.Tab(tabDownl, label='Zip Download'),
        # dcc.Tab(tabAbout, label='About')

    ], id='inputTabs'
)

mapCollapseDiv = html.Div(
    [
        dbc.Button(
            'Open map',
            id='mapCollapseB',
            color='info',
            style={'fontWeight': 'bold',
                   'margin-left': '50em',
                   'margin-top': '-6em',
                   'text-align': 'center',
                   },
            size='sm'
        ),
        dbc.Collapse(
            dbc.Card(dbc.CardBody(
                dcc.Graph(id='DataPointsMap', figure=mapSamplersFig(endpointURL=localHost, repoID=serdifRepoID))
            )),
            id='mapCollapse',
        ),
    ]
)

homeTab = dcc.Tab(dbc.Card([
    dbc.CardHeader('SERDIF', style={'fontWeight': 'bold'}),
    dbc.CardBody([
        dcc.Markdown(
            '''
            The SERDIF framework aims to support researchers who require a flexible methodology to integrate 
            environmental data with longitudinal and geospatial diverse clinical data in their hypothesis exploration 
            of environmental factors for rare disease research. The framework is a combination of a methodology, 
            a knowledge graph and a dashboard.
            
            The **dashboard** is designed from a user-centric perspective to support Health Data Researchers (HDR) access, 
            explore and export the linked spatio-temporal environmental data by aiding a HDR formulate a query in an 
            intelligible non-technical manner and to explore the data with appropriate visualizations.
            
            **How to use the dashboard?**
            
            1. Read the dashboard information carefully
            2. Select and submit the Query Inputs on the left
            3. Explore the resulting linked environmental data that appear after clicking submit
            4. Export the data for your needs
                        
            A text file named 'userQueryHistory.txt' is automatically saved in the app local folder 
            with the history of your Query Input selections. You will be able to use this file to 
            get the data directly through an API in the future.
                     
            **Environmental Data Sources**: [weather](https://www.met.ie//climate/available-data/historical-data), 
            [pollution](https://airquality.ie/) and [aerosol](https://aeronet.gsfc.nasa.gov/new_web/index.html) data. (right click + open in new tab)
            
            **Data Points Density**: Click the button and hover over the regions to get the number of data points. 
            '''
        ),
        mapCollapseDiv
    ]),
    dbc.CardFooter('Contact: albert.navarro@adaptcentre.ie'),
]), label='Home')

compTab = dcc.Tab(dbc.Card([
    dbc.CardHeader('Compare your queries', style={'fontWeight': 'bold'}),
    dbc.CardBody([
        dcc.Markdown(
            '''
            Query data previously submitted in this session can be compared by specific variable. 
            You can combine these queries into groups with the multiple selection inputs, 
            to potentially increase the signal-to-noise ratio.
            
            1. Decide the number of groups that you wish to compare
            2. Select which queries you want to group
            3. Explore each environmental variable with the different plots
            
            Queries are grouped by computing the mean per unit of time in the TimeSeries plot, 
            and by concatenating the values in the Box and Dist plots. Therefore, the time series
            plot has a limitation when comparing queries with different time units.
            '''
        ),
        html.Div([
            html.Label('Number of Groups:', style={'fontWeight': 'bold'}),
            # html.Br(),
            dcc.Input(
                id='nGroups',
                type='number',
                min=1,
                max=10,
                value=1,
                style={'width': '3em', 'margin-left': '1em'}
            ),
            dbc.Button(
                'Click to generate groups',
                id='nGenGroup',
                color='info',
                style={'fontWeight': 'bold',
                       'margin-left': '1em',
                       'text-align': 'center',
                       },
                size='sm'
            ),
            dbc.Button(
                'Click to plot groups',
                id='visGroupsButton',
                color='info',
                style={'fontWeight': 'bold',
                       'margin-left': '1em',
                       'text-align': 'center',
                       },
                size='sm',
                # disabled=True
            ),
        ], style={'display': 'block', 'margin-bottom': '1em'}
        ),
        dcc.Store(id='qDataS'),
        html.Div(id='nGroupsButtonList'),
        html.Div(id='visGroupsPlot'),
        html.Div([], style={'marginBottom': '1em'}),

    ])
]), label='Comparative')

outTabs = dbc.Spinner([  # dcc.Loading(
    dbc.Tabs([homeTab, compTab],
             id='outTabsT'),
], color='info', spinner_style={'width': '30rem', 'height': '30rem'},
)

appBody = dbc.Container([
    dbc.Row([
        dbc.Col([inputTabs], md=3),
        # dbc.Col([dcc.Tab(tabQuery, label='Query')], md=3),
        dbc.Col([outTabs], md=9, id='test'),
    ])
], className='mt-8', fluid=True,
)

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], server=server)

app.layout = html.Div([topNavbarHelical, appBody])


# 0. SERDIF info map collapse
@app.callback(
    Output('mapCollapse', 'is_open'),
    [Input('mapCollapseB', 'n_clicks')],
    [State('mapCollapse', 'is_open')],
)
def map_toggle_collapse(n, is_open):
    if n:
        return not is_open
    return is_open


# 1. Rare disease
@app.callback(
    [Output('eoi', 'disabled'),
     Output('eoi', 'value'),
     Output('smpDataS', 'data')],
    [Input('rareDisease', 'value')]
)
def selRD(dVal):
    if not dVal:
        dValNo = [True, None, None]
        return dValNo
    else:
        smpData = serdifSamplers(endpointURL=localHost, repoID=serdifRepoID)
        dValYes = [False, None, smpData]
        return dValYes


# 2.2. EOI pop up info
@app.callback(
    Output('eoiPopoverText', 'is_open'),
    [Input('eoiPopover', 'n_clicks')],
    [State('eoiPopoverText', 'is_open')],
)
def eoi_toggle_popover(n, is_open):
    if n:
        return not is_open
    return is_open


# 3. LOI
# 3.1. LOI Options
@app.callback(
    [Output('eoiTable', 'data')],
    [Input('eoi', 'value'),
     Input('smpDataS', 'data')]
)
def queryEOIDates(eoiVal, smpData):
    if not eoiVal or not smpData:
        raise PreventUpdate
    else:
        # EOI table with EOI_Count per LOI
        LOI_Ire = serdifEOIdates(
            endpointURL=localHost,
            repoID=serdifRepoID,
            QPrefixes=QPrefixes,
            eoiVal=eoiVal)
        # Merge to add environmental data
        eoiTableD = pd.merge(pd.DataFrame(LOI_Ire), pd.DataFrame(smpData), on='LOI', how='left').to_dict('list')
        return [eoiTableD]


# Event display
@app.callback(
    [Output('loiDate', 'columns'),
     Output('loiDate', 'data')],
    [Input('eoiTable', 'data')]
)
def tableLoiEv(eoiDict):
    # Avoid update when there is no LOI selected and the
    # "Select All" checklist is not selected
    if not eoiDict:
        return None, None
    else:
        eoiTable = pd.DataFrame.from_dict(eoiDict, orient='index').transpose()
        eoi_ColNames = [{'name': i, 'id': i} for i in eoiTable.columns]
        return eoi_ColNames, eoiTable.to_dict('records')


# 2. EOI
# 2.1. EOI Value
@app.callback(
    [Output('loi', 'disabled'),
     Output('loi', 'value'),
     Output('allLOI', 'labelStyle')],
    [Input('loiDate', 'columns'),
     Input('eoi', 'value')]
)
def actLOI(loiVal, eoiVal):
    if not loiVal and not eoiVal:
        eoiNoDisplay = [True, None, {'display': 'none', 'margin-right': '20px'}]
        return eoiNoDisplay
    else:
        eoiDisplay = [False, None, {'display': 'inline-block', 'margin-right': '20px'}]
        return eoiDisplay


# 3.2. LOI value
@app.callback(
    [Output('wLength', 'disabled')],
    [Input('loi', 'value'),
     Input('allLOI', 'value')]
)
def selLOI(dVal, allVal):
    if not dVal and not allVal:
        return [True]
    else:
        return [False]


# 3.2. LOI value
@app.callback(
    [Output('wLag', 'disabled')],
    [Input('wLength', 'value')]
)
def selLOI(wLenVal):
    if not wLenVal:
        return [True]
    else:
        return [False]


# 6. Temporal Unit
@app.callback(
    [Output('timeUnit', 'labelStyle')],
    [Input('wLag', 'value')]
)
def selTimeAgg(dVal):
    if str(dVal) == 'None':
        return [{'display': 'none', 'margin-right': '20px'}]
    else:
        return [{'display': 'inline-block', 'margin-right': '20px'}]


# 6. Temporal aggregation
@app.callback(
    [Output('spatialAgg', 'labelStyle')],
    [Input('timeUnit', 'value')]
)
def selTimeAgg(dVal):
    if not dVal:
        return [{'display': 'none', 'margin-right': '20px'}]
    else:
        return [{'display': 'inline-block', 'margin-right': '20px'}]

# 6. Temporal aggregation
@app.callback(
    [Output('timeAgg', 'labelStyle')],
    [Input('spatialAgg', 'value')]
)
def selTimeAgg(dVal):
    if not dVal:
        return [{'display': 'none', 'margin-right': '20px'}]
    else:
        return [{'display': 'inline-block', 'margin-right': '20px'}]

# 6. Temporal aggregation
@app.callback(
    [Output('eoiAgg', 'labelStyle')],
    [Input('timeAgg', 'value')]
)
def selTimeAgg(dVal):
    if not dVal:
        return [{'display': 'none', 'margin-right': '20px'}]
    else:
        return [{'display': 'inline-block', 'margin-right': '20px'}]


# 7. Submit button actionable only if all fields are selected
@app.callback(
    [Output('submitData', 'disabled')],
    [Input('rareDisease', 'value'),
     Input('eoi', 'value'),
     Input('loi', 'value'),
     Input('allLOI', 'value'),
     Input('wLength', 'value'),
     Input('wLag', 'value'),
     Input('timeUnit', 'value'),
     Input('timeAgg', 'value'),
     Input('spatialAgg', 'value'),
     Input('eoiAgg', 'value')
     ],
    [State('loi', 'options'), ]
)
def submitActive(rdVal, eoiVal, loiVal, loiValAll, wLen, wLag, tUnitVal, tAggVal, sAggVal, eAggVal, loiOpt):
    # Ireland selected
    if loiValAll == ['GetAll']:
        loiVal = [loi['value'] for loi in loiOpt]

    # print(rdVal, eoiVal, loiVal, loiValAll, wLen, wLag, tUnitVal, tAggVal, sAggVal, eAggVal)
    # If a date is missing disable button
    if not rdVal or not eoiVal or (not loiVal and not loiValAll) or not wLen or str(wLag) == 'None' \
            or not tUnitVal or not tAggVal or not sAggVal or not eAggVal:
        return [True]
    else:
        qDataAsk = serdif_EnvDataAsk(
            endpointURL=localHost,
            repoID=serdifRepoID,
            QPrefixes=QPrefixes,
            sLOI=loiVal,
            eoiVal=eoiVal,
            wLenVal=str(wLen),
            wLagVal=str(wLag)
        )

        if not qDataAsk['boolean']:
            return [True]
        else:
            return [False]


# 8. Query Output
@app.callback(
    [Output('outTabsT', 'children'),
     Output('outTabsT', 'active_tab'),
     Output('submitData', 'title')
     ],
    [Input('submitData', 'n_clicks')],
    [State('loi', 'options'),
     State('loi', 'value'),
     State('wLength', 'value'),
     State('wLag', 'value'),
     State('timeAgg', 'value'),
     State('outTabsT', 'children'),
     State('timeUnit', 'value'),
     State('allLOI', 'value'),
     State('rareDisease', 'value'),
     State('eoi', 'value'),
     State('spatialAgg', 'value'),
     State('eoiAgg', 'value')
     ]
)
def update_output(n_clicks, LOI_Ire, loiVal, wLen, wLag, timeAggSel, outTabsInit, timeUnitSel,
                  loiValAll, rareDiseaseVal, eoiVal, spatialAggSel, eoiAggSel):
    # rdVal, eoiVal, loiVal, loiValAll, wLen, wLag, tUnitVal, tAggVal, loiOpt,
    # Wait until the user clicks the submit button
    if n_clicks == 0:
        raise PreventUpdate
    else:
        LOI_Ire = [loi['value'] for loi in LOI_Ire]

        if loiValAll == ['GetAll']:
            loiVal = LOI_Ire  # [1:5]
            # print('ALL-IN')

        # Query weather data
        weaDataQ = serdif_EnvData(  # PointWeaDataIDs(
            endpointURL=localHost,
            repoID=serdifRepoID,
            QPrefixes=QPrefixes,
            qGo=timeUnitSel,
            sLOI=loiVal,
            eoiVal=eoiVal,
            wLenVal=str(wLen),
            wLagVal=str(wLag),
            timeAgg=timeAggSel,
            spatialAgg=spatialAggSel,
            eoiAgg=eoiAggSel,
        )

        # Define default dictionary
        # If a key is not present is defaultdict,
        # the default factory value is returned and displayed
        ddWea = defaultdict(list)

        # For every variable available per date
        for wVars in weaDataQ['results']['bindings']:
            # For every required variable obtained from the header
            # request, to keep track of missing values
            for reqVar in weaDataQ['head']['vars']:
                # Checks if there is the variable in the specific weather record
                if reqVar in wVars:
                    weaVarsValue = wVars[reqVar]['value']
                    ddWea[reqVar].append(weaVarsValue)
                # Fills with NaN if the variable is not present
                else:
                    ddWea[reqVar].append(np.nan)

        # Weather Table
        dfStoDataQ = pd.DataFrame(ddWea)
        dfStoDataQ = dfStoDataQ.dropna(axis=1, how='all')

        # 1.Convert to CSV
        dfStoCsv = dfStoDataQ.to_csv(index=False)
        # 2.ReParse CSV object as text and then read as CSV. This process will
        # format the columns of the data frame to data types instead of objects.
        dfSto = pd.read_csv(io.StringIO(dfStoCsv)).round(decimals=1)
        # 3.Combine columns to create datetime column for analysis
        # Standard table
        # 1.Select Numeric columns and standardize them by standard scores (z-scores)
        # to be able to compare them. The result represents the number of standard
        # deviations above or below the mean value.
        # dfWeaStd = dfWea.select_dtypes(include=['float64', 'int64']).apply(stats.zscore, axis=0).round(decimals=2)
        dfStoStd = dfSto.apply(stats.zscore, axis=0)  # .round(decimals=2)
        # 2.Extract available variables for the plot
        stoVarsNames = dfSto.loc[:, ]
        # 3. Add dates column as a reference
        # dfStoStd['relDate'] = dfSto.index
        dfSto.insert(loc=0, column='relDate', value=dfSto.index + wLag)
        # 4. Formatting cells to detect values at least 2 sd above or below
        # the variable mean value for the period selected
        conditionalColorCols = [
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': '#F5F5F5'
            },
            {
                'if': {
                    'column_id': '',
                    'filter_query': '',
                },
                'backgroundColor': '#CD5C5C',
                'color': 'white',
            },
            {
                'if': {
                    'column_id': '',
                    'filter_query': '',
                },
                'backgroundColor': '#5CCDCD',
                'color': 'white',
            },
        ]

        conditionColor = [conditionalColorCols[0]]
        for c in stoVarsNames:
            # Top limit for Red Background z-score > 2
            dictTop2 = copy.deepcopy(conditionalColorCols[1])
            topValStd2 = 2 * pd.Series(stoVarsNames.loc[:, c]).std() + pd.Series(
                stoVarsNames.loc[:, c]).mean()
            dictTop2['if']['column_id'] = c
            dictTop2['if']['filter_query'] = '{' + c + '} > ' + str(topValStd2.round(decimals=2))

            # Bot limit for Blue Background z-score < -2
            botValStd2 = -2 * pd.Series(stoVarsNames.loc[:, c]).std() + pd.Series(
                stoVarsNames.loc[:, c]).mean()
            dictBot2 = copy.deepcopy(conditionalColorCols[2])
            dictBot2['if']['column_id'] = c
            dictBot2['if']['filter_query'] = '{' + c + '} < ' + str(botValStd2.round(decimals=2))

            conditionColor.append(dictTop2)
            conditionColor.append(dictBot2)

        # Tab names
        # IDsNames = ', '.join(loiVal)
        tabQueryName = 'Q' + str(n_clicks)
        tabQueryID = 'tab-' + str(n_clicks + 1)
        tabQueryDataID = 'tabID' + '_' + tabQueryName
        tabQueryTableID = {'type': 'qDataTable',
                           'index': 'dataTable' + '_' + tabQueryName,
                           }
        tabDataTSID = tabQueryTableID['index'] + '_TS'
        tabDataBoxID = tabQueryTableID['index'] + '_Box'
        msgPolID = tabQueryTableID['index'] + '_msgPol'

        # Texts
        textDataTable = dcc.Markdown('''
        The full name of the variables with the units appear when hovering over the headings of the data table.
        For further information please refer to the data sources links in the Home tab.
        
        The Toggle Columns button allows to select the columns of interest and the Export button to download
        the data as a csv file to your computer. Only the visible columns will be downloaded.
        ''')

        textTSPlot = dcc.Markdown('''
                **Time series plot: visual story along time**

                This visualization is interactive:
                * **Plot**: zoom, hover (single and multiple), pan and download as .png
                * **Legend**: click the variable to de/select and double-click to select only
                * **Range Slider**: click and drag to select the period of interest on the bottom plot.
                ''')

        textPolarPlot = dcc.Markdown('''
                **Scatter polar plots: complex variable-wind dependencies**

                The radius length indicates the wind speed and the degrees the wind direction.

                This visualization is interactive:
                * **Plot**: zoom, hover (single and multiple), pan and download as .png
                ''')

        textBoxPlot = dcc.Markdown('''
                **Box plots: variability across samples**

                The box bounds the IQR divided by the median, and Tukey-style whiskers extend
                to a maximum of 1.5 × IQR beyond the box.

                This visualization is interactive:
                * **Plot**: zoom, hover (single and multiple), pan and download as .png
                ''')

        # Plots
        named_colorscales = px.colors.named_colorscales()
        # Time series plot definition, https://plotly.com/python/time-series/
        dfStoStd.insert(loc=0, column='relDate', value=dfStoStd.index + wLag)
        dfStoTS = dfStoStd.set_index('relDate')

        dfStoTSFig = px.line(dfStoTS, x=dfStoTS.index, y=dfStoTS.columns.values.tolist(),
                             labels={'value': 'z-scores',
                                     'relDate': 'Relative dates from EOI [' + timeUnitSel + ']'})
        dfStoTSFig.update_xaxes(rangeslider_visible=True, autorange='reversed')

        # dfWeaTSFig['data'][1]['hovertemplate'] = 'x=%{x}<br>y=%{y:$.2f}*{4:$.2f}'

        # Box plot definition, https://plotly.com/python/box-plots/
        dfStoBoxFig = px.box(dfStoTS, points="all", category_orders=dfStoTS.columns)
        dfStoBoxFig.update_traces(marker_size=2,
                                  marker_outliercolor='red',
                                  selector=dict(type='box'),
                                  showlegend=True)

        # Polar plot definition, https://plotly.com/python/polar-chart/
        # 1. Select variables for the color dimension of the plots
        windVars = ['wdsp', 'wddir']
        if all(var in dfStoTS.columns.values for var in windVars):
            stoPolVars = [x for x in dfStoTS.columns.values.tolist() if x not in windVars]
            # 2. Store in a list individual dcc.Graphs with a scatter polar plot:
            # 2.1. Common variables: wind speed (radius) and wind direction (angle)
            # 2.2. Generate a plot for every variable in the query output datatable
            stoPolarList = [html.Div([], style={'marginTop': '1em'}),
                            textPolarPlot,
                            dcc.Dropdown(id={'type': 'qPolar',
                                             'index': n_clicks},
                                         options=listToOptions(stoPolVars),
                                         multi=False
                                         ),
                            html.Div(id={'type': 'pPolar',
                                         'index': n_clicks}),
                            ]
        else:
            stoPolarList = [html.Div([], style={'marginTop': '1em'}),
                            textPolarPlot,
                            dcc.ConfirmDialog(
                                id=msgPolID, message='''No wind data available''',
                                displayed=True,
                            ),
                            ]

        # Data table to show:
        dfStoNames = [{"name": i, "id": i, "hideable": True} for i in dfSto.columns]
        # variable definition
        dfStoDef = serdif_EnvDesc(endpointURL=localHost, repoID=serdifRepoID)
        dfStoDef['relDate'] = 'Relative dates from the EOI'
        # Data table dash definition
        stoTableDash = dash_table.DataTable(
            id=tabQueryTableID,
            style_table={'overflowX': 'auto'},
            style_cell={
                'overflow': 'hidden',
                'textOverflow': 'ellipsis',
                'width': 100,
                'minWidth': 100,
                'maxWidth': 100,
                'textAlign': 'center'
            },
            style_header={
                'backgroundColor': '#17a2b8',  # '#458B74',
                'fontWeight': 'bold',
                'color': 'white',
                'textDecoration': 'underline',
                'textDecorationStyle': 'dotted',
            },
            style_data_conditional=conditionColor,
            tooltip_header=dfStoDef,
            tooltip_delay=0,
            tooltip_duration=None,
            column_selectable='single',
            export_format='csv',
            export_headers='display',
            sort_action='native',
            page_size=24,
            fixed_rows={'headers': True},
            columns=dfStoNames,
            data=dfSto.to_dict('records'),

            # Style the tooltip headers and export button
            css=[{
                'selector': '.dash-table-tooltip',
                'rule': 'background-color: #A4DCD1'
            }],
        )

        weaTSPlot = dcc.Graph(id=tabDataTSID,
                              figure=dfStoTSFig)

        weaBoxPlot = dcc.Graph(id=tabDataBoxID,
                               figure=dfStoBoxFig
                               )

        # Translator for eoiVal
        transEoiDict = {'http://serdif.org/kg/datasource/event/RndEvIre/Definite': 'Definite',
                        'http://serdif.org/kg/datasource/event/RndEvIre/HighProbability': 'High Probability',
                        'http://serdif.org/kg/datasource/event/RndEvIre/Possible': 'Possible',
                        'http://serdif.org/kg/datasource/event/RndEvIre/No': 'No'}
        # Translate value to flare probability
        transEoiVal = [transEoiDict[keyEoi] for keyEoi in eoiVal]

        # Ireland name for loi
        if loiValAll == ['GetAll']:
            loiVal = ['Ireland']

        # Query Input Table
        qInputData = {'Rare Disease': rareDiseaseVal,
                      'EOI': ' ,'.join(transEoiVal),
                      'LOI': ' ,'.join(loiVal),
                      'Window Length': str(wLen) + ' [days]',
                      'Window Lag': str(wLag) + ' [days]',
                      'Time Units': timeUnitSel,
                      'Spatial Agg': spatialAggSel,
                      'Temporal Agg': timeAggSel,
                      'EOI records Agg': eoiAggSel,
                      }
        #qInputDataS = '\n'.join(f'{key}:{value}' for key, value in qInputData.items()[0:6])
        qInputDF = pd.DataFrame.from_dict(qInputData, orient='index')
        qInputDF.reset_index(level=0, inplace=True)
        qInputDF.columns = ['Options', 'Input']

        qInputTableID = 'qInputTable' + tabQueryName

        qInputTable = dash_table.DataTable(
            id=qInputTableID,
            data=qInputDF.to_dict('records'),
            columns=[{'name': i, 'id': i} for i in qInputDF.columns],
            column_selectable='single',
            page_size=4,
            style_cell={
                'overflow': 'hidden',
                'textOverflow': 'ellipsis',
                'maxWidth': 0,
                'textAlign': 'center',
                'whiteSpace': 'normal',
                'height': 'auto',
            },
            style_header={
                'backgroundColor': 'whitesmoke',
                'fontWeight': 'bold',
                'color': 'black',
            },
        )

        dataStdInfoColours = dcc.Markdown(
            '''
        Datatable background:
        If data is normally distributed 95% should be between -2 and +2 Z-scores (white)
        * Values > 2 are **high** (red)
        * Values < -2 are **low** (blue)
        
        Z-scores are computed using the mean value form the data available in the data table
        ''')

        # Collapse info buttons
        qTabInfo = html.Div(
            [dbc.Button(
                'Open Query Input Summary',
                id={'type': 'qInTable',
                    'index': n_clicks},
                color='info',
                size='sm',
                style={'fontWeight': 'bold',
                       'margin-left': '1em',
                       'text-align': 'center',
                       'margin-bottom': '1em',
                       },
            ),
                dbc.Button(
                    'Open Colour Table Description',
                    id={'type': 'qColourTable',
                        'index': n_clicks},
                    color='info',
                    size='sm',
                    style={'fontWeight': 'bold',
                           'margin-left': '1em',
                           'text-align': 'center',
                           'margin-bottom': '1em',
                           },
                ),

                dbc.Collapse(
                    dbc.Card([
                        dbc.CardHeader('Query Input Summary',
                                       style={'background-color': '#17a2b8',
                                              'fontWeight': 'bold',
                                              'color': 'white'}),
                        dbc.CardBody([qInputTable])
                    ], color='info', outline=True),
                    id={'type': 'qInTable-collapse',
                        'index': n_clicks}),

                dbc.Collapse(
                    dbc.Card([
                        dbc.CardHeader('Table Colours',
                                       style={'background-color': '#17a2b8',
                                              'fontWeight': 'bold',
                                              'color': 'white'}),
                        dbc.CardBody([dataStdInfoColours])
                    ], color='info', outline=True),
                    id={'type': 'qColourTable-collapse',
                        'index': n_clicks}),
            ], style={'display': 'block', 'margin-bottom': '1em'})

        # New tab per Query
        tabNew = dbc.Card([
            dbc.CardHeader('Environmental Linked Data'),
            dbc.CardBody([
                qTabInfo,
                # html.Div([], style={'marginBottom': '1em'}),
                dbc.Tabs([
                    dcc.Tab([html.Div([], style={'marginTop': '1em'}),
                             textDataTable,
                             stoTableDash], label='Data'),
                    dcc.Tab([html.Div([], style={'marginTop': '1em'}),
                             textTSPlot, weaTSPlot], label='TimeSeries'),
                    dcc.Tab([html.Div([], style={'marginTop': '1em'}),
                             textBoxPlot, weaBoxPlot], label='BoxPlot'),
                    dcc.Tab(stoPolarList, label='PolarPlot'),
                ])
            ])
        ],
            className='mt-3',
            id=tabQueryDataID)

        # Add new Patient data everytime there is a submit
        outTabsInit.append(dcc.Tab(tabNew, label=tabQueryName))

        # Button title to block double clicks
        subTitleToolTip = 'Queries submitted: ' + str(n_clicks)

    return outTabsInit, tabQueryID, subTitleToolTip


# 8.1. Info  tab buttons collapse
@app.callback(
    Output({'type': 'qColourTable-collapse', 'index': MATCH}, 'is_open'),
    [Input({'type': 'qColourTable', 'index': MATCH}, 'n_clicks')],
    [State({'type': 'qColourTable-collapse', 'index': MATCH}, 'is_open')],
)
def colourTableCollapse(n, is_open):
    if n:
        return not is_open
    return is_open


# 8.2. Info  tab buttons collapse
@app.callback(
    Output({'type': 'qInTable-collapse', 'index': MATCH}, 'is_open'),
    [Input({'type': 'qInTable', 'index': MATCH}, 'n_clicks')],
    [State({'type': 'qInTable-collapse', 'index': MATCH}, 'is_open')],
)
def inTableCollapse(n, is_open):
    if n:
        return not is_open
    return is_open


# 8.3. Scatter polar plots variable selection
@app.callback(
    [Output({'type': 'pPolar', 'index': MATCH}, 'children')],
    [Input({'type': 'qPolar', 'index': MATCH}, 'value'),
     Input('qDataS', 'data')],
    [State({'type': 'qPolar', 'index': MATCH}, 'id')]
)
def polarPlotVar(polarVar, dataQStore, qNumID):
    if not dataQStore or not polarVar:
        raise PreventUpdate
    else:
        # Generate query num label
        qNumData = 'Q' + str(qNumID['index'])
        # Import data from queries
        envQData = pd.DataFrame(dataQStore[qNumData])
        # Polar plot definition, https://plotly.com/python/polar-chart/
        checkWindVarsL = ['wdsp', 'wddir']
        if not set(checkWindVarsL).issubset(envQData.columns.values):
            raise PreventUpdate
        else:
            # 1. Select variables for the color dimension of the plots
            windAndDateTVars = ['dateT', 'yearT', 'monthT', 'dayT', 'hourT', 'wdsp', 'wddir']
            weaPolarPlotVars = [x for x in envQData.columns.values if x not in windAndDateTVars]
            # 2. Store in a list individual dcc.Graphs with a scatter polar plot:
            # 2.1. Common variables: wind speed (radius) and wind direction (angle)
            # 2.2. Generate a plot for every variable in the query output datatable
            envPolarFig = px.scatter_polar(
                envQData, r='wdsp', theta='wddir',
                color=polarVar,
                color_continuous_scale=px.colors.sequential.Jet)

            envPolarFig.update_traces(
                marker=dict(
                    size=6,
                    opacity=0.4,
                    line=dict(width=0,
                              color='DarkSlateGrey')),
                selector=dict(mode='markers'))

            return [[dcc.Graph(figure=envPolarFig, id='polar' + qNumData)]]


# 9. Generate a history for all query inputs
@app.callback(
    [Output('infoQuery', 'data')],
    [Input('submitData', 'n_clicks')],
    [State('infoQuery', 'data'),
     State('rareDisease', 'value'),
     State('eoi', 'value'),
     State('loi', 'value'),
     State('wLength', 'value'),
     State('wLag', 'value'),
     State('timeUnit', 'value'),
     State('timeAgg', 'value'),
     State('allLOI', 'value')]
)
def queryInfoStore(n_clicks, infoQStore, rareDiseaseVal, eoiVal, loiVal, wLen, wLag,
                   timeUnitVal, timeAggVal, loiValAll):
    if not n_clicks:
        raise PreventUpdate
    else:
        # Create the dictionary if there is not already one stored
        if not infoQStore:
            # Default dict to store session input
            infoQStore = defaultdict(dict)

        # Translator for eoiVal
        transEoiDict = {'http://serdif.org/kg/datasource/event/RndEvIre/Definite': 'Definite',
                        'http://serdif.org/kg/datasource/event/RndEvIre/High%20Probability': 'High Probability',
                        'http://serdif.org/kg/datasource/event/RndEvIre/Possible': 'Possible',
                        'http://serdif.org/kg/datasource/event/RndEvIre/No': 'No'}
        # Translate value to flare probability
        transEoiVal = [transEoiDict[keyEoi] for keyEoi in eoiVal]

        # Ireland name for loi
        if loiValAll == ['GetAll']:
            loiVal = 'Ireland'

        # Query Input Table
        qInputData = {'QDateTime': str(datetime.now(pytz.timezone('UTC'))),
                      'Rare Disease': rareDiseaseVal,
                      'eoi': ', '.join(transEoiVal),
                      'loi': ', '.join(loiVal),
                      'wLen': str(wLen),
                      'wLag': str(wLag),
                      'timeUnit': timeUnitVal,
                      'timeAgg': timeAggVal,
                      }

        qTime = datetime.now().strftime('%Y%m%dT%H%M%S')  # str(datetime.now(pytz.timezone("UTC")))

        infoQStore[qTime] = qInputData
        # Display infoQStore dictionary as text
        qHistoryFile = queryStoreDir + '/' + 'userQueryHistory.txt'
        with open(qHistoryFile, 'w') as infoQStoreFile:
            json.dump(infoQStore, infoQStoreFile, indent=4)

        # infoQStoreText = dcc.Markdown(json.dumps(infoQStore))

        return [infoQStore]


# 9. Comparative tab 'nGroupsButtonList'
@app.callback(
    Output('nGroupsButtonList', 'children'),
    [Input('nGenGroup', 'n_clicks'),
     Input('submitData', 'n_clicks')],
    [State('nGroups', 'value')]
)
def on_genCompGroups(gen_click, n_clicks, numG):
    if not gen_click or not n_clicks:
        raise PreventUpdate
    else:
        selGroupList = list()
        for nG in range(numG):
            gID = 'inGroup' + str(nG + 1)
            gLabel = 'Group ' + str(nG + 1)
            selGroupI = html.Div([
                html.Label(gLabel, style={'fontWeight': 'bold'}),
                dcc.Dropdown(
                    id={
                        'type': 'qGroupDropdown',
                        'index': gID
                    },
                    options=[{'label': 'Q' + str(q + 1), 'value': 'Q' + str(q + 1)} for q in range(n_clicks)],
                    multi=True,
                    # style={'width': '6em'}
                )
            ], style={'display': 'inline-block', 'margin-right': '2em'})
            selGroupList.append(selGroupI)

        return selGroupList


# 10. Enable button to plot groups
@app.callback(
    Output('visGroupsButton', 'disabled'),
    # [Input('nGenGroup', 'n_clicks')],
    Input({'type': 'qGroupDropdown', 'index': ALL}, 'value')
)
def on_clickCompGroups(qGSel):
    if not qGSel:
        # if all(v for v in qGSel):
        return True
    elif None in qGSel:
        return True
    else:
        return False


# 11. Store Query data after submitting
@app.callback(
    [Output('qDataS', 'data')],
    [Input('submitData', 'n_clicks'),
     Input({'type': 'qDataTable', 'index': ALL}, 'data')],
    [State('qDataS', 'data')]
)
def queryDataStore(sub_click, dataTableQ, dataQStore):
    if not sub_click or not dataTableQ:
        raise PreventUpdate
    elif len(dataTableQ) != sub_click:
        raise PreventUpdate
    else:

        # Create the dictionary if there is not already one stored
        if not dataQStore:
            # Default dict to store session input
            dataQStore = defaultdict(dict)

        qNum = 'Q' + str(sub_click)

        dataQStore[qNum] = dataTableQ[sub_click - 1]  # list(chain.from_iterable(dataTableQ))
        # print(pd.DataFrame(dataQStore['Q1']))

        return [dataQStore]


# 12. Visualize comparison between groups
@app.callback(
    [Output('visGroupsPlot', 'children'), ],
    [Input('visGroupsButton', 'n_clicks'), ],
    [State({'type': 'qGroupDropdown', 'index': ALL}, 'value')]
)
def on_visCompGroups(vis_click, ngQ):
    if not vis_click or None in ngQ:
        raise PreventUpdate

    else:
        # Variables available from data sources
        envVars = dataSourceSel(selDataSL=['weather', 'pollution'])
        # Button to select variable to compare with boxplots
        groupVarSel_TS = [
            html.Div([], style={'marginTop': '1em'}),
            html.Label('Select variable to compare groups:'),
            dcc.Dropdown(id={'type': 'cTSSel',
                             'index': vis_click},
                         options=listToOptions(envVars),
                         multi=False
                         ),
            html.Div(id={'type': 'cTSPlot',
                         'index': vis_click}),
        ]
        # Button to select variable to compare with boxplots
        groupVarSel_Box = [
            html.Div([], style={'marginTop': '1em'}),
            html.Label('Select variable to compare groups:'),
            dcc.Dropdown(id={'type': 'cBoxSel',
                             'index': vis_click},
                         options=listToOptions(envVars),
                         multi=False
                         ),
            html.Div(id={'type': 'cBoxPlot',
                         'index': vis_click}),
        ]
        # Button to select variable to compare with distplot
        groupVarSel_Dist = [
            html.Div([], style={'marginTop': '1em'}),
            html.Label('Select variable to compare groups:'),
            dcc.Dropdown(id={'type': 'cDistSel',
                             'index': vis_click},
                         options=listToOptions(envVars),
                         multi=False
                         ),
            html.Div(id={'type': 'cDistPlot',
                         'index': vis_click}),
        ]

        selGroupI = dbc.Tabs([
            dcc.Tab(groupVarSel_TS, label='TimeSeries'),
            dcc.Tab(groupVarSel_Box, label='Box'),
            dcc.Tab(groupVarSel_Dist, label='Dist'),

        ], id='compTabPlots', style={'marginTop': '1em'})

        return [selGroupI]


# 12. Visualize comparison between groups
# 12.1. TSplot
@app.callback(
    [Output({'type': 'cTSPlot', 'index': MATCH}, 'children')],
    [Input({'type': 'cTSSel', 'index': MATCH}, 'value')],
    [State({'type': 'cTSSel', 'index': MATCH}, 'id'),
     State('nGroupsButtonList', 'children'),
     State({'type': 'qGroupDropdown', 'index': ALL}, 'value'),
     State('qDataS', 'data')]
)
def tsCompGroups(tsVal, tsDivID, numGroupIn, ngQ, dataQStore):
    if not tsVal or None in ngQ:
        raise PreventUpdate

    else:
        # Access Generated groups and queries selected
        nGroupBu = [dBuList['props']['children'] for dBuList in numGroupIn]
        nGroupName = [dDiv['props']['children'] for dDivList in nGroupBu for dDiv in dDivList if
                      'children' in dDiv['props']]
        # Empty list to fill with the aggregated variables for plot visualization
        groupDataL = list()

        for nQVal in ngQ:
            if nQVal:
                airGL = list()
                for qGData in nQVal:
                    airGData = pd.DataFrame(dataQStore[qGData])
                    # Set index from relative dates column
                    airGData = airGData.set_index('relDate')
                    # If the variable exists in the Query
                    if tsVal in airGData:
                        airGL.append(airGData[tsVal])
                    # There is no selected variable in the group
                    else:
                        airGData['emptyCol'] = [None] * airGData.index.size
                        airGL.append(airGData['emptyCol'])
                # concat by index
                airGDataL = pd.concat(airGL, axis=1)

                # compute the mean for the already selected variable
                airGDataL[tsVal] = airGDataL.mean(axis=1)

                # remove duplicated column
                airGDataL = airGDataL.loc[:, ~airGDataL.columns.duplicated()]
                if tsVal in airGDataL.columns:
                    groupDataL.append(airGDataL)

        # Check if key exists
        checkVar = [airData[tsVal].isnull().all() for airData in groupDataL if tsVal in airData.columns]
        # if check var is [False] or [] prevent update

        if not checkVar or all(checkVar):
            raise PreventUpdate
        else:
            # Select key from dict from user selection
            cTSDict = [pd.DataFrame({nGName + '_' + tsVal: airData[tsVal]}) for nGName, airData in
                       zip(nGroupName, groupDataL)]
            cTSDF = pd.concat(cTSDict, axis=1)
            # Time series plot definition, https://plotly.com/python/time-series/
            cTSFig = px.line(cTSDF, x=cTSDF.index,
                             y=cTSDF.columns.values.tolist(),
                             labels={'value': tsVal,
                                     'relDate': 'Relative dates from EOI '}
                             )
            cTSFig.update_xaxes(rangeslider_visible=True, autorange='reversed')
            cTSPlot = dcc.Graph(id='compTS_' + str(tsDivID['index']), figure=cTSFig)

            return [cTSPlot]


# 12.1. Boxplot
@app.callback(
    [Output({'type': 'cBoxPlot', 'index': MATCH}, 'children')],
    [Input({'type': 'cBoxSel', 'index': MATCH}, 'value')],
    [State({'type': 'cBoxSel', 'index': MATCH}, 'id'),
     State('nGroupsButtonList', 'children'),
     State({'type': 'qGroupDropdown', 'index': ALL}, 'value'),
     State('qDataS', 'data')]
)
def boxCompGroups(boxVal, boxDivID, numGroupIn, ngQ, dataQStore):
    if not boxVal or None in ngQ:
        raise PreventUpdate

    else:
        # Access Generated groups and queries selected
        nGroupBu = [dBuList['props']['children'] for dBuList in numGroupIn]
        nGroupName = [dDiv['props']['children'] for dDivList in nGroupBu for dDiv in dDivList if
                      'children' in dDiv['props']]
        #  airStDf = pd.concat(airStList, axis=1)
        groupDataL = list()
        for nQVal in ngQ:
            if nQVal:
                airGDataList = [pd.DataFrame(dataQStore[qGData]) for qGData in nQVal]
                airGDataListNoT = [airGData[airGData.columns.drop(airGData.filter(regex='T').columns)] for airGData in
                                   airGDataList]
                airGData = pd.concat(airGDataListNoT)
                groupDataL.append(airGData)

        # Check if key exists
        checkVar = [airData[boxVal].isnull().all() for airData in groupDataL if boxVal in airData.columns]
        # if check var is [False] or [] prevent update
        if not checkVar or all(checkVar):
            raise PreventUpdate
        else:
            # Select key from dict from user selection
            cBoxDict = [pd.DataFrame({nGName + '_' + boxVal: airData[boxVal].values.tolist()}) for nGName, airData in
                        zip(nGroupName, groupDataL) if boxVal in airData.columns]
            cBoxDF = pd.concat(cBoxDict, axis=1)
            # Box plot definition, https://plotly.com/python/box-plots/
            cBoxFig = px.box(cBoxDF, points="all")
            cBoxFig.update_traces(marker_size=2,
                                  marker_outliercolor='red',
                                  selector=dict(type='box'))
            cBoxPlot = dcc.Graph(id='compBox_' + str(boxDivID['index']), figure=cBoxFig)

            return [cBoxPlot]


# 12.1. Distplot
@app.callback(
    [Output({'type': 'cDistPlot', 'index': MATCH}, 'children')],
    [Input({'type': 'cDistSel', 'index': MATCH}, 'value')],
    [State({'type': 'cDistSel', 'index': MATCH}, 'id'),
     State('nGroupsButtonList', 'children'),
     State({'type': 'qGroupDropdown', 'index': ALL}, 'value'),
     State('qDataS', 'data')]
)
def distCompGroups(distVal, distDivID, numGroupIn, ngQ, dataQStore):
    if not distVal or None in ngQ:
        raise PreventUpdate

    else:
        # Access Generated groups and queries selected
        nGroupBu = [dBuList['props']['children'] for dBuList in numGroupIn]
        nGroupName = [dDiv['props']['children'] for dDivList in nGroupBu for dDiv in dDivList if
                      'children' in dDiv['props']]
        #  airStDf = pd.concat(airStList, axis=1)
        groupDataL = list()
        for nQVal in ngQ:
            if nQVal:
                airGDataList = [pd.DataFrame(dataQStore[qGData]) for qGData in nQVal]
                airGDataListNoT = [airGData[airGData.columns.drop(airGData.filter(regex='T').columns)] for airGData in
                                   airGDataList]
                airGData = pd.concat(airGDataListNoT)
                groupDataL.append(airGData)

        # Check if key exists
        checkVar = [airData[distVal].isnull().all() for airData in groupDataL if distVal in airData.columns]
        # if check var is [False] or [] prevent update
        if not checkVar or all(checkVar):
            raise PreventUpdate
        else:
            # Select key from dict from user selection
            cDistDict = [pd.DataFrame({nGName + '_' + distVal: airData[distVal].values.tolist()}) for nGName, airData in
                         zip(nGroupName, groupDataL) if distVal in airData.columns]
            cDistDF = pd.concat(cDistDict, axis=1)
            # Density plot, https://plotly.com/python/distplot/
            cDistFig = ff.create_distplot([cDistDF[c].dropna().unique().tolist() for c in cDistDF.columns],
                                          cDistDF.columns, show_hist=False)  # bin_size=.25)

            cDistPlot = dcc.Graph(id='compDist_' + str(distDivID['index']), figure=cDistFig)

            return [cDistPlot]


# 13. Download all data as a zip file
@app.callback(
    Output('zipCheck', 'children'),
    [Input('qDatatableZip', 'n_clicks')],
    [State('qDataS', 'data')]
)
def allQueryDownload(zip_click, dataQStore):
    if not zip_click or not dataQStore:
        raise PreventUpdate
    else:
        # Store data as CSV files within a zip file
        zipDownlLink = queryStoreDir + '/' + 'userDataTables.zip'
        with zipfile.ZipFile(zipDownlLink, 'w') as csv_zip:
            for qNum, qDataTable in dataQStore.items():
                csv_zip.writestr(qNum + '.csv', pd.DataFrame(qDataTable).to_csv())

        return [html.Label('zip file dowloaded in local folder named appFiles')]


# @app.server.route('/dash/urldownload')

# def allQueryDownloadl():
#	return send_file('example.zip', attachment_filename = 'example.zip', as_attachment = True)


# csvStdString = "data:text/csv;charset=utf-8," + requests.utils.requote_uri(csvStdFile)

# New call back to compare data
# Input datatable from each query tab (use id)
# Output select value from dropdown with all variables available
# - Same query tab plots but per variable
# - Summary metadata table
# - Download all tables as a zip: eoi_loi_startDate_EndDate_Datasources_aggMethod.csv
# -- Example: ANCAFlaresDefinite_Dublin_s01-02-2020_e28-02-2020_weatherpollution_avg.csv


if __name__ == '__main__':
    app.run_server(debug=True, dev_tools_props_check=False,  # dev_tools_ui=False,
                   host='0.0.0.0', port=5000)
