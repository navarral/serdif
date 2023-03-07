import dash
from dash import dcc, html, Input, Output, State, MATCH, ALL, dash_table
# from dash_table.Format import Format, Scheme, Sign, Symbol
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import pandas as pd
import base64
import datetime
import io
import os
from openready.api_openready import evLoc, serdifAPI
import flag
import flagpy as fp

app = dash.Dash(
    external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.BOOTSTRAP]
)

app.title = 'SERDIF'
server = app.server

serdif_example_endpoint = 'https://serdif-example.adaptcentre.ie/repositories/',
serdif_example_ie_repo = 'repo-serdif-envo-ie',
qEvLoc = evLoc(referer=serdif_example_endpoint, repo=serdif_example_ie_repo)
evLocList = [loc['LOI']['value'] for loc in qEvLoc]

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
    brand='SERDIF - Semantic Environmental and Rare Disease data Integration Framework (v.0.2.0)',
    brand_href='#',
    sticky='top',
    # style={'background-color': '#ffffff'}
)

'''
dbc.Card(
    dbc.CardBody(
        [
            html.Div([
                html.Div([
                    html.Div([html.P('Supported Countries:', className='card-text')],
                             style={'marginRight': '1rem', 'font-size': '12px', 'marginBottom': '-1.5rem'}),
                    html.I(className='bi bi-bicycle me-1',
                           style={'font-size': '3rem', 'marginBottom': '-1.5rem'}),
                ], className='d-flex align-items-center', ),
                html.Div([
                    html.Div([html.P('Environmental data:', className='card-text')],
                             style={'marginRight': '1rem', 'font-size': '12px', 'marginBottom': '-1rem'}),
                    html.I(className='bi bi-cloud-sun me-1',
                           style={'font-size': '3rem', 'marginBottom': '-1rem'}),
                    html.I(className='bi bi-cloud-haze me-1',
                           style={'font-size': '3rem', 'marginLeft': '1rem', 'marginBottom': '-1rem'}),
                ], className='d-flex align-items-center', ),
            ], style={'marginBottom': '-4rem', 'marginLeft': '60rem', 'marginTop': '-6rem', 'width':'60%'})
        ],
    ), style={'borderWidth': '0px'},
),
'''

# Steps summary summarizing how to use the converter
howto_card = dbc.Card(
    dbc.CardBody(
        [
            dbc.Row([
                dbc.Col([
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.Div([html.H5('1', className='card-title')], style={'marginRight': '0.5rem'}),
                                # , 'color': '#66b2b2'
                                html.I(className='bi bi-box-arrow-up me-6', style={'font-size': '3rem'}),
                                # box-seam for the output #card-checklist for options
                                # layer-forward and layer-backward to exemplify the uplift and downlift
                                # share to exemplify linkage
                                # table to exemplify the csv input
                                # tag for metadata

                                html.Div([
                                    html.P(
                                        'Upload the Event file to convert'
                                    ),
                                ], style={'marginLeft': '1rem'})
                            ], className='d-flex align-items-center',
                        ), style={'borderWidth': '0px'},
                    ),

                ]),
                dbc.Col([
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.Div([html.H5('2', className='card-title')], style={'marginRight': '1rem'}),
                                html.I(className='bi bi-calendar4-range me-6', style={'font-size': '3rem'}),
                                html.Div([
                                    html.P(
                                        'Choose target options'
                                    ),
                                ], style={'marginLeft': '1rem'})
                            ], className='d-flex align-items-center',
                        ), style={'borderWidth': '0px'},
                    ),

                ]),
                dbc.Col([
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.Div([html.H5('3', className='card-title')], style={'marginRight': '1rem'}),
                                html.I(className='bi bi-box-seam me-6', style={'font-size': '3rem'}),
                                html.Div([
                                    html.P(
                                        'Download the output as a zip file'
                                    ),
                                ], style={'marginLeft': '1rem'})
                            ], className='d-flex align-items-center',
                        ), style={'borderWidth': '0px'},
                    ),

                ]),
            ]),
        ],  # style={'textAlign': 'center'}
    ), style={'borderWidth': '0px', 'marginBottom': '-1rem', 'marginTop': '-1rem'},
    className='d-grid gap-2 col-10 mx-auto',
)

# Data availability table info
df_datakg = pd.DataFrame({
    'Data Type': ['Climate', 'Air Pollution'],
    'Data Source': ['<a href="https://doi.org/10.24381/cds.e2161bac" target="_blank">Copernicus</a>',
                    '<a href="https://www.eea.europa.eu/data-and-maps/data/aqereporting-9" target="_blank">EEA</a>'],
    'Period': ['2000-2021', '2000-2021'],
    'Country': [flag.flagize('Ireland :IE: - United Kingdom :GB: - Switzerland :CH: - Czechia :CZ: '),
                flag.flagize('Ireland :IE: - United Kingdom :GB: - Switzerland :CH: - Czechia :CZ: ')]
})

linkageEx_card = dbc.Card(
    [
        dbc.Row(
            [
                dbc.Col(
                    dbc.CardImg(
                        src=app.get_asset_url('environmental_data_before_event.png'),
                        className='img-fluid rounded-start',
                    ),
                    className="col-md-6",
                ),
                dbc.Col(
                    dbc.CardBody(
                        [
                            html.H4('Example use case', className="card-title"),
                            dcc.Markdown(
                                '''
                                A health data researcher is trying to understand why two patients (A and B) have disease
                                flares during different times, which could be related to the environment each patient
                                is exposed to.
                                
                                * A-flare-01: located in POINT(-6.2539, 53.3431) at 2010-01-14.
                                * B-flare-01: located in POINT(-8.4241, 51.8902) at 2010-03-20.
                                
                                The researcher inputs the event data into the serdif UI, selects the linkage options and
                                exports the linked event-environmental data and interactive report to study both events. 
                                ''',
                                className='card-text',
                            ),
                            html.Small(
                                html.A(
                                    'Example output data',
                                    href='https://doi.org/10.5281/zenodo.5544257',
                                    target='_blank'),
                                className="card-text text-muted",
                            ),
                        ]
                    ),
                    className='col-md-6',
                ),
            ],
            className='g-0 d-flex align-items-center',
        )
    ], color='light', outline=True,
    className='mb-3',
    # style={"maxWidth": "540px"},
)

