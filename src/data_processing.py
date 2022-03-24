 # Libraries
import traceback
# Data
# File Management
import os # Operating system library
import pathlib # file paths
import json
import requests
import math
import numpy as np
import pandas as pd # Dataframe manipulations
import sqlite3
import datetime
from datetime import datetime, timedelta

# import local modules
from config_settings import *

# ----------------------------------------------------------------------------
# HELPER FUNCTIONS
# ----------------------------------------------------------------------------

def use_b_if_not_a(a, b):
    if not pd.isnull(a):
        x = a
    else:
        x = b
    return x

def create_multiindex(df, split_char):
    cols = df.columns
    multi_cols = []
    for c in cols:
        multi_cols.append(tuple(c.split(split_char)))
    multi_index = pd.MultiIndex.from_tuples(multi_cols)
    df.columns = multi_index
    return df

def convert_to_multindex(df, delimiter = ': '):
    cols = list(df.columns)
    cols_with_delimiter = [c for c in cols if delimiter in c]
    df_mi = df[cols_with_delimiter].copy()
    df_mi.columns = [tuple(x) for x in df_mi.columns.str.split(delimiter)]
    df_mi.columns = pd.MultiIndex.from_tuples(df_mi.columns)
    return df_mi

def datatable_settings_multiindex(df, flatten_char = '_'):
    ''' Plotly dash datatables do not natively handle multiindex dataframes. This function takes a multiindex column set
    and generates a flattend column name list for the dataframe, while also structuring the table dictionary to represent the
    columns in their original multi-level format.

    Function returns the variables datatable_col_list, datatable_data for the columns and data parameters of
    the dash_table.DataTable'''
    datatable_col_list = []

    levels = df.columns.nlevels
    if levels == 1:
        for i in df.columns:
            datatable_col_list.append({"name": i, "id": i})
    else:
        columns_list = []
        for i in df.columns:
            col_id = flatten_char.join(i)
            datatable_col_list.append({"name": i, "id": col_id})
            columns_list.append(col_id)
        df.columns = columns_list

    datatable_data = df.to_dict('records')

    return datatable_col_list, datatable_data

# ----------------------------------------------------------------------------
# DATA DISPLAY DICTIONARIES
# ----------------------------------------------------------------------------
def load_display_terms(ASSETS_PATH, display_terms_file):
    try:
        display_terms = pd.read_csv(os.path.join(ASSETS_PATH, display_terms_file))

        # Get display terms dictionary for one-to-one records
        display_terms_uni = display_terms[display_terms.multi == 0]
        display_terms_dict = get_display_dictionary(display_terms_uni, 'api_field', 'api_value', 'display_text')

        # Get display terms dictionary for one-to-many records
        display_terms_multi = display_terms[display_terms.multi == 1]
        display_terms_dict_multi = get_display_dictionary(display_terms_multi, 'api_field', 'api_value', 'display_text')

        return display_terms, display_terms_dict, display_terms_dict_multi
    except Exception as e:
        traceback.print_exc()
        return None

def get_display_dictionary(display_terms, api_field, api_value, display_col):
    '''from a dataframe with the table display information, create a dictionary by field to match the database
    value to a value for use in the UI '''
    try:
        display_terms_list = display_terms[api_field].unique() # List of fields with matching display terms

        # Create a dictionary using the field as the key, and the dataframe to map database values to display text as the value
        display_terms_dict = {}
        for i in display_terms_list:
            term_df = display_terms[display_terms.api_field == i]
            term_df = term_df[[api_value,display_col]]
            term_df = term_df.rename(columns={api_value: i, display_col: i + '_display'})
            term_df = term_df.apply(pd.to_numeric, errors='ignore')
            display_terms_dict[i] = term_df
        return display_terms_dict

    except Exception as e:
        traceback.print_exc()
        return None


# ----------------------------------------------------------------------------
# DATA LOADING
# ----------------------------------------------------------------------------
# Weekly data from from json files stored at TACC
def get_subjects_data_from_local_file(mcc_list):
    try:
        # Read files into json
        r_status = 'local_file'
        weekly_data = pd.DataFrame()
        for mcc in mcc_list:
            try:
                mcc_file = ''.join(['data/subjects-',str(mcc),'-latest.json'])
                mcc_json = pd.read_json(mcc_file, orient='index').reset_index()
                mcc_data['mcc'] = mcc
                if weekly_data.empty:
                    weekly_data = mcc_data
                else:
                    weekly_data = pd.concat([weekly_data, mcc_data])
            except Exception as e:
                traceback.print_exc()
                weekly_data = weekly_data
        if 'index' in weekly_data.columns:
            weekly_data.rename(columns={"index": "record_id"}, inplace=True)
        return weekly_data, r_status
    except Exception as e:
        traceback.print_exc()
        return None, None

def get_subjects_data_from_file(file_url_root, report, report_suffix, mcc_list):
    try:
        # Read files into json
        weekly_data = pd.DataFrame()
        for mcc in mcc_list:
            try:
                json_url = '/'.join([file_url_root, report,report_suffix.replace('[mcc]',str(mcc))])
                r = requests.get(json_url)
                if r.status_code == 200:
                # TO DO: add an else statement to use local files if the request fails
                    mcc_json = r.json()
                    mcc_data = pd.DataFrame.from_dict(mcc_json, orient = 'index').reset_index()
                    mcc_data['mcc'] = mcc
                    if weekly_data.empty:
                        weekly_data = mcc_data
                    else:
                        weekly_data = pd.concat([weekly_data, mcc_data])
                else:
                    print(r.status_code)
                    # Remove these 2 lines if you don't want to use local files
                    # weekly_data, r_status = get_subjects_data_from_local_file(mcc_list)
                    # return weekly_data, r_status
            except Exception as e:
                traceback.print_exc()
                weekly_data = weekly_data
        if 'index' in weekly_data.columns:
            weekly_data.rename(columns={"index": "record_id"}, inplace=True)
        return weekly_data, r.status_code
    except Exception as e:
        traceback.print_exc()
        return None, None

