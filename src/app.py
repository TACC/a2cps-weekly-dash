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
A2CPS_SANKEY_URL = os.environ.get("A2CPS_SANKEY_URL", None)

# ----------------------------------------------------------------------------
# STYLING
# ----------------------------------------------------------------------------

CONTENT_STYLE = {
    "padding": "2rem 1rem",
    "font-family": '"Times New Roman", Times, serif'
}


# ----------------------------------------------------------------------------
# DATA LOADING AND CLEANING
# ----------------------------------------------------------------------------
# ----------------------------------------------------------------------------
# API DATA
# ----------------------------------------------------------------------------

# Load API data
response = requests.get(A2CPS_SANKEY_URL)
redcap_data = response.json()

# Convert API Json --> pandas DataFrame
redcap_df = pd.DataFrame.from_dict(redcap_data)

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
            columns=[{"name": i, "id": i} for i in data_source.columns],
            style_cell= {'textAlign': 'left'},
            data=data_source.to_dict('records'),
            export_format="csv",
        )
    return new_datatable


# ----------------------------------------------------------------------------
# DASH APP LAYOUT
# ----------------------------------------------------------------------------
external_stylesheets_list = [dbc.themes.LITERA] # set any external stylesheets

app = dash.Dash(__name__,
                external_stylesheets=external_stylesheets_list,
                meta_tags=[{'name': 'viewport', 'content': 'width=device-width, initial-scale=1'}],
                assets_folder=ASSETS_PATH,
                requests_pathname_prefix=REQUESTS_PATHNAME_PREFIX,
                )

app.layout = html.Div([
    dbc.Row([
        dbc.Col([
            html.Div([dcc.Graph(figure=sankey_fig_api)],id='div_sankey'),
        ],width=6)
    ]),
    dbc.Row([
        dbc.Col([
            html.Div([build_datatable(redcap_df,'table_csv')],id='div_table' ,style={'padding':'15px'}),
        ],width=12)
    ])

], style =CONTENT_STYLE)
# ----------------------------------------------------------------------------
# DATA CALLBACKS
# ----------------------------------------------------------------------------

# ----------------------------------------------------------------------------
# RUN APPLICATION
# ----------------------------------------------------------------------------

if __name__ == '__main__':
    app.run_server(debug=True)
else:
    server = app.server
