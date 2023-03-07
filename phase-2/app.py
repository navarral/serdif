# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------
# Github: navarral
# Author: 'https://orcid.org/0000-0002-2336-753X'
# Version: 0.1.0
# ------------------------------------------------------------------------
# SERDIF Dashboard
# ------------------------------------------------------------------------

# Libraries to set paths and download/upload files
# from pathlib import Path
# from flask import Flask, send_from_directory
# Libraries for Dash
import time

import dash
import dash_bootstrap_components as dbc
# import dash_auth
from dash import dcc, html, Input, Output, State, MATCH, ALL, dash_table
from dash.exceptions import PreventUpdate
import pandas as pd
import numpy as np
import io
import requests
import json
import xmltodict
from textwrap import dedent
import sys
import os
import copy

# Visualizations
import plotly.express as px
from io import BytesIO
import base64
import zipfile
import tempfile
# Functions from queries.py
from assets.queries import nEvents, evLoc, envoLoc, evTypeLocDateT, evEnvoDataAsk, evEnvoDataSet, envoVarNameUnit
from assets.metadataTemplateGen import genMetadataFile
from assets.openAirPolarPlot import dfToPolar

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])  # , server=server)
server = app.server
app.title = 'SERDIF'


# Function to convert a list to dash input options
def listToOptions(optDM):
    listOpt = []
    for entry in optDM:
        dictID = {'label': entry, 'value': entry}
        listOpt.append(dictID)
    return listOpt

# helper function for closing temporary files
def close_tmp_file(tf):
    try:
        os.unlink(tf.name)
        tf.close()
    except:
        pass


# App top navigation bar
topNavbarHelical = dbc.NavbarSimple(
    children=[
        # dbc.NavItem([html.Img(src='/static/images/ADAPT_Logo_CMYK.png', height='20em')]),
        dbc.NavItem([
            dbc.NavLink('ADAPT', href='https://www.adaptcentre.ie/', target='_blank')
        ]),
        dbc.NavItem([
            dbc.NavLink('Trinity College Dublin', href='https://www.tcd.ie/', target='_blank')
        ]),
    ],
    brand='SERDIF - Semantic Environmental and Rare Disease data Integration Framework (v.0.1.0)',
    brand_href='#',
    sticky='top',
)

# User login
loginInput = dbc.Card([
    dbc.CardHeader([
        'User Login',
    ], style={'fontWeight': 'bold'}
    ),
    dbc.CardBody([
        html.Label('Username:', style={'fontWeight': 'bold', 'marginBottom': '0.5em'}),
        dbc.Input(id='userInput', placeholder='Type username...', type='text',
                  persistence_type='session', required='required', value='hdr001', disabled=True,
                  style={'fontWeight': 'normal', 'marginBottom': '0.5em'}),
        html.Label('Password:', style={'fontWeight': 'bold', 'marginBottom': '0.5em'}),
        dbc.Input(id='passwordInput', placeholder='Type password...', type='text', value='hdr001?', disabled=True,
                  persistence_type='session', required='required', debounce=True,  # n_blur=100,
                  style={'fontWeight': 'normal', 'marginBottom': '0.5em'}),
        html.Div([
            dbc.Button('Sign in', id='signInButton',
                       color='primary', style={'margin-bottom': '0.5em'})
        ], className='d-grid gap-2 mx-auto'),
        dbc.Spinner([
            dbc.Alert(
                id='loginAlert',
                dismissable=True,
                is_open=False,
                style={'verticalAlign': 'middle',
                       'margin-bottom': '0.5em',
                       'fontWeight': 'normal',
                       }
            ),
        ], color='primary'),

    ]),
])

# Query input panel
tabQuery = dbc.Card([
    dbc.CardHeader([
        'Query Input Options',
    ], style={'fontWeight': 'bold'}
    ),
    dbc.CardBody([
        html.Label('Case study:', style={'fontWeight': 'bold', 'marginBottom': '0.5em'}),
        dcc.Dropdown(
            id='projectID',
            options=listToOptions(['Example Events - Ireland']),
            style={'marginBottom': '0.5em', 'fontWeight': 'normal'}
        ),
        html.Div([
            html.Label('Events:', style={'fontWeight': 'bold', 'marginBottom': '0.5em'}),
            dbc.Button('i', id='evPopover', color='primary',
                       style={'fontWeight': 'bold',
                              'margin-left': '1em',
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
                    dbc.PopoverBody('Event classified as Definite by an Agent'),
                    dbc.PopoverHeader('High probability'),
                    dbc.PopoverBody('Event classified as High probability by an Agent'),
                    dbc.PopoverHeader('Possible'),
                    dbc.PopoverBody('Event classified as Possible by an Agent'),
                    dbc.PopoverHeader('No'),
                    dbc.PopoverBody('Event classified as No by an Agent'),
                ],
                id='evPopoverText',
                is_open=False,
                target='evPopover',
            ),
        ]),
        dbc.Spinner([
            dcc.Dropdown(
                id='eventTypeCount',
                # options=listToOptions(evTypeCountL),
                multi=True,
                style={'marginBottom': '0.5em', 'fontWeight': 'normal'}
            ),
        ], color='primary'),

        html.Label('Location (county):', style={'fontWeight': 'bold', 'marginBottom': '0.5em'}),
        dcc.Dropdown(
            id='eventLoc',
            multi=True,
            style={'marginBottom': '0.5em', 'fontWeight': 'normal'}
        ),
        html.Div([
            html.Div([
                html.Label('Time-window length [days]:', style={'fontWeight': 'bold'}),
            ], style={'display': 'inline-block', 'margin-right': '0.5em'}),
            html.Div([
                dcc.Input(
                    id='wLength',
                    type='number',
                    min=1,
                    # value=10,
                    # step=10,
                    style={'width': '3em'},
                ),
            ], style={'display': 'inline-block', 'margin-bottom': '0.5em'}),
        ]),
        html.Div([
            html.Div([
                html.Label('Time-window lag [days]:', style={'fontWeight': 'bold'}),
            ], style={'display': 'inline-block', 'margin-right': '2em'}),
            html.Div([
                dcc.Input(
                    id='wLag',
                    type='number',
                    min=0,
                    # value=10,
                    # step=10,
                    style={'width': '3em'},
                ),
            ], style={'display': 'inline-block',
                      'margin-bottom': '0.5em'}),
        ]),
        html.Div(
            [html.Div([
                dbc.Button('Click to check data availability', id='evEnvoDataButton',
                           color='primary', style={'margin-bottom': '0.5em'})
            ], className='d-grid gap-2 mx-auto'),
                dbc.Spinner([
                    dbc.Alert(
                        id='evEnvoDataText',
                        dismissable=True,
                        is_open=False,
                        color='warning',
                        style={'verticalAlign': 'middle',
                               'margin-bottom': '0.5em',
                               'fontWeight': 'normal',
                               }
                    ),
                ], color='primary'),
            ],
        ),
        html.Div(
            style={'margin-bottom': '0.5em',
                   'border-top': '2px solid #C0C0C0'}
        ),
        html.Label(
            html.Div([
                'Temporal Unit:  (',
                html.Span(' i ',
                          id='timeUnitTooltip',
                          style={'fontWeight': 'bold',
                                 'textDecoration': 'underline',
                                 'cursor': 'pointer'}
                          ), ')'
            ], style={'fontWeight': 'bold',
                      'margin-bottom': '0.5em', }
            )
        ),
        dbc.Tooltip(
            dcc.Markdown(
                '''Envo datasets will be aggregated at the following temporal unit if finer resolution data is available'''
            ), target='timeUnitTooltip'
        ),
        dcc.RadioItems(
            id='timeUnit',
            options=[
                {'label': ' Hour ', 'value': 'hour'},
                {'label': ' Day ', 'value': 'day'},
                {'label': ' Month ', 'value': 'month'},
                {'label': ' Year ', 'value': 'year'}
            ], style={'margin-bottom': '0.5em', 'fontWeight': 'normal'}
        ),
        html.Label(
            html.Div([
                'Aggregation method:  (',
                html.Span(' i ',
                          id='stAggTooltip',
                          style={'fontWeight': 'bold',
                                 'textDecoration': 'underline',
                                 'cursor': 'pointer'}
                          ), ')'
            ], style={'fontWeight': 'bold',
                      'margin-bottom': '0.5em'}
            )
        ),
        dbc.Tooltip(
            dcc.Markdown(
                '''Spatiotemporal aggregation method for the time series observations within the selected location'''
            ), target='stAggTooltip'
        ),
        dcc.RadioItems(
            id='spAgg',
            # labelStyle={'display': 'inline-block', 'margin-right': '1em'},
            options=[
                {'label': ' Mean ', 'value': 'AVG'},
                {'label': ' Sum ', 'value': 'SUM'},
                {'label': ' Min ', 'value': 'MIN'},
                {'label': ' Max ', 'value': 'MAX'},
            ], style={'margin-bottom': '0.5em', 'fontWeight': 'normal'}
        ),

        # Submit button to display Table Output
        dbc.Spinner([
            html.Div([
                dbc.Button(children='Submit', id='submitData', n_clicks=0,
                           disabled=True, color='primary'),
            ], className='d-grid gap-2 mx-auto')
        ], color='primary'),
        # Store event dates and location and data sets associated to the events
        dcc.Store(id='evEnvoDateLocDataSet', storage_type='memory'),
        html.Div(id='testSubmit')

    ])
],  # className='mt-3',
)