# Extract data with multiple values (stored as 'adverse effects' column)
def extract_adverse_effects_data(weekly_data):
    index_cols = ['record_id','main_record_id', 'mcc']
    # reset index using index_cols
    weekly_data = weekly_data.set_index(index_cols)
    # Extract multi data values
    multi_df = weekly_data[['adverse_effects']].dropna()
    # Convert from data frame back to dict
    multi_dict = multi_df.to_dict('index')
    # Turn dict into df with multi=index and reset_index
    multi = pd.DataFrame.from_dict({(i,k): multi_dict[i][j][k]
                               for i in multi_dict.keys()
                               for j in multi_dict[i].keys()
                               for k in multi_dict[i][j].keys()
                           },
                           orient='index')
    # Replace empty strings with NaN
    multi = multi.replace(r'^\s*$', np.nan, regex=True)
    multi = multi.reset_index()
    multi[index_cols] = pd.DataFrame(multi['level_0'].tolist(), index=multi.index)
    multi['instance'] = multi['level_1']
    multi.drop(['level_0', 'level_1'], axis=1, inplace=True)
    return multi

# ----------------------------------------------------------------------------
# DATA CLEANING
# ----------------------------------------------------------------------------

def clean_weekly_data(weekly, display_terms_dict):
    try:
        # Convert all string 'N/A' values to nan values
        weekly = weekly.replace('N/A', np.nan)

        # Handle 1-many dem_race, take multi-select values and convert to 8
        if not np.issubdtype(weekly['dem_race'].dtype, np.number):
            weekly['dem_race_original'] = weekly['dem_race']
            weekly.loc[(weekly.dem_race.str.contains('|', regex=False, na=False)),'dem_race']='8'

        # Coerce numeric values to enable merge
        weekly = weekly.apply(pd.to_numeric, errors='ignore')

        for i in display_terms_dict.keys():
            if i in weekly.columns:
                display_terms = display_terms_dict[i]
                if weekly[i].dtype == np.float64:
                    # for display columns where data is numeric, merge on display dictionary, treating cols as floats to handle nas
                    display_terms[i] = display_terms[i].astype('float64')
                weekly = weekly.merge(display_terms, how='left', on=i)

        # convert date columns from object --> datetime datatypes as appropriate
        datetime_cols_list = ['date_of_contact','date_and_time','obtain_date','ewdateterm','sp_surg_date','sp_v1_preop_date','sp_v2_6wk_date','sp_v3_3mo_date'] #erep_local_dtime also dates, but currently an array
        weekly[datetime_cols_list] = weekly[datetime_cols_list].apply(pd.to_datetime, errors='coerce')

        return weekly

    except Exception as e:
        traceback.print_exc()
        return None, None


def clean_adverse_events(adverse_events, display_terms_dict_multi):
    try:
        # Coerce to numeric
        multi_data = adverse_events.apply(pd.to_numeric, errors='ignore')

        # convert date columns from object --> datetime datatypes as appropriate
        multi_datetime_cols = ['erep_local_dtime','erep_ae_date','erep_onset_date','erep_resolution_date']
        multi_data[multi_datetime_cols] = multi_data[multi_datetime_cols].apply(pd.to_datetime, errors='coerce')

        # Convert numeric values to display values using dictionary
        for i in display_terms_dict_multi.keys():
            if i in multi_data.columns:
                multi_data = multi_data.merge(display_terms_dict_multi[i], how='left', on=i)

        return multi_data
    except Exception as e:
        traceback.print_exc()
        return None

def get_screening_sites(ASSETS_PATH, df, id_col):
    # Get dataframes
    ids = df.loc[:, [id_col]]
    screening_sites = pd.read_csv(os.path.join(ASSETS_PATH, 'screening_sites.csv'))

    # open sql connection to create new datarframe with record_id paired to screening site
    conn = sqlite3.connect(':memory:')
    ids.to_sql('ids', conn, index=False)
    screening_sites.to_sql('ss', conn, index=False)

    sql_qry = f'''
    select {id_col}, screening_site
    from ids
    join ss on
    ids.{id_col} between ss.record_id_start and ss.record_id_end
    '''
    sites = pd.read_sql_query(sql_qry, conn)
    conn.close()

    return sites

def add_screening_site(ASSETS_PATH, df, id_col):
    sites = get_screening_sites(ASSETS_PATH, df, id_col)
    df = sites.merge(df, how='left', on=id_col)
    return df

# ----------------------------------------------------------------------------
# Get dataframes and parameters
# ----------------------------------------------------------------------------

def get_time_parameters(end_report, report_days_range = 7):
    today = datetime.now()
    start_report = end_report - timedelta(days=report_days_range)
    start_report_text = str(start_report.date()) #dt.strftime('%m/%d/%Y')
    end_report_text = str(end_report.date()) #dt.strftime('%m/%d/%Y')
    report_range_msg = 'This report generated on: ' + str(datetime.today().date()) + ' covering the previous ' + str(report_days_range) + ' days.'
    report_date_msg = 'This report generated on: ' + str(datetime.today().date())
    return today, start_report, end_report, report_date_msg, report_range_msg

def get_data_for_page(ASSETS_PATH, display_terms_file, file_url_root, report, report_suffix, mcc_list):
    ''' Take the input parameters, files and project specific functions to create base dataframes for use in the page '''
    # Load display dictionaries to turn numeric values into display values
    display_terms, display_terms_dict, display_terms_dict_multi =  load_display_terms(ASSETS_PATH, display_terms_file)

    # Load data from API
    weekly, r_status = get_subjects_data_from_file(file_url_root, report, report_suffix, mcc_list) # Switch back to this when done debugging

    # weekly, r_status = get_subjects_data_from_local_file(mcc_list) # Debugging: use local
    sweekly = add_screening_site(ASSETS_PATH, weekly, 'record_id')

    # Extract the one-to-many data from the adverse effects column nested dictionary
    adverse_events = extract_adverse_effects_data(weekly)

# -------------------------
# USE THIS SECTION TO LOAD LOCAL FILES DURING DEVELOPMENT TO AVOID 500 SERVER ERRORS
    # weekly = pd.read_csv(os.path.join(DATA_PATH,'weekly.csv'))
    # r_status='0'
    # sweekly = pd.read_csv(os.path.join(DATA_PATH,'sweekly.csv'))
    # adverse_events = pd.read_csv(os.path.join(DATA_PATH,'adverse_events.csv'))
