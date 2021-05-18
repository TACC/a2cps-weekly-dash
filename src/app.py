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
from datetime import datetime, timedelta

# import local modules
import data_processing as dp

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


# ----------------------------------------------------------------------------
# DATA Loading and Cleaning
# ----------------------------------------------------------------------------
weekly_csv = 'https://redcap.tacc.utexas.edu/api/vbr_api.php?op=weekly' # Production


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
                'font-family':'sans-serif',
                'padding': '5px'
                },
            style_as_list_view=True,
            style_header={
                'backgroundColor': 'grey',
                'fontWeight': 'bold',
                'color': 'white'
            },

            # export_format="csv",
        )
    return new_datatable

# ----------------------------------------------------------------------------
# TABS
# ----------------------------------------------------------------------------

tab1 = html.Div([
    html.Div([
        html.H5('Table 1. Number of Subjects Screened'),
        # html.Div(build_datatable(t2_site_count, 'table_2')),
    ]),
    html.Div([
        html.H5('Table 2. Reasons for declining'),
        html.H6('Table 2.a. Reasons for declining by Site'),
        # html.Div(build_datatable(t2_site_count, 'table_2')),
        html.H6('Table 2.b. Reasons for declining ‘Additional Comments’'),
        # html.Div(build_datatable(t2_site_count, 'table_2')),
    ]),
    html.Div([
        html.H5('Table 3. Number of Subjects Consented'),
        # html.Div(build_datatable(t2_site_count, 'table_2')),
    ]),
])

tab2 = html.Div([
    html.Div([
        html.H5('Table 4. Ongoing Study Status'),
        # html.Div(build_datatable(t2_site_count, 'table_2')),
    ]),
    html.Div([
        html.H5('Table 5. Rescinded Consent'),
        # html.Div(build_datatable(t2_site_count, 'table_2')),
    ]),
    html.Div([
        html.H5('Table 6. Early Study Termination Listing'),
        # html.Div(build_datatable(t2_site_count, 'table_2')),
    ]),
])

tab3 = html.Div([
    html.Div([
        html.H5('Table 7. Protocol Deviations'),
        html.H6('Table 7.a. Protocol Deviations'),
        # html.Div(build_datatable(t2_site_count, 'table_2')),
        html.H6('Table 7.b. Description of Protocol Deviations'),
        # html.Div(build_datatable(t2_site_count, 'table_2')),
    ]),
    html.Div([
        html.H5('Table 8. Adverse Events'),
        html.H6('Table 8.a. Adverse Events'),
        # html.Div(build_datatable(t2_site_count, 'table_2')),
        html.H6('Table 8.b. Description of Adverse Events'),
        # html.Div(build_datatable(t2_site_count, 'table_2')),
    ]),
])


tab4 = html.Div([
    html.Div([
        html.H5('Table 9. Demographic Characteristics'),
        # html.Div(build_datatable(t2_site_count, 'table_2')),
    ]),
])

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
        html.H2(['A2CPS Weekly Report']),
        dcc.Tabs(id='tabs_tables', value='tab-1', children=[
            dcc.Tab(label='Screening', value='tab-1'),
            dcc.Tab(label='Study Status', value='tab-2'),
            dcc.Tab(label='Deviations & Adverse Events', value='tab-3'),
            dcc.Tab(label='Demographics', value='tab-4'),
        ]),
        html.Div(id='tabs_tables-content'),
        # html.Div([
        #     html.H3('Table 2'),
        #     build_datatable(t2_site_count, 'table_2'),
        # ]),
    ]
    , style =CONTENT_STYLE)
],style=TACC_IFRAME_SIZE)
# ----------------------------------------------------------------------------
# DATA CALLBACKS
# ----------------------------------------------------------------------------

@app.callback(Output('tabs_tables-content', 'children'),
              Input('tabs_tables', 'value'))
def render_content(tab):
    if tab == 'tab-1':
        return tab1
    elif tab == 'tab-2':
        return tab2
    elif tab == 'tab-3':
        return tab3
    elif tab == 'tab-4':
        return tab4
    else:
        return html.Div('please select a tab')



# ----------------------------------------------------------------------------
# RUN APPLICATION
# ----------------------------------------------------------------------------

if __name__ == '__main__':
    app.run_server(debug=True)
else:
    server = app.server