# Zip download
tabDownl = dbc.Card([
    dbc.CardHeader('Query Datatables', style={'fontWeight': 'bold'}),
    dbc.CardBody([
        html.Div([
            dbc.Button(
                'Download all datatables',
                id='qDatatableZip',
                color='primary',
                style={'fontWeight': 'normal',
                       'text-align': 'center',
                       },
            ),
            dcc.Download(id='download-datatable-zip'),
        ], style={'display': 'block', 'margin-bottom': '1em', 'margin-top': '1em'}),
        html.Div([], id='zipCheck')

    ])

])

# Group elements into input and output tabs
inputTabs = dbc.Tabs(
    [
        dbc.Tab(loginInput, label='Login', style={'fontWeight': 'bold'}, id='loginTab'),
        dbc.Tab(tabQuery, label='Query', style={'fontWeight': 'bold'}, id='queryTab', disabled=True),
        dcc.Tab(tabDownl, label='Download All', style={'fontWeight': 'bold'}, id='zipTab', disabled=True),
        # dcc.Tab(tabAbout, label='About')

    ], id='inputTabs',  # className='mt-3'
)

# homeTab
homeTab = dcc.Tab(dbc.Card([
    dbc.CardHeader('SERDIF', style={'fontWeight': 'bold'}),
    dbc.CardBody([
        dbc.Row([
            dcc.Markdown(
                '''
            The SERDIF framework aims to address the interoperability challenges in environmental science
            research when integrating multiple and diverse data sources. The framework links individual
            events with scientific data through location and time using knowledge graphs. The framework is 
            a combination of a [methodology](https://github.com/navarral/serdif-example), 
            a [knowledge graph](https://serdif-example.adaptcentre.ie/) and this dashboard. 
            
            The dashboard is designed from a user-centric perspective to support researchers (1) access, 
            (2) explore and (3) export environmental data associated to individual events. 
            
            1. **Access**: selected query input options from the query panel are substituted in a SPARQL query
            template and executed against the graph database.
            2. **Explore**: after submiting a query a tab will be generated with the raw environmental data 
            associated to individual events. The data will display as a metadata summary and raw datatable,
            which can be explored through visualizations.
            3. **Export**: the event-environmental linked data can be exported as a CSV for analysis or as
            RDF following the FAIR guiding principles.
            '''
            ),
            # Store query data to be used in the generated query result tabs
            dcc.Store(id='qDataS'),
        ]),
        dbc.Row([
            dbc.CardImg(
                src=app.get_asset_url('SERDIF_GraphicalAbstract.png'),
                # className='center-block', # className='img-fluid rounded-start',
                style={'height': '80%', 'width': '80%', 'margin-bottom': '1em'},
            ),
        ], justify='center'),
    ], ),
    dbc.CardFooter([
        dbc.Row([
            dbc.Col([
                dbc.CardImg(
                    src=app.get_asset_url('researchLogoCombo.svg'),
                    className='img-fluid rounded-start',
                ), ], md=6),
            dbc.Col([dcc.Markdown('''
            This research was conducted with the financial support of [HELICAL](https://helical-itn.eu/) as part of the European Union’s 
            Horizon 2020 research and innovation programme under the Marie Sklodowska-Curie Grant Agreement 
            No. 813545 at the [ADAPT Centre for Digital Content Technology](https://www.adaptcentre.ie/) (grant number 13/RC/2106 P2) at 
            Trinity College Dublin. | Contact: albert.navarro@adaptcentre.ie
            ''', className='card-text', style={'font-size': '12px'}
                                  )], md=6),
        ], ),
    ]),
]), label='Home')

outTabs = dbc.Spinner([  # dcc.Loading([ #d
    dbc.Tabs([homeTab],  # , compTab, metaTab],
             id='outTabsT'),  # className='mt-3'),
], id='tabsLoading', color='primary'
)

