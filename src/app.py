# ----------------------------------------------------------------------------
# PYTHON LIBRARIES
# ----------------------------------------------------------------------------

# File Management
import os # Operating system library
import pathlib # file paths

# Data Cleaning and transformations
import pandas as pd
import numpy as np
import requests
from datetime import datetime
import json

# Data visualization
import plotly.express as px
import plotly.graph_objects as go

# Dash Framework
import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import dash_table as dt
import dash_daq as daq
from dash.dependencies import Input, Output, State, ALL, MATCH

# ----------------------------------------------------------------------------
# CONFIG SETTINGS
# ----------------------------------------------------------------------------
DATA_PATH = pathlib.Path(__file__).parent.joinpath("data")
ASSETS_PATH = pathlib.Path(__file__).parent.joinpath("assets")
REQUESTS_PATHNAME_PREFIX = os.environ.get("REQUESTS_PATHNAME_PREFIX", "/")

# ----------------------------------------------------------------------------
# STYLING
# ----------------------------------------------------------------------------

TACC_IFRAME_SIZE = {
    "max-width" : "1060px", "max-height" : "980px" # THESE ARE SET TO FIT IN THE 1080x1000 TACC iFRAME.  CAN BE REMOVED IF THOSE CONSTRAINTS COME OFF
}

CONTENT_STYLE = {
    "padding": "2rem 1rem",
    "font-family": 'Arial, Helvetica, sans-serif',
}

export_style = '''
    position:absolute;
    right:25px;
    bottom:-55px;
    font-family: Arial, Helvetica, sans-serif;
    margin: 10px;
    color: #fff;
    background-color: #17a2b8;
    border-color: #17a2b8;
    display: inline-block;
    font-weight: 400;
    text-align: center;
    white-space: nowrap;
    vertical-align: middle;
    -webkit-user-select: none;
    -moz-user-select: none;
    -ms-user-select: none;
    user-select: none;
    border: 1px solid transparent;
    padding: .375rem .75rem;
    font-size: 1rem;
    line-height: 1.5;
    border-radius: .25rem;
    transition: color .15s ease-in-out,background-color .15s ease-in-out,border-color .15s ease-in-out,box-shadow .15s ease-in-out;
'''


# ----------------------------------------------------------------------------
# API DATA FUNCTIONS
# ----------------------------------------------------------------------------

## FUNCTIONS FOR LOADING DATA: MOVE TO MODULE
def load_api_data(api_url):
    '''Get dictionary of sankey data if provided a valid API url'''
    response = requests.get(api_url)
    try:
        api_data = response.json()
    except ValueError as e:
        return False
    return api_data

def get_api_df(api_data):
    ''' Take a dictionary of data balues and return a dataframe with source, target and value columns to build sankey '''
    if load_api_data(api_url):
        api_data = load_api_data(api_url)
        df = pd.DataFrame.from_dict(api_data)
    else:
        cosort_columns = ['source','target','value']
        df = pd.DataFrame(columns = cosort_columns)
    return df

def get_sankey_nodes(dataframe,source_col = 'source', target_col = 'target'):
    ''' Extract node infomration from sankey dataframe in case this is not provided '''
    nodes = pd.DataFrame(list(dataframe[source_col].unique()) + list(dataframe[target_col].unique())).drop_duplicates().reset_index(drop=True)
    nodes.reset_index(inplace=True)
    nodes.columns = ['NodeID','Node']
    return nodes

def get_sankey_dataframe (data_dataframe,
                          node_id_col = 'NodeID', node_name_col = 'Node',
                          source_col = 'source', target_col = 'target', value_col = 'value'):
    ''' Merge Node dataframes with data dataframe to create dataframe properly formatted for Sankey diagram.
        This means each source and target gets assigned the Index value from the nodes dataframe for the diagram.
    '''
    # get nodes from data
    nodes = get_sankey_nodes(data_dataframe)

    # Copy of Node data to merge on source
    sources = nodes.copy()
    sources.columns = ['sourceID','source']

    # Copy of Node data to merge on target
    targets = nodes.copy()
    targets.columns = ['targetID','target']

    # Merge the data dataframe with node information
    sankey_dataframe = data_dataframe.merge(sources, on='source')
    sankey_dataframe = sankey_dataframe.merge(targets, on='target')

    return nodes, sankey_dataframe

# ----------------------------------------------------------------------------
# LOAD API DATA
# ----------------------------------------------------------------------------
api_url = 'https://redcap.tacc.utexas.edu/api/vbr_api.php?op=consort'