# -------------------------

    # Clean loaded data
    clean_weekly = clean_weekly_data(weekly, display_terms_dict)
    clean_adverse = clean_adverse_events(adverse_events, display_terms_dict_multi)
    screening_data = add_screening_site(ASSETS_PATH, clean_weekly, 'record_id')

    # Get subset of consented patients, i.e. main_record_id exists
    consented = screening_data[screening_data.obtain_date.notnull()].copy()
    # Get treatment site for consented patients, using sp
    consented['treatment_site'] = consented.apply(lambda x: use_b_if_not_a(x['sp_data_site_display'], x['redcap_data_access_group_display']), axis=1)

    # Get list of centers to use in the system
    # screening centers
    screening_centers_list = clean_weekly.redcap_data_access_group_display.unique()
    screening_centers_df = pd.DataFrame(screening_centers_list, columns = ['redcap_data_access_group_display'])
    # treatment centers
    centers_list = clean_weekly.redcap_data_access_group_display.unique()
    centers_df = pd.DataFrame(centers_list, columns = ['treatment_site'])

    return display_terms, display_terms_dict, display_terms_dict_multi, clean_weekly, consented, screening_data, clean_adverse, centers_df, r_status


# ----------------------------------------------------------------------------
# Screening Tables
# ----------------------------------------------------------------------------
def get_table_1_screening(df):
    try:
       # Define needed columns for this table and select subset from main dataframe
        t1_cols = ['screening_site','participation_interest_display','record_id']
        t1 = df[t1_cols]

        # drop missing data rows
        t1 = t1.dropna()

        # group by center and participation interest value and count number of IDs in each group
        t1 = t1.groupby(by=["screening_site",'participation_interest_display']).count()

        # Reset data frame index to get dataframe in standard form with center, participation interest flag, count
        t1 = t1.reset_index()

        # Pivot participation interest values into separate columns
        t1 = t1.pivot(index=['screening_site'], columns='participation_interest_display', values='record_id')

        # Reset Index so center is a column
        t1 = t1.reset_index()

        # remove index name
        t1.columns.name = None

        # Create Summary row ('All Sites') and Summary column ('All Participants')
        t1_sum = t1
        t1_sum.loc['All Sites']= t1_sum.sum(numeric_only=True, axis=0)
        t1_sum.loc[:,'All Participants'] = t1_sum.sum(numeric_only=True, axis=1)

        # Rename and reorder columns for display
        t1_sum = t1_sum.rename(columns = {'screening_site':'Screening Site'})
        cols_display_order = ['Screening Site', 'All Participants', 'Yes', 'Maybe', 'No']
        t1_sum = t1_sum[cols_display_order]

        return t1_sum
    except Exception as e:
        traceback.print_exc()

        return None

def get_table_2a_screening(df, display_terms_t2a):
    # Get decline columns from dataframe where participant was not interested (participation_interest == 0)
    t2_cols = ['record_id','screening_site','reason_not_interested', 'ptinterest_comment'] # cols to select
    t2 = df[df.participation_interest == 0][t2_cols]

    # group data by center and count the # of main_record_ids
    t2_site_count = pd.DataFrame(t2.groupby('screening_site')['record_id'].size())

    # rename aggregate column
    t2_site_count.columns = ['Total Declined']

    # reset table index to turn center from index --> column
    t2_site_count = t2_site_count.reset_index()

    # The reason_not_interested column is one-to-many so can contain a comma separated string of multiple values.
    # Use the explode function to give each value its own row in the dataframe and drop rows with missing values
    t2_reasons = t2.assign(reason_not_interested=t2['reason_not_interested'].str.split('|')).explode('reason_not_interested')
    t2_reasons = t2_reasons.fillna(-1)

    # Convert reasons column to numeric and merge with display terms dictionary
    t2_reasons = t2_reasons.apply(pd.to_numeric, errors='ignore')

    # Group the data by center and count number of entries by reason value
    t2_reasons = pd.DataFrame(t2_reasons.groupby(['screening_site','reason_not_interested']).size())
    t2_reasons.columns=['count']
    t2_reasons = t2_reasons.reset_index()

    # pivot table so the reasons are converted from values in a column to individual columns
    t2_reasons = t2_reasons.pivot(index=['screening_site'],columns=['reason_not_interested'], values = 'count')

    # Create dictionary from display terms dict to rename columns from int values
    reason_display_dict = display_terms_t2a.set_index('reason_not_interested').to_dict()['reason_not_interested_display']

    # Rename according to dictionary
    t2_reasons = t2_reasons.rename(columns = reason_display_dict)

    # Merge the reasons with the data on the total count of declines by center
    # Note: the reasons may add up to < than total declined because the data entry allowed for NA. also possible more because
    # patients could select more than one reason.
    t2_site_count_detailed = t2_site_count.merge(t2_reasons, on='screening_site')
    t2_site_count_detailed = t2_site_count_detailed.rename(columns = {'screening_site':'Screening Site'})

    # Fill missing data with 0 and sum across all sites
    t2_site_count_detailed = t2_site_count_detailed.fillna(0)
    t2_site_count_detailed.loc['All Sites']= t2_site_count_detailed.sum(numeric_only=True, axis=0)

    return t2_site_count_detailed

def get_table_2b_screening(df, start_report, end_report):
    # Each decline includes a comment field - show these for the period of the report (previous 7 days)
    decline_comments = df[df.participation_interest == 0][['screening_site','date_of_contact','ptinterest_comment']].dropna()

    # Show Comments during reporting period
    decline_comments = decline_comments[(decline_comments.date_of_contact > start_report) & (decline_comments.date_of_contact <= end_report)]

    # Rename and reorder columns for display
    decline_comments = decline_comments.rename(columns = {'screening_site':'Screening Site','ptinterest_comment':'Reason' })
    cols_display_order = ['Screening Site', 'Reason']
    decline_comments = decline_comments[cols_display_order]

    return decline_comments

def get_table_3_screening(df,end_report_date = datetime.now(), days_range = 30):
    t3 = df
    # Get eligible patients using sp field logic
