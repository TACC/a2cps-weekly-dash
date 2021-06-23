  # Libraries
# Data
# File Management
import os # Operating system library
import pathlib # file paths
import json
import requests
import math
import numpy as np
import pandas as pd # Dataframe manipulations
import datetime
from datetime import datetime, timedelta

# ----------------------------------------------------------------------------
# MAIN DATA Loading and Prep
# ----------------------------------------------------------------------------
# Display Dictionary
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
        print(e)
        return None

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
        print(e)
        return None


# path to Data APIs and reference files / load data
# Weekly Data from csv
def load_weekly_data(weekly_csv, display_terms_dict):
    try:
        df = pd.read_csv(weekly_csv)
        df = df.apply(pd.to_numeric, errors='ignore')

        # convert date columns from object --> datetime datatypes as appropriate
        datetime_cols_list = ['date_of_contact','date_and_time','obtain_date','ewdateterm'] #erep_local_dtime also dates, but currently an array
        df[datetime_cols_list] = df[datetime_cols_list].apply(pd.to_datetime)
        for i in display_terms_dict.keys():
            if i in df.columns:
                df = df.merge(display_terms_dict[i], how='left', on=i)
        # Get subset of consented patients
        # get data subset of just consented patients
        consented = df[df.record_id.notnull()].copy()
        return df, consented
    except Exception as e:
        print(e)
        return None, None

# Load data from API for One-to-Many data points per record ID
def get_multi_row_data(json_api_url):
    ''' Take the adverse effects JSON and convert into a data frame for analysis.

        API returns data in the format [{record_id:
                                            {instance:
                                                {field:value}
                                            }
                                        }] '''

    df = pd.DataFrame() # create empty dataframe
    try:
        multi_dict = requests.get(json_api_url).json()
        for i in multi_dict:
            for key in i.keys():
                df_key = pd.DataFrame.from_dict(i[key], orient='index') #.reset_index()
                seq = [key] * len(df_key)
                df_key = df_key.reindex(['record_id', *df_key.columns], axis=1).assign(record_id= seq)
                df = pd.concat([df, df_key], axis = 0)
        df = df.reset_index()
        df = df.rename(columns={'index': 'instance'})
        return df
    except Exception as e:
        print(e)
        return None

def load_multi_data(multi_row_json, display_terms_dict_multi):
    try:
        # Load data and coerce to numeric
        multi_data = get_multi_row_data(multi_row_json)
        multi_data = multi_data.apply(pd.to_numeric, errors='ignore')

        # convert date columns from object --> datetime datatypes as appropriate
        multi_datetime_cols = ['erep_local_dtime','erep_ae_date','erep_onset_date','erep_resolution_date']
        multi_data[multi_datetime_cols] = multi_data[multi_datetime_cols].apply(pd.to_datetime)

        # Convert numeric values to display values using dictionary
        for i in display_terms_dict_multi.keys():
            if i in multi_data.columns:
                multi_data = multi_data.merge(display_terms_dict_multi[i], how='left', on=i)

        return multi_data
    except Exception as e:
        print(e)
        return None

# ----------------------------------------------------------------------------
# Get dataframes and parameters
# ----------------------------------------------------------------------------

def get_data_for_page(ASSETS_PATH, display_terms_file, weekly_csv, multi_row_json):
    # Get dataframes
    display_terms, display_terms_dict, display_terms_dict_multi =  load_display_terms(ASSETS_PATH, display_terms_file)
    df, consented = load_weekly_data(weekly_csv, display_terms_dict)
    multi_data = load_multi_data(multi_row_json, display_terms_dict_multi)

    centers_list = df.redcap_data_access_group_display.unique()
    centers_df = pd.DataFrame(centers_list, columns = ['redcap_data_access_group_display'])

    return display_terms, display_terms_dict, display_terms_dict_multi, df, consented, multi_data, centers_df


def get_time_parameters(end_report, report_days_range = 7):
    today = datetime.now()
    start_report = end_report - timedelta(days=report_days_range)
    start_report_text = str(start_report.date()) #dt.strftime('%m/%d/%Y')
    end_report_text = str(end_report.date()) #dt.strftime('%m/%d/%Y')
    report_range_msg = 'This report generated on: ' + str(datetime.today().date()) + ' covering the previous ' + str(report_days_range) + ' days.'
    report_date_msg = 'This report generated on: ' + str(datetime.today().date())
    return today, start_report, end_report, report_date_msg, report_range_msg