titleAndDataLink = html.Div([
    html.H5('How to Convert Event Files to Event-Environmental Linked Data',
            style={'textAlign': 'center', 'marginTop': '2rem', 'marginBottom':'2rem' },
            className='card-title'),
    dbc.Card([
        dbc.CardBody([
            dbc.Row([
                html.H6(
                    'Event: something that occurs in a certain place during a particular time.',
                    className='card-title', style={'textAlign': 'center', 'marginBottom': '0.5rem'}),
                html.Hr(),
                dcc.Markdown('''              
                    Environmental data is associated with individual events through **location** and **time**.
                    The linkage is the result of a semantic query that integrates environmental data **within a region/closest to the event** 
                    and selects a **period of data before the event**.
                    ''', className='justify-content-center'
                             ),
                linkageEx_card,
                html.Div(style={'margin-bottom': '1rem'}),
                html.Hr(),
            ]),
            dbc.Row([
                howto_card,
                html.Hr(),
            ]),
            dbc.Row([
                html.Label('Data Available:', style={'fontWeight': 'bold', 'marginRight': '2rem'}),
                dash_table.DataTable(
                    data=df_datakg.to_dict('records'),
                    columns=[{'name': i, 'id': i, 'presentation': 'markdown'} for i in df_datakg.columns],
                    id='table-data-kg',
                    markdown_options={'html': True},
                    style_header={
                        'backgroundColor': '#66b2b2',  # '#458B74',
                        'fontWeight': 'bold',
                        'color': 'white',
                        'textAlign': 'center'
                    },
                    style_cell={
                        'textAlign': 'center'
                    },
                    style_data={
                        'whiteSpace': 'normal',
                        'height': 'auto',
                        'textAlign': 'center'
                    },
                    # textAlign center does not work if the table has markdown options, it needs to be included as following:
                    css=[dict(selector="p", rule="margin: 0px; text-align: center")]
                ),
            ], style={'width': '90%', 'marginBottom': '1rem', }, className='d-grid gap-2 col-6 mx-auto'),
        ])
    ], color='dark', outline=True, style={'marginBottom': '1rem'},
        className='d-grid gap-2 col-10 mx-auto')
])

# Acknowledgements and contact
contact_card = dbc.Card(
    [
        dbc.Row(
            [
                dbc.Col(
                    dbc.CardImg(
                        src=app.get_asset_url('researchLogoCombo.svg'),
                        className='img-fluid rounded-start',
                    ),
                    className='col-md-6',
                ),
                dbc.Col(
                    dbc.CardBody(
                        [
                            dcc.Markdown('''
                                This research was conducted with the financial support of [HELICAL](https://helical-itn.eu/) as part of the European Union’s 
                                Horizon 2020 research and innovation programme under the Marie Sklodowska-Curie Grant Agreement 
                                No. 813545 at the [ADAPT Centre for Digital Content Technology](https://www.adaptcentre.ie/) (grant number 13/RC/2106 P2) at 
                                Trinity College Dublin. | Contact: albert.navarro@adaptcentre.ie
                                ''', className='card-text', style={'font-size': '12px'}
                                         )
                        ]
                    ),
                    className='col-md-6',
                ),
            ],
            className="g-0 d-flex align-items-center",
        )
    ],
    className='d-grid gap-2 col-10 mx-auto',
    style={'borderWidth': '0px', },
)

stepsNav = html.Div([
    dbc.Nav(
        [
            dbc.NavItem(dbc.NavLink('Step 1: Upload', href="#", active=True)),
            dbc.NavItem(dbc.NavLink('Step 2: Options', href="#")),
            dbc.NavItem(dbc.NavLink('Step 3: Output', href="#")),
        ],
        pills=True, justified=True
    )
], style={'width': '70%', 'textAlign': 'center', 'marginBottom': '1rem'}, className='d-grid gap-2 col-6 mx-auto'
)

# Read example data
df_event_data = pd.read_csv('event_data.csv')

# Step 1 card where the user uploads the Event file
step1_card = dbc.Card(
    [
        # dbc.CardHeader('Input'),
        dbc.CardBody(
            [
                html.H5('Step 1: Upload', className="card-title"),
                html.P('Import a data table following the example below'),
                html.Div([
                    dcc.Upload(
                        id='upload-data',
                        children=html.Div([
                            'Drag and Drop or ',
                            html.A('Select File')
                        ]),
                        style={
                            'width': '100%',
                            'height': '60px',
                            'lineHeight': '60px',
                            'borderWidth': '1px',
                            'borderStyle': 'dashed',
                            'borderRadius': '5px',
                            'textAlign': 'center',
                        },
                        # Allow multiple files to be uploaded
                        multiple=False,
                    ),
                ], style={'marginBottom': '1em'},
                    className='d-grid gap-2 col-6 mx-auto'),
                dbc.Alert(is_open=False, id='data-upload-user-alert'),
                html.P('or', style={'marginBottom': '1em'}),
                html.P('Edit the data table following the example inputs below'),
                html.Div([
                    dash_table.DataTable(
                        id='table-events-example',
                        data=df_event_data.to_dict('records'),
                        # columns=[{'id': cn, 'name': cn} for cn in df_event_data.columns],
                        columns=[
                            {'id': 'event', 'name': 'event', 'type': 'text'},
                            {'id': 'country', 'name': 'country', 'type': 'text'},
                            {'id': 'region', 'name': 'region', 'type': 'text'},
                            {'id': 'evDateT', 'name': 'evDateT', 'type': 'text'},
                            {'id': 'wLag', 'name': 'wLag', 'type': 'numeric'},
                            {'id': 'wLen', 'name': 'wLen', 'type': 'numeric'},
                        ],
                        tooltip_header={
                            'event': 'Name of the event',
                            'country': 'Two-letter country code [ISO 3166 ALPHA-2]',
                            'region': 'Region(s) within the country in capitals (separated with a space)',
                            'evDateT': 'Datetime of the event [YYYY-MM-DDThh:mm:ssTZ]',
                            'wLen': 'Time interval to gather data [days]',
                            'wLag': 'Time between the data and the event [days]',
                        },
                        # Style the tooltip headers and export button
                        css=[{
                            'selector': '.dash-table-tooltip',
                            'rule': 'background-color: #e6e6e6'
                        }],
                        tooltip_delay=0,
                        tooltip_duration=None,
                        editable=True,
                        row_deletable=True,
                        export_format='csv',
                        export_headers='display',
                        sort_action='native',
                        style_header={
                            'backgroundColor': '#66b2b2',  # '#458B74',
                            'fontWeight': 'bold',
                            'color': 'white',
                            'textAlign': 'center'
                        },
                        style_cell={
                            'textAlign': 'center'
                        },
                    ),
                ], style={'width': '90%', 'marginBottom': '1rem'}, className='d-grid gap-2 col-6 mx-auto'
                ),
                dbc.Button('Add Row', id='editing-rows-button', n_clicks=0,
                           color='secondary', outline=True,
                           style={'marginBottom': '1rem'}),
                # html.Hr(style={'width': '10%'}),
                dbc.Button('Upload Data Table', color='primary', id='upload-file-button', n_clicks=0,
                           outline=True, className='d-grid gap-2 col-3 mx-auto', style={'marginBottom': '1rem'}),
                dbc.Alert('The data table was successfully uploaded! Go to Step 2: Options.', color='success',
                          is_open=False, id='upload-data-alert', dismissable=False)
            ]
        ),
    ], style={'width': '70%', 'textAlign': 'center', 'marginBottom': '2rem', 'borderWidth': '0.2rem', },
    className='d-grid gap-2 col-6 mx-auto'
)