#    eligible_cols = ['sp_inclcomply', 'sp_inclage1884' , 'sp_inclsurg','sp_exclarthkneerep','sp_exclinfdxjoint','sp_exclnoreadspkenglish','sp_mricompatscr' ]
#     eligible = (t3.sp_inclcomply ==1) & (t3.sp_inclage1884 ==1) & (t3.sp_inclsurg ==1) & (t3.sp_exclarthkneerep ==0) & (t3.sp_exclinfdxjoint ==0) & (t3.sp_exclnoreadspkenglish ==0) & (t3.sp_mricompatscr ==4)
# Update logic to reflect addition of back patients at MCC2s who use different columns to assess
    eligible_short = (t3.sp_inclcomply ==1) & (t3.sp_inclage1884 ==1) & (t3.sp_inclsurg ==1) & (t3.sp_exclnoreadspkenglish ==0) & (t3.sp_mricompatscr ==4)
    eligible_knee = (t3.mcc == 1) & (t3.sp_exclarthkneerep ==0) & (t3.sp_exclinfdxjoint ==0)
    eligible_back = (t3.mcc == 2) & (t3.sp_exclothmajorsurg ==0) & (t3.sp_exclprevbilthorpro ==0)
    t3['eligible'] = (eligible_short & eligible_knee) | (eligible_short & eligible_back)

    # Get conset within last days range days
    within_days_range = ((end_report_date - t3.obtain_date).dt.days) <= days_range
    t3['within_range'] = within_days_range

    # Aggregate data for table 3
    # Set the columns to groupby, and the the columns to role up with desired aggregating functions
    # Note: can supply a list of aggregate functions to one columnm i.e. 'col_name': ['min','max']
    cols_for_groupby = ["screening_site"]
    aggregate_columns_dict={'main_record_id':'count',
                            'obtain_date':'max',
                             'eligible':'sum',
                             'ewdateterm':'count',
                           'within_range':'sum'}
    cols = cols_for_groupby + list(aggregate_columns_dict.keys())
    t3_aggregate = t3[cols].groupby(by=cols_for_groupby).agg(aggregate_columns_dict)

    # Reset Index
    t3_aggregate = t3_aggregate.reset_index()

    # Calculate the number of days since the last consent
    t3_aggregate['days_since_consent'] = (end_report_date.date() - t3_aggregate['obtain_date'].dt.date).astype(str)

    # Calculate # of ineligible from total - eligible
    t3_aggregate['ineligible'] = t3_aggregate['main_record_id'] - t3_aggregate['eligible']


    # Rename and reorder columns for display
    consent_range_col_name = 'Consents in last ' + str(days_range) +' Days'
    rename_dict = {'screening_site':'Screening Site',
                    'main_record_id':'Consented',
                    'days_since_consent':'Days Since Last Consent',
                    'within_range':consent_range_col_name,
                   'eligible':'Total Eligible',
                   'ineligible':'Total ineligible',
                   'ewdateterm': 'Total Rescinded'
                  }
    t3_aggregate = t3_aggregate.rename(columns = rename_dict)
    cols_display_order = ['Screening Site', 'Consented', 'Days Since Last Consent',consent_range_col_name,
                          'Total Eligible', 'Total ineligible',  'Total Rescinded'
       ]
    t3_aggregate = t3_aggregate[cols_display_order]

    # Add aggregate sum row
    t3_aggregate.loc['All']= t3_aggregate.sum(numeric_only=True, axis=0)
    t3_aggregate.loc['All','Screening Site'] = 'All Sites'
    t3_aggregate.fillna("", inplace=True)

    return t3, t3_aggregate


# ----------------------------------------------------------------------------
# Study Status Tables
# ----------------------------------------------------------------------------
def get_table_4(centers, consented_patients, compare_date = datetime.now()):
    # select table4 columns for patients with a main record id
    table4_cols = ["main_record_id", "treatment_site", "start_v1_preop","sp_surg_date",
                   "start_v2_6wk","start_v3_3mo","start_6mo","start_12mo", 'ewdateterm']
    table4 = consented_patients[table4_cols]

    # Sort by record ID
    table4 = table4.sort_values(by=['main_record_id'])

    # Flag patients with complete surgeries
    table4['sp_surg_date'] = table4['sp_surg_date'].apply(pd.to_datetime)
    table4['surg_complete'] = table4['sp_surg_date'] < compare_date

    # Convert Rescinded to boolean
    table4['ewdateterm'] = table4['ewdateterm'].notnull()

    # Aggregate table 4
    agg_dict = {'main_record_id':'size',
                'start_v1_preop':'sum','surg_complete':'sum','start_v2_6wk': 'sum',
                'start_v3_3mo': 'sum', 'start_6mo': 'sum', 'start_12mo': 'sum','ewdateterm': 'sum',}
    table4_agg = table4.groupby('treatment_site').agg(agg_dict).reset_index()

    # Merge Centers list with aggregated data
    table4_agg = centers.merge(table4_agg, how='outer', on = 'treatment_site')

    # fill na with 0
    table4_agg.fillna(0, inplace=True)

    # treat numeric columns as ints
    int_cols = table4_agg.columns.drop('treatment_site')
    table4_agg[int_cols] = table4_agg[int_cols].astype(int)

    # Rename columns
    rename_cols_dict = {'treatment_site':'Center',
                        'main_record_id': 'Consented',
                        'start_v1_preop': 'Baseline',
                        'surg_complete': 'Surgery Complete',
                        'start_v2_6wk':'6 week',
                        'start_v3_3mo': '3 Month',
                        'start_6mo':'6 Month',
                        'start_12mo':'12 Month',
                        'ewdateterm':'Resc./Early Term.'}
    table4_agg.rename(columns=rename_cols_dict, inplace = True)

    table4_agg.loc['All']= table4_agg.sum(numeric_only=True, axis=0)
    table4_agg.loc['All','Center'] = 'All Sites'
    table4_agg.fillna("", inplace=True)

    return table4_agg