# App Layout
appBody = dbc.Container([
    dbc.Row([
        dbc.Col([inputTabs], md=3),
        dbc.Col([outTabs], md=9, id='test'),
    ])
], className='mt-8', fluid=True,
)

app.layout = html.Div([topNavbarHelical, appBody])


# 0. Login with valid credentials for https://serdif-example.adaptcentre.ie/
@app.callback(
    [Output('queryTab', 'disabled'),
     Output('loginTab', 'disabled'),
     Output('inputTabs', 'active_tab'),
     Output('loginAlert', 'children'),
     Output('loginAlert', 'is_open'),
     Output('loginAlert', 'color'),
     Output('eventTypeCount', 'options')],
    [Input('signInButton', 'n_clicks')],
    [State('userInput', 'value'),
     State('passwordInput', 'value')],
)
def enableEvents(signInClick, dVal_user, dVal_psswd):
    # use the dash.callback_context property to trigger the callback only when
    # the number of clicks has changed rather than after the first click
    changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]

    if 'signInButton' not in changed_id or not signInClick or not dVal_user or not dVal_psswd:
        raise PreventUpdate
    else:
        testQuery = requests.post(
            'https://serdif-example.adaptcentre.ie/repositories/repo-serdif-events-ie',
            data={'query': 'SELECT ?s ?p ?o { ?s ?p ?o . } LIMIT 4'},
            auth=(dVal_user, dVal_psswd),
        )
        if testQuery.status_code == 200:
            # Alert data message danger
            alertDataMsg = [html.H5('Successful login!', className='alert-heading'),
                            html.P('Please proceed to the Query tab.')]
            alertColour = 'success'
            # Query number of events per type
            qEvType = nEvents(referer='https://serdif-example.adaptcentre.ie/repositories/',
                              repo='repo-serdif-events-ie',
                              username=dVal_user,
                              password=dVal_psswd)
            evTypeCountL = [evTC['eventType']['value'] + ' (' + evTC['eventCount']['value'] + ')' for evTC in qEvType]

            return [False, True, 'tab-1', alertDataMsg, True, alertColour, listToOptions(evTypeCountL)]
        else:
            # Alert data message danger
            alertDataMsg = [html.H5('Wrong credentials!', className='alert-heading'),
                            html.P('Please try again with a different user and/or password.')]
            alertColour = 'danger'
            return [True, False, 'tab-0', alertDataMsg, True, alertColour, ['']]


# 1. Enable Events after Case study has been selected
@app.callback(
    Output('eventTypeCount', 'disabled'),
    [Input('projectID', 'value')],
)
def enableEvents(dVal):
    if not dVal:
        return True
    else:
        return False


# 2.2. EOI pop up info
@app.callback(
    Output('evPopoverText', 'is_open'),
    [Input('evPopover', 'n_clicks')],
    [State('evPopoverText', 'is_open')],
)
def evTogglePopover(n, is_open):
    if n:
        return not is_open
    return is_open


# 3. Enable Events Location after Event Type has been selected
@app.callback(
    [Output('eventLoc', 'disabled'),
     Output('eventLoc', 'options')],
    [Input('eventTypeCount', 'value')],
    [State('userInput', 'value'),
     State('passwordInput', 'value')],
)
def enableEvents(dVal, dVal_user, dVal_psswd):
    if not dVal:
        locAvailable = listToOptions([''])
        return [True, locAvailable]
    else:
        qEvLoc = evLoc(
            referer='https://serdif-example.adaptcentre.ie/repositories/',
            repo='repo-serdif-events-ie',
            username=dVal_user,
            password=dVal_psswd)
        evLocList = [loc['LOI']['value'] for loc in qEvLoc]
        locAvailable = listToOptions(evLocList)
        return [False, locAvailable]


# 4. Display number of events and envo data sets fEnable Events Location after Event Type has been selected
@app.callback(
    [Output('wLength', 'disabled'),
     Output('wLag', 'disabled')],
    [Input('eventLoc', 'disabled'),
     Input('eventLoc', 'value')],
)
def enableTimeWindow(dValA, dValB):
    if dValA or not dValB:
        return [True, True]
    else:
        return [False, False]


# 5. Enable Data Availability button after the time-window parameters have been selected
@app.callback(
    [Output('evEnvoDataButton', 'disabled')],
    [Input('wLength', 'value'),
     Input('wLag', 'value'),
     Input('wLength', 'disabled'),
     Input('wLag', 'disabled')
     ],
)
def enableDataCheckButton(dValA, dValB, dValA_dis, dValB_dis):
    if not dValA or str(dValB) == 'None' or dValA_dis or dValB_dis:
        return [True]
    else:
        return [False]


# 5. Check Events and Envo datasets within the selected location
@app.callback(
    [Output('evEnvoDataText', 'children'),
     Output('evEnvoDataText', 'is_open'),
     Output('evEnvoDataText', 'color'),
     Output('evEnvoDateLocDataSet', 'data')],
    [Input('evEnvoDataButton', 'n_clicks'), ],
    [State('eventTypeCount', 'value'),
     State('eventLoc', 'value'),
     State('wLength', 'value'),
     State('wLag', 'value'),
     State('userInput', 'value'),
     State('passwordInput', 'value')
     ]
)
def clickDataAvailable(nClick, dValType, dValLoc, dValLen, dValLag, dVal_user, dVal_psswd):
    # use the dash.callback_context property to trigger the callback only when
    # the number of clicks has changed rather than after the first click
    changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]

    if 'evEnvoDataButton' not in changed_id:
        return ['', False, 'warning', {}]
    else:
        # Query envo datasets within the selected location
        qEnvoLoc = envoLoc(
            referer='https://serdif-example.adaptcentre.ie/repositories/',
            repo='repo-serdif-envo-ie',
            envoLoc=dValLoc,
            username=dVal_user,
            password=dVal_psswd
        )
        envoDSList = [envoDS['envoDataSet']['value'] for envoDS in qEnvoLoc]
        # Query events within the selected location
        qEvLoc = evTypeLocDateT(
            referer='https://serdif-example.adaptcentre.ie/repositories/',
            repo='repo-serdif-events-ie',
            evType=[evType.split(' (')[0] for evType in dValType],
            evLoc=dValLoc,
            wLen=dValLen,
            wLag=dValLag,
            username=dVal_user,
            password=dVal_psswd
        )

        evNumberList = [evInfo['event']['value'] for evInfo in qEvLoc]
        if len(evNumberList) == 0 or len(envoDSList) == 0:
            # Alert data message danger
            alertDataMsg = [html.H5('No events or envo data available!', className='alert-heading'),
                            html.P('Please try again with different input options.')]
            alertColour = 'danger'
        else:
            # Alert data message success
            alertDataMsg = [html.H5('Events and envo data available!', className='alert-heading'),
                            html.P('Events (' + str(len(evNumberList)) + ') | Envo datasets (' + str(
                                len(envoDSList)) + ')'),
                            html.P('Please continue below.')]
            alertColour = 'success'

        # Store events and envo data sets for following queries to reuse
        # Give a default data dict with empty fields if there's no data.
        dataEvEnvo = {}
        for ev in qEvLoc:
            dataEvEnvo[ev['event']['value']] = {
                'event': ev['event']['value'],
                'eventType': ev['eventType']['value'],
                'evDateT': ev['evDateT']['value'],
                'dateStart': ev['dateStart']['value'],
                'dateLag': ev['dateLag']['value'],
                'envoDS': [envoDS['envoDataSet']['value'] for envoDS in qEnvoLoc \
                           if envoDS['LOI']['value'] == ev['LOI']['value']],
                'LOI_ev': ev['LOI']['value'],
            }

        return [alertDataMsg, True, alertColour, dataEvEnvo]
    # https://serdif-example.adaptcentre.ie/resource?uri=http%3A%2F%2Fexample.org%2Fns%23event-276
    # https://serdif-example.adaptcentre.ie/graphs-visualizations?uri=http:%2F%2Fexample.org%2Fns%23ID-76-geo
    # https://serdif-example.adaptcentre.ie/graphs-visualizations?uri=http:%2F%2Fexample.org%2Fns%23event-23
    # dataset-eea-20211012T120000-IE001DM