# Step 2 card where the user select the conversion options according to their needs
step2_card = dbc.Card(
    [
        dbc.CardBody(
            [
                html.H5('Step 2: Options', className='card-title'),
                html.P('Choose from the conversion options below according to your needs'),
                html.Hr(),
                html.Div([
                    dcc.Markdown(
                        'The research purpose affects the metadata record which is generated in the conversion. '
                        'The record supports the re-use, traceability and analysis the data in a transparent manner '
                        'since it includes information about the data origin, processing, use with the associated '
                        'risks and governance.'
                    ),
                    html.Label('Conversion Purpose:', style={'fontWeight': 'bold', 'marginRight': '2rem'}),
                    dbc.Button('Research', id='research-button', active=False, disabled=True,
                               color='success', outline=True, size='me-1',
                               style={'marginRight': '2rem'}),
                    dbc.Tooltip('The research metadata record provides a more granular description to share only '
                                'with parties or entities that have the permission to access the event data. '
                                'Including the regions, the time interval for all the events and the specific '
                                'data sets used in the combining and association process.',
                                target='research-button', placement='bottom'),
                    dbc.Button('Publication', id='publication-button', active=False, disabled=True,
                               color='success', outline=True, size='me-1',
                               style={'marginRight': '2rem'}),
                    dbc.Tooltip(
                        'The publication metadata record does not include identifying information about the individuals. '
                        'That is why, the locations are generalized to the country, the time interval for the '
                        'whole period where environmental data is available and the data sets to the data source.',
                        target='publication-button', placement='bottom'),
                ], style={'marginBottom': '0.5rem'}),
                dbc.Alert(
                    dcc.Markdown(
                        'You require **explicit permission** from the data controller and/or Data Protection Officer assigned to '
                        'the event data to access, use and process the data **if the event data is considered personal data**.'),
                    id='research-alert',
                    dismissable=True,
                    is_open=False,
                    color='warning',
                    style={'verticalAlign': 'middle',
                           'fontWeight': 'normal',
                           }
                ),
                dbc.Alert(
                    dcc.Markdown(
                        '''
                        You require **approval** from the data controller and/or Data Protection Officer assigned to 
                        the event data to deposit the data in an open data repository
                        **if the event data is considered personal data**.
                        '''
                    ),
                    id='publication-alert',
                    dismissable=True,
                    is_open=False,
                    color='warning',
                    style={'verticalAlign': 'middle',
                           'fontWeight': 'normal',
                           }
                ),
                html.Div([
                    html.Label('Metadata input:', style={'fontWeight': 'bold', 'marginRight': '2rem'}),
                    dbc.Button('Recommended', id='recommended-metadata-button', active=False, disabled=True,
                               color='success', outline=True, size='me-1',
                               style={'marginRight': '2rem'}),
                    dbc.Tooltip('The recommended metadata includes specific details about the events (e.g. '
                                'event refer to Disease A), publisher, data set publisher and license; and the '
                                'data protection and privacy information (e.g. data controller and processing purpose)',
                                target='recommended-metadata-button', placement='bottom'),
                    dbc.Button('Minimum', id='minimum-metadata-button', active=False, disabled=True,
                               color='success', outline=True, size='me-1',
                               style={'marginRight': '2rem'}),
                    dbc.Tooltip(
                        'The minimum metadata includes only specific details about the events (e.g. '
                        'event refer to Disease A), publisher, data set publisher and license.',
                        target='minimum-metadata-button', placement='bottom'),
                ], style={'marginBottom': '0.5rem'}),

                html.Div(id='metadata-upload'),
                html.Hr(),
                html.Div([
                    dcc.Markdown(
                        '''    
                        The linkage between events and environmental data sets requires to set the following options.
                        '''
                    ),
                    html.Div([
                        html.Label('Spatial Linkage:', style={'fontWeight': 'bold', 'marginRight': '2rem'}),
                        dcc.RadioItems(
                            id='spatial-linkage-button',
                            labelStyle={'display': 'inline-block', 'margin-right': '1em'},
                            options=[
                                {'label': ' Closest data point ', 'value': 'closest'},
                                {'label': ' Within a region ', 'value': 'region'},
                                {'label': ' Distance (circle) ', 'value': 'distance'},
                            ], style={'fontWeight': 'normal'}
                        ),
                        # dbc.FormText(''),
                    ], style={'marginBottom': '0.5rem'}, className='d-flex justify-content-center'
                    ),
                    html.Div([
                        html.Div([
                            html.Label('Distance in km:',
                                       style={'fontWeight': 'bold', 'marginRight': '2rem', 'display': 'none'},
                                       id='spatial-distance-label'),
                            dbc.Input(type='number', min=0, max=100, step=10, value=10,
                                      id='spatial-distance-button',
                                      style={
                                          'fontWeight': 'normal',
                                          'width': '10%',
                                          'marginRight': '3rem',
                                          'display': 'none'
                                      },
                                      ),
                        ], id='spatial-distance-display', ),
                        html.Div([
                            html.Label('Region levels:',
                                       style={'fontWeight': 'bold', 'marginRight': '2rem', 'display': 'none'},
                                       id='spatial-nuts-label'),
                            dbc.Select(
                                id='spatial-nuts-button',
                                options=[
                                    {'label': 'NUTS-0', 'value': 'NUTS-0'},
                                    {'label': 'NUTS-1', 'value': 'NUTS-1'},
                                    {'label': 'NUTS-2', 'value': 'NUTS-2'},
                                    {'label': 'NUTS-3', 'value': 'NUTS-3'},
                                ],
                                value='NUTS-3',
                                style={
                                    'fontWeight': 'normal',
                                    'width': '20%',
                                    'display': 'none'
                                }
                            ),
                            dbc.FormText(
                                html.A(
                                    'The regions that correspond to each NUTS level can be explored by clicking the countries in here',
                                    href='https://ec.europa.eu/eurostat/web/nuts/nuts-maps',
                                    target='_blank'),
                                style={'display': 'none'}, id='spatial-nuts-info')
                        ], id='spatial-nuts-display', )
                        # dbc.FormText(''),
                    ], style={'marginBottom': '0.5rem'}, className='d-flex justify-content-center'
                    ),
                    html.Div([
                        html.Label('Temporal Unit:', style={'fontWeight': 'bold', 'marginRight': '2rem'}),
                        dcc.RadioItems(
                            id='temporal-unit-button',
                            labelStyle={'display': 'inline-block', 'margin-right': '1em'},
                            options=[
                                {'label': ' Hour ', 'value': 'hour'},
                                {'label': ' Day ', 'value': 'day'},
                                {'label': ' Month ', 'value': 'month'},
                                {'label': ' Year ', 'value': 'year'}
                            ], style={'fontWeight': 'normal'}
                        ),
                    ], style={'marginBottom': '0.5rem'}, className='d-flex justify-content-center'
                    ),
                    html.Div([
                        html.Label('Aggregation Method:', style={'fontWeight': 'bold', 'marginRight': '2rem'}),
                        dcc.RadioItems(
                            id='agg-method-button',
                            labelStyle={'display': 'inline-block', 'marginRight': '1rem'},
                            options=[
                                {'label': ' Mean', 'value': 'AVG'},
                                {'label': ' Sum', 'value': 'SUM'},
                                {'label': ' Min', 'value': 'MIN'},
                                {'label': ' Max', 'value': 'MAX'},
                            ], style={'fontWeight': 'normal'}
                        ),
                    ], style={'marginBottom': '1rem'}, className='d-flex justify-content-center'
                    ),
                    html.Hr(),
                    dcc.Markdown(
                        '''
                        The resulting event-environmental data can be exported in two different data formats.
                        '''
                    ),
                    html.Div([
                        html.Label('Data File Format:', style={'fontWeight': 'bold', 'marginRight': '2rem'}),
                        dcc.RadioItems(
                            id='data-file-format-button',
                            labelStyle={'display': 'inline-block', 'marginRight': '1rem'},
                            options=[
                                {'label': ' Data Table', 'value': 'datatable'},
                                {'label': ' Graph', 'value': 'graph'},
                                {'label': ' Both', 'value': 'both'},
                            ], style={'fontWeight': 'normal'}
                        ),
                    ], style={'marginBottom': '0.5em'}, className='d-flex justify-content-center'
                    ),
                ]),

                html.Hr(),
                dbc.Spinner([
                    dbc.Button('Convert', id='convert-button', color='primary', outline=True, size='me-1',
                               disabled='True'),
                ]),
                dbc.Alert('The event-environmental (meta)data was successfully converted! Go to Step 3: Output.',
                          is_open=False, color='success', id='convert-data-alert', dismissable=False,
                          style={'marginTop': '1rem'})
            ]
        ),
    ], style={'width': '70%', 'textAlign': 'center', 'marginBottom': '2rem', 'borderWidth': '0.2rem', },
    className='d-grid gap-2 col-6 mx-auto'
)

