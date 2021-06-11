# ----------------------------------------------------------------------------
# PYTHON LIBRARIES
# ----------------------------------------------------------------------------
# Dash Framework
import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import dash_table as dt
import dash_daq as daq
from dash.dependencies import Input, Output, State, ALL, MATCH
from dash.exceptions import PreventUpdate
from dash_extensions import Download
from dash_extensions.snippets import send_file

# import local modules
from config_settings import *
from data_processing import *
from styling import *

# for export
import io
import flask
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
# POINTERS TO DATA FILES AND APIS
# ----------------------------------------------------------------------------
display_terms_file = 'A2CPS_display_terms.csv'
weekly_csv = 'https://redcap.tacc.utexas.edu/api/vbr_api.php?op=weekly' # Production
multi_row_json = 'https://redcap.tacc.utexas.edu/api/vbr_api_devel.php?op=adverse_effects'


# ----------------------------------------------------------------------------
# FUNCTIONS FOR DASH UI COMPONENTS
# ----------------------------------------------------------------------------

def build_datatable(data_source, table_id):
    if(data_source.columns.nlevels == 2):
        columns_list = []
        for i in data_source.columns:
            columns_list.append({"name": [i[0],i[1]], "id": i[1]})
        data_source.columns = data_source.columns.droplevel()
    else:
        columns_list = [{"name": i, "id": i} for i in data_source.columns]
    new_datatable =  dt.DataTable(
            id = table_id,
            data=data_source.to_dict('records'),
            columns=columns_list,
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
            merge_duplicate_headers=True,
        )
    return new_datatable
# ----------------------------------------------------------------------------
# TABS
# ----------------------------------------------------------------------------
def build_tabs(report_date, ASSETS_PATH, display_terms_file, weekly_csv, multi_row_json):
    # try:
    report_date_msg, report_range_msg, table1, table2a, table2b, table3, table4, table5, table6, table7a, table7b, table8a, table8b, sex, race, ethnicity, age = get_page_data(datetime.now(), ASSETS_PATH, display_terms_file, weekly_csv, multi_row_json)

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
                html.Div([report_range_msg]),
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
                html.Div([report_range_msg]),
                html.Div(build_datatable(table7b, 'table_7b')),
            ]),
        ]),
        dbc.Card([
            html.H5('Table 8.a. Adverse Events'),
            html.Div([report_date_msg, '. Table is cumulative over study']),
            html.Div(build_datatable(table8a, 'table_8a')),
        ],body=True),
        dbc.Card([
            html.H5('Table 8.b. Description of Adverse Events'),
            html.Div([report_range_msg]),
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

    return tab1, tab2, tab3, tab4

    # except Exception as e:
    #     print(e)
    #     return None

# ----------------------------------------------------------------------------
# DASH APP LAYOUT FUNCTION
# ----------------------------------------------------------------------------
def serve_layout():
    try:
        tab1, tab2, tab3, tab4 = build_tabs(datetime.now(), ASSETS_PATH, display_terms_file, weekly_csv, multi_row_json)
        page_tabs = html.Div([
                    dcc.Tabs(id='tabs_tables', children=[
                        dcc.Tab(label='Screening', children=tab1),
                        dcc.Tab(label='Study Status', children=tab2),
                        dcc.Tab(label='Deviations & Adverse Events', children=tab3),
                        dcc.Tab(label='Demographics', children=tab4),
                    ]),
                    ])

    except:
        page_tabs = html.Div(['There has been a problem accessing the data for this Report.'])
    s_layout = html.Div([
        Download(id="download-dataframe-xlxs"),
        html.Div([
            html.Button("Download Report as Excel",n_clicks=0, id="btn_xlxs",style =EXCEL_EXPORT_STYLE ),
            html.H2(['A2CPS Weekly Report']),
            html.Div(id='download-msg'),
            page_tabs,
        ]
        , style =CONTENT_STYLE)
    ],style=TACC_IFRAME_SIZE)
    return s_layout

app.layout = serve_layout
# ----------------------------------------------------------------------------
# DATA CALLBACKS
# ----------------------------------------------------------------------------
# Create excel spreadsheel
# Download Data
@app.callback(
        Output("download-dataframe-xlxs", "data"),
        [Input("btn_xlxs", "n_clicks")],
        [State('table_1','data'), State('table_2a','data'),
        State('table_2b','data'), State('table_3','data'),
        State('table_4','data'), State('table_5','data'),
        State('table_6','data'),
        State('table_7a','data'),
        State('table_7b','data'),
        State('table_8a','data'),
        State('table_8b','data'),
        State('table_9a','data'),
        State('table_9b','data'),
        State('table_9c','data'),
        State('table_9d','data')
        ],
        )
def generate_xlsx(n_clicks,table_1,table_2a,table_2b,table_3,table_4,table_5,table_6,table_7a,table_7b,table_8a,table_8b,table_9a,table_9b,table_9c,table_9d):
    if n_clicks == 0:
        raise PreventUpdate
    else:
        table_data = (table_1,table_2a,table_2b,table_3,table_4,table_5,table_6,table_7a,table_7b,table_8a,table_8b,table_9a,table_9b,table_9c,table_9d
        )
        excel_sheet_name = ('Subjects Screened','Reasons for Declining',
                            'Declining Comments','Subjects Consented',
                            'Study Status','Rescinded Consent',
                            'Early Termination',
                            'Protocol Deviations','Deviation Descriptionss',
                            'Adverse Events','Event Descriptions',
                            'Gemder','Race','Ethnicity ','Age')
        tables = tuple(zip(table_data, excel_sheet_name))

        today = datetime.now().strftime('%Y_%m_%d')
        download_filename = datetime.now().strftime('%Y_%m_%d') + '_a2cps_weekly_report.xlsx'

        writer = pd.ExcelWriter(download_filename, engine='xlsxwriter')
        for i in range(0,len(tables)):
            df = pd.DataFrame(tables[i][0])
            if len(df) == 0 :
                df = pd.DataFrame(['No data for this table'])
            df.to_excel(writer, sheet_name=tables[i][1], index = False)
        writer.save()

        return send_file(writer, download_filename)


# RUN APPLICATION
# ----------------------------------------------------------------------------

if __name__ == '__main__':
    app.run_server(debug=True)
else:
    server = app.server
