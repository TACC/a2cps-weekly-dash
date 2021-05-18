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

## FUNCTIONS FOR LOADING DATA: MOVE TO MODULE
def load_api_data(api_url):
    '''Get dictionary of sankey data if provided a valid API url'''
    try:
        response = requests.get(api_url)
        api_data = response.json()
    except:
        return False
    return api_data



# ----------------------------------------------------------------------------
# DATA Loading and Cleaning
# ----------------------------------------------------------------------------
weekly_csv = 'https://redcap.tacc.utexas.edu/api/vbr_api.php?op=weekly' # Production
df = pd.read_csv(weekly_csv)

# convert date columns from object --> datetime datatypes
df['date_of_contact'] =  pd.to_datetime(df['date_of_contact'])
df['date_and_time'] =  pd.to_datetime(df['date_and_time'])
df['ewdateterm'] =  pd.to_datetime(df['ewdateterm'])

# data subset of consented patients
consented = df[df.consent_process_form_complete == 2].copy()

# cutoff date 1 week before report
today = datetime.now()
end_report = today # ** CAN CHANGE THIS TO GET PAST REPORTS
cutoff_report_range_days = 7
cutoff_date = end_report - timedelta(days=cutoff_report_range_days)

# ----------------------------------------------------------------------------
# TABLE 1
# ----------------------------------------------------------------------------

# Define needed columns for this table and select subset from main dataframe
t1_cols = ['redcap_data_access_group','participation_interest','screening_id']
t1 = df[t1_cols]

# drop missing data rows
t1 = t1.dropna()

# group by center and participation interest value and count number of IDs in each group
t1 = t1.groupby(by=["redcap_data_access_group",'participation_interest']).count()

# Reset data frame index to get dataframe in standard form with center, participation interest flag, count
t1 = t1.reset_index()

# Pivot participation interest values into separate columns
t1 = t1.pivot(index='redcap_data_access_group', columns='participation_interest', values='screening_id')

# Rename columns from numerical value to text description
t1 = t1.rename(columns={0.0: "No", 1.0: "Maybe", 2.0: 'Yes'})

# Reset Index so center is a column
t1 = t1.reset_index()

# remove index name
t1.columns.name = None

# Create Summary row ('All Sites') and Summary column ('All Participants')
t1_sum = t1
t1_sum.loc['All Sites']= t1_sum.sum(numeric_only=True, axis=0)
t1_sum.loc[:,'All Participants'] = t1_sum.sum(numeric_only=True, axis=1)

# ----------------------------------------------------------------------------
# TABLE 2
# ----------------------------------------------------------------------------
# Get decline columns from dataframe where participant was not interested (participation_interest == 0)
t2_cols = ['screening_id','redcap_data_access_group','reason_not_interested'] # cols to select
t2 = df[df.participation_interest == 0][t2_cols]

# group data by center and count the # of screening_ids
t2_site_count = pd.DataFrame(t2.groupby('redcap_data_access_group')['screening_id'].size())

# rename aggregate column
t2_site_count.columns = ['Total Declined']

# reset table index to turn center from index --> column
t2_site_count = t2_site_count.reset_index()

# ----------------------------------------------------------------------------
# TABLE 3
# ----------------------------------------------------------------------------




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
        html.Div([
            html.H3('Table 1'),
            build_datatable(t1_sum, 'table_1'),
        ]),
        html.Div([
            html.H3('Table 2'),
            build_datatable(t2_site_count, 'table_2'),
        ]),
    ]
    , style =CONTENT_STYLE)
],style=TACC_IFRAME_SIZE)
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