# Read recommended event metadata
df_event_metadata = pd.read_csv('event_metadata.csv')

# Read minimum event metadata
df_event_metadata_min = pd.read_csv('minimum_metadata.csv')

# Step 3 card where the user exports the event-environmental linked data
step3_card = dbc.Card(
    [
        # dbc.CardHeader('Input'),
        dbc.CardBody(
            [
                dbc.Row([
                    html.H5('Step 3: Output', className='card-title', style={'textAlign': 'center'}),
                    dbc.Col([
                        html.Div(id='convert-output'),
                        dcc.Markdown(
                            '''
                            The resulting event-environmental linked data is compressed in a zip file that contains:
                            * The data for analysis as a data table and/or graph
                            * The metadata for research or publication 
                            * The interactive report to explore the (meta)data                 
                            '''
                        ),
                    ], width=9),
                    dbc.Col([
                        dbc.Row([
                            dbc.Spinner([
                                dbc.Button('Explore Report', id='explore-report-button', active=False,
                                           color='primary', outline=True, size='me-1', disabled=True,
                                           style={'marginBottom': '2rem'}
                                           ),
                            ]),
                        ]),
                        dbc.Row([
                            dbc.Spinner([
                                dbc.Button('Export Output', id='export-output-button', active=False,
                                           color='primary', outline=True, size='me-1', disabled=True,
                                           ),
                            ]),
                        ])

                        # dbc.NavItem(dbc.NavLink('Export Output', href="#", active=True)),
                        # dbc.NavItem(dbc.NavLink('Explore Report', href="#", active=True)),
                    ], width=3, className='d-flex flex-wrap align-content-center')
                ]),
                html.Div([
                    dcc.Store(id='store-zip'),
                    dcc.Download(id='download-zip')
                ])
            ]
        ),
    ], style={'width': '70%', 'marginBottom': '2rem', 'borderWidth': '0.2rem', },
    className='d-grid gap-2 col-6 mx-auto'
)