def get_tables_5_6(df):
    # Get patients who rescinded consent, i.e. have a value in the 'ewdateterm' column
    rescinded = df.dropna(subset=['ewdateterm'])
    rescinded_cols = ['treatment_site','main_record_id','obtain_date','sp_surg_date','ewdateterm','ewprimaryreason_display','ewcomments']
    rescinded = rescinded[rescinded_cols]

    # Display main record id as int
    rescinded.main_record_id = rescinded.main_record_id.astype('int32')

    # convert datetime columns to just date
    for date_col in ['obtain_date','ewdateterm','sp_surg_date']:
        rescinded[date_col] = rescinded[date_col].dt.date

    # TO DO: need to convert reasons to text reasons
    # Rename columns to user friendly versions
    rescinded.columns =['Center Name', 'Record ID', 'Consent Date','Surgery Date',
       'Early Termination Date', 'Reason', 'Comments']

    # rescinded['pre-surgery'] = np.where(rescinded['Early Termination Date'] < rescinded['Surgery Date'], 'Active', 'Inactive')
    rescinded['pre-surgery'] = np.where(rescinded['Surgery Date'].isna(), True, (np.where(rescinded['Early Termination Date'] < rescinded['Surgery Date'], True, False)))

    rescinded_pre_surgery = rescinded[rescinded['pre-surgery']].drop(['Surgery Date','pre-surgery'],axis=1)
    if len(rescinded_pre_surgery) == 0:
            rescinded_pre_surgery = pd.DataFrame(columns=['No Patients meet these criteria'])

    rescinded_post_surgery = rescinded[~rescinded['pre-surgery']].drop(['pre-surgery'],axis=1)
    if len(rescinded_post_surgery) == 0:
            rescinded_post_surgery = pd.DataFrame(columns=['No Patients meet these criteria'])

    return rescinded_pre_surgery, rescinded_post_surgery


# ----------------------------------------------------------------------------
# Deviation & Adverse Event Tables
# ----------------------------------------------------------------------------
def get_deviation_records(weekly, adverse_events):
    # Set which columns to select
    deviations_cols = ['record_id','main_record_id', 'mcc', 'instance','erep_local_dtime',
           'erep_protdev_type','erep_protdev_type_display','erep_protdev_desc',
           'erep_protdev_caplan']

    # Get Data on Protocol deviations separate from adverse events
    deviations = adverse_events[adverse_events.erep_protdev_type.notnull()][deviations_cols]

    # Merge deviations with center info
    deviations = deviations.merge(weekly[['treatment_site','main_record_id','mcc','start_v1_preop']], how='left', on = ['main_record_id','mcc'])

    return deviations


def get_deviations_by_center(centers, df, deviations, display_terms_dict):
    dev_cols = ['main_record_id','treatment_site','start_v1_preop']
    baseline = df[df['start_v1_preop']==1][dev_cols]
    baseline = baseline.reset_index()

    # Count consented patients who have had baseline visits
    centers_baseline = baseline[['treatment_site','main_record_id']].groupby(['treatment_site']).size().reset_index(name='baseline')

    # Count patients who have an associated deviation
    records_with_deviation = deviations.main_record_id.unique()
    baseline_with_dev = baseline[baseline.main_record_id.isin(records_with_deviation)]
    centers_baseline_dev = baseline_with_dev[['treatment_site','main_record_id']].groupby(['treatment_site']).size().reset_index(name='patients_with_deviation')

    # Add count of all deviations for a given center
    center_count = pd.DataFrame(deviations.value_counts(subset=['treatment_site'])).reset_index()
    center_count.columns =['treatment_site','total_dev']

    # Get Deviation Pivot by center
    centers_dev = centers.merge(display_terms_dict['erep_protdev_type'], how='cross')
    dev_by_center = deviations[['main_record_id','erep_protdev_type_display', 'instance','treatment_site']]
    dev_by_center = dev_by_center.groupby(by=['treatment_site','erep_protdev_type_display'],as_index=False).size()
    centers_dev = centers_dev.merge(dev_by_center, how='outer', on=['treatment_site','erep_protdev_type_display']).fillna(0)
    dev_by_center_pivot =  pd.pivot_table(centers_dev, index=["treatment_site"], columns=["erep_protdev_type_display"], values=["size"])
    dev_by_center_pivot.columns = dev_by_center_pivot.columns.droplevel()
    dev_by_center_pivot.columns.name = ''
    dev_by_center_pivot = dev_by_center_pivot.reset_index()

    # Merge data frames together
    centers_all = centers
    df_to_merge = [centers_baseline, centers_baseline_dev, center_count, dev_by_center_pivot]
    for df in df_to_merge:
        centers_all = centers_all.merge(df, how='left', on = 'treatment_site')

    # Fill na with 0
    centers_all = centers_all.fillna(0)

    # treat numeric columns as ints
    int_cols = centers_all.columns.drop('treatment_site')
    centers_all[int_cols] = centers_all[int_cols].astype(int)

    # Add summary row
    centers_all.loc['All']= centers_all.sum(numeric_only=True, axis=0)
    centers_all.loc['All','treatment_site'] = 'All Sites'

    # Calculate % with deviations
    centers_all['percent_baseline_with_dev'] = 100 * (centers_all['patients_with_deviation'] / centers_all['baseline'])
    centers_all['percent_baseline_with_dev'] = centers_all['percent_baseline_with_dev'].map('{:,.2f}'.format)
    centers_all['percent_baseline_with_dev'] = centers_all['percent_baseline_with_dev'].replace('nan','-')

    # Reorder for display
    cols = list(centers_all.columns)
    col_order = cols[0:3] + cols[-1:] + cols[3:-1]
    centers_all = centers_all[col_order]

    # Rename columns
    rename_dict = {'treatment_site': ('', 'Center Name'),
                     'baseline': ('Subjects', 'Baseline'),
                     'patients_with_deviation': ('Subjects', '# With 1+ Deviations'),
                     'percent_baseline_with_dev': ('Subjects', '% Baseline with Deviation'),
                     'total_dev': ('Deviations', 'Total # of Dev.'),
                     'Blood Draw': ('Deviations', 'Blood Draw'),
                     'Functional Testing': ('Deviations', 'Functional Testing'),
                     'Imaging': ('Deviations', 'Imaging  '),
                     'Informed Consent': ('Deviations', 'Informed Consent'),
                     'Other': ('Deviations', 'Other'),
                     'QST': ('Deviations', 'QST'),
                     'Visit Timeline': ('Deviations', 'Visit Timeline')}
    centers_all.rename(columns=rename_dict, inplace=True)

    # Convert columns to MultiIndex **FOR NOW DROP LEVEL BECAUSE OF WEIRD DISPLAY
    centers_all.columns = pd.MultiIndex.from_tuples(centers_all.columns)

    return centers_all

