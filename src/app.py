# ----------------------------------------------------------------------------
# PYTHON LIBRARIES
# ----------------------------------------------------------------------------

# # File Management
# import os # Operating system library
# # import pathlib # file paths
# import json
#
# # Data Cleaning and transformations
# import pandas as pd
# import numpy as np
# import requests
# import datetime
# from datetime import datetime, timedelta

# Dash Framework
import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import dash_table as dt
import dash_daq as daq
from dash.dependencies import Input, Output, State, ALL, MATCH


# import local modules
from config_settings import *
from data_processing import *
from styling import *

# ----------------------------------------------------------------------------
# APP Settings
# ----------------------------------------------------------------------------

external_stylesheets_list = [dbc.themes.SANDSTONE] #  set any external stylesheets

app = dash.Dash(__name__,
                external_stylesheets=external_stylesheets_list,
                meta_tags=[{'name': 'viewport', 'content': 'width=device-width, initial-scale=1'}],
                assets_folder=ASSETS_PATH,
                requests_pathname_prefix=REQUESTS_PATHNAME_PREFIX,
                )



# ----------------------------------------------------------------------------
# LOAD DATA
# ----------------------------------------------------------------------------
# Pointers to data files
display_terms_file = 'A2CPS_display_terms.csv'
weekly_csv = 'https://redcap.tacc.utexas.edu/api/vbr_api.php?op=weekly' # Production
multi_row_json = 'https://redcap.tacc.utexas.edu/api/vbr_api_devel.php?op=adverse_effects'


# Get dataframes
display_terms, display_terms_dict, display_terms_dict_multi =  load_display_terms(ASSETS_PATH, display_terms_file)
df, consented = load_weekly_data(weekly_csv, display_terms_dict)
multi_data = load_multi_data(multi_row_json, display_terms_dict_multi)

centers_list = df.redcap_data_access_group_display.unique()
centers_df = pd.DataFrame(centers_list, columns = ['redcap_data_access_group_display'])

# Set date range parameters for weekly reporting
# cutoff date 1 week before report
today = datetime.now()
end_report = today # ** CAN CHANGE THIS TO GET PAST REPORTS
cutoff_report_range_days = 7
cutoff_date = end_report - timedelta(days=cutoff_report_range_days)

report_date_msg = 'Report generated on ' + str(datetime.today().date())

# ----------------------------------------------------------------------------
# Generate Data for Tables
# ----------------------------------------------------------------------------

## SCREENING TABLES
table1 = get_table_1(df)

display_terms_t2a = display_terms_dict_multi['reason_not_interested']
table2a = get_table_2a(df, display_terms_t2a)

table2b = get_table_2b(df, cutoff_date, end_report)

table3_data, table3 = get_table_3(consented, today, 30)

## STUDY Status
table4 = get_table_4(centers_df, consented, today)

table5, table6 = get_tables_5_6(df)

## Deviations
deviations = get_deviation_records(df, multi_data, display_terms_dict_multi)
table7a = get_deviations_by_center(centers_df, consented, deviations, display_terms_dict_multi)
table7b = get_table7b_timelimited(deviations)

## Adverse Events
adverse_events = get_adverse_event_records(df, multi_data, display_terms_dict_multi)
table8a = get_adverse_events_by_center(centers_df, df, adverse_events, display_terms_dict_multi)
table8b = get_table_8b(adverse_events, today)

## Demographics

demographics = get_demographic_data(consented)
# get subset of active patients
demo_active = demographics[demographics['Status']=='Active']

sex  =  rollup_demo_data(demo_active, 'Sex', display_terms_dict, 'sex')
race = rollup_demo_data(demo_active, 'Race', display_terms_dict, 'dem_race')
ethnicity = rollup_demo_data(demo_active, 'Ethnicity', display_terms_dict, 'ethnic')
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
            export_format="csv",
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
        html.Div([report_date_msg]),
        html.Div(build_datatable(table4, 'table_4')),
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
        html.Div([report_date_msg, '. Table is cumulative over study']),
        html.Div(build_datatable(table8a, 'table_8a')),
        # html.Div(build_datatable(t2_site_count, 'table_2')),
    ],body=True),
    dbc.Card([
        html.H5('Table 8.b. Description of Adverse Events'),
        html.Div([report_date_msg, '. Table includes observations from the past week.']),
        html.Div(build_datatable(table8b, 'table_8b')),
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