layoutRows = dbc.Col(
    [
        dbc.Row(titleAndDataLink),
        dbc.Row(step1_card),
        dbc.Row(step2_card),
        dbc.Row(step3_card),
        dbc.Row(contact_card),
    ], style={'background-color': '#f2f2f2'}  # '#e5f5f5'
)

# App Layout
appBody = html.Div([layoutRows])

app.layout = html.Div([topNavbarHelical, appBody])


def valid_sparql_datetime(date_text):
    try:
        datetime.datetime.strptime(date_text, '%Y-%m-%dT%H:%M:%S%z')
    except ValueError:
        raise ValueError("Incorrect data format, should be YYYY-MM-DDThh:mm:ssTZ")


@app.callback(
    [
        Output('data-upload-user-alert', 'children'),
        Output('data-upload-user-alert', 'color'),
        Output('data-upload-user-alert', 'is_open'),
        Output('upload-data-alert', 'is_open'),
        Output('upload-file-button', 'outline'),
    ],
    [
        Input('upload-file-button', 'n_clicks'),
        Input('upload-data', 'contents'),
    ],
    [
        State('upload-data', 'filename'),
    ],

)
def data_user_input(uploadFileClick, list_of_contents, list_of_names):
    # use the dash.callback_context property to trigger the callback only when
    # the number of clicks has changed rather than after the first click
    changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]

    # Prevent update if the user has not selected any function
    if not list_of_contents and not uploadFileClick:
        raise PreventUpdate
    elif 'upload-file-button' in changed_id:
        return ['', 'warning', False, True, False]
    elif list_of_contents and 'upload-data' in changed_id:
        content_type, content_string = list_of_contents.split(',')
        decoded = base64.b64decode(content_string)
        if 'csv' in list_of_names:
            # Assume that the user uploaded a CSV file
            df_event_up = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
        elif 'xls' in list_of_names:
            # Assume that the user uploaded an excel file
            df_event_up = pd.read_excel(io.BytesIO(decoded))
        else:
            return [list_of_names + ' needs to be CSV or XLS file.', 'danger', True]

        if df_event_up.columns.all() != df_event_data.columns.all():
            return [
                'The column names in ' + list_of_names + ' need to be as in the example data table below.',
                'danger', True, False, True]

        elif not (df_event_up.country == 'IE').all():
            return ['The values in column "country" need to be supported countries (only "IE" supported).',
                    'danger', True, False, True]
        else:
            try:
                valid_datetime = [datetime.datetime.strptime(i[:-1], '%Y-%m-%dT%H:%M:%S') for i in
                                  df_event_up.evDateT]
            except ValueError:
                return ['The values in column "evDateT" need to be valid datetimes.',
                        'danger', True, False, True]

            if not pd.to_numeric(df_event_up['wLen'], errors='coerce').notnull().all():
                return ['The values in column "wLen" need to be integers.',
                        'danger', True, False, True]
            elif not pd.to_numeric(df_event_up['wLag'], errors='coerce').notnull().all():
                return ['The values in column "wLag" need to be integers.',
                        'danger', True, False, True]
            else:
                event_up_regions = [r.split() for r in df_event_up.region]
                event_up_regions_f = [item for sublist in event_up_regions for item in sublist]

                if not set(event_up_regions_f) <= set(evLocList):
                    return [
                        'The values in column "region" need to be supported regions (only "IE" counties supported).',
                        'danger', True, False, True]
                else:
                    return [list_of_names + ' file was successfully uploaded! Go to Step 2: Options.', 'success', True,
                            False, True]

    else:
        raise PreventUpdate


@app.callback(
    Output('table-events-example', 'data'),
    Input('editing-rows-button', 'n_clicks'),
    State('table-events-example', 'data'),
    State('table-events-example', 'columns'))
def add_row(n_clicks, rows, columns):
    if n_clicks > 0:
        rows.append({c['id']: '' for c in columns})
    return rows


@app.callback(
    [
        Output('research-button', 'disabled'),
        Output('publication-button', 'disabled'),
        Output('recommended-metadata-button', 'disabled'),
        Output('minimum-metadata-button', 'disabled'),
    ],
    [
        Input('data-upload-user-alert', 'color'),
        Input('upload-data-alert', 'is_open'),
    ],
)
def activate_options(selectFileAlert, uploadFileAlert):
    # Prevent update if the user has not selected any function
    if selectFileAlert == 'success':
        return [False, False, False, False]
    elif uploadFileAlert:
        return [False, False, False, False]
    else:
        return [True, True, True, True]


@app.callback(
    [
        Output('research-button', 'outline'),
        Output('publication-button', 'outline'),
        Output('research-alert', 'is_open'),
        Output('publication-alert', 'is_open'),
    ],
    [
        Input('research-button', 'n_clicks'),
        Input('publication-button', 'n_clicks'),
    ]
)
def purpose_option(researchClick, publicationClick):
    # use the dash.callback_context property to trigger the callback only when
    # the number of clicks has changed rather than after the first click
    changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]

    # Prevent update if the user has not selected any function
    if not researchClick and not publicationClick:
        raise PreventUpdate
    else:
        if 'research-button' in changed_id:
            return [False, True, True, False]
        if 'publication-button' in changed_id:
            return [True, False, True, True]