# ----------------------------------------------------------------------------
# DATA VISUALIZATION
# ----------------------------------------------------------------------------

def build_sankey(nodes_dataframe, data_dataframe):
    sankey_fig = go.Figure(data=[go.Sankey(
        # Define nodes
        node = dict(
          pad = 15,
          thickness = 20,
          line = dict(color = "black", width = .5),
          label =  nodes_dataframe['Node'],
           # color =  "red"
        ),
        # Add links
        link = dict(
          source =  data_dataframe['sourceID'],
          target =  data_dataframe['targetID'],
          value =  data_dataframe['value'],
          ),
        # orientation = 'v'
    )])
    return sankey_fig


# ----------------------------------------------------------------------------
# DATA FOR DASH UI COMPONENTS
# ----------------------------------------------------------------------------

# Data table of API data
def build_datatable(data_source, table_id):
    new_datatable =  dt.DataTable(
            id = table_id,
            data=data_source.to_dict('records'),
            columns=[{"name": i, "id": i} for i in data_source.columns],
            css=[{'selector': '.row', 'rule': 'margin: 0; flex-wrap: nowrap'},
                {'selector':'.export','rule':export_style }
                # {'selector':'.export','rule':'position:absolute;right:25px;bottom:-35px;font-family:Arial, Helvetica, sans-serif,border-radius: .25re'}
                ],
            style_cell= {
                'text-align':'left',
                'padding': '5px'
                },
            style_as_list_view=True,
            style_header={
                'backgroundColor': 'grey',
                'fontWeight': 'bold',
                'color': 'white'
            },

            export_format="csv",
        )
    return new_datatable

def build_dash_content(str_date, sankey_fig, data_frame): # build_sankey(nodes, sankey_df) build_datatable(redcap_df,'table_csv') redcap_df
    dash_content = [
        dbc.Row([
            dbc.Col([
                html.Div(str_date),
            ],md = 8, lg=10),
        ]),
        dbc.Row([
            dbc.Col([
                html.Div([dcc.Graph(figure=sankey_fig)],id='div_sankey'),
            ],width=12),
        # ]),
        # dbc.Row([
            dbc.Col([
                html.Div([build_datatable(data_frame,'table_csv')],id='div_table'),
            ], width=12)
        ])
    ]
    return dash_content
# ----------------------------------------------------------------------------
# DASH APP LAYOUT
# ----------------------------------------------------------------------------
external_stylesheets_list = [dbc.themes.SANDSTONE] #  set any external stylesheets

app = dash.Dash(__name__,
                external_stylesheets=external_stylesheets_list,
                meta_tags=[{'name': 'viewport', 'content': 'width=device-width, initial-scale=1'}],
                assets_folder=ASSETS_PATH,
                requests_pathname_prefix=REQUESTS_PATHNAME_PREFIX,
                )

app.layout = html.Div([
    html.Div([
        dcc.Store(id='store_api'),
        dbc.Row([
            dbc.Col([
                html.H1('CONSORT Report'),
            ],md = 8, lg=10),
            dbc.Col([
                dcc.Dropdown(
                    id='dropdown_datasource',
                    options=[
                        {'label': 'Live Data', 'value': 'api'},
                        # {'label': 'Historical Data', 'value': 'csv'},
                    ],
                    value='api',
                    style={'display': 'none'} # Remove this when historical data is ready to go
                ),
            ],id='dd_datasource',md=4, lg=2)
        ]),
        html.Div(id = 'dash_content')
    ], style =CONTENT_STYLE)
],style=TACC_IFRAME_SIZE)
# ----------------------------------------------------------------------------
# DATA CALLBACKS
# ----------------------------------------------------------------------------

@app.callback(
    Output('dash_content','children'),
    Input('dropdown_datasource', 'value')
)
def dd_values(data_source):
    # time of date loading
    now = datetime.now()
    date_string = now.strftime("%m/%d/%Y")
    time_string = now.strftime("%H:%M")
    msg_string = "This report generated on " + str(date_string) + " at " + str(time_string)
    redcap_df = get_api_df(api_url) # load API Json and convert --> pandas DataFrame
    nodes, sankey_df = get_sankey_dataframe(redcap_df)
    # create page content
    dash_content = build_dash_content(msg_string, build_sankey(nodes, sankey_df),redcap_df)

    return dash_content

# ----------------------------------------------------------------------------
# RUN APPLICATION
# ----------------------------------------------------------------------------

if __name__ == '__main__':
    app.run_server(debug=True)
else:
    server = app.server
