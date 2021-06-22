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
                suppress_callback_exceptions=True
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
def build_datatable_from_table_dict(table_dict, key, table_id, fill_width = False):
    try:
        table_columns = table_dict[key]['columns_list']
        table_data = table_dict[key]['data']
        new_datatable =  dt.DataTable(
                id = table_id,
                columns=table_columns,
                data=table_data,
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
                    'whiteSpace': 'normal',
                    'fontWeight': 'bold',
                    'color': 'white',
                },

                fill_width=fill_width,
                # style_table={'overflowX': 'auto'},
                # export_format="csv",
                merge_duplicate_headers=True,
            )
        return new_datatable
    except:
        return None

# ----------------------------------------------------------------------------
# TABS
# ----------------------------------------------------------------------------
def build_tables_dict(report_date, ASSETS_PATH, display_terms_file, weekly_csv, multi_row_json):
    report_date_msg, report_range_msg, table1, table2a, table2b, table3, table4, table5, table6, table7a, table7b, table8a, table8b, sex, race, ethnicity, age = get_page_data(datetime.now(), ASSETS_PATH, display_terms_file, weekly_csv, multi_row_json)
    tables_names = ("table1", "table2a", "table2b", "table3", "table4", "table5", "table6", "table7a", "table7b", "table8a", "table8b", "sex", "race", "ethnicity", "age")
    excel_sheet_names = ("Screened", "Decline_Reasons", "Decline_Comments", "Consent", "Stud_Status", "Rescinded_Consent", "Early_Termination", "Protocol_Deviations", "Protocol_Deviations_Description",
    "Adverse_Events", "Adverse_Events_Description", "Gender", "Race", "Ethnicity", "Age")

    tables = (table1, table2a, table2b, table3, table4, table5, table6, table7a, table7b, table8a, table8b, sex, race, ethnicity, age)

    page_meta_dict = {}
    page_meta_dict['report_date_msg'] = report_date_msg
    page_meta_dict['report_range_msg'] = report_range_msg

    tables_dict = {}
    for i in range(0,len(tables_names)):
        table_name = tables_names[i]
        excel_sheet_name = excel_sheet_names[i]
        data_source = tables[i]

        if(data_source.columns.nlevels == 2):
            columns_list = []
            for i in data_source.columns:
                columns_list.append({"name": [i[0],i[1]], "id": i[1]})
            data_source.columns = data_source.columns.droplevel()
        else:
            columns_list = [{"name": i, "id": i} for i in data_source.columns]

        tables_dict[table_name] = {'excel_sheet_name': excel_sheet_name,
                                    'columns_list': columns_list,
                                    'data': data_source.to_dict('records')  }

    return page_meta_dict, tables_dict