# ----------------------------------------------------------------------------
# Screening Tables
# ----------------------------------------------------------------------------
def get_table_1(df):
    try:
       # Define needed columns for this table and select subset from main dataframe
        t1_cols = ['redcap_data_access_group_display','participation_interest_display','screening_id']
        t1 = df[t1_cols]

        # drop missing data rows
        t1 = t1.dropna()

        # group by center and participation interest value and count number of IDs in each group
        t1 = t1.groupby(by=["redcap_data_access_group_display",'participation_interest_display']).count()

        # Reset data frame index to get dataframe in standard form with center, participation interest flag, count
        t1 = t1.reset_index()

        # Pivot participation interest values into separate columns
        t1 = t1.pivot(index=['redcap_data_access_group_display'], columns='participation_interest_display', values='screening_id')

        # Reset Index so center is a column
        t1 = t1.reset_index()

        # remove index name
        t1.columns.name = None

        # Create Summary row ('All Sites') and Summary column ('All Participants')
        t1_sum = t1
        t1_sum.loc['All Sites']= t1_sum.sum(numeric_only=True, axis=0)
        t1_sum.loc[:,'All Participants'] = t1_sum.sum(numeric_only=True, axis=1)

        # Rename and reorder columns for display
        t1_sum = t1_sum.rename(columns = {'redcap_data_access_group_display':'Center Name'})
        cols_display_order = ['Center Name', 'All Participants', 'Yes', 'Maybe', 'No']
        t1_sum = t1_sum[cols_display_order]

        return t1_sum
    except Exception as e:
        print(e)

        return None

def get_table_2a(df, display_terms_t2a):
    # Get decline columns from dataframe where participant was not interested (participation_interest == 0)
    t2_cols = ['screening_id','redcap_data_access_group_display','reason_not_interested', 'ptinterest_comment'] # cols to select
    t2 = df[df.participation_interest == 0][t2_cols]

    # group data by center and count the # of screening_ids
    t2_site_count = pd.DataFrame(t2.groupby('redcap_data_access_group_display')['screening_id'].size())

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
    t2_reasons = pd.DataFrame(t2_reasons.groupby(['redcap_data_access_group_display','reason_not_interested']).size())
    t2_reasons.columns=['count']
    t2_reasons = t2_reasons.reset_index()

    # pivot table so the reasons are converted from values in a column to individual columns
    t2_reasons = t2_reasons.pivot(index=['redcap_data_access_group_display'],columns=['reason_not_interested'], values = 'count')

    # Create dictionary from display terms dict to rename columns from int values
    reason_display_dict = display_terms_t2a.set_index('reason_not_interested').to_dict()['reason_not_interested_display']

    # Rename according to dictionary
    t2_reasons = t2_reasons.rename(columns = reason_display_dict)

    # Merge the reasons with the data on the total count of declines by center
    # Note: the reasons may add up to < than total declined because the data entry allowed for NA. also possible more because
    # patients could select more than one reason.
    t2_site_count_detailed = t2_site_count.merge(t2_reasons, on='redcap_data_access_group_display')
    t2_site_count_detailed = t2_site_count_detailed.rename(columns = {'redcap_data_access_group_display':'Center Name'})

    # Fill missing data with 0 and sum across all sites
    t2_site_count_detailed = t2_site_count_detailed.fillna(0)
    t2_site_count_detailed.loc['All Sites']= t2_site_count_detailed.sum(numeric_only=True, axis=0)

    return t2_site_count_detailed

def get_table_2b(df, start_report, end_report):
    # Each decline includes a comment field - show these for the period of the report (previous 7 days)
    decline_comments = df[df.participation_interest == 0][['redcap_data_access_group_display','date_of_contact','ptinterest_comment']].dropna()

    # Show Comments during reporting period
    decline_comments = decline_comments[(decline_comments.date_of_contact > start_report) & (decline_comments.date_of_contact <= end_report)]

    # Rename and reorder columns for display
    decline_comments = decline_comments.rename(columns = {'redcap_data_access_group_display':'Center Name','ptinterest_comment':'Reason' })
    cols_display_order = ['Center Name', 'Reason']
    decline_comments = decline_comments[cols_display_order]

    return decline_comments