@app.callback(
    [
        Output('recommended-metadata-button', 'outline'),
        Output('minimum-metadata-button', 'outline'),
        Output('metadata-upload', 'children'),
    ],
    [
        Input('recommended-metadata-button', 'n_clicks'),
        Input('minimum-metadata-button', 'n_clicks'),
    ]
)
def metadata_record_option(recommendedClick, minimumClick):
    # use the dash.callback_context property to trigger the callback only when
    # the number of clicks has changed rather than after the first click
    changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]

    # Prevent update if the user has not selected any function
    if not recommendedClick and not minimumClick:
        raise PreventUpdate
    else:
        if 'recommended-metadata-button' in changed_id:
            metadata_upload = html.Div([
                html.Div([
                    html.P('Import a data table following the example below'),
                    dcc.Upload(
                        id={'type': 'upload-metadata', 'index': 'rec_' + str(recommendedClick)},
                        children=html.Div([
                            'Drag and Drop or ',
                            html.A('Select File')
                        ]),
                        style={
                            'width': '100%',
                            'height': '60px',
                            'lineHeight': '60px',
                            'borderWidth': '1px',
                            'borderStyle': 'dashed',
                            'borderRadius': '5px',
                            'textAlign': 'center',
                        },
                        # Allow multiple files to be uploaded
                        multiple=False,
                    ),
                ], style={'marginBottom': '1rem'},
                    className='d-grid gap-2 col-6 mx-auto'),
                dbc.Alert(is_open=False,
                          id={'type': 'metadata-upload-user-alert', 'index': 'rec_' + str(recommendedClick)}),
                html.P('or', style={'marginBottom': '1rem'}),
                html.P('Edit the data table following the example inputs below'),
                html.Div([
                    dash_table.DataTable(
                        id={'type': 'table-events-metadata', 'index': 'rec_' + str(recommendedClick)},
                        data=df_event_metadata.to_dict('records'),
                        columns=[{'id': cn, 'name': cn} for cn in df_event_metadata.columns],
                        editable=True,
                        export_format='csv',
                        # style_table={'overflowX': 'auto'},
                        export_headers='display',
                        sort_action='native',
                        page_size=5,
                        style_header={
                            'backgroundColor': '#66b2b2',  # '#458B74',
                            'fontWeight': 'bold',
                            'color': 'white',
                            'textAlign': 'center'
                        },
                        style_data={
                            'whiteSpace': 'normal',
                            'height': 'auto',
                        },
                        # css=[{'selector': 'table', 'rule': 'table-layout: fixed'}],
                        style_cell={
                            'textAlign': 'center',
                            # 'overflow': 'hidden',
                            # 'textOverflow': 'ellipsis',
                            # 'width': '{}%'.format(len(df_event_metadata.columns)),
                        },
                    )
                ], style={'width': '90%', 'marginBottom': '1rem'}, className='d-grid gap-2 col-6 mx-auto'
                ),
                # html.Hr(style={'width': '10%'}),
                dbc.Button('Upload Metadata', color='primary',
                           id={'type': 'upload-metadata-button', 'index': 'rec_' + str(recommendedClick)},
                           outline=True, className='d-grid gap-2 col-3 mx-auto'),
                dbc.Alert('The metadata table was successfully uploaded! Proceed to select the options below.',
                          color='success', is_open=False,
                          id={'type': 'upload-metadata-alert', 'index': 'rec_' + str(recommendedClick)},
                          dismissable=False, style={'marginBottom': '-6rem'})
            ], style={'width': '90%', 'textAlign': 'center', 'marginBottom': '-2rem', 'borderWidth': '0.2rem', },
                className='d-grid gap-2 col-6 mx-auto'
            )
            return [False, True, metadata_upload]

        if 'minimum-metadata-button' in changed_id:
            metadata_upload = html.Div([
                html.Div([
                    html.P('Import a data table following the example below'),
                    dcc.Upload(
                        id={'type': 'upload-metadata', 'index': 'min_' + str(minimumClick)},
                        children=html.Div([
                            'Drag and Drop or ',
                            html.A('Select File')
                        ]),
                        style={
                            'width': '100%',
                            'height': '60px',
                            'lineHeight': '60px',
                            'borderWidth': '1px',
                            'borderStyle': 'dashed',
                            'borderRadius': '5px',
                            'textAlign': 'center',
                        },
                        # Allow multiple files to be uploaded
                        multiple=False,
                    ),
                ], style={'marginBottom': '1em'},
                    className='d-grid gap-2 col-6 mx-auto'),
                dbc.Alert(is_open=False,
                          id={'type': 'metadata-upload-user-alert', 'index': 'min_' + str(minimumClick)}),
                html.P('or', style={'marginBottom': '1em'}),
                html.P('Edit the data table following the example inputs below'),
                html.Div([
                    dash_table.DataTable(
                        id={'type': 'table-events-metadata', 'index': 'min_' + str(minimumClick)},
                        data=df_event_metadata_min.to_dict('records'),
                        columns=[{'id': cn, 'name': cn} for cn in df_event_metadata_min.columns],
                        editable=True,
                        export_format='csv',
                        # style_table={'overflowX': 'auto'},
                        export_headers='display',
                        style_header={
                            'backgroundColor': '#66b2b2',  # '#458B74',
                            'fontWeight': 'bold',
                            'color': 'white',
                            'textAlign': 'center'
                        },
                        style_cell={
                            'textAlign': 'center',
                        },
                    )
                ], style={'width': '90%', 'marginBottom': '1rem'}, className='d-grid gap-2 col-6 mx-auto'
                ),
                dbc.Button('Upload Metadata', color='primary',
                           id={'type': 'upload-metadata-button', 'index': 'min_' + str(minimumClick)},
                           outline=True,
                           className='d-grid gap-2 col-3 mx-auto'
                           ),
                dbc.Alert('The metadata table was successfully uploaded! Proceed to select the options below.',
                          color='success', is_open=False,
                          id={'type': 'upload-metadata-alert', 'index': 'min_' + str(minimumClick)}, dismissable=False)
            ], style={'width': '90%', 'textAlign': 'center', 'marginBottom': '2rem', 'borderWidth': '0.2rem', },
                className='d-grid gap-2 col-6 mx-auto'
            )
            return [True, False, metadata_upload]