def get_table7b_timelimited(deviations,end_report_date = datetime.now(), days_range = 7):
    # Get deviations within last days range days
    within_days_range = ((end_report_date - deviations.erep_local_dtime).dt.days) <= days_range
    deviations['within_range'] = within_days_range
    table7b = deviations[deviations['within_range']]

    # Sort by most recent, then record_id, then instance
    table7b = table7b.sort_values(['erep_local_dtime', 'main_record_id', 'erep_protdev_type'], ascending=[False, True, True])

    #select columns for display and rename
    table7b_cols = ['treatment_site','main_record_id', 'erep_local_dtime', 'erep_protdev_type_display',
       'erep_protdev_desc', 'erep_protdev_caplan']
    table7b_cols_new_names = ['Center Name','PID', 'Deviation Date', 'Deviation',
       'Description', 'Corrective Action']
    table7b = table7b[table7b_cols]
    table7b.columns = table7b_cols_new_names

    # Adjust cols: Record ID as int, Datetime in DD/MM/YY format
    table7b['PID'] = table7b['PID'].astype(int)
    table7b['Deviation Date'] = table7b['Deviation Date'].dt.strftime('%m/%d/%Y')

    return table7b


def get_adverse_event_records(weekly, adverse_events):
    # Set which columns to select
    adverse_event_flag_cols = ['erep_ae_yn'] # must = 1
    adverse_event_cols = ['main_record_id', 'mcc', 'instance','erep_ae_yn','erep_ae_relation', 'erep_ae_severity', 'erep_ae_serious',
            'erep_onset_date', 'erep_ae_desc', 'erep_action_taken', 'erep_outcome','erep_ae_yn_display',
       'erep_ae_severity_display', 'erep_ae_relation_display',
       'erep_ae_serious_display']

    # Get Data on adverse events separate from Protocol deviations
    ae = adverse_events[adverse_events.erep_ae_yn==1][adverse_event_cols]

    # Merge adverse events with center info
    ae = ae.merge(weekly[['treatment_site','main_record_id','mcc','sp_surg_date']], how='left', on = ['main_record_id','mcc'])

    return ae

def get_adverse_events_by_center(centers, df, adverse_events, display_terms_mapping):
    # Select subset of patients who have had baseline visits (start_v1_preop not null), using record_id as unique identifier
    baseline_cols = ['main_record_id','treatment_site','start_v1_preop']
    baseline = df[df['start_v1_preop']==1][baseline_cols]
    baseline = baseline.reset_index()

    # Count consented patients who have had baseline visits
    centers_baseline = baseline[['treatment_site','main_record_id']].groupby(['treatment_site']).size().reset_index(name='patients_baseline')

    # Count patients who have an adverse events
    records_with_adverse_events = adverse_events.main_record_id.unique()
    baseline_with_ae = baseline[baseline.main_record_id.isin(records_with_adverse_events)]
    centers_baseline_ae = baseline_with_ae[['treatment_site','main_record_id']].groupby(['treatment_site']).size().reset_index(name='patients_with_ae')

    # Add count of all adverse events for a given center
    center_count_ae = pd.DataFrame(adverse_events.value_counts(subset=['treatment_site'])).reset_index()
    center_count_ae.columns =['treatment_site','total_ae']

    # Merge data frames together
    centers_ae = centers
    df_to_merge = [centers_baseline, centers_baseline_ae, center_count_ae]
    for df in df_to_merge:
        centers_ae = centers_ae.merge(df, how='left', on = 'treatment_site')

    # Get data for variables at center level, pivot and merge with centers data
    ae_api_fields = ['erep_ae_severity' ,'erep_ae_relation']
    for ae_field in ae_api_fields:
        ae_field_display = ae_field +'_display'
        centers_ae_field = centers.merge(display_terms_mapping[ae_field], how='cross')
        ae_by_center = adverse_events[['main_record_id',ae_field_display, 'instance','treatment_site']]
        ae_by_center = ae_by_center.groupby(by=['treatment_site',ae_field_display],as_index=False).size()
        centers_ae_field = centers_ae_field.merge(ae_by_center, how='outer', on=['treatment_site',ae_field_display]).fillna(0)
        centers_ae_field = centers_ae_field.drop(ae_field, axis=1)
        ae_by_center_pivot =  pd.pivot_table(centers_ae_field, index=["treatment_site"], columns=[ae_field_display], values=["size"])
        ae_by_center_pivot.columns = ae_by_center_pivot.columns.droplevel()
        ae_by_center_pivot.columns.name = ''
        ae_by_center_pivot = ae_by_center_pivot.reset_index()
        centers_ae = centers_ae.merge(ae_by_center_pivot, how = 'left', on = 'treatment_site')

    # Fill na with 0
    centers_ae = centers_ae.fillna(0)

    # treat numeric columns as ints
    int_cols = centers_ae.columns.drop('treatment_site')
    centers_ae[int_cols] = centers_ae[int_cols].astype(int)

    # Calculate % with adverse events
    centers_ae['percent_baseline_with_ae'] = 100 * (centers_ae['patients_with_ae'] / centers_ae['patients_baseline'])
    centers_ae['percent_baseline_with_ae'] = centers_ae['percent_baseline_with_ae'].map('{:,.2f}'.format)
    centers_ae['percent_baseline_with_ae'] = centers_ae['percent_baseline_with_ae'].replace('0.00','-')

    # Rename and Reorder for display
    rename_cols =[('', 'Center'),
                 ('', 'Patients'),
                 ('', '# With Adverse Event'),
                 ('', '% with 1+ Adverse Events'),
                 ('Severity', 'Mild'),
                 ('Severity', 'Moderate'),
                 ('Severity', 'Severe'),
                 ('Relationship', 'Definitely Related'),
                 ('Relationship', 'Possibly/Probably Related'),
                 ('Relationship', 'Not Related'),
                 ('', '% Of Subjects with A.E.')]
    centers_ae.columns = rename_cols
    col_order = rename_cols[0:3] + rename_cols[-1:] + rename_cols[4:8] + rename_cols[9:10]  + rename_cols[8:9] + rename_cols[3:4]
    centers_ae = centers_ae[col_order]

    # Convert columns to MultiIndex
    centers_ae.columns = pd.MultiIndex.from_tuples(centers_ae.columns)

    return centers_ae