# 6. Enable time unit selection for envo data sets if envo data and events are available
@app.callback(
    [Output('timeUnit', 'labelStyle'),
     Output('spAgg', 'labelStyle')],
    [Input('evEnvoDataText', 'color'),
     Input('projectID', 'value'),
     Input('eventTypeCount', 'value'),
     Input('eventLoc', 'value'),
     Input('wLength', 'value'),
     Input('wLag', 'value'),
     ]
)
def selTimeUnitAggMethod(dVal_color, dValProject, dValType, dValLoc, dValLen, dValLag):
    # use the dash.callback_context property to trigger the callback only when
    # the number of clicks has changed rather than after the first click
    changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]

    if 'evEnvoDataButton' not in changed_id and \
            ('dValProject' in changed_id or 'eventTypeCount' in changed_id or 'eventLoc' in changed_id or
             'wLength' in changed_id or 'wLag' in changed_id):
        return [{'display': 'none', 'margin-right': '20px'},
                {'display': 'none', 'margin-right': '20px'}]
    if dVal_color != 'success':
        return [{'display': 'none', 'margin-right': '20px'},
                {'display': 'none', 'margin-right': '20px'}]
    else:
        return [{'display': 'inline-block', 'margin-right': '1em'},
                {'display': 'inline-block', 'margin-right': '1em'}]


# 7. Enable submit button when all input options have been selected
@app.callback(
    [Output('submitData', 'disabled')],
    [Input('projectID', 'value'),
     Input('eventTypeCount', 'value'),
     Input('eventLoc', 'value'),
     Input('wLength', 'value'),
     Input('wLag', 'value'),
     Input('timeUnit', 'value'),
     Input('spAgg', 'value'),
     Input('evEnvoDateLocDataSet', 'data'),
     Input('timeUnit', 'labelStyle')],
    [State('userInput', 'value'),
     State('passwordInput', 'value')],
)
def enableSubmitButton(dVal_ProjectID, dVal_evType, dVal_evLoc, dVal_wLen, dVal_wLag,
                       dVal_tUnit, dVal_spAgg, evEnvoDataInfo, labelStyle, dVal_user, dVal_psswd,):

    if not dVal_ProjectID or not dVal_evType or not dVal_evLoc or not str(dVal_wLen) or \
            not str(dVal_wLag) or not dVal_tUnit or not dVal_spAgg or labelStyle['display'] == 'none':
        return [True]

    else:
        evEnvoAsk = evEnvoDataAsk(
            referer='https://serdif-example.adaptcentre.ie/repositories/',
            repo='repo-serdif-envo-ie',
            evEnvoDict=evEnvoDataInfo,
            username=dVal_user,
            password=dVal_psswd
        )
        if evEnvoAsk:
            return [False]
        else:
            return [True]