@app.callback(
    [
        Output({'type': 'metadata-upload-user-alert', 'index': MATCH}, 'children'),
        Output({'type': 'metadata-upload-user-alert', 'index': MATCH}, 'color'),
        Output({'type': 'metadata-upload-user-alert', 'index': MATCH}, 'is_open'),
        Output({'type': 'upload-metadata-alert', 'index': MATCH}, 'is_open'),
        Output({'type': 'upload-metadata-button', 'index': MATCH}, 'outline'),
    ],
    [
        Input('recommended-metadata-button', 'outline'),
        Input('minimum-metadata-button', 'outline'),
        Input({'type': 'upload-metadata-button', 'index': MATCH}, 'n_clicks'),
        Input({'type': 'upload-metadata', 'index': MATCH}, 'contents'),
    ],
    [
        State({'type': 'upload-metadata', 'index': MATCH}, 'filename'),
        State({'type': 'upload-metadata', 'index': MATCH}, 'last_modified')
    ],

)
def metadata_user_input(recOutline, minOutline, uploadFileClick, list_of_contents, list_of_names, list_of_dates):
    # use the dash.callback_context property to trigger the callback only when
    # the number of clicks has changed rather than after the first click
    changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]

    # Prevent update if the user has not selected any function
    if (not recOutline and not minOutline) or (not list_of_contents and not uploadFileClick):
        raise PreventUpdate
    elif 'upload-metadata-button' in changed_id:
        return ['', 'warning', False, True, False]
    elif list_of_contents and 'upload-metadata' in changed_id:
        content_type, content_string = list_of_contents.split(',')
        decoded = base64.b64decode(content_string)
        if 'csv' in list_of_names:
            # Assume that the user uploaded a CSV file
            df_metadata_up = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
        elif 'xls' in list_of_names:
            # Assume that the user uploaded an excel file
            df_metadata_up = pd.read_excel(io.BytesIO(decoded))
        else:
            return [list_of_names + ' needs to be CSV or XLS file.', 'danger', True]
        if not recOutline:
            if set(df_metadata_up.columns.values) != set(df_event_metadata.columns.values):
                return [
                    'The column names in ' + list_of_names + ' need to be as in the example metadata table below.',
                    'danger', True, False, True]
            elif set(df_metadata_up['key'].values) != set(df_event_metadata['key'].values):
                return ['The values in column "key" need to be as in the example metadata table below.',
                        'danger', True, False, True]
            else:
                return [list_of_names + ' file was successfully uploaded! Proceed to select the options below.',
                        'success', True, False, True]
        elif not minOutline:
            if set(df_metadata_up.columns.values) != set(df_event_metadata_min.columns.values):
                return [
                    'The column names in ' + list_of_names + ' need to be as in the example metadata table below.',
                    'danger', True, False, True]
            if set(df_metadata_up['key'].values) != set(df_event_metadata_min['key'].values):
                return ['The values in column "key" need to be as in the example metadata table below.',
                        'danger', True, False, True]
            else:
                return [list_of_names + ' file was successfully uploaded! Proceed to select the options below.',
                        'success', True, False, True]
    else:
        raise PreventUpdate


@app.callback(
    [
        Output('convert-button', 'disabled'),
    ],
    [
        Input('data-upload-user-alert', 'color'),
        Input('upload-data-alert', 'is_open'),
        Input('research-button', 'outline'),
        Input('publication-button', 'outline'),
        Input('recommended-metadata-button', 'outline'),
        Input('minimum-metadata-button', 'outline'),
        Input({'type': 'metadata-upload-user-alert', 'index': ALL}, 'color'),
        Input({'type': 'upload-metadata-alert', 'index': ALL}, 'is_open'),
        Input('temporal-unit-button', 'value'),
        Input('agg-method-button', 'value'),
        Input('data-file-format-button', 'value'),
    ]
)
def convert_ready(uploadData1, uploadData2, researchOutline, publicationOutline, recommendedOutline, minimumOutline,
                  uploadMetadata1, uploadMetadata2,
                  tempUnitValue, aggMethodValue, dataFormatValue):
    uploadMetadata1_f = ''.join([str(elem) for elem in uploadMetadata1 if elem is not None])

    if (uploadData1 == 'success' or uploadData2) and (not researchOutline or not publicationOutline) and \
            (not recommendedOutline or not minimumOutline) and \
            (uploadMetadata1_f == 'success' or all(uploadMetadata2)) and \
            tempUnitValue and aggMethodValue and dataFormatValue:
        return [False]
    else:
        return [True]


@app.callback(
    [
        Output('spatial-distance-button', 'style'),
        Output('spatial-distance-label', 'style'),
        Output('spatial-nuts-button', 'style'),
        Output('spatial-nuts-label', 'style'),
        Output('spatial-nuts-info', 'style'),
    ],
    [
        Input('spatial-linkage-button', 'value'),
    ]
)
def display_linkage(sp_val):
    if sp_val == 'closest':
        return [{'display': 'none'}, {'display': 'none'}, {'display': 'none'}, {'display': 'none'},
                {'display': 'none'}, ]
    # className='d-flex justify-content-center'
    elif sp_val == 'region':
        return [{'display': 'none'}, {'display': 'none'},
                {'display': 'inline-block', 'width': '20%', 'fontWeight': 'normal', },
                {'fontWeight': 'bold', 'marginRight': '2rem', 'display': 'inline-block'},
                {'display': 'block'}, ]
    elif sp_val == 'distance':
        return [{'display': 'inline-block', 'width': '20%', 'fontWeight': 'normal', },
                {'fontWeight': 'bold', 'marginRight': '2rem', 'display': 'inline-block'},
                {'display': 'none'}, {'display': 'none'}, {'display': 'none'}, ]
    else:
        return [{'display': 'none'}, {'display': 'none'}, {'display': 'none'}, {'display': 'none'},
                {'display': 'none'}, ]


