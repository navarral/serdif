import dash
from dash import dcc, html, Input, Output, State, MATCH, ALL, dash_table
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import pandas as pd
import base64
import datetime
import io
import os
import requests
from app_linkage import load_events, uplift_metadata, serdif_geosparql, link_data
# from serdif import linkage
import time
import re

# Set the working directory relative to the script's location
# os.chdir(os.path.dirname(__file__))

app = dash.Dash(external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.BOOTSTRAP])

app.title = 'SERDIF-UI'
server = app.server

serdif_version = 'v20230413'

# Read example data
df_event_data = pd.read_csv('./data/event_data.csv')
# Read example metadata
df_event_meta = pd.read_csv('./data/event_metadata.csv')

topNavbarHelical = dbc.NavbarSimple(
    children=[
        dbc.NavItem([
            dbc.NavLink('HELICAL', href='https://helical-itn.eu/', target='_blank')
        ]),
        dbc.NavItem([
            dbc.NavLink('ADAPT', href='https://www.adaptcentre.ie/', target='_blank')
        ]),
        dbc.NavItem([
            dbc.NavLink('Trinity College Dublin', href='https://www.tcd.ie/', target='_blank')
        ]),
    ],
    brand='SERDIF: a data linkage framework (' + serdif_version + ')',
    brand_href='#',
    sticky='top',
    # style={'background-color': '#ffffff'}
)
# Diagram of the linkage steps:
# step 1: deposit data
step_deposit = dbc.Col(
    dbc.Card(
        dbc.CardBody(
            [
                html.H5(['1. Deposit',
                         html.I(className='bi bi-folder me-6',
                                style={'font-size': '2rem', 'margin-left': '1rem'})], className='card-title'),
                dcc.Markdown('Deposit your spatiotemporal data in the `raw/` folder', className='card-text'),
                html.Div([
                    dbc.Button('Check', id='deposit-button', color='primary', outline=True, n_clicks=0, ),
                    dbc.Popover(
                        'Test popover',
                        target='deposit-button',
                        body=True,
                        trigger='legacy',
                        placement='bottom',
                        id='deposit-popover',
                    ),
                ], style={'textAlign': 'center'}),
            ]
        ), id='deposit-card', color='primary', outline=True, style={'border-width': '2px'}),
    width=3)