# 8. Submit query to retrieve environmental data associated to individual events
@app.callback(
    [Output('outTabsT', 'children'),
     Output('outTabsT', 'active_tab'),
     Output('submitData', 'href'), ],
    [Input('submitData', 'n_clicks')],
    [State('timeUnit', 'value'),
     State('spAgg', 'value'),
     State('evEnvoDateLocDataSet', 'data'),
     State('userInput', 'value'),
     State('passwordInput', 'value'),
     State('outTabsT', 'children'),
     State('wLength', 'value'),
     State('wLag', 'value'),
     ]
)
def submitQueryEvEnvo(submit_click, dVal_tUnit, dVal_spAgg, evEnvoDataInfo,
                      dVal_user, dVal_psswd, outTabsInit, dVal_wLen, dVal_wLag):
    # use the dash.callback_context property to trigger the callback only when
    # the number of clicks has changed rather than after the first click
    changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]

    if 'submitData' not in changed_id:
        raise PreventUpdate
    else:
        evEnvoDataRaw = evEnvoDataSet(
            referer='https://serdif-example.adaptcentre.ie/repositories/',
            repo='repo-serdif-envo-ie',
            evEnvoDict=evEnvoDataInfo,
            timeUnit=dVal_tUnit,
            spAgg=dVal_spAgg,
            username=dVal_user,
            password=dVal_psswd
        )
        # Read xml content and convert to dictionary to access the data within
        evEnvoData = json.loads(json.dumps(xmltodict.parse(evEnvoDataRaw['queryContent'])))

        # Select events
        eventElements = [od['eg:refEvent'] for od in evEnvoData['rdf:RDF']['rdf:Description'] if
                         'eg:refEvent' in od.keys()]
        eventKeys = [d['@rdf:resource'] for d in eventElements if type(d) is dict]
        # Build dictionary with environmental observations associated to events
        ee_dict = dict()
        for ev in eventKeys:
            # Check if there is already an event key available
            ev = ev.split('ns#')[1]
            # print(ev)
            if ev not in ee_dict:
                ee_dict[ev] = {}
                for od in evEnvoData['rdf:RDF']['rdf:Description']:
                    if ev + '-obs-' in od['@rdf:about']:
                        dateTimeKey = od['@rdf:about'].split('obs-')[1]
                        # check if there is already an event-dateT pair available
                        if dateTimeKey not in ee_dict[ev]:
                            ee_dict[ev][dateTimeKey] = {}
                        # Store values for specific event-dateTime pair
                        for envProp in od.keys():
                            if 'eg:has' in envProp:
                                envPropKey = envProp.split('eg:has')[1]
                                ee_dict[ev][dateTimeKey][envPropKey] = od[envProp]['#text']

        # Nested dictionary to pandas dataframe
        df_ee = pd.DataFrame.from_dict(
            {(i, j): ee_dict[i][j]
             for i in ee_dict.keys()
             for j in ee_dict[i].keys()},
            orient='index'
        )
        # Multi-index to column
        df_ee = df_ee.reset_index()
        # 1.Convert to CSV
        df_ee_csv = df_ee.to_csv(index=False)
        # 2.ReParse CSV object as text and then read as CSV. This process will
        # format the columns of the data frame to data types instead of objects.
        df_ee_r = pd.read_csv(io.StringIO(df_ee_csv), index_col='level_1').round(decimals=2)
        # Converting the index as dateTime
        df_ee_r.index = pd.to_datetime(df_ee_r.index)
        df_ee_r.rename(columns={'level_0': 'event'}, inplace=True)
        # Sort by event and dateT
        df_ee_r = df_ee_r.rename_axis('dateT').sort_values(by=['dateT', 'event'], ascending=[True, True])

        # print(df_ee_r)

        # z-score function that can handle NaN values
        def z_score(df):
            return (df - df.mean()) / df.std(ddof=0)

        # Compute z-scores for each numeric column and generate a standard datatable
        df_ee_std = df_ee_r.select_dtypes(include=['float64', 'int64']).apply(z_score, axis=0)
        # Extract available variables for the conditional datatable formating
        eeVarsCondF = df_ee_r.loc[:, df_ee_r.columns != 'event']
        # Insert events column to standard datatable
        # df_ee_std.insert(loc=0, column='event', value=df_ee_r.event)

        # Formatting datatable cells to detect values at least 2 sd above or below
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

        for c in eeVarsCondF:
            # Top limit for Red Background z-score > 2
            dictTop2 = copy.deepcopy(conditionalColorCols[1])
            topValStd2 = (2 * pd.Series(eeVarsCondF.loc[:, c]).std()) + pd.Series(
                eeVarsCondF.loc[:, c]).mean()
            dictTop2['if']['column_id'] = c
            dictTop2['if']['filter_query'] = '{' + c + '} > ' + str(topValStd2.round(decimals=2))

            # Bot limit for Blue Background z-score < -2
            botValStd2 = -2 * pd.Series(eeVarsCondF.loc[:, c]).std() + pd.Series(
                eeVarsCondF.loc[:, c]).mean()
            dictBot2 = copy.deepcopy(conditionalColorCols[2])
            dictBot2['if']['column_id'] = c
            dictBot2['if']['filter_query'] = '{' + c + '} < ' + str(botValStd2.round(decimals=2))

            conditionColor.append(dictTop2)
            conditionColor.append(dictBot2)

        # Output tabs IDs
        tabQueryName = 'Q' + str(submit_click)
        tabQueryID = 'tab-' + str(submit_click)  # +2 when Comparative is available
        tabQueryDataID = 'tabID' + '_' + tabQueryName
        tabQueryTableID = {'type': 'qDataTable',
                           'index': 'dataTable' + '_' + tabQueryName,
                           }
        # METADATA
        # Select file size for metadata
        fileSizeRDF = str(sys.getsizeof(evEnvoDataRaw['queryContent']))
        # Select query time for metadata
        qtDateTime = [od['qb:observation'] for od in evEnvoData['rdf:RDF']['rdf:Description'] if
                      'qb:observation' in od.keys()][0]['@rdf:resource'].split('QT_')[1].split('-event')[0]
        # Metadata construct query
        qMetadataExp = genMetadataFile(
            queryTimeUrl=str(qtDateTime),
            evEnvoDict=evEnvoDataInfo,
            timeUnit=dVal_tUnit,
            spAgg=dVal_spAgg,
            username=dVal_user,
            password=dVal_psswd,
            fileSize=fileSizeRDF,
            wLag=dVal_wLag,
            wLen=dVal_wLen,
            qText=evEnvoDataRaw['queryBody'],
            eeVars=list(eeVarsCondF),
        )
        # Select only lineage metadata
        linMetadata = qMetadataExp.split('# -- Data provenance and lineage ---------------------------------------\n\n')[1].split('\n\n# -- Data protection terms ---------------------------------------------')[0]
        ################################################
        ####         Datatable definition           ####
        ################################################
        df_ee_r = df_ee_r.reset_index()
        # Data table to show:
        df_ee_colNames = [{"name": i, "id": i, "hideable": True} for i in df_ee_r.columns]
        # Variable description
        df_ee_desc = envoVarNameUnit(
            referer='https://serdif-example.adaptcentre.ie/repositories/',
            repo='repo-serdif-envo-ie',
            username=dVal_user,
            password=dVal_psswd
        )
        df_ee_desc['event'] = 'Events'
        # Data table dash definition
        eeDatatable = dash_table.DataTable(
            id=tabQueryTableID,
            style_table={'overflowX': 'auto'},
            style_cell={
                'overflow': 'hidden',
                'textOverflow': 'ellipsis',
                'width': 100,
                'minWidth': 100,
                #'maxWidth': 100,
                'textAlign': 'center'
            },
            fill_width=True,
            style_header={
                'backgroundColor': '#17a2b8',  # '#458B74',
                'fontWeight': 'bold',
                'color': 'white',
                'textDecoration': 'underline',
                'textDecorationStyle': 'dotted',
            },
            style_data_conditional=conditionColor,
            tooltip_header=df_ee_desc,
            tooltip_delay=0,
            tooltip_duration=None,
            column_selectable='single',
            export_format='csv',
            export_headers='display',
            sort_action='native',
            page_size=24,
            fixed_rows={'headers': True},
            columns=df_ee_colNames,
            data=df_ee_r.to_dict('records'),

            # Style the tooltip headers and export button
            css=[{
                'selector': '.dash-table-tooltip',
                'rule': 'background-color: #A4DCD1'
            }],
        )

        datatableInfo = html.Div([dcc.Markdown(
            '''
        **Datatable background:**
        If data is normally distributed 95% should be between -2 and +2 Z-scores (white)
        * Values > 2 are **high** (red) | Values < -2 are **low** (blue)
        Z-scores are computed using the mean value form the data available in the data table
        ''')],style={'margin-top': '0.5em'})

        # Heatmap to represent the value of an environmental
        # variable for all events over time
        eeHeatmap = [
            dcc.Dropdown(
                id={'type': 'qHeatmap',
                    'index': submit_click},
                options=listToOptions(eeVarsCondF),
                multi=False,
                style={'margin-top': '0.5em'}
            ),
            html.Div(
                id={'type': 'pHeatmap',
                    'index': submit_click}
            ),
        ]

        # Boxplot to represent the values distribution of an
        # environmental variable for all events
        eeBoxPlot = [
            dcc.Dropdown(
                id={'type': 'qBoxplot',
                    'index': submit_click},
                options=listToOptions(eeVarsCondF),
                multi=False,
                style={'margin-top': '0.5em'}
            ),
            html.Div(
                id={'type': 'pBoxplot',
                    'index': submit_click}
            ),
        ]

        # Boxplot to represent the values distribution of an
        # environmental variable for all events
        eeVarsCondF_Polar = [e for e in eeVarsCondF if e not in ('Wdsp', 'Wddir')]
        eePolarPlot = [
            dcc.Dropdown(
                id={'type': 'qPolarplot',
                    'index': submit_click},
                options=listToOptions(eeVarsCondF_Polar),
                multi=False,
                style={'margin-top': '0.5em'}
            ),
            html.Div(
                id={'type': 'pPolarplot',
                    'index': submit_click}
            ),
        ]
        query_buttons = html.Div([
            dbc.Button('Data Provenance', color='primary', className='me-1',
                       id={'type': 'provTableButton',
                           'index': submit_click}
                       ),
            dbc.Button('Data Lineage', color='primary', className='me-1',
                       id={'type': 'dataLinVizButton',
                           'index': submit_click}
                       ),
            dbc.Button('Full Metadata Exploration', color='primary', className='me-1',
                       id={'type': 'metadataVizButton',
                           'index': submit_click}
                       ),
            dbc.Button('FAIR Metadata Export', color='primary', className='me-1',
                       id={'type': 'fairMetadataExportButton',
                           'index': submit_click}
                       ),
            dbc.Button('FAIR Data Export', color='primary', className='me-1',
                       id={'type': 'fairDataExportButton',
                           'index': submit_click}
                       ),

        ], style={'marginBottom': '0.5em','display': 'inline-block', 'margin-right': '0.5em'})

        # FAIR data export
        fairExport = html.Div([
            dcc.Download(id={'type': 'fairDataExportFile',
                             'index': submit_click},
                         ),
            # Store FAIR data to be used in the generated query result tabs
            dcc.Store(id={'type': 'qDataSFAIR',
                          'index': submit_click},
                      data=evEnvoDataRaw['queryContent'].decode('utf8'),
                      ),
        ])

        # Data Lineage text area
        dataLinViz = html.Div([
            # Store FAIR data to be used in the generated query result tabs
            dbc.Collapse(
                dbc.Card([
                    dcc.Textarea(
                        id={'type': 'dataLinVizText',
                            'index': submit_click},
                        value=linMetadata,
                        style={'width': '100%', 'height': '100%'},
                        #contentEditable=False,
                        readOnly=True,
                    ),
                ], style={'height': '20em'}),
                id={'type': 'dataLinVizCol',
                    'index': submit_click},
                is_open=False,
            ),
        ], style={'marginBottom': '0.5em', 'display': 'inline-block', 'margin-right': '0.5em', 'width': '100%',
                  'height': '100%'})

        # Metadata text area
        metadataExport = html.Div([

            dcc.Download(id={'type': 'fairMetadataExportFile',
                             'index': submit_click},
                         ),
            # Store FAIR data to be used in the generated query result tabs
            dcc.Store(id={'type': 'qMetadataSFAIR',
                          'index': submit_click},
                      data=qMetadataExp,
                      ),
        ])

        metadataViz = html.Div([
            # Store FAIR data to be used in the generated query result tabs
            dbc.Collapse(
                dbc.Card([
                    dcc.Textarea(
                        id={'type': 'metadataVizText',
                            'index': submit_click},
                        value=qMetadataExp,
                        style={'width': '100%', 'height': '100%'},
                        readOnly=True,
                    ),
                ], style={'height':'20em'}), #qMetadataExp
                id={'type': 'metadataVizCol',
                    'index': submit_click},
                is_open=False,
            ),
        ], style={'marginBottom': '0.5em','display': 'inline-block', 'margin-right': '0.5em', 'width': '100%', 'height': '100%'})

        # Nested dictionary to dataframe
        provDF = pd.DataFrame.from_dict(evEnvoDataInfo, orient='index')
        provDF['event'] = provDF['event'].str.replace('http://example.org/ns#', 'eg:')
        provDF['caseStudy'] = 'Example Events\nIreland'
        provDF['envoDS'] = ['\n'.join(e).replace('http://example.org/ns#', 'eg:') for e in provDF['envoDS'].values.tolist()]

        # Rename columns
        provDF.rename(columns={'LOI_ev': 'county', 'dateLag': 'dateLag', 'dateStart': 'dateStart',
                               'envoDS': 'dataSetsUsed', 'evDateT': 'eventDate', 'event': 'event',
                               'eventType':'eventType','caseStudy':'caseStudy'
                               }, inplace=True)

        # Reorder columns
        provDF = provDF[['caseStudy','event', 'eventType', 'county', 'eventDate', 'dataSetsUsed']] # 'dateStart', 'dateLag',


        provTable = html.Div([
            # Store FAIR data to be used in the generated query result tabs
            dbc.Collapse(
                dbc.Card([
                    #dbc.Table.from_dataframe(provDF, striped=True, bordered=True,size='sm', responsive='sm',style={'height':'20em'})
                    dash_table.DataTable(
                        data=provDF.to_dict('records'),
                        columns=[{'id': c, 'name': c} for c in provDF.columns],
                        page_action='none',
                        style_table={'overflowY': 'auto', 'overflowX': 'auto'},
                        fixed_rows={'headers': True},
                        style_header={'fontWeight': 'bold','textAlign': 'center'},
                        export_format='csv',
                        export_headers='display',
                        style_cell={
                            'whiteSpace': 'pre-line',
                            'height': 'auto',
                            'textAlign': 'center'
                           # 'maxWidth': '20'
                        },
                    )

                ]),
                id={'type': 'provTableCol',
                    'index': submit_click},
                is_open=False,
            ),
        ], style={'marginBottom': '0.5em', 'display': 'inline-block',
                  'margin-right': '0.5em', 'width': '100%', 'height': '100%'}
        )

        # https://serdif-example.adaptcentre.ie/graphs-visualizations?query=CONSTRUCT%7B%0A%20%20%20%20%3Fs%20%3Fp%20%3Fo%20.%0A%7D%0Awhere%20%7B%20%0A%09%3Fs%20%3Fp%20%3Fo%20.%0A%7D%20limit%2010%20%0A&sameAs&inference

        # New tab per Query
        tabNew = dbc.Card([
            dbc.CardHeader('Event-environmental linked data through location & time'),
            dbc.CardBody([
                html.Div([
                    dcc.Markdown('''
                    The buttons below can be clicked to comprehend the event-environmental linked data through data
                    provenance, lineage, risks, use and limitations; and to export FAIR (meta)data for publishing.
                    The text area displayed when clicking the Full Metadata Exploration button can be searched with 
                    CTRL+F for specific information (e.g. eg:DataUse, eg:IdentificationRisk, dct:license)
                    '''),
                    query_buttons,
                    provTable,
                    dataLinViz,
                    metadataViz,
                    metadataExport,
                    fairExport,

                ], style={'margin-bottom':'-1em'}),
                dbc.Tabs([
                    dcc.Tab([datatableInfo, eeDatatable], label='Datatable'),
                    dcc.Tab(eeHeatmap, label='Heatmap'),
                    dcc.Tab(eeBoxPlot, label='BoxPlot'),
                    dcc.Tab(eePolarPlot, label='PolarPlot'),
                ])
            ])
        ], className='mt-3', id=tabQueryDataID
        )

        # Add new Patient data everytime there is a submit
        outTabsInit.append(dcc.Tab(tabNew, label=tabQueryName))

        # Button title to block double clicks
        subTitleToolTip = 'Queries submitted: ' + str(submit_click)

        return [outTabsInit, tabQueryID, subTitleToolTip]


