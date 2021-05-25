# ----------------------------------------------------------------------------
# PYTHON LIBRARIES
# ----------------------------------------------------------------------------

# File Management
import os # Operating system library
import pathlib # file paths
import json

# Data Cleaning and transformations
import pandas as pd
import numpy as np
import requests
import datetime
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

external_stylesheets_list = [dbc.themes.SANDSTONE] #  set any external stylesheets

app = dash.Dash(__name__,
                external_stylesheets=external_stylesheets_list,
                meta_tags=[{'name': 'viewport', 'content': 'width=device-width, initial-scale=1'}],
                assets_folder=ASSETS_PATH,
                requests_pathname_prefix=REQUESTS_PATHNAME_PREFIX,
                )

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
# MAIN DATA Loading and Prep
# ----------------------------------------------------------------------------
# Display Dictionary
display_terms_file = 'A2CPS_display_terms.csv'
display_terms = pd.read_csv(os.path.join(ASSETS_PATH, display_terms_file))
display_terms_dict = dp.get_display_dictionary(display_terms, 'api_field', 'api_value', 'display_text')

# path to Data APIs and reference files / load data
# Weekly Data from csv
weekly_csv = 'https://redcap.tacc.utexas.edu/api/vbr_api.php?op=weekly' # Production
df = pd.read_csv(weekly_csv)
df = df.apply(pd.to_numeric, errors='ignore')
# convert date columns from object --> datetime datatypes as appropriate
datetime_cols_list = ['date_of_contact','date_and_time','ewdateterm'] #erep_local_dtime also dates, but currently an array
df[datetime_cols_list] = df[datetime_cols_list].apply(pd.to_datetime)
# Convert 1-to-1 fields to user friendly format using display terms dictionary
one_to_many_cols = ['reason_not_interested','erep_protdev_type']
for i in display_terms_dict.keys():
    if i in df.columns:
        if i not in one_to_many_cols: # exclude the cols containing one to many data
            df = df.merge(display_terms_dict[i], how='left', on=i)

# Load data from API for One-to-May data points per record ID
multi_row_json = 'https://redcap.tacc.utexas.edu/api/vbr_api_devel.php?op=adverse_effects'
multi_data = dp.get_multi_row_data(multi_row_json)
multi_data = multi_data.apply(pd.to_numeric, errors='ignore')
multi_datetime_cols = ['erep_local_dtime','erep_ae_date','erep_onset_date','erep_resolution_date']
multi_data[multi_datetime_cols] = multi_data[multi_datetime_cols].apply(pd.to_datetime)

# Get subset of consented patients
# get data subset of just consented patients
consented = df[df.consent_process_form_complete == 2].copy()

# Set date range parameters for weekly reporting
# cutoff date 1 week before report
today = datetime.now()
end_report = today # ** CAN CHANGE THIS TO GET PAST REPORTS
cutoff_report_range_days = 7
cutoff_date = end_report - timedelta(days=cutoff_report_range_days)

# ----------------------------------------------------------------------------
# Data for Tables
# ----------------------------------------------------------------------------
report_date_msg = 'Report generated on ' + str(datetime.today().date())

## SCREENING TABLES
table1 = dp.get_table_1(df)

display_terms_t2a = display_terms_dict['reason_not_interested']
table2a = dp.get_table_2a(df, display_terms_t2a)

table2b = dp.get_table_2b(df, cutoff_date, end_report)

table3_data, table3 = dp.get_table_3(consented, today, 30)

## STUDY Status
table5, table6 = dp.get_tables_5_6(df)

## Deviations & Adverse Events
deviations = dp.get_deviation_records(df, multi_data, display_terms_dict)
table7a = dp.get_deviations_by_center(df, deviations, display_terms_dict)
table7b = dp.get_table7b_timelimited(deviations)

## Demographics

demographics = dp.get_demographic_data(consented)
# get subset of active patients
demo_active = demographics[demographics['Status']=='Active']

sex  =  dp.rollup_demo_data(demo_active, 'Sex', display_terms_dict, 'sex')
race = dp.rollup_demo_data(demo_active, 'Race', display_terms_dict, 'dem_race')
ethnicity = dp.rollup_demo_data(demo_active, 'Ethnicity', display_terms_dict, 'ethnic')
age = pd.DataFrame(demo_active.Age.describe().reset_index())

# ----------------------------------------------------------------------------
# FUNCTIONS FOR DASH UI COMPONENTS
# ----------------------------------------------------------------------------

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
                'vertical-align': 'top',
                'font-family':'sans-serif',
                'padding': '5px',
                'whiteSpace': 'normal',
                'height': 'auto',
                },
            style_as_list_view=True,
            style_header={
                'backgroundColor': 'grey',
                'fontWeight': 'bold',
                'color': 'white',
            },
            style_table={'overflowX': 'auto'},
            # export_format="csv",
        )
    return new_datatable

# ----------------------------------------------------------------------------
# TABS
# ----------------------------------------------------------------------------