def build_content(tables_dict, page_meta_dict):

    report_date_msg, report_range_msg = page_meta_dict['report_date_msg'], page_meta_dict['report_range_msg']

    section1 = html.Div([
        dbc.Card(
            dbc.CardBody([
                html.H5('Table 1. Number of Subjects Screened', className="card-title"),
                html.Div([report_date_msg, '. Table is cumulative over study']),
                html.Div(build_datatable_from_table_dict(tables_dict, 'table1', 'table_1')),
                dcc.Markdown('''
                    **Center Name:** MCC and Site
                    **All Participants:** Total number of subjects screened
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
                html.Div(build_datatable_from_table_dict(tables_dict, 'table2a', 'table_2a')),
                dcc.Markdown('''
                    **Center Name:** MCC and Site
                    **Total Declined:** Total number of subjects screened
                    **Additional Columns:** Total number of subjects who sited that reason in declining.
                    *Note*: Subjects may report multiple reasons (or no reason) for declining.
                    '''
                    ,style={"white-space": "pre"}),
            ]),
        ),
        dbc.Card(
            dbc.CardBody([
                html.H6('Table 2.b. Reasons for declining ‘Additional Comments’'),
                html.Div([report_range_msg]),
                html.Div(build_datatable_from_table_dict(tables_dict, 'table2b', 'table_2b')),
            ]),
        ),
        dbc.Card(
            dbc.CardBody([
                html.H5('Table 3. Number of Subjects Consented'),
                html.Div([report_date_msg, '. Table is cumulative over study']),
                html.Div(build_datatable_from_table_dict(tables_dict, 'table3', 'table_3')),
                dcc.Markdown('''
                    **Center Name:** MCC and Site
                    **Consented:** Total number of subjects consented
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

    section2 = html.Div([
        dbc.Card([
            html.H5('Table 4. Ongoing Study Status'),
            html.Div([report_date_msg]),
            html.Div(build_datatable_from_table_dict(tables_dict, 'table4', 'table_4')),
        ],body=True),
        dbc.Card([
            html.H5('Table 5. Rescinded Consent'),
            html.Div([report_date_msg]),
            # daq.ToggleSwitch(
            #     id='toggle-rescinded',
            #     label=['Previous Week','Cumulative'],
            #     value=False
            # ),
            html.Div(build_datatable_from_table_dict(tables_dict, 'table5', 'table_5')),
        ],body=True),
        dbc.Card([
            html.H5('Table 6. Early Study Termination Listing'),
            html.Div([report_date_msg]),
            html.Div(build_datatable_from_table_dict(tables_dict, 'table6', 'table_6')),
        ],body=True),
    ])

    section3 = html.Div([
        dbc.Card([
            dbc.CardBody([
                html.H5('Table 7.a. Protocol Deviations'),
                html.Div([report_date_msg, '. Table is cumulative over study']),
                html.Div(build_datatable_from_table_dict(tables_dict, 'table7a', 'table_7a')),
                dcc.Markdown('''
                    **Center Name:** MCC and Site
                    **Baseline Patients:** Total number of subjects reaching baseline
                    **# with Deviation:** Total number of subjects with at least one deviation
                    **Total Deviations:** Total of all deviations at this center (a single patient can have more than one)
                    **% with 1+ Deviations:** Percent of Patients with 1 or more deviations
                    **Additional Columns:** Count by center of the total number of each particular type of deviation
                    '''
                    ,style={"white-space": "pre"}),
            ]),
        ]),
        dbc.Card([
            dbc.CardBody([
                html.H5('Table 7.b. Description of Protocol Deviations'),
                html.Div([report_range_msg]),
                html.Div(build_datatable_from_table_dict(tables_dict, 'table7b', 'table_7b')),
            ]),
        ]),
        dbc.Card([
            html.H5('Table 8.a. Adverse Events'),
            html.Div([report_date_msg, '. Table is cumulative over study']),
            html.Div(build_datatable_from_table_dict(tables_dict, 'table8a', 'table_8a')),
        ],body=True),
        dbc.Card([
            html.H5('Table 8.b. Description of Adverse Events'),
            html.Div([report_range_msg]),
            html.Div(build_datatable_from_table_dict(tables_dict, 'table8b', 'table_8b')),
        ],body=True),
    ])

    section4 = html.Div([
        dbc.Card([
            html.H5('Table 9. Demographic Characteristics'),
            html.Div([report_date_msg, '. Table is cumulative over study']),
            html.H5('Gender'),
            html.Div(build_datatable_from_table_dict(tables_dict, 'sex', 'table_9a')),
            html.H5('Race'),
            html.Div(build_datatable_from_table_dict(tables_dict, 'race', 'table_9b')),
            html.H5('Ethnicity'),
            html.Div(build_datatable_from_table_dict(tables_dict, 'ethnicity', 'table_9c')),
            html.H5('Age'),
            html.Div(build_datatable_from_table_dict(tables_dict, 'age', 'table_9d')),
        ],body=True),
    ])

    return section1, section2, section3, section4

def get_sections_dict_for_store(section1, section2, section3, section4):
    sections_dict = {}
    sections_dict['section1'] = section1
    sections_dict['section2'] = section2
    sections_dict['section3'] = section3
    sections_dict['section4'] = section4
    return sections_dict

# ----------------------------------------------------------------------------
# DASH APP LAYOUT FUNCTION
# ----------------------------------------------------------------------------
def build_page_layout(toggle_view_value, sections_dict):

    section1 = sections_dict['section1']
    section2 = sections_dict['section2']
    section3 = sections_dict['section3']
    section4 = sections_dict['section4']

    if toggle_view_value:
        page_layout = [html.H3('Screening'), section1, html.H3('Study Status'), section2, html.H3('Deviations & Adverse Events'), section3, html.H3('Demographics'), section4]
    else:
        page_layout = html.Div([
                    dcc.Tabs(id='tabs_tables', children=[
                        dcc.Tab(label='Screening', children=[
                            html.Div([section1], id='section_1'),
                        ]),
                        dcc.Tab(label='Study Status', children=[
                            html.Div([section2], id='section_2'),
                        ]),
                        dcc.Tab(label='Deviations & Adverse Events', children=[
                            html.Div([section3], id='section_3'),
                        ]),
                        dcc.Tab(label='Demographics', children=[
                            html.Div([section4], id='section_4'),
                        ]),
                    ]),
                    ])
    return page_layout

def serve_layout():
    page_meta_dict, tables_dict, sections_dict = {}, {}, {}
    try:
        page_meta_dict, tables_dict = build_tables_dict(datetime.now(), ASSETS_PATH, display_terms_file, weekly_csv, multi_row_json)
        section1, section2, section3, section4 = build_content(tables_dict, page_meta_dict)
        sections_dict = get_sections_dict_for_store(section1, section2, section3, section4)
        page_layout = html.Div(id='page_layout')
    except:
        page_layout = html.Div(['There has been a problem accessing the data for this Report.'])

    s_layout = html.Div([
        dcc.Store(id='store_meta', data = page_meta_dict),
        dcc.Store(id='store_tables', data = tables_dict),
        dcc.Store(id='store_sections', data = sections_dict),
        Download(id="download-dataframe-xlxs"),
        Download(id="download-dataframe-html"),

        html.Div([
            html.H2(['A2CPS Weekly Report']),
            html.Div([
                html.Button("Download as Excel",n_clicks=0, id="btn_xlxs",style =EXCEL_EXPORT_STYLE ),
                daq.ToggleSwitch(
                    id='toggle-view',
                    label=['Tabs','Single Page'],
                    value=False,
                    style =EXCEL_EXPORT_STYLE
                ),
            ],id='print-hide', className='print-hide'),
            html.H5(page_meta_dict['report_date_msg']),
            html.Div(id='download-msg'),
            page_layout,
        ]
        , style =CONTENT_STYLE)
    ],style=TACC_IFRAME_SIZE)
    return s_layout

app.layout = serve_layout
# ----------------------------------------------------------------------------
# DATA CALLBACKS
# ----------------------------------------------------------------------------

# Use toggle to display either tabs or single page LAYOUT
@app.callback(Output("page_layout","children"), Input('toggle-view',"value"),State('store_sections', 'data'))
def set_page_layout(value, sections):
    return build_page_layout(value, sections)

# Create excel spreadsheel
@app.callback(
        Output("download-dataframe-xlxs", "data"),
        Input("btn_xlxs", "n_clicks"),
        State("store_tables","data"),
        )
def click_excel(n_clicks,store):
    if n_clicks == 0:
        raise PreventUpdate
    if store:
        # msg =  html.Div(json.dumps(store))
        today = datetime.now().strftime('%Y_%m_%d')
        download_filename = datetime.now().strftime('%Y_%m_%d') + '_a2cps_weekly_report_data.xlsx'
        table_keys = store.keys()

        writer = pd.ExcelWriter(download_filename, engine='xlsxwriter')

        for key in table_keys:
            excel_sheet_name = store[key]['excel_sheet_name']
            df = pd.DataFrame(store[key]['data'])
            if len(df) == 0 :
                df = pd.DataFrame(columns =['No data for this table'])
            df.to_excel(writer, sheet_name=excel_sheet_name, index = False)
        writer.save()

        excel_file =  send_file(writer, download_filename)

    else:
        excel_file = None
    return excel_file

# RUN APPLICATION
# ----------------------------------------------------------------------------

if __name__ == '__main__':
    app.run_server(debug=True)
else:
    server = app.server