@app.callback(
    [
        Output('store-zip', 'data'),
        Output('convert-button', 'href'),  #
        Output('convert-data-alert', 'is_open'),
        Output('export-output-button', 'disabled'),
        Output('explore-report-button', 'disabled'),
    ],
    [
        Input('convert-button', 'n_clicks'),
    ],
    [
        # Data
        State('data-upload-user-alert', 'color'),
        State('upload-data-alert', 'is_open'),
        State('upload-data', 'contents'),
        State('upload-data', 'filename'),
        State('table-events-example', 'data'),
        # Options
        State('research-button', 'outline'),
        State('publication-button', 'outline'),
        State('recommended-metadata-button', 'outline'),
        State('minimum-metadata-button', 'outline'),
        State('temporal-unit-button', 'value'),
        State('agg-method-button', 'value'),
        State('data-file-format-button', 'value'),
        # Metadata
        State({'type': 'metadata-upload-user-alert', 'index': ALL}, 'color'),
        State({'type': 'upload-metadata-alert', 'index': ALL}, 'is_open'),
        State({'type': 'upload-metadata', 'index': ALL}, 'contents'),
        State({'type': 'upload-metadata', 'index': ALL}, 'filename'),
        State({'type': 'table-events-metadata', 'index': ALL}, 'data'),
        # Store filename for export
        State('store-zip', 'data')
    ]
)
def convert_ready(
        convertClick,
        uploadDataUserColor, uploadDataTableColor, uploadDataUserContent, uploadDataUserFilename, uploadDataTableData,
        researchOutline, publicationOutline, recommendedOutline, minimumOutline,
        tempUnitValue, aggMethodValue, dataFormatValue,
        uploadMetadataUserColor, uploadMetadataTableColor,
        uploadMetadataUserContent, uploadMetadataUserFilename, uploadMetadataTableData,
        storeFilename):
    # use the dash.callback_context property to trigger the callback only when
    # the number of clicks has changed rather than after the first click
    changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]

    # Prevent update if the user has not clicked the 'Convert' button
    if not convertClick:
        raise PreventUpdate

    # ------------------------------------------------------------------------------------------------------------------
    # Data
    # ------------------------------------------------------------------------------------------------------------------
    # Read user data input
    if uploadDataUserColor == 'success':
        data_content_type, data_content_string = uploadDataUserContent.split(',')
        data_decoded = base64.b64decode(data_content_string)
        if 'csv' in uploadDataUserFilename:
            # Assume that the user uploaded a CSV file
            df_data_up = pd.read_csv(io.StringIO(data_decoded.decode('utf-8')),
                                     converters={'region': lambda x: x.split(' ')})
        elif 'xls' in uploadDataUserFilename:
            # Assume that the user uploaded an excel file
            df_metadata_up = pd.read_excel(io.BytesIO(data_decoded),
                                           converters={'region': lambda x: x.split(' ')})
    # Read example data table input
    elif uploadDataTableColor:
        df_data_up = pd.DataFrame(uploadDataTableData)
        df_data_up['region'] = [r.split(' ') for r in df_data_up['region']]

    # print(df_data_up)

    # ------------------------------------------------------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------------------------------------------------------

    # Read user data input
    if uploadMetadataUserColor == 'success':
        metadata_content_type, metadata_content_string = uploadMetadataUserContent.split(',')
        metadata_decoded = base64.b64decode(metadata_content_string)
        if 'csv' in uploadMetadataUserFilename:
            # Assume that the user uploaded a CSV file
            df_metadata_up = pd.read_csv(io.StringIO(metadata_decoded.decode('utf-8')))
        elif 'xls' in uploadMetadataUserFilename:
            # Assume that the user uploaded an excel file
            df_metadata_up = pd.read_excel(io.BytesIO(metadata_decoded))
    # Read example data table input
    elif uploadMetadataTableColor:
        df_metadata_up = pd.DataFrame(uploadMetadataTableData[0])

    # print(df_metadata_up)

    # ------------------------------------------------------------------------------------------------------------------
    # Query to associate environmental data with events
    # ------------------------------------------------------------------------------------------------------------------
    # User options selected
    if not researchOutline:
        userPurpose = 'research'
    elif not publicationOutline:
        userPurpose = 'publication'

    if not recommendedOutline:
        userMetadataType = 'recommended'
    elif not minimumOutline:
        userMetadataType = 'minimum'

    # clean 'downloads' directory
    for root, dirs, files in os.walk('./downloads/'):
        for file in files:
            os.remove(os.path.join(root, file))

    event_environmental_pack = serdifAPI(
        eventDF=df_data_up,
        metadataDF=df_metadata_up,
        # Select temporal units for the datasets used with environmental
        # data from: 'hour', 'day', 'month' or 'year'
        timeUnit=tempUnitValue,
        # Select spatiotemporal aggregation method for the datasets
        # used with environmental data from: 'AVG', 'SUM', 'MIN' or 'MAX'
        spAgg=aggMethodValue,
        # Select the returning data format as 'datatable', 'graph' or 'both'
        dataFormat=dataFormatValue,
        purpose=userPurpose,
        metadataType=userMetadataType,
    )

    # Button title to block double clicks
    subTitleToolTip = 'Queries submitted: ' + str(convertClick)

    # Create the dictionary if there is not already one stored
    if not storeFilename:
        storeFilename = {}

    qNum = 'Q' + str(convertClick)
    storeFilename[qNum] = event_environmental_pack

    return [storeFilename, subTitleToolTip, True, False, False]


@app.callback(
    [Output('download-zip', 'data')],
    Input('export-output-button', 'n_clicks'),
    Input('convert-button', 'n_clicks'),
    State('store-zip', 'data')
)
def func(exportClick, convertClick, filename):
    if not exportClick or not filename:
        raise PreventUpdate
    elif len(filename) != convertClick:
        raise PreventUpdate
    else:
        exportFilePath = './downloads/' + filename['Q' + str(convertClick)]
        sendFileLink = dcc.send_file(exportFilePath)
        if os.path.isfile(exportFilePath):
            os.remove(exportFilePath)
    return [sendFileLink]


if __name__ == "__main__":
    app.run_server(debug=True, port=5555)