def get_table_8b(event_records, end_report, report_days = 30):
    table8b_cols_dict = {'treatment_site':'Center',
                    'main_record_id':'PID',
                    'erep_onset_date':'AE Date',
                         'sp_surg_date': 'Surgery Date',
                   'erep_ae_severity_display':'Severity',
                    'erep_ae_relation_display':'Relationship',
#                     'erep_ae_serious_display':'Serious',
                  'erep_ae_desc':'Description',
                    'erep_action_taken':'Action',
                    'erep_outcome':'Outcome'}
    table8b_cols = table8b_cols_dict.keys()
    table8b = event_records[table8b_cols].copy()

    # Limit report if report_days is not None
    if report_days:
        # Get report start date
        start_report = end_report - timedelta(days=report_days)

        # Get records that are adverse envet records in the time frame of report
        table8b = table8b[(table8b.erep_onset_date > start_report) &  (table8b.erep_onset_date <= end_report)]

    # convert datetime column to show date
    table8b.erep_onset_date = table8b.erep_onset_date.dt.strftime('%m/%d/%Y')

    # Use col dict to rename cols for display
    table8b = table8b.rename(columns=table8b_cols_dict)

    if len(table8b) <1 :
        return pd.DataFrame(columns = ['No Adverse Events in the reporting timeframe'])
    else:
        table8b = table8b.sort_values(by=['AE Date'], ascending=False)


    return table8b
# ----------------------------------------------------------------------------
# Demographics Tables
# ----------------------------------------------------------------------------
def get_demographic_data(df):
    id_cols = ['record_id','mcc','treatment_site', 'ewdateterm']
    demo_cols = ['age', 'dem_race_display', 'ethnic_display',  'sex_display']
    screening_cols = ['screening_age', 'screening_race_display', 'screening_ethnicity_display', 'screening_gender_display']
    demo= df[id_cols + demo_cols + screening_cols].copy()

    # Fill in data from screening where missing
    # demo_ethnic['ethnicity'] = np.where(demo_ethnic['ethnic_description'].isnull(), demo_ethnic['screening_ethnicity_description'], demo_ethnic['ethnic_description'])
    mapping_dict = { 'age':'screening_age',
                    'dem_race_display': 'screening_race_display',
                    'ethnic_display': 'screening_ethnicity_display',
                     'sex_display':'screening_gender_display'}

    # 1) replace values with screening data if missing
    mapped_cols = []
    for key in mapping_dict.keys():
        mapped_col = key + '_merge'
        mapped_cols = mapped_cols + [mapped_col]
        demo[mapped_col] = np.where(demo[key].isnull(), demo[mapping_dict[key]], demo[key])

    # 2) select subset of columns
    demo = demo[id_cols + mapped_cols]

    # 3) Fill na with 'Unknown'
    demo = demo.fillna('Unknown')

    # 4) use Termination date column to map status as active or inactive
    demo['Status'] = np.where(demo.ewdateterm == 'Unknown', 'Active', 'Inactive')

    # 5) Rename Columns
    demo.columns = ['ID', 'MCC', 'Center Name', 'Termination Date','Age', 'Race', 'Ethnicity', 'Sex', 'Status']

    return demo

def rollup_demo_data(demo_df, demo_col, display_terms_dict, display_term_key):
    df_all = pd.DataFrame(display_terms_dict[display_term_key][display_term_key + '_display'])
    df_all.columns = [demo_col]
    counts = pd.DataFrame(demo_df[demo_col].value_counts()).reset_index()
    normal = pd.DataFrame(demo_df[demo_col].value_counts(normalize=True)).reset_index()
    merged = counts.merge(normal, on='index')
    merged.columns = [demo_col,'Count','Percent']
    df_all = df_all.merge(merged, how='left', on = demo_col)
    df_all = df_all.fillna(0)
    df_all['Count'] = df_all['Count'].astype(int)
    df_all['Percent'] = df_all['Percent'].map("{:.2%}".format)
    df_all.loc['All'] = df_all.sum(numeric_only=True, axis=0)
    return df_all

def rollup_with_split_col(demo_df, demo_col, display_terms_dict, display_term_key, split_col):
    rollup = rollup_demo_data(demo_df, demo_col, display_terms_dict, display_term_key)
    rollup.columns =[demo_col,
                 'All:Count',
                 'All:Percent']
    for i in list(demo_df[split_col].unique()):
        df = demo_df[demo_df[split_col] == i]
        i_rollup = rollup_demo_data(df, demo_col, display_terms_dict, display_term_key)
        i_rollup.columns =[demo_col,
                 str(split_col) + str(i) + ':Count',
                 str(split_col) + str(i) + ':Percent']
        rollup = rollup.merge(i_rollup, how='left', on=demo_col)
    rollup.rename(columns={demo_col: ':'+demo_col}, inplace=True)
    create_multiindex(rollup, ':')
    return rollup

def get_describe_col(df, describe_col, round_rows = {2:['mean', 'std']}):
    df_describe = pd.DataFrame(df[describe_col].describe().reset_index())
    if round_rows:
        for k in round_rows.keys():
            df_describe[describe_col] = np.where((df_describe['index'].isin(round_rows[k])), df_describe[describe_col].round(k).astype(str), df_describe[describe_col])
    return df_describe

def get_describe_col_subset(df, describe_col, subset_col, round_rows = {2:['mean', 'std']}):
    df_describe = get_describe_col(df, describe_col)
    df_describe.columns = ['index',describe_col + ': All']
    for i in list(df[subset_col].unique()):
        i_df = df[df[subset_col] == i]
        i_describe = get_describe_col(i_df, describe_col)
        i_describe.columns = ['index',describe_col + ': ' + subset_col + str(i)]
        df_describe = df_describe.merge(i_describe, how='left', on='index')
    df_describe.rename(columns={"index": ":Measure"}, inplace=True)
    create_multiindex(df_describe, ':')
    return df_describe