# 9. Store Query data after submitting
@app.callback(
    [Output('qDataS', 'data')],
    [Input('submitData', 'n_clicks'),
     Input({'type': 'qDataTable', 'index': ALL}, 'data')],
    [State('qDataS', 'data')]
)
def queryDataStore(submit_click, dataTableQ, dataQStore):
    if not submit_click or not dataTableQ:
        raise PreventUpdate
    elif len(dataTableQ) != submit_click:
        raise PreventUpdate
    else:
        # Create the dictionary if there is not already one stored
        if not dataQStore:
            dataQStore = {}

        qNum = 'Q' + str(submit_click)
        dataQStore[qNum] = dataTableQ[submit_click - 1]

        return [dataQStore]


# 10. Heatmap variable selection display plot
@app.callback(
    [Output({'type': 'pHeatmap', 'index': MATCH}, 'children')],
    [Input({'type': 'qHeatmap', 'index': MATCH}, 'value'),
     Input('qDataS', 'data')],
    [State({'type': 'qHeatmap', 'index': MATCH}, 'id'),
     State('userInput', 'value'),
     State('passwordInput', 'value'),
     ]
)
def heatmapVar(dVal_Heatmap, dataQStore, qNumID, dVal_user, dVal_psswd):
    if not dataQStore or not dVal_Heatmap:
        raise PreventUpdate
    else:
        # Generate query num label
        qNumData = 'Q' + str(qNumID['index'])
        # Import data from queries
        envQData = pd.DataFrame(dataQStore[qNumData])
        # Heatmap plot: https://plotly.com/python/heatmaps/ https://plotly.com/python/box-plots/
        envQData = envQData[['dateT', 'event', dVal_Heatmap]]
        # Drop events full of NaN for the selected variable
        envQData = envQData.loc[envQData.groupby('event')[dVal_Heatmap].filter(lambda x: len(x[pd.isnull(x)]) != len(x)).index]
        envQData['dateT'] = pd.to_datetime(envQData['dateT'])
        envQData['rank'] = envQData.groupby('event')['dateT'].rank(ascending=True)
        # Temporal units
        dateDiff = envQData['dateT'][0] - envQData['dateT'][1]
        timeUnitsNum = float(str(dateDiff).split(' days')[0][1:])
        if timeUnitsNum < 1:
            timeUnitLabel = '[HOUR]'
        elif timeUnitsNum == 1:
            timeUnitLabel = '[DAY]'
        elif 1 < timeUnitsNum < 30:
            timeUnitLabel = '[MONTH]'
        else:
            timeUnitLabel = '[YEAR]'
        # Variable full name and units
        df_ee_desc = envoVarNameUnit(
            referer='https://serdif-example.adaptcentre.ie/repositories/',
            repo='repo-serdif-envo-ie',
            username=dVal_user,
            password=dVal_psswd
        )
        # Number of Ranks
        numRank = envQData['rank'].unique()
        # Number of events
        numEvents = envQData['event'].unique()
        envQData_f = [v.tolist() for v in envQData.set_index(dVal_Heatmap).groupby('event', sort=False, as_index=False).groups.values()]

        heatmapFig = px.imshow(
            envQData_f,
            labels=dict(x='Relative time from the event ' + timeUnitLabel, y='', color=dVal_Heatmap),
            x=-numRank,
            y=numEvents,
            color_continuous_scale='YlGnBu',
            title=df_ee_desc[dVal_Heatmap],
        )
        heatmapFig.update_xaxes(rangeslider_visible=True, ) #autorange='reversed', 
        heatmapFig.update_layout(
            yaxis_nticks=len(envQData['event'].unique()),
            font=dict(size=16),
        )

        return [dcc.Graph(figure=heatmapFig, id='heatmap' + qNumData)]