def get_table_3(df,end_report_date = datetime.now(), days_range = 30):
    t3 = df
    # Get eligible patients using sp field logic
    eligible_cols = ['sp_inclcomply', 'sp_inclage1884' , 'sp_inclsurg','sp_exclarthkneerep','sp_exclinfdxjoint','sp_exclnoreadspkenglish','sp_mricompatscr' ]
    eligible = (t3.sp_inclcomply ==1) & (t3.sp_inclage1884 ==1) & (t3.sp_inclsurg ==1) & (t3.sp_exclarthkneerep ==0) & (t3.sp_exclinfdxjoint ==0) & (t3.sp_exclnoreadspkenglish ==0) & (t3.sp_mricompatscr ==4)
    t3['eligible'] = eligible

    # Get conset within last days range days
    within_days_range = ((end_report_date - t3.obtain_date).dt.days) <= days_range
    t3['within_range'] = within_days_range

    # Aggregate data for table 3
    # Set the columns to groupby, and the the columns to role up with desired aggregating functions
    # Note: can supply a list of aggregate functions to one columnm i.e. 'col_name': ['min','max']
    cols_for_groupby = ["redcap_data_access_group_display"]
    aggregate_columns_dict={'screening_id':'count',
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
    t3_aggregate['ineligible'] = t3_aggregate['screening_id'] - t3_aggregate['eligible']


    # Rename and reorder columns for display
    consent_range_col_name = 'Consents in last ' + str(days_range) +' Days'
    rename_dict = {'redcap_data_access_group_display':'Center Name',
                    'screening_id':'Consented',
                    'days_since_consent':'Days Since Last Consent',
                    'within_range':consent_range_col_name,
                   'eligible':'Total Eligible',
                   'ineligible':'Total ineligible',
                   'ewdateterm': 'Total Rescinded'
                  }
    t3_aggregate = t3_aggregate.rename(columns = rename_dict)
    cols_display_order = ['Center Name', 'Consented', 'Days Since Last Consent',consent_range_col_name,
                          'Total Eligible', 'Total ineligible',  'Total Rescinded'
       ]
    t3_aggregate = t3_aggregate[cols_display_order]

    # Add aggregate sum row
    t3_aggregate.loc['All']= t3_aggregate.sum(numeric_only=True, axis=0)
    t3_aggregate.loc['All','Center Name'] = 'All Sites'
    t3_aggregate.fillna("", inplace=True)

    return t3, t3_aggregate


# ----------------------------------------------------------------------------
# Study Status Tables
# ----------------------------------------------------------------------------
def get_table_4(centers, consented_patients, compare_date = datetime.now()):
    # select table4 columns for patients with a record id
    table4_cols = ["record_id", "redcap_data_access_group_display", "start_v1_preop","sp_surg_date",
                   "start_v2_6wk","start_v3_3mo","start_6mo","start_12mo", 'ewdateterm']
    table4 = consented_patients[table4_cols]

    # Sort by record ID
    table4 = table4.sort_values(by=['record_id'])

    # Flag patients with complete surgeries
    table4['sp_surg_date'] = table4['sp_surg_date'].apply(pd.to_datetime)
    table4['surg_complete'] = table4['sp_surg_date'] < compare_date

    # Convert Rescinded to boolean
    table4['ewdateterm'] = table4['ewdateterm'].notnull()

    # Aggregate table 4
    agg_dict = {'record_id':'size',
                'start_v1_preop':'sum','surg_complete':'sum','start_v2_6wk': 'sum',
                'start_v3_3mo': 'sum', 'start_6mo': 'sum', 'start_12mo': 'sum','ewdateterm': 'sum',}
    table4_agg = table4.groupby('redcap_data_access_group_display').agg(agg_dict).reset_index()

    # Merge Centers list with aggregated data
    table4_agg = centers.merge(table4_agg, how='outer', on = 'redcap_data_access_group_display')

    # fill na with 0
    table4_agg.fillna(0, inplace=True)

    # treat numeric columns as ints
    int_cols = table4_agg.columns.drop('redcap_data_access_group_display')
    table4_agg[int_cols] = table4_agg[int_cols].astype(int)

    # Rename columns
    rename_cols_dict = {'redcap_data_access_group_display':'Center',
                        'record_id': 'Consented',
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
    rescinded_cols = ['redcap_data_access_group_display','record_id','date_and_time','ewdateterm','ewprimaryreason_display','ewcomments','sp_surg_date']
    rescinded = rescinded[rescinded_cols]

    # Display record id as int
    rescinded.record_id = rescinded.record_id.astype('int32')

    # convert datetime columns to just date
    for date_col in ['date_and_time','ewdateterm']:
        rescinded[date_col] = rescinded[date_col].dt.date

    # TO DO: need to convert reasons to text reasons
    # Rename columns to user friendly versions
    rescinded.columns =['Center Name', 'Record ID', 'Consent Date',
       'Early Termination Date', 'Reason', 'Comments', 'sp_surg_date']

    # Split dataset into leaving before pr after surgery
    rescinded_pre_surgery = rescinded[rescinded.sp_surg_date.isna()].drop(['sp_surg_date'],axis=1)
    if len(rescinded_pre_surgery) == 0:
            rescinded_pre_surgery = pd.DataFrame(columns=['No Patients meet these criteria'])

    rescinded_post_surgery = rescinded.dropna(subset=['sp_surg_date'])
    if len(rescinded_post_surgery) == 0:
            rescinded_post_surgery = pd.DataFrame(columns=['No Patients meet these criteria'])

    return rescinded_pre_surgery, rescinded_post_surgery

# ----------------------------------------------------------------------------
# Deviation & Adverse Event Tables
# ----------------------------------------------------------------------------
def get_deviation_records(df, multi_data, display_terms_mapping):
    # Get Data on Protocol deviations
    deviation_flag_cols = ['erep_prot_dev']
    deviations_cols = ['record_id', 'instance','erep_local_dtime',
           'erep_protdev_type', 'erep_protdev_desc',
           'erep_protdev_caplan']
    deviations = multi_data.dropna(subset=deviation_flag_cols)[deviations_cols ]

    # Merge deviations with center info
    deviations = deviations.merge(df[['redcap_data_access_group','redcap_data_access_group_display','record_id','start_v1_preop']], how='left', on = 'record_id')

    # Convert deviation type to text
    deviation_terms = display_terms_mapping['erep_protdev_type']
    deviation_terms.columns = ['erep_protdev_type','Deviation']
    deviations = deviations.merge(deviation_terms, how='left', on='erep_protdev_type')

    return deviations


def get_deviations_by_center(centers, df, deviations, display_terms_dict):
    dev_cols = ['record_id','redcap_data_access_group_display','start_v1_preop']
    baseline = df[df['start_v1_preop']==1][dev_cols]
    baseline = baseline.reset_index()

    # Count consented patients who have had baseline visits
    centers_baseline = baseline[['redcap_data_access_group_display','record_id']].groupby(['redcap_data_access_group_display']).size().reset_index(name='baseline')

    # Count patients who have an associated deviation
    records_with_deviation = deviations.record_id.unique()
    baseline_with_dev = baseline[baseline.record_id.isin(records_with_deviation)]
    centers_baseline_dev = baseline_with_dev[['redcap_data_access_group_display','record_id']].groupby(['redcap_data_access_group_display']).size().reset_index(name='patients_with_deviation')

    # Add count of all deviations for a given center
    center_count = pd.DataFrame(deviations.value_counts(subset=['redcap_data_access_group_display'])).reset_index()
    center_count.columns =['redcap_data_access_group_display','total_dev']

    # Get Deviation Pivot by center
    centers_dev = centers.merge(display_terms_dict['erep_protdev_type'], how='cross')
    dev_by_center = deviations[['record_id','Deviation', 'instance','redcap_data_access_group_display']]
    dev_by_center = dev_by_center.groupby(by=['redcap_data_access_group_display','Deviation'],as_index=False).size()
    centers_dev = centers_dev.merge(dev_by_center, how='outer', on=['redcap_data_access_group_display','Deviation']).fillna(0)
    dev_by_center_pivot =  pd.pivot_table(centers_dev, index=["redcap_data_access_group_display"], columns=["Deviation"], values=["size"])
    dev_by_center_pivot.columns = dev_by_center_pivot.columns.droplevel()
    dev_by_center_pivot.columns.name = ''
    dev_by_center_pivot = dev_by_center_pivot.reset_index()

    # Merge data frames together
    centers_all = centers
    df_to_merge = [centers_baseline, centers_baseline_dev, center_count, dev_by_center_pivot]
    for df in df_to_merge:
        centers_all = centers_all.merge(df, how='left', on = 'redcap_data_access_group_display')

    # Fill na with 0
    centers_all = centers_all.fillna(0)

    # treat numeric columns as ints
    int_cols = centers_all.columns.drop('redcap_data_access_group_display')
    centers_all[int_cols] = centers_all[int_cols].astype(int)

    # Add summary row
    centers_all.loc['All']= centers_all.sum(numeric_only=True, axis=0)
    centers_all.loc['All','redcap_data_access_group_display'] = 'All Sites'

    # Calculate % with deviations
    centers_all['percent_baseline_with_dev'] = 100 * (centers_all['patients_with_deviation'] / centers_all['baseline'])
    centers_all['percent_baseline_with_dev'] = centers_all['percent_baseline_with_dev'].map('{:,.2f}'.format)
    centers_all['percent_baseline_with_dev'] = centers_all['percent_baseline_with_dev'].replace('nan','-')

    # Reorder for display
    cols = list(centers_all.columns)
    col_order = cols[0:3] + cols[-1:] + cols[3:-1]
    centers_all = centers_all[col_order]

    # Rename columns
    rename_dict = {'redcap_data_access_group_display': ('', 'Center Name'),
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
    table7b = table7b.sort_values(['erep_local_dtime', 'record_id', 'erep_protdev_type'], ascending=[False, True, True])

    #select columns for display and rename
    table7b_cols = ['redcap_data_access_group_display','record_id', 'erep_local_dtime', 'Deviation',
       'erep_protdev_desc', 'erep_protdev_caplan']
    table7b_cols_new_names = ['Center Name','PID', 'Deviation Date', 'Deviation',
       'Description', 'Corrective Action']
    table7b = table7b[table7b_cols]
    table7b.columns = table7b_cols_new_names

    # Adjust cols: Record ID as int, Datetime in DD/MM/YY format
    table7b['PID'] = table7b['PID'].astype(int)
    table7b['Deviation Date'] = table7b['Deviation Date'].dt.strftime('%m/%d/%Y')

    return table7b

def get_adverse_event_records(df, multi_data, display_terms_dict_multi):
    # Get Data on Adverse Events
    adverse_event_cols = ['record_id', 'instance','erep_ae_yn','erep_ae_relation', 'erep_ae_severity', 'erep_ae_serious',
            'erep_onset_date', 'erep_ae_desc', 'erep_action_taken', 'erep_outcome']
    adverse_events = multi_data[multi_data.erep_ae_yn==1][adverse_event_cols]

    # Merge adverse events with center info
    adverse_events = adverse_events.merge(df[['redcap_data_access_group_display','record_id']], how='left', on = 'record_id')
    for num_col in ['erep_ae_yn', 'erep_ae_severity', 'erep_ae_relation', 'erep_ae_serious']:
        adverse_events = adverse_events.merge(display_terms_dict_multi[num_col], how='left', on=num_col)

    return adverse_events

def get_adverse_events_by_center(centers, df, adverse_events, display_terms_mapping):
    # Select subset of patients who have had baseline visits (start_v1_preop not null), using record_id as unique identifier
    baseline_cols = ['record_id','redcap_data_access_group_display','start_v1_preop']
    baseline = df[df['start_v1_preop']==1][baseline_cols]
    baseline = baseline.reset_index()

    # Count consented patients who have had baseline visits
    centers_baseline = baseline[['redcap_data_access_group_display','record_id']].groupby(['redcap_data_access_group_display']).size().reset_index(name='patients_baseline')

    # Count patients who have an adverse events
    records_with_adverse_events = adverse_events.record_id.unique()
    baseline_with_ae = baseline[baseline.record_id.isin(records_with_adverse_events)]
    centers_baseline_ae = baseline_with_ae[['redcap_data_access_group_display','record_id']].groupby(['redcap_data_access_group_display']).size().reset_index(name='patients_with_ae')

    # Add count of all adverse events for a given center
    center_count_ae = pd.DataFrame(adverse_events.value_counts(subset=['redcap_data_access_group_display'])).reset_index()
    center_count_ae.columns =['redcap_data_access_group_display','total_ae']

    # Merge data frames together
    centers_ae = centers
    df_to_merge = [centers_baseline, centers_baseline_ae, center_count_ae]
    for df in df_to_merge:
        centers_ae = centers_ae.merge(df, how='left', on = 'redcap_data_access_group_display')

    # Get data for variables at center level, pivot and merge with centers data
    ae_api_fields = ['erep_ae_severity' ,'erep_ae_relation']
    for ae_field in ae_api_fields:
        ae_field_display = ae_field +'_display'
        centers_ae_field = centers.merge(display_terms_mapping[ae_field], how='cross')
        ae_by_center = adverse_events[['record_id',ae_field_display, 'instance','redcap_data_access_group_display']]
        ae_by_center = ae_by_center.groupby(by=['redcap_data_access_group_display',ae_field_display],as_index=False).size()
        centers_ae_field = centers_ae_field.merge(ae_by_center, how='outer', on=['redcap_data_access_group_display',ae_field_display]).fillna(0)
        centers_ae_field = centers_ae_field.drop(ae_field, axis=1)
        ae_by_center_pivot =  pd.pivot_table(centers_ae_field, index=["redcap_data_access_group_display"], columns=[ae_field_display], values=["size"])
        ae_by_center_pivot.columns = ae_by_center_pivot.columns.droplevel()
        ae_by_center_pivot.columns.name = ''
        ae_by_center_pivot = ae_by_center_pivot.reset_index()
        centers_ae = centers_ae.merge(ae_by_center_pivot, how = 'left', on = 'redcap_data_access_group_display')

    # Fill na with 0
    centers_ae = centers_ae.fillna(0)

    # treat numeric columns as ints
    int_cols = centers_ae.columns.drop('redcap_data_access_group_display')
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

def get_table_8b(event_records, end_report, report_days = 7):
    table8b_cols_dict = {'redcap_data_access_group_display':'Center',
                    'record_id':'PID',
                    'erep_onset_date':'AE Date',
                   'erep_ae_severity_display':'Severity',
                    'erep_ae_relation_display':'Relationship',
#                     'erep_ae_serious_display':'Serious',
                  'erep_ae_desc':'Description',
                    'erep_action_taken':'Action',
                    'erep_outcome':'Outcome'}
    table8b_cols = table8b_cols_dict.keys()

    # Get report start date
    start_report = end_report - timedelta(days=report_days)

    # Get records that are adverse envet records in the time frame of report
    table8b = event_records[(event_records.erep_ae_yn==1) & (event_records.erep_onset_date > start_report) &  (event_records.erep_onset_date <= end_report) ][table8b_cols]

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
    id_cols = ['screening_id','redcap_data_access_group_display', 'ewdateterm']
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
    demo.columns = ['ID', 'Center Name', 'Termination Date','Age', 'Race', 'Ethnicity', 'Sex', 'Status']

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

# ----------------------------------------------------------------------------
# GET DATA FOR PAGE
# ----------------------------------------------------------------------------

def get_page_data(report_date, ASSETS_PATH, display_terms_file, weekly_csv, multi_row_json):
    ''' Load all the data for the page'''
    display_terms, display_terms_dict, display_terms_dict_multi, df, consented, multi_data, centers_df  = get_data_for_page(ASSETS_PATH, display_terms_file, weekly_csv, multi_row_json)
    today, start_report, end_report, report_date_msg, report_range_msg  = get_time_parameters(report_date)

    ## SCREENING TABLES
    table1 = get_table_1(df)

    display_terms_t2a = display_terms_dict_multi['reason_not_interested']
    table2a = get_table_2a(df, display_terms_t2a)

    table2b = get_table_2b(df, start_report, end_report)

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
    age_round_rows = ['mean', 'std']
    age['Age'] = np.where((age['index'].isin(age_round_rows)), age['Age'].round(2).astype(str), age['Age'])

    return report_date_msg, report_range_msg, table1, table2a, table2b, table3, table4, table5, table6, table7a, table7b, table8a, table8b, sex, race, ethnicity, age
