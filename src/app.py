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
from flask import request
from dash.exceptions import PreventUpdate
from dash.dependencies import Input, Output, State, ALL, MATCH

# ----------------------------------------------------------------------------
# CONFIG SETTINGS
# ----------------------------------------------------------------------------
DATA_PATH = pathlib.Path(__file__).parent.joinpath("data")
ASSETS_PATH = pathlib.Path(__file__).parent.joinpath("assets")
REQUESTS_PATHNAME_PREFIX = os.environ.get("REQUESTS_PATHNAME_PREFIX", "/")

# ----------------------------------------------------------------------------
# SECURITY FUNCTION
# ----------------------------------------------------------------------------
def get_django_user():
    """
    Utility function to retrieve logged in username
    from Django
    """
    DJANGO_LOGIN_HOST = os.environ.get("DJANGO_LOGIN_HOST", None)
    SESSIONS_API_KEY = os.environ.get("SESSIONS_API_KEY", None)
    try:
        if not DJANGO_LOGIN_HOST:
            return True
        session_id = request.cookies.get('sessionid')
        if not session_id:
            raise Exception("sessionid cookie is missing")
        if not SESSIONS_API_KEY:
            raise Exception("SESSIONS_API_KEY not configured")
        api = "{django_login_host}/api/sessions_api/".format(
            django_login_host=DJANGO_LOGIN_HOST
        )
        response = requests.get(
            api, 
            params={
                "session_key": session_id,
                "sessions_api_key": SESSIONS_API_KEY
            }
        )
        return response.json()
    except Exception as e:
        print(e)
        return None

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
    try:
        response = requests.get(api_url)
        api_data = response.json()
    except:
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

def load_historical_data(csv_url):
    '''Load csv of historical dates and extract unique dates for dropdown options'''
    try :
        # Data Frame
        historical_data = pd.read_csv(csv_url, header = None)
        historical_data.columns=['source','target','value','date']
        historical_data['date_time'] = historical_data['date'].apply(lambda x: pd.Timestamp(x).strftime('%Y-%m-%d (%H:%M)'))

    except :
        historical_data = 'Could not access data'

    return historical_data

# ----------------------------------------------------------------------------
# DATA urls
# ----------------------------------------------------------------------------
# URL of live API data
api_url = 'https://redcap.tacc.utexas.edu/api/vbr_api.php?op=consort'

# URL of csv of historical dataframe
csv_url = 'https://portals-api.tacc.utexas.edu/files/v2/download/wma_prtl/system/a2cps.storage.public/reports/consort/consort-data-all.csv'

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

def build_dates_dropdown(type, options):
    if type == 'api':
        dates_dropdown = 'api'
    else:
        dates_dropdown = 'other'
    return dates_dropdown

def build_dash_content(chart, data_table): # build_sankey(nodes, sankey_df) build_datatable(redcap_df,'table_csv') redcap_df
    dash_content = [
        dbc.Row([
            dbc.Col([
                html.Div(chart, id='div_sankey'),
            ],width=12),
            dbc.Col([
                html.Div(data_table, id='div_table'),
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

def get_layout():
    if not get_django_user():
        return html.H1("Unauthorized")
    return html.Div([
        html.Div([
            dcc.Store(id='store_historical'),
            html.Div(['version: 040721 17:15'],id="version",style={'display':'none'}),
            html.Div(id='div_test'),
            dbc.Row([
                dbc.Col([
                    html.H1('CONSORT Report'),
                ],md = 9),
                dbc.Col([
                    daq.ToggleSwitch(
                        id='toggle-datasource',
                        label=['Live','Historical'],
                        value=False
                    ),
                ],id='dd_datasource',md=3)
            ]),
            dbc.Row([
                dbc.Col([
                    html.Div(id="report_msg"),
                ],md = 9),
                dbc.Col([
                    html.Div([dcc.Dropdown(id="dropdown_dates")],id="div_dropdown_dates"),
                ],md = 3),
            ]),
            dcc.Loading(
                id="loading-1",
                type="default",
                children=html.Div(id="loading-output-1")
            ),
            dcc.Loading(
                id="loading-2",
                type="default",
                children=html.Div(id="loading-output-2")
            ),
            html.Div(id = 'dash_content'),

        ], style =CONTENT_STYLE)
    ],style=TACC_IFRAME_SIZE)

app.layout = get_layout

# ----------------------------------------------------------------------------
# DATA CALLBACKS
# ----------------------------------------------------------------------------

# return data on toggle
@app.callback(
    Output("loading-output-1", "children"),
    Output('store_historical','data'),
    Output('report_msg','children'),
    Output('dropdown_dates','options'),
    Output('div_dropdown_dates','style'),
    # Output('dash_content','children'),
    Input('toggle-datasource', 'value'),
    State('store_historical','data')
)
def dd_values(data_source, data_state):
    if not get_django_user():
        raise PreventUpdate
    # time of date loading
    now = datetime.now().astimezone()
    date_string = now.strftime("%m/%d/%Y %H:%M %z")
    msg_string = "Data last loaded at " + str(date_string) + "UTC"

    hist_dict = data_state
    dropdown_style = {}

    if(data_source): # Load historical data if not yet loaded
        if not data_state:
            hist_dict = {}
            hd = load_historical_data(csv_url) # load data from csv
            dates = list(hd['date_time'].unique()) # list of unique dates in dataframe to supply dropdown options
            dates.sort(reverse=True)
            hist_dict['data'] = hd.to_dict('records') #store data in local data store
            hist_dict['dates']  = dates

        # set dropdown dropdown_options from dates
        dropdown_options = [{'label': i, 'value': i} for i in hist_dict['dates']]

    else: # load API Json and convert --> pandas DataFrame. Always do this live.
        # Set date dropdown to API values
        dropdown_options = [{'label': 'api', 'value': 'api'}]
        dropdown_style = {'display':'none'}

    return data_source, hist_dict, msg_string, dropdown_options, dropdown_style

@app.callback(
    Output('dropdown_dates', 'value'),
    [Input('dropdown_dates', 'options')])
def set_dropdown_dates_value(available_options):
    if not get_django_user():
        raise PreventUpdate
    return available_options[0]['value']

@app.callback(
    Output("loading-output-2", "children"),
    Output('dash_content','children'),
    Input('dropdown_dates','value'),
    State('toggle-datasource', 'value'),
    State('store_historical','data')
)
def dd_values(dropdown, toggle, historical_data):
    if not get_django_user():
        raise PreventUpdate
    df = pd.DataFrame()

    if not toggle: # live data from api
        df = get_api_df(api_url) # Get data from API
        chart_title = 'CONSORT Report from live API data'

    else: # historical data from csv loaded to data store
        df = pd.DataFrame(historical_data['data'])
        df = df[df['date_time'] == dropdown]
        chart_title = 'CONSORT Report from historical archive on ' + dropdown

    if not df.empty:
        data_table = [build_datatable(df,'table_csv')] # Build data_table from api data
        nodes, sankey_df = get_sankey_dataframe(df) # transform API data into sankey data
        sankey_fig = build_sankey(nodes, sankey_df) # turn sankey data into sankey figure
        sankey_fig.update_layout(title = chart_title)
        chart = dcc.Graph(id="sankey_chart",figure=sankey_fig) # create dash component chart from figure
        dash_content = build_dash_content(chart, data_table) # create page content from variables

    else:
        dash_content = html.Div('There has been an issue in loading data')

    return toggle, dash_content

# ----------------------------------------------------------------------------
# RUN APPLICATION
# ----------------------------------------------------------------------------

if __name__ == '__main__':
    app.run_server(debug=True)
else:
    server = app.server