# 11. Box plot variable selection display plot
@app.callback(
    [Output({'type': 'pBoxplot', 'index': MATCH}, 'children')],
    [Input({'type': 'qBoxplot', 'index': MATCH}, 'value'),
     Input('qDataS', 'data')],
    [State({'type': 'qBoxplot', 'index': MATCH}, 'id'),
     State('userInput', 'value'),
     State('passwordInput', 'value')]
)
def boxPlotVar(dVal_Boxplot, dataQStore, qNumID, dVal_user, dVal_psswd):
    if not dataQStore or not dVal_Boxplot:
        raise PreventUpdate
    else:
        # Generate query num label
        qNumData = 'Q' + str(qNumID['index'])
        # Import data from queries
        envQData = pd.DataFrame(dataQStore[qNumData])
        # Box plot: https://plotly.com/python/box-plots/
        envQData = envQData[['dateT', 'event', dVal_Boxplot]]
        envQData['dateT'] = pd.to_datetime(envQData['dateT'])
        envQData['rank'] = envQData.groupby('event')['dateT'].rank(ascending=True)
        # Variable full name and units
        df_ee_desc = envoVarNameUnit(
            referer='https://serdif-example.adaptcentre.ie/repositories/',
            repo='repo-serdif-envo-ie',
            username=dVal_user,
            password=dVal_psswd
        )
        boxplotFig = px.box(x=envQData[dVal_Boxplot], y=envQData['event'], points="all",
                            category_orders=envQData.columns)
        boxplotFig.update_traces(
            marker_size=2,
            marker_outliercolor='red',
            selector=dict(type='box'),
            orientation='h')
        boxplotFig.update_layout(
            xaxis_title= df_ee_desc[dVal_Boxplot],
            yaxis_title='',
            font=dict(size=16)
        )

        return [dcc.Graph(figure=boxplotFig, id='boxplot' + qNumData)]