# ----------------------------------------------------------------------------
# Enrollment FUNCTIONS
# ----------------------------------------------------------------------------
def get_enrollment_data(screening_sites,screening_data, consented):
    # Load screening sites
    screening_sites['start_date'] = pd.to_datetime(screening_sites['start_date'], errors='coerce').dt.date
    screening_sites = screening_sites[~(screening_sites.start_date.isna())]

    # get enrollment data
    enroll_cols = ['record_id','main_record_id','obtain_date', 'redcap_data_access_group_display']
    enrolled = consented[consented['ewdateterm'].isna()][enroll_cols] # Do we want to do this?
    enrolled = enrolled.merge(screening_data[['record_id','screening_site']], how='left', on='record_id')
    enrolled = enrolled.merge(screening_sites[['screening_site','start_month','start_year']], how='left', on='screening_site')
    enrolled['obtain_year'] = enrolled['obtain_date'].dt.year
    enrolled['obtain_month'] = enrolled['obtain_date'].dt.month
    enrolled['study_month'] = 12 * (enrolled['obtain_year'] - enrolled['start_year']) + enrolled['obtain_month'] - enrolled['start_month'] + 1
    enrolled['study_month'] = enrolled['study_month'].astype(int)
    enrolled['study_month']  = np.where(enrolled['study_month']  < 1, 1, enrolled['study_month'])

    #expected data
    expect = screening_sites[['screening_site','study_month','expected_enrollment']].copy()
    expect['expected_enrollment'] = expect['expected_enrollment'].str.split(', ')
    expect['study_month'] = expect['study_month'].str.split(', ')
    expected = expect.apply(pd.Series.explode).reset_index(drop=True)
    expected.dropna(inplace=True)
    expected['expected_enrollment'] = expected['expected_enrollment'].astype(int)
    expected_cum = expected.set_index(['screening_site','study_month']).groupby(level=0).cumsum().reset_index()
    expected_cum.columns = ['screening_site','study_month','expected_enrollment_cum']
    expected = expected.merge(expected_cum, on=['screening_site','study_month'])
    expected.rename(columns={"expected_enrollment": "Expected: Monthly", 'expected_enrollment_cum': 'Expected: Cumulative'}, inplace=True)
    expected = expected.melt(id_vars=['screening_site', 'study_month'])
    expected['study_month'] = expected['study_month'].astype(int)

    # get rolled up data
    ne = enrolled[['screening_site','study_month','record_id']].copy()
    ne = ne.groupby(['screening_site','study_month']).count()

    ne_cumsum = ne.groupby(level=0).cumsum().reset_index()
    ne_cumsum['variable'] = 'Actual: Cumulative'

    ne = ne.reset_index()
    ne['variable'] = 'Actual: Monthly'

    er = pd.concat([ne,ne_cumsum])

    er.rename(columns={"record_id": "value"}, inplace=True)

    # Combine enrollment with expected data
    enrollment = pd.concat([er,expected])

    return enrolled, enrollment

def get_site_enrollment(site, enrollment):
    df = enrollment[enrollment['screening_site'] == site]
    site_df = df.pivot_table(index=['study_month'],
                        columns=['screening_site','variable'],
                        values='value')
    site_df.columns = site_df.columns.droplevel()
    site_df.reset_index(inplace=True)
    site_df['Study Time: Year'] = site_df['study_month'].apply(lambda x: int((x-1)/12))
    site_df['Study Time: Month'] = site_df['study_month'].apply(lambda x: ((x-1) % 12) + 1)

    # Fill monthly NA with 0, cumulative with max
    site_df['Actual: Monthly'] = site_df['Actual: Monthly'].fillna(0)
    site_df['Actual: Cumulative'] = site_df['Actual: Cumulative'].fillna(site_df['Actual: Cumulative'].max())

    site_df['Percent: Monthly'] = (100 * site_df['Actual: Monthly'] / site_df['Expected: Monthly']).round(1).astype(str) + '%'
    site_df['Percent: Cumulative'] = (100 * site_df['Actual: Cumulative'] / site_df['Expected: Cumulative']).round(1).astype(str) + '%'
    site_df.loc[site_df['Actual: Monthly'] == 0, 'Percent: Monthly'] = ''

    col_order = [ 'study_month', 'Study Time: Year', 'Study Time: Month',
                 'Expected: Monthly', 'Expected: Cumulative',
                 'Actual: Monthly', 'Actual: Cumulative',
                 'Percent: Monthly', 'Percent: Cumulative'
           ]
    site_df = site_df[col_order]
    return site_df


# ----------------------------------------------------------------------------
# GET DATA FOR PAGE
# ----------------------------------------------------------------------------

def get_tables(today, start_report, end_report, report_date_msg, report_range_msg, display_terms, display_terms_dict, display_terms_dict_multi, clean_weekly, consented, screening_data, clean_adverse, centers_df):
    ''' Load all the data for the page'''
    ## SCREENING TABLES
    table1 = get_table_1_screening(screening_data)

    display_terms_t2a = display_terms_dict_multi['reason_not_interested']
    table2a = get_table_2a_screening(screening_data, display_terms_t2a)

    table2b = get_table_2b_screening(screening_data, start_report, end_report)

    table3_data, table3 = get_table_3_screening(consented, today, 30)

    ## STUDY Status
    table4 = get_table_4(centers_df, consented, today)

    table5, table6 = get_tables_5_6(consented)

    ## Deviations
    deviations = get_deviation_records(consented, clean_adverse)
    table7a = get_deviations_by_center(centers_df, consented, deviations, display_terms_dict_multi)
    table7b = get_table7b_timelimited(deviations)

    ## Adverse Events
    ae = get_adverse_event_records(consented, clean_adverse)
    table8a = get_adverse_events_by_center(centers_df, consented, ae, display_terms_dict_multi)
    table8b = get_table_8b(ae, today, None)

    ## Demographics
    demographics = get_demographic_data(consented)
    # get subset of active patients
    demo_active = demographics[demographics['Status']=='Active']

    # Currently splitting on MCC values
    split_col = 'MCC'

    # SEX
    demo_df, demo_col, display_terms_dict, display_term_key = demo_active, 'Sex', display_terms_dict, 'sex'
    sex = rollup_with_split_col(demo_df, demo_col, display_terms_dict, display_term_key, split_col)

    # RACE
    demo_df, demo_col, display_terms_dict, display_term_key = demo_active, 'Race', display_terms_dict, 'dem_race'
    race = rollup_with_split_col(demo_df, demo_col, display_terms_dict, display_term_key, split_col)

    # ETHNICITY
    demo_df, demo_col, display_terms_dict, display_term_key = demo_active, 'Ethnicity', display_terms_dict, 'ethnic'
    ethnicity = rollup_with_split_col(demo_df, demo_col, display_terms_dict, display_term_key, split_col)

    # AGE
    # Drop na
    age_df = demo_active.copy()
    age_df["Age"] = pd.to_numeric(age_df["Age"], errors='coerce') # handle records that have no age value anywhere
    age = get_describe_col_subset(age_df, 'Age', 'MCC')


    return table1, table2a, table2b, table3, table4, table5, table6, table7a, table7b, table8a, table8b, sex, race, ethnicity, age
