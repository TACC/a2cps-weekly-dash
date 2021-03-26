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
from datetime import date

# Data visualization
import plotly.express as px
import plotly.graph_objects as go

# Dash Framework
import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import dash_table as dt
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

CONTENT_STYLE = {
    "padding": "2rem 1rem",
    "font-family": 'Arial, Helvetica, sans-serif'
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
# DATA LOADING AND CLEANING
# ----------------------------------------------------------------------------
# ----------------------------------------------------------------------------
# API DATA
# ----------------------------------------------------------------------------

## FUNCTIONS FOR LOADING DATA: MOVE TO MODULE
def load_api_data(api_url):
    response = requests.get(api_url)
    try:
        api_data = response.json()
    except ValueError as e:
        return False
    return api_data

def get_consort_df(api_url):
    if load_api_data(api_url):
        api_data = load_api_data(api_url)
        df = pd.DataFrame.from_dict(api_data)
    else:
        cosort_columns = ['source','target','value']
        df = pd.DataFrame(columns = cosort_columns)
    return df


# Load API data
api_url = 'https://redcap.tacc.utexas.edu/api/vbr_api.php?op=consort'

# time of date loading
today = date.today()
today_string = "This report generated on " + str(today)

# Convert API Json --> pandas DataFrame
redcap_df = get_consort_df(api_url)

# Get df of Nodes present in API
nodes = pd.DataFrame(list(redcap_df['source'].unique()) + list(redcap_df['target'].unique())).drop_duplicates().reset_index(drop=True)
nodes.reset_index(inplace=True)
nodes.columns = ['NodeID','Node']

# Merge data frames to create sankey dataframe
sources = nodes.copy()
sources.columns = ['sourceID','source']
targets = nodes.copy()
targets.columns = ['targetID','target']
sankey_df = redcap_df.merge(sources, on='source')
sankey_df = sankey_df.merge(targets, on='target')

# ----------------------------------------------------------------------------
# DATA VISUALIZATION
# ----------------------------------------------------------------------------

sankey_fig_api = go.Figure(data=[go.Sankey(
    # Define nodes
    node = dict(
      pad = 15,
      thickness = 20,
      line = dict(color = "black", width = .5),
      label =  nodes['Node'],
       # color =  "red"
    ),
    # Add links
    link = dict(
      source =  sankey_df['sourceID'],
      target =  sankey_df['targetID'],
      value =  sankey_df['value'],
      ),
    # orientation = 'v'
)])


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
    dbc.Row([
        dbc.Col([
            html.H1('CONSORT Report'),
            html.P(today_string),
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


    dbc.Row([
        dbc.Col([
            html.Div([dcc.Graph(figure=sankey_fig_api)],id='div_sankey'),
        ],xl=6),
    # ]),
    # dbc.Row([
        dbc.Col([
            html.Div([build_datatable(redcap_df,'table_csv')],id='div_table'),
        ],xl=6)
    ])

], style =CONTENT_STYLE)
# ----------------------------------------------------------------------------
# DATA CALLBACKS
# ----------------------------------------------------------------------------

@app.callback(
    Output('div_sankey','children'),
    Output('div_table','children'),
    Input('dropdown_datasource', 'value')
)
def dd_values(data_source):
    if data_source is None:
        div_sankey = html.H3('Please select a data source from the dropdown')
        div_table = html.Div()
    else:
        if data_source == 'api':
            selected_fig = sankey_fig_api
            selected_table = build_datatable(redcap_df,'table_api')
        else:
            selected_fig = sankey_fig_csv
            selected_table = build_datatable(sankey_data,'table_csv')
        div_sankey = dcc.Graph(figure=selected_fig)
        div_table = selected_table
    return div_sankey, div_table

# ----------------------------------------------------------------------------
# RUN APPLICATION
# ----------------------------------------------------------------------------

if __name__ == '__main__':
    app.run_server(debug=True)
else:
    server = app.server