# 11. Polar plot variable selection display plot
@app.callback(
    [Output({'type': 'pPolarplot', 'index': MATCH}, 'children')],
    [Input({'type': 'qPolarplot', 'index': MATCH}, 'value'),
     Input('qDataS', 'data')],
    [State({'type': 'qPolarplot', 'index': MATCH}, 'id')]
)
def polarPlotVar(dVal_Polarplot, dataQStore, qNumID):
    if not dataQStore or not dVal_Polarplot:
        raise PreventUpdate
    else:
        # Generate query num label
        qNumData = 'Q' + str(qNumID['index'])
        # Import data from queries
        envQData = pd.DataFrame(dataQStore[qNumData])
        # Bivariate polar plot
        checkWindVarsL = ['Wdsp', 'Wddir']
        if not set(checkWindVarsL).issubset(envQData.columns.values):
            noWindVarsAlert = dbc.Alert(
                children=[html.H5('No wind variables available!', className='alert-heading'),
                          html.P('Please try again with different LOCATION input options.')],
                id='polarplot' + qNumData,
                dismissable=False,
                is_open=True,
                style={'verticalAlign': 'middle',
                       'margin-bottom': '0.5em',
                       'fontWeight': 'normal',
                       },
                color='danger'
            ),
            return noWindVarsAlert
        else:
            envQData = envQData[['Wdsp', 'Wddir', dVal_Polarplot]]
            envQData = envQData[envQData[dVal_Polarplot].notna()]
            dfToPolar(df=envQData, dVal_Polarplot=dVal_Polarplot,
                      fileName='polarRPY2.png') #os.getcwd() +
            encoded_image = base64.b64encode(open('polarRPY2.png', 'rb').read()).decode('ascii').replace('\n', '')
            return [html.Img(id='polarplot' + qNumData,
                             src='data:image/png;base64,{}'.format(encoded_image))]  # fig_to_uri(fig))]


# 12. Download FAIR data
@app.callback(
    Output({'type': 'fairDataExportFile', 'index': MATCH}, 'data'),
    Input({'type': 'fairDataExportButton', 'index': MATCH}, 'n_clicks'),
    State({'type': 'qDataSFAIR', 'index': MATCH}, 'data'),
    # prevent_initial_call=True,
)
def downloadFAIRdata(fairData_clicks, fairData):
    if not fairData_clicks:
        raise PreventUpdate
    else:
        dataFileName = 'dataset-ee-20211012T120000-IE' + '.rdf'
        return dict(content=fairData, filename=dataFileName,
                    type='application/xml')

# 13. Download FAIR metadata
@app.callback(
    Output({'type': 'fairMetadataExportFile', 'index': MATCH}, 'data'),
    Input({'type': 'fairMetadataExportButton', 'index': MATCH}, 'n_clicks'),
    State({'type': 'qMetadataSFAIR', 'index': MATCH}, 'data'),
    # prevent_initial_call=True,
)
def downloadFAIRdata(fairMetadata_clicks, fairMetadata):
    if not fairMetadata_clicks:
        raise PreventUpdate
    else:
        dataFileName = 'metadata-ee-20211012T120000-IE' + '.ttl'
        return dict(content=fairMetadata, filename=dataFileName,
                    type='text/plain')


# 14. Display FAIR metadata
@app.callback(
    Output({'type': 'metadataVizCol', 'index': MATCH}, 'is_open'),
    Input({'type': 'metadataVizButton', 'index': MATCH}, 'n_clicks'),
    State({'type': 'metadataVizCol', 'index': MATCH}, 'is_open'),
    # prevent_initial_call=True,
)
def vizFAIRMetadata(n, is_open):
    if n:
        return not is_open
    return is_open

# 15. Enable download all tab and Comparative tab after submitting the first query
@app.callback(
    [Output('zipTab', 'disabled')],
     #Output('compTab', 'disabled')
    [Input('qDataS', 'data')],
)
def enableDownloadAll(dVal):
    if not dVal:
        return [True] #, True]
    else:
        return [False] #, False]


# 16. Download all data tables (CSV) as a zip file
@app.callback(
    [Output('download-datatable-zip', 'data')],
    [Input('qDatatableZip', 'n_clicks')],
    [State('qDataS', 'data')]
)
def allQueryDownload(zip_click, dataQStore):
    if not zip_click or not dataQStore:
        raise PreventUpdate
    else:
        # Store data as CSV files within a zip file
        zipDownlLink = 'userDataTables-ee-20211012T120000-IE.zip'
        with zipfile.ZipFile(zipDownlLink, 'w') as csv_zip:
            for qNum, qDataTable in dataQStore.items():		
                csv_zip.writestr(qNum + '.csv', pd.DataFrame(qDataTable).to_csv())

        return [dcc.send_file(zipDownlLink,filename='userDataTables-ee-20211012T120000-IE.zip')]


# 17. Display Data Provenance summary
@app.callback(
    Output({'type': 'provTableCol', 'index': MATCH}, 'is_open'),
    Input({'type': 'provTableButton', 'index': MATCH}, 'n_clicks'),
    State({'type': 'provTableCol', 'index': MATCH}, 'is_open'),
    # prevent_initial_call=True,
)
def vizDataProv(n, is_open):
    if n:
        return not is_open
    return is_open


# 18. Display Data Lineage summary
@app.callback(
    Output({'type': 'dataLinVizCol', 'index': MATCH}, 'is_open'),
    Input({'type': 'dataLinVizButton', 'index': MATCH}, 'n_clicks'),
    State({'type': 'dataLinVizCol', 'index': MATCH}, 'is_open'),
    # prevent_initial_call=True,
)
def vizvizDataLin(n, is_open):
    if n:
        return not is_open
    return is_open

if __name__ == '__main__':
    app.run_server(debug=False, dev_tools_props_check=False,  #dev_tools_ui=False,
                   host='0.0.0.0', port=5000)