tab1 = html.Div([
    dbc.Card(
        dbc.CardBody([
            html.H5('Table 1. Number of Subjects Screened', className="card-title"),
            html.Div([report_date_msg, '. Table is cumulative over study']),
            html.Div(build_datatable(table1, 'table_1')),
            dcc.Markdown('''
                **Center Name:** Center ID # and name
                **All Participants:** Total Number of Subjects screened
                **Yes:** Total number of subjects who expressed interest in participating in study
                **Maybe:** Total number of subjects who said they might participate in study
                **No:** Total number of subjects who declined to participate in study
                '''
                ,style={"white-space": "pre"}),
        ]),
    ),
    dbc.Card(
        dbc.CardBody([
            html.H5('Table 2. Reasons for declining'),
            html.H6('Table 2.a. Reasons for declining by Site'),
            html.Div([report_date_msg, '. Table is cumulative over study']),
            html.Div(build_datatable(table2a, 'table_2a')),
            dcc.Markdown('''
                **Center Name:** Center ID # and name
                **Total Declined:** Total Number of Subjects screened
                **Additional Columns:** Total Number of Subjects who sited that reason in declining.
                *Note*: Subjects may report multiple reasons (or no reason) for declining.
                '''
                ,style={"white-space": "pre"}),
        ]),
    ),
    dbc.Card(
        dbc.CardBody([
            html.H6('Table 2.b. Reasons for declining ‘Additional Comments’'),
            html.Div([report_date_msg, '. Table includes observations from the past week.']),
            html.Div(build_datatable(table2b, 'table_2b')),
        ]),
    ),
    dbc.Card(
        dbc.CardBody([
            html.H5('Table 3. Number of Subjects Consented'),
            html.Div([report_date_msg, '. Table is cumulative over study']),
            html.Div(build_datatable(table3, 'table_3')),
            dcc.Markdown('''
                **Center Name:** Center ID # and name
                **Consented:** Total Number of Subjects consented
                **Days Since Last Consent:** Number of days since most recent consent (for sites who have consented at least one subject)
                **Consents in last 30 days** : Rate of consent per 30 days
                **Total Eligible:** Total number of subjects who declined to participate in study
                **Total Ineligible:** Total number of subjects who were ineligible to participate in study
                **Total Rescinded:** Total number of subjects who withdrew from the study
                '''
                ,style={"white-space": "pre"}),
        ]),
    ),
])

tab2 = html.Div([
    dbc.Card([
        html.H5('Table 4. Ongoing Study Status'),
        html.Div('Table to come further into study'),
    ],body=True),
    dbc.Card([
        html.H5('Table 5. Rescinded Consent'),
        html.Div([report_date_msg]),
        # daq.ToggleSwitch(
        #     id='toggle-rescinded',
        #     label=['Previous Week','Cumulative'],
        #     value=False
        # ),
        html.Div(build_datatable(table5, 'table_5')),
    ],body=True),
    dbc.Card([
        html.H5('Table 6. Early Study Termination Listing'),
        html.Div([report_date_msg]),
        html.Div(build_datatable(table6, 'table_6')),
    ],body=True),
])

tab3 = html.Div([
    dbc.Card([
        dbc.CardBody([
            html.H5('Table 7.a. Protocol Deviations'),
            html.Div([report_date_msg, '. Table is cumulative over study']),
            html.Div(build_datatable(table7a, 'table_7a')),
            dcc.Markdown('''
                **Center Name:** Center ID # and name
                **Total Subjects:** Total Number of Subjects consented
                **Total Subjects with Deviation:** Total Number of Subjects with at least one deviation
                **Percent with 1+ Deviations:** Percent of Subjects with 1 or more deviations
                **Total Deviations:** Total of all deviations at this center
                **Additional Columns:** Count by center of the total number of each particular type of deviation
                '''
                ,style={"white-space": "pre"}),
        ]),
    ]),
    dbc.Card([
        dbc.CardBody([
            html.H5('Table 7.b. Description of Protocol Deviations'),
            html.Div([report_date_msg, '. Table includes observations from the past week.']),
            html.Div(build_datatable(table7b, 'table_7b')),
        ]),
    ]),
    dbc.Card([
        html.H5('Table 8.a. Adverse Events'),
        html.Div('No Data to Report at this time')
        # html.Div(build_datatable(t2_site_count, 'table_2')),
    ],body=True),
    dbc.Card([
        html.H5('Table 8.b. Description of Adverse Events'),
        html.Div('No Data to Report at this time')
    ],body=True),
])


tab4 = html.Div([
    dbc.Card([
        html.H5('Table 9. Demographic Characteristics'),
        html.Div([report_date_msg, '. Table is cumulative over study']),
        html.H5('Gender'),
        html.Div(build_datatable(sex, 'table_9a')),
        html.H5('Race'),
        html.Div(build_datatable(race, 'table_9b')),
        html.H5('Ethnicity'),
        html.Div(build_datatable(ethnicity, 'table_9c')),
        html.H5('Age'),
        html.Div(build_datatable(age, 'table_9d')),
    ],body=True),
])

# ----------------------------------------------------------------------------
# DASH APP LAYOUT
# ----------------------------------------------------------------------------
app.layout = html.Div([
    html.Div([
        html.H2(['A2CPS Weekly Report']),
        dcc.Tabs(id='tabs_tables', children=[
            dcc.Tab(label='Screening', children=[tab1]),
            dcc.Tab(label='Study Status', children=[tab2]),
            dcc.Tab(label='Deviations & Adverse Events', children=[tab3]),
            dcc.Tab(label='Demographics', children=[tab4]),

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