# step 2: upload data
data_up_popover = [
    dbc.PopoverHeader('Upload your event data', style={'fontWeight': 'bold'}),
    dbc.PopoverBody([
        dcc.Markdown('Edit or import a data table following the example below',
                     style={'margin-bottom': '1rem'}),
        dcc.Markdown(
            'Edit the data table below by clicking the cell, entering the new value and then, clicking enter. '
            'Use the "Export" button to export the data table'),
        html.Div([
            dash_table.DataTable(
                id='table-events-example',
                data=df_event_data.to_dict('records'),
                # columns=[{'id': cn, 'name': cn} for cn in df_event_data.columns],
                columns=[
                    {'id': 'id', 'name': 'id', 'type': 'text'},
                    {'id': 'group', 'name': 'group', 'type': 'text'},
                    {'id': 'longitude', 'name': 'lon', 'type': 'numeric'},
                    {'id': 'latitude', 'name': 'lat', 'type': 'numeric', },
                    {'id': 'date', 'name': 'date', 'type': 'datetime'},
                    {'id': 'length', 'name': 'length', 'type': 'numeric'},
                    {'id': 'lag', 'name': 'lag', 'type': 'numeric'},
                    {'id': 'spatial', 'name': 'spatial'},

                ],
                # Formating validation

                tooltip_header={
                    'id': 'Event identifier (ID) [only letters, numbers and dashed without spaces]',
                    'group': 'Name to group the events [only letters, numbers and dashed without spaces]',
                    'longitude': "Longitude coordinate of the event's location [numeric]",
                    'latitude': "Latitude coordinate of the event's location [numeric]",
                    'date': 'Date of the event [YYYY-MM-DD]',
                    'length': 'Time interval to gather data [days]',
                    'lag': 'Time between the data and the event [days]',
                    'spatial': '''spatial linkage method between events and datasets. 
    The allowed values are standard NUTS regions [https://ec.europa.eu/eurostat/web/nuts/nuts-maps] "NUTS-0", "NUTS-1", "NUTS-2", "NUTS-3";
    or any positive number which refers to the radius from the event location in km.'''
                },
                # Style the tooltip headers and export button
                css=[{
                    'selector': '.dash-table-tooltip',
                    'rule': 'background-color: #e6e6e6',
                }],
                tooltip_delay=0,
                tooltip_duration=None,
                editable=True,
                row_deletable=True,
                export_format='csv',
                export_headers='display',
                sort_action='native',
                style_header={
                    'backgroundColor': '#5499c7',  # '#458B74',
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
        dbc.Button('Upload table above', color='primary', id='upload-file-button', n_clicks=0,
                   outline=True, className='d-grid gap-2 col-3 mx-auto',
                   style={'marginBottom': '2rem'}),

        html.P(
            html.Span('OR', style={'background': '#fff', 'padding': '0 10px', 'font-weight': 'bold'}),
            style={'width': '100%', 'text-align': 'center',
                   'border-bottom': '0.1em solid #ced4da', 'line-height': '0.1em',
                   'margin': '10px 0 20px',
                   }),

        dcc.Markdown('Import a .csv or .xls data table file with the exact format above',
                     style={'margintop': '2rem'}),
        html.Div([
            dcc.Upload(
                id='upload-data',
                children=html.Div([
                    'Drag and Drop or ',
                    html.A('Select File',
                           style={'color': '#0A84FF',
                                  'text-decoration': 'underline'})
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
        dbc.Alert('Data table was successfully uploaded! Go to Upload metadata.', color='success',
                  is_open=False, id='upload-data-alert', dismissable=False),
    ])
]

meta_up_popover = [
    dbc.PopoverHeader('Upload your event metadata', style={'fontWeight': 'bold'}),
    dbc.PopoverBody([
        dcc.Markdown('Edit or import a data table following the example below',
                     style={'margin-bottom': '1rem'}),
        dcc.Markdown(
            'Edit the data table below by clicking the cell, entering the new value and then, clicking enter. '
            'Use the "Export" button to export the data table'),
        html.Div([
            dash_table.DataTable(
                id='table-events-metadata',
                data=df_event_meta.to_dict('records'),
                columns=[
                    {'id': 'key', 'name': 'key', 'type': 'text'},
                    {'id': 'value', 'name': 'value', 'type': 'text'},
                ],
                # Formating validation

                tooltip_header={
                    'key': 'Minimum metadata fields for the linkage process',
                    'value': 'Value of the metadata field that needs to conform to the [format]',
                },
                tooltip_data=[
                    {
                        'key': 'Type of events or health context',
                        'value': '[letters, numbers and spaces]',
                    },
                    {
                        'key': 'Dataset publisher',
                        'value': '[valid URL]',
                    },
                    {
                        'key': 'Dataset license',
                        'value': '[valid URL]',
                    },
                    {
                        'key': 'Data controller entity assigned to the dataset',
                        'value': '[valid URL]',
                    },
                    {
                        'key': 'Data processor person or entity that conducted the linkage',
                        'value': '[valid URL]',
                    },
                ],
                # Style the tooltip headers and export button
                css=[{
                    'selector': '.dash-table-tooltip',
                    'rule': 'background-color: #e6e6e6',
                }],
                tooltip_delay=0,
                tooltip_duration=None,
                editable=True,
                row_deletable=False,
                export_format='csv',
                export_headers='display',
                sort_action='native',
                style_header={
                    'backgroundColor': '#5499c7',  # '#458B74',
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
        dbc.Button('Upload table above', color='primary', id='upload-meta-button', n_clicks=0,
                   outline=True, className='d-grid gap-2 col-3 mx-auto',
                   style={'marginBottom': '2rem'}),

        html.P(
            html.Span('OR', style={'background': '#fff', 'padding': '0 10px', 'font-weight': 'bold'}),
            style={'width': '100%', 'text-align': 'center',
                   'border-bottom': '0.1em solid #ced4da', 'line-height': '0.1em',
                   'margin': '10px 0 20px',
                   }),

        dcc.Markdown('Import a .csv or .xls data table file with the exact format above',
                     style={'margintop': '2rem'}),
        html.Div([
            dcc.Upload(
                id='upload-metadata',
                children=html.Div([
                    'Drag and Drop or ',
                    html.A('Select File',
                           style={'color': '#0A84FF',
                                  'text-decoration': 'underline'})
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

        dbc.Alert(is_open=False, id='metadata-upload-user-alert'),
        dbc.Alert('Metadata table successfully uploaded! Go to 3. Linkage.', color='success',
                  is_open=False, id='upload-metadata-alert', dismissable=False),
    ])
]

step_upload = dbc.Col(
    dbc.Card(
        dbc.CardBody(
            [
                html.H5(['2. Upload',
                         html.I(className='bi bi-box-arrow-up me-6',
                                style={'font-size': '2rem', 'margin-left': '1rem'})], className='card-title'),
                dcc.Markdown('Upload health event data and metadata for linkage', className='card-text'),
                html.Div([
                    dbc.Button('Data', id='data-up-button', color='primary', outline=True, n_clicks=0, disabled=True),
                    dbc.Popover(
                        data_up_popover,
                        target='data-up-button',
                        body=True,
                        trigger='legacy',
                        placement='bottom',
                        id='data-up-popover',
                        style={'max-width': '100%', 'textAlign': 'center', 'border': '2px solid #0d6efd'},
                    ),
                    dbc.Button('Metadata', id='meta-up-button', color='primary', outline=True, n_clicks=0,
                               disabled=True, style={'margin-left': '1rem'}),
                    dbc.Popover(
                        meta_up_popover,
                        target='meta-up-button',
                        body=True,
                        trigger='legacy',
                        placement='bottom',
                        id='meta-up-popover',
                        style={'max-width': '100%', 'textAlign': 'center', 'border': '2px solid #0d6efd'},
                    ),
                ], style={'textAlign': 'center', 'margin': 'auto'}),
            ]
        ), id='upload-card', color='light', outline=False, style={'border-width': '2px'}),
    width=3)
# step 3: linkage
linkage_popover = [
    dbc.PopoverHeader('Link your event data with spatiotemporal datasets', style={'text-align': 'center'}),
    dbc.PopoverBody([
        html.Div([
            html.P('The observations of your datasets can be integrated to a broader temporal unit or kept as input:'),
            html.Div([
                dcc.RadioItems(
                    id='temporal-unit-button',
                    labelStyle={'display': 'inline-block', 'margin-right': '1em'},
                    options=[
                        {'label': ' as input ', 'value': 'raw'},
                        {'label': ' Hour ', 'value': 'hour'},
                        {'label': ' Day ', 'value': 'day'},
                        {'label': ' Month ', 'value': 'month'},
                        {'label': ' Year ', 'value': 'year'}
                    ], style={'fontWeight': 'normal', 'width': '50%'}
                ),
            ], style={'marginBottom': '0.5rem'}, className='d-flex justify-content-center'
            ),
            html.P(
                'Given that more than one dataset can be linked to an event, select an aggregation method to integrate the '
                'observations for the same variable:'),
            html.Div([
                dcc.RadioItems(
                    id='agg-method-button',
                    labelStyle={'display': 'inline-block', 'marginRight': '1rem'},
                    options=[
                        {'label': ' Mean', 'value': 'avg'},
                        {'label': ' Sum', 'value': 'sum'},
                        {'label': ' Min', 'value': 'min'},
                        {'label': ' Max', 'value': 'max'},
                    ], style={'fontWeight': 'normal'}
                ),
            ], style={'marginBottom': '1rem', 'textAlign': 'center'}, #className='d-flex justify-content-center'
            ),
            # html.Hr(),

        ], ),
        html.Hr(),
        html.Div([
            html.P(
                'The linkage process can take from seconds to minutes depending on the number of events, size of '
                'the event area selected and length of the data interval.'),
            dbc.Spinner([
                dbc.Button('Link', id='start-linkage-button', color='primary', outline=True, size='me-1',
                           disabled='True', style={'textAlign': 'center'}),
            ]),
            dbc.Alert('The event-environmental (meta)data was successfully converted! Go to Step 3: Output.',
                      is_open=False, color='success', id='convert-data-alert', dismissable=False,
                      style={'marginTop': '1rem'})
        ], style={'textAlign': 'center'}),
    ], ),
]
step_linkage = dbc.Col(
    dbc.Card(
        dbc.CardBody(
            [
                html.H5(['3. Linkage',
                         html.I(className='bi bi-calendar4-range me-6',
                                style={'font-size': '2rem', 'margin-left': '1rem'})], className='card-title'),
                dcc.Markdown('Link the health event and spatiotemporal data'),
                html.Div([
                    dbc.Button('Linkage Options', id='linkage-button', color='primary', outline=True, n_clicks=0,
                               disabled=True),
                    dbc.Popover(
                        linkage_popover,
                        target='linkage-button',
                        body=True,
                        trigger='legacy',
                        placement='bottom',
                        id='linkage-popover',
                        style={'max-width': '80%', 'textAlign': 'justify', 'border': '2px solid #0d6efd'},
                    ),
                ], style={'textAlign': 'center'}),
            ]
        ), id='linkage-card', color='light', outline=False, style={'border-width': '2px'}),
    width=3)
# step 4: export
step_export = dbc.Col(
    dbc.Card(
        dbc.CardBody(
            [
                html.H5(['4. Export',
                         html.I(className='bi bi-box-seam me-6',
                                style={'font-size': '2rem', 'margin-left': '1rem'})], className='card-title'),
                dcc.Markdown('Export the event linked data as a zip file'),
                dbc.Spinner([
                    dbc.Button('Export', id='export-output-button', color='primary', outline=True, n_clicks=0,
                               disabled=True),
                ]),
                html.Div([
                    dcc.Store(id='store-metalayer'),
                    dcc.Store(id='store-zip'),
                    dcc.Download(id='download-zip')
                ])
            ]
        ), id='export-card', color='light', outline=False, style={'border-width': '2px'}),
    width=3)

# collate the steps
steps_diagram = dbc.Row(
    [
        step_deposit,
        step_upload,
        step_linkage,
        step_export,
    ], className='g-2'
)

# Title of the app
titleAndDataLink = html.Div([
    html.H3('Link health events with spatiotemporal data - Offline Version',
            style={'textAlign': 'center', 'marginTop': '1rem', 'color': '#005A9C'},
            className='card-title'),
    dbc.Card([
        dbc.CardBody([
            dbc.Row([steps_diagram], style={'marginTop': '-0.5rem'}),
        ], ),
    ], style={'border': '0px'},
        className='d-grid gap-2 col-10 mx-auto'),
])

# progress bar to track the linkage process
progress_bar = html.Div([
    dbc.Progress(id='linkage-progress', label='',
                 color='success', value=0, striped=True, animated=True,
                 style={'height': '3rem', 'font-size': '1rem', 'fontWeight': 'bold',
                        'backgroundColor': '#dadfe4', })
], className='d-grid gap-2 col-10 mx-auto', )

# personal data disclamer
personaldata_alert = html.Div([
    dbc.Alert(
        [
            dcc.Markdown(
                '**If the event data from your input is considered personal data**, '
                'you require **explicit permission** from the data controller and/or Data Protection Officer '
                'assigned to the data for *accessing*, *using* and *processing* the data. '
                '**Further approval** is needed if the intend is to *share* the data with others or *deposit* '
                'the data in an open data repository.'),
            dbc.Spinner([
                dbc.RadioButton(
                    label='I have obtained the required permission and approval to link the event data and my input datasets',
                    id='consent-input',
                    value=False,
                    style={'margin-bottom': '-0.5rem', },
                ),
            ])
        ],
        id='research-alert',
        dismissable=False,
        is_open=False,
        color='warning',
        style={'verticalAlign': 'middle',
               'fontWeight': 'normal',
               }
    ),
], className='d-grid gap-2 col-10 mx-auto')

# add an export summary alert
export_alert = html.Div([
    dbc.Alert(
        [
            dcc.Markdown(
                'The event linked data export contains the following files:'
                '\n\n - **Interactive report (.html)**: start with this document'
                '\n\n - **Data tables (.csv)**: raw and aggregated data tables for analysis'
                '\n\n - **Mapping files (.ttl and .properties)**: files to uplift the data tables to RDF graphs'
                '\n\n - **Graph data and metadata (.trig)**: interoperable data ready to be shared as FAIR '
                'data with the necessary information to be reused by other researchers in different contexts '
            ),
        ],
        id='export-alert',
        dismissable=False,
        is_open=False,
        color='success',
        style={'verticalAlign': 'middle',
               'fontWeight': 'normal',
               }
    ),
], className='d-grid gap-2 col-10 mx-auto')

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
                    className='col-md-5',
                ),
                dbc.Col(
                    dbc.CardBody(
                        [
                            dcc.Markdown('''
                                This research was conducted with the financial support of [HELICAL](https://helical-itn.eu/) as part of the European Union’s 
                                Horizon 2020 research and innovation programme under the Marie Sklodowska-Curie Grant Agreement 
                                No. 813545 at the [ADAPT Centre for Digital Content Technology](https://www.adaptcentre.ie/) (grant number 13/RC/2106 P2) at 
                                Trinity College Dublin. | **Contact:** albert.navarro@fht.org
                                ''', className='card-text', style={'font-size': '14px', 'text-align': 'justify'}
                                         )
                        ]
                    ),
                    className='col-md-7',
                ),
                dcc.Markdown('Thanks to [Fondazione Human Technopole](https://humantechnopole.it/) for hosting this web service.'),
            ],
            className="g-0 d-flex align-items-center",
        )
    ],
    className='d-grid gap-2 col-10 mx-auto',
    style={'borderWidth': '0px', },
)

layoutRows = dbc.Col(
    [
        dbc.Row(titleAndDataLink),
        dbc.Row(export_alert),
        dbc.Row(personaldata_alert),
        dbc.Row(progress_bar),
        dbc.Row(contact_card),
    ], style={'background-color': 'white'}  # '#f2f2f2' '#e5f5f5'
)

# App Layout
appBody = html.Div([layoutRows])

app.layout = html.Div([topNavbarHelical, appBody])


# Callbacks
# Main callback to navigate the user interface
@app.callback(
    [
        Output('deposit-popover', 'children'),
        Output('deposit-popover', 'style'),
        # Show progress with border color
        Output('deposit-card', 'outline'),
        Output('deposit-card', 'color'),
        Output('upload-card', 'outline'),
        Output('upload-card', 'color'),
        Output('linkage-card', 'outline'),
        Output('linkage-card', 'color'),
        Output('export-card', 'outline'),
        Output('export-card', 'color'),
        # Activate upload data button
        Output('data-up-button', 'disabled'),
        # Progress bar
        Output('linkage-progress', 'label'),
        Output('linkage-progress', 'value'),
        # Consent alert
        Output('research-alert', 'is_open'),
        # Activate linkage button
        Output('linkage-button', 'disabled'),
        # Plot for spatial linkage
        #Output('linkage-map', 'figure'),
        # Disable consent button after click
        Output('consent-input', 'disabled'),
        # store identifier and meta layer
        #Output('store-metalayer', 'data'),
    ],
    [
        Input('deposit-button', 'n_clicks'),
        Input('upload-data-alert', 'is_open'),
        Input('data-upload-user-alert', 'color'),
        Input('upload-metadata-alert', 'is_open'),
        Input('metadata-upload-user-alert', 'color'),
        Input('consent-input', 'value'),
        Input('start-linkage-button', 'disabled'),
        Input('export-output-button', 'disabled'),
    ],
    [
        State('table-events-example', 'data'),
        State('store-metalayer', 'data'),
        State('upload-data', 'contents'),
        State('upload-data', 'filename'),
    ],
)
def deposit_toggle_collapse(n_deposit,
    data_alert, data_color, metadata_alert, metadata_color,
    consent_val,
    linkage_disabled, export_disabled,
    event_data, meta_layer,
    list_of_contents, list_of_names
):  # , n_upload_data, n_upload_metadata, n_linkage):
    # use the dash.callback_context property to trigger the callback only when
    # the number of clicks has changed rather than after the first click
    # Prevent update if the user has not selected any function
    changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]
    print(changed_id)
    if not n_deposit:  # or not n_upload_data or not n_upload_metadata or not n_linkage:
        raise PreventUpdate

    # Create the dictionary if there is not already one stored
    if not meta_layer:
        meta_layer = {}

    # display the datasets in the raw/ folder in the deposit-popover when clicking the deposit button
    if 'deposit-button' in changed_id:
        # identify datasets available in raw data folder
        raw_datasets = os.listdir('raw')
        # Filter out files that start with a dot
        raw_datasets_nodot = [file for file in raw_datasets if not file.startswith('.')]
        # join raw_datasets names to a string
        raw_datasets_join = ', '.join(raw_datasets_nodot)
        print(raw_datasets_nodot)
        # check if the raw_dataset are NetCDF files, CSV files or GRIB files
        if any(not (rs.endswith('.nc') or rs.endswith('.csv') or rs.endswith('.grib')) for rs in raw_datasets_nodot):
            deposit_alert = [dbc.PopoverHeader('Warning!', style={'background-color': '#dc3545', 'color': '#fff'}),
                             dbc.PopoverBody(dcc.Markdown(
                                 'The raw data folder contains datasets that **are not NetCDF, CSV or GRIB files**: `' + raw_datasets_join +
                                 '`. Please deposit only the supported dataset types in the raw/ folder.',
                                 style={'marginBottom': '-1rem'}))]
            return [deposit_alert, {'border': '2px solid #dc3545'},
                    True, 'primary', False, 'light', False, 'light', False, 'light',
                    True, '', 0, False, True, True]
        else:
            deposit_alert = [
                dbc.PopoverHeader('Go to 2. Upload!', style={'background-color': '#198754', 'color': '#fff'}),
                dbc.PopoverBody(
                    dcc.Markdown(
                        'The raw data folder cointains the following datasets: `' + raw_datasets_join + '`.',
                        style={'marginBottom': '-1rem'}))]
            return [deposit_alert, {'border': '2px solid #198754'},
                    True, 'success', True, 'primary', False, 'light', False, 'light',
                    False, 'Upload event data...', 20,
                    False, True, True]

    if 'data-upload-user-alert' in changed_id and (data_alert or data_color == 'success'):
        if 'metadata-upload-user-alert' not in changed_id:
            if data_alert:
                data_up_mode = 'example'
            if data_color == 'success':
                data_up_mode = 'manual'
            print('data upload: ', data_up_mode)
            return [dash.no_update, {'border': '2px solid #198754'},
                    True, 'success', True, 'primary', False, 'light', False, 'light',
                    False, 'Upload event metadata...', 30,
                    False, True, True]

        elif 'metadata-upload-user-alert' in changed_id and (metadata_alert or metadata_color == 'success'):
            if metadata_alert:
                metadata_up_mode = 'example'
            if metadata_color == 'success':
                metadata_up_mode = 'manual'
            print('metadata upload: ', metadata_up_mode)
            return [dash.no_update, {'border': '2px solid #198754'},
                    True, 'success', True, 'success', True, 'primary', False, 'light',
                    False, 'Waiting for consent confirmation...', 40,
                    True, True, False]

    if 'consent-input' in changed_id and consent_val:
        # generate identifier to be used in the linkage process
        

        return [list(), {'border': '2px solid #198754'},
                True, 'success', True, 'success', True, 'primary', False, 'light',
                False, 'Waiting for linkage options...', 60,
                True, False, True]
    if 'start-linkage-button' in changed_id and not linkage_disabled:
        return [dash.no_update, {'border': '2px solid #198754'},
                True, 'success', True, 'success', True, 'primary', False, 'light',
                False, 'Linking the deposited datasets with your events...', 80,
                True, False, True]
    if 'export-output-button' in changed_id and not export_disabled:
        return [dash.no_update, {'border': '2px solid #198754'},
                True, 'success', True, 'success', True, 'success', True, 'primary',
                False, 'Linked data ready to export!', 100,
                True, False, True]

    raise PreventUpdate


# Callback to upload data
@app.callback(
    [
        Output('data-upload-user-alert', 'children'),
        Output('data-upload-user-alert', 'color'),
        Output('data-upload-user-alert', 'is_open'),
        Output('upload-data-alert', 'is_open'),
        Output('upload-file-button', 'outline'),
        Output('upload-file-button', 'disabled'),
    ],
    [
        Input('upload-file-button', 'n_clicks'),
        Input('upload-data', 'contents'),
        Input('table-events-example', 'data')
    ],
    [
        State('upload-data', 'filename'),
    ],

)
def data_user_input(uploadFileClick, list_of_contents, editTableValues, list_of_names):
    # use the dash.callback_context property to trigger the callback only when
    # the number of clicks has changed rather than after the first click
    changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]

    # Prevent update if the user has not selected any function
    if not list_of_contents and not uploadFileClick:
        raise PreventUpdate
    elif 'upload-file-button' in changed_id:
        # Check if there are empty strings '' in any of the input cells
        if '' in pd.DataFrame(editTableValues).to_numpy().flatten():
            return ['The data table has missing values', 'danger', True, False, True, False]
        else:
            return ['', 'warning', False, True, False, False]
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
            return [list_of_names + ' needs to be CSV or XLS file.', 'danger', True, False, True, False]

        # Format input events to an adequate format for serdif
        # check if there are any missing values like empty strings or nan in the input data
        if '' in df_event_up.to_numpy().flatten() or df_event_up.isnull().values.any():
            return [
                'There are some missing values in ' + list_of_names + '.',
                'danger', True, False, True, False]
        # check if the column names from df_event_up are the same as in df_event_data
        elif any(df_event_up.columns != df_event_data.columns):
            return [
                'The column names in ' + list_of_names + ' need to be as in the example data table below.',
                'danger', True, False, True, False]

        else:
            # replace any special characters from event and group columns with underscores
            df_event_up['event'] = df_event_up['event'].astype(str).replace('[^A-Za-z0-9\-_]+', '_', regex=True)
            df_event_up['group'] = df_event_up['group'].astype(str).replace('[^A-Za-z0-9\-_]+', '_', regex=True)
            # convert df_event_up column date to a '%Y-%m-%d' format
            df_event_up['date'] = pd.to_datetime(df_event_up['date']).dt.strftime('%Y-%m-%d')
            try:
                # convert df_event_up column date to a '%Y-%m-%d' format
                df_event_up['date'] = pd.to_datetime(df_event_up['date']).dt.strftime('%Y-%m-%d')
            except ValueError:
                return ['The values in column "date" need to be valid dates with the YYYY-MM-DD format.',
                        'danger', True, False, True, False]
            # check if the values in the columns length, lag, lon and lat are integers
            if not pd.to_numeric(df_event_up['length'], errors='coerce').notnull().all():
                return ['The values in column "length" need to be integers.',
                        'danger', True, False, True, False]
            elif not pd.to_numeric(df_event_up['lag'], errors='coerce').notnull().all():
                return ['The values in column "lag" need to be integers.',
                        'danger', True, False, True, False]
            if not pd.to_numeric(df_event_up['lon'], errors='coerce').notnull().all():
                return ['The values in column "longitude" need to be decimals.',
                        'danger', True, False, True, False]
            elif not pd.to_numeric(df_event_up['lat'], errors='coerce').notnull().all():
                return ['The values in column "latitude" need to be decimals.',
                        'danger', True, False, True, False]
            else:
                return [list_of_names + ' file was successfully uploaded! Go to 3. Linkage.', 'success',
                        True, False, True, True]

    else:
        raise PreventUpdate


# add rows to the event data table
@app.callback(
    Output('table-events-example', 'data'),
    Input('editing-rows-button', 'n_clicks'),
    State('table-events-example', 'data'),
    State('table-events-example', 'columns'))
def add_row(n_clicks, rows, columns):
    if n_clicks > 0:
        rows.append({c['id']: '' for c in columns})
    return rows


# Callback to upload metadata
@app.callback(
    [
        Output('metadata-upload-user-alert', 'children'),
        Output('metadata-upload-user-alert', 'color'),
        Output('metadata-upload-user-alert', 'is_open'),
        Output('upload-metadata-alert', 'is_open'),
        Output('upload-meta-button', 'outline'),
        Output('upload-meta-button', 'disabled'),
    ],
    [
        Input('upload-meta-button', 'n_clicks'),
        Input('upload-metadata', 'contents'),
        Input('table-events-metadata', 'data')
    ],
    [
        State('upload-metadata', 'filename'),
    ],

)
def metadata_user_input(uploadFileClick, list_of_contents, editTableValues, list_of_names):
    # use the dash.callback_context property to trigger the callback only when
    # the number of clicks has changed rather than after the first click
    changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]

    # Prevent update if the user has not selected any function
    if not list_of_contents and not uploadFileClick:
        raise PreventUpdate
    elif 'upload-meta-button' in changed_id:
        # Check if there are empty strings '' in any of the input cells
        if '' in pd.DataFrame(editTableValues).to_numpy().flatten():
            return ['The data table has missing values', 'danger', True, False, True, False]
        else:
            return ['', 'warning', False, True, False, False]
    elif list_of_contents and 'upload-metadata' in changed_id:
        content_type, content_string = list_of_contents.split(',')
        decoded = base64.b64decode(content_string)
        if 'csv' in list_of_names:
            # Assume that the user uploaded a CSV file
            df_event_up = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
        elif 'xls' in list_of_names:
            # Assume that the user uploaded an excel file
            df_event_up = pd.read_excel(io.BytesIO(decoded))
        else:
            return [list_of_names + ' needs to be CSV or XLS file.', 'danger', True, False, True, False]

        # Check if there are missing values like empty strings or nan
        if '' in df_event_up.to_numpy().flatten() or df_event_up.isnull().values.any():
            return [
                'There are some missing values in ' + list_of_names + '.',
                'danger', True, False, True, False]

        if any(df_event_up.columns != df_event_meta.columns):
            return [
                'The column names in ' + list_of_names + ' need to be as in the example data table below.',
                'danger', True, False, True, False]
        # check if the URLs are valid
        meta_url_list = df_event_up['value'].values.tolist()[1:]
        valid_url = []
        for url in meta_url_list:
            try:
                response = requests.get(url)
                valid_url.append(response.status_code == 200)
                print(url + ' is valid and exists on the Internet')
            except requests.ConnectionError as exception:
                print(url + ' does not exist on the Internet')
                return [url + ' does not exist on the Internet',
                        'danger', True, False, True, False]

        if len(valid_url) == len(meta_url_list):
            return [list_of_names + ' file was successfully uploaded! Go to 3. Linkage.', 'success',
                    True, False, True, True]
    else:
        raise PreventUpdate


# enable the metadata upload button if the user has uploaded the event data
@app.callback(
    Output('meta-up-button', 'disabled'),
    [Input('upload-data-alert', 'is_open'),
     Input('data-upload-user-alert', 'color'), ]
)
def enable_metadata_upload_button(data_open, data_color):
    if data_open or data_color == 'success':
        return False
    else:
        return True

@app.callback(
    [
        Output('start-linkage-button', 'disabled'),
    ],
    [
        Input('upload-data-alert', 'is_open'),
        Input('data-upload-user-alert', 'color'),
        Input('upload-metadata-alert', 'is_open'),
        Input('metadata-upload-user-alert', 'color'),
        Input('consent-input', 'value'),
        #Input('spatial-linkage-button', 'value'),
        Input('temporal-unit-button', 'value'),
        Input('agg-method-button', 'value'),
        # Input('event-date-button', 'value'),
    ]
)
def linkage_ready(uploadData, uploadDataColor, uploadMetadata, uploadMetadataColor,
                  consent_val,
                  #spLinkValue, 
                  tempUnitValue, aggMethodValue):
    if tempUnitValue and aggMethodValue: #spLinkValue and 
        if (uploadData or uploadDataColor == 'success') and (uploadMetadata or uploadMetadataColor == 'success') \
                and consent_val and tempUnitValue and aggMethodValue: #and spLinkValue 
            return [False]
        return [False]
    else:
        return [True]
    

@app.callback(
    [
        Output('store-zip', 'data'),
        Output('linkage-button', 'href'),
        Output('start-linkage-button', 'href'),
        Output('export-output-button', 'disabled'),
        Output('export-alert', 'is_open'),
    ],
    [
        Input('start-linkage-button', 'n_clicks'),
    ],
    [
        # Data
        State('data-upload-user-alert', 'color'),
        State('upload-data-alert', 'is_open'),
        State('upload-data', 'contents'),
        State('upload-data', 'filename'),
        State('table-events-example', 'data'),
        # Metadata
        State('metadata-upload-user-alert', 'color'),
        State('upload-metadata-alert', 'is_open'),
        State('upload-metadata', 'contents'),
        State('upload-metadata', 'filename'),
        State('table-events-metadata', 'data'),
        # Options
        #State('spatial-linkage-button', 'value'),
        #State('spatial-nuts-button', 'value'),
        #State('spatial-distance-button', 'value'),
        State('temporal-unit-button', 'value'),
        State('agg-method-button', 'value'),
        # Store filename for export
        State('store-zip', 'data'),
        #State('store-metalayer', 'data')
    ],
)
def start_linkage(n_linkage,
                  uploadDataUserColor, uploadDataTableColor, uploadDataUserContent, uploadDataUserFilename,
                  uploadDataTableData,
                  uploadMetadataUserColor, uploadMetadataTableColor, uploadMetadataUserContent,
                  uploadMetadataUserFilename, uploadMetadataTableData,
                  #spLinkValue, nutsValue, distanceValue, 
                  tempUnitValue, aggMethodValue,
                  storeFilename, 
                  #meta_layer
    ):
    # use the dash.callback_context property to trigger the callback only when
    # the number of clicks has changed rather than after the first click
    changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]

    # Prevent update if the user has not selected any function
    if not n_linkage:
        raise PreventUpdate

    if 'start-linkage-button' in changed_id:
        queryTimeStr = time.strftime('%Y%m%dT%H%M%S')

        # -----------------------------------------------------------------------------------------
        # Data
        # -----------------------------------------------------------------------------------------
        # Read user data input
        if uploadDataUserColor == 'success':
            data_content_type, data_content_string = uploadDataUserContent.split(',')
            data_decoded = base64.b64decode(data_content_string)
            if 'csv' in uploadDataUserFilename:
                # Assume that the user uploaded a CSV file
                df_data_up = pd.read_csv(io.StringIO(data_decoded.decode('utf-8')))
            elif 'xls' in uploadDataUserFilename:
                # Assume that the user uploaded an excel file
                df_data_up = pd.read_excel(io.BytesIO(data_decoded), )
        # Read example data table input
        elif uploadDataTableColor:
            df_data_up = pd.DataFrame(uploadDataTableData)

        # ---------------------------------------------------------------------------------------
        # Metadata
        # ---------------------------------------------------------------------------------------

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
            df_metadata_up = pd.DataFrame(uploadMetadataTableData)

        # Link the data using the funcitons in linkage.py
        load_events(
            event_data=df_data_up,
            event_metadata=df_metadata_up
        )
        
        uplift_metadata(
            raw_folder='./raw',
            queryTimeStr=queryTimeStr,
        )

        serdif_geosparql()
        
        ee_pack = link_data(
            raw_folder='./raw',
            df_input_path=df_data_up,
            df_info_path=df_metadata_up,
            queryTimeStr=queryTimeStr,
            agg_method=aggMethodValue,
            time_Unit=tempUnitValue,
        )

        # Button title to block double clicks
        subTitleToolTip = 'Queries submitted: ' + str(n_linkage)

        # Create the dictionary if there is not already one stored
        if not storeFilename:
            storeFilename = {}

        qNum = 'Q' + str(n_linkage)
        storeFilename[qNum] = ee_pack

        return [storeFilename, subTitleToolTip, subTitleToolTip, False, True]


@app.callback(
    [Output('download-zip', 'data')],
    Input('export-output-button', 'n_clicks'),
    Input('linkage-button', 'n_clicks'),
    State('store-zip', 'data')
)
def func(exportClick, linkageClick, filename):
    if not exportClick or not filename:
        raise PreventUpdate
    elif len(filename) != linkageClick:
        raise PreventUpdate
    else:
        exportFilePath = filename['Q' + str(linkageClick)]  # './downloads/' +
        sendFileLink = dcc.send_file(exportFilePath)
        if os.path.isfile(exportFilePath):
            os.remove(exportFilePath)
    return [sendFileLink]


if __name__ == "__main__":
    app.run_server(debug=True, port=8081)