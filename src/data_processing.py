  # Libraries
# Data
import requests
import math
import numpy as np
import pandas as pd # Dataframe manipulations
import datetime
from datetime import datetime, timedelta

# ----------------------------------------------------------------------------
# DATA LOADING AND CLEANING FUNCTIONS
# ----------------------------------------------------------------------------
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

    except:
        return 'Improper format for file'

def get_multi_row_data(json_api_url):
    ''' Take the adverse effects JSON and convert into a data frame for analysis.

        API returns data in the format [{record_id:
                                            {instance:
                                                {field:value}
                                            }
                                        }] '''

    df = pd.DataFrame() # create empty dataframe
    try:
        adv_effects_dict = requests.get(json_api_url).json()
        for i in adv_effects_dict:
            for key in i.keys():
                df_key = pd.DataFrame.from_dict(i[key], orient='index') #.reset_index()
                seq = [key] * len(df_key)
                df_key = df_key.reindex(['record_id', *df_key.columns], axis=1).assign(record_id= seq)
                df = pd.concat([df, df_key], axis = 0)
        df = df.reset_index()
        df = df.rename(columns={'index': 'instance'})
        return df
    except:
        return pd.DataFrame()

# ----------------------------------------------------------------------------
# Screening Tables
# ----------------------------------------------------------------------------
def get_table_1(df):
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
    within_days_range = ((end_report_date - t3.date_and_time).dt.days) <= days_range
    t3['within_range'] = within_days_range

    # Aggregate data for table 3
    # Set the columns to groupby, and the the columns to role up with desired aggregating functions
    # Note: can supply a list of aggregate functions to one columnm i.e. 'col_name': ['min','max']
    cols_for_groupby = ["redcap_data_access_group_display"]
    aggregate_columns_dict={'screening_id':'count',
                            'date_and_time':'max',
                             'eligible':'sum',
                             'ewdateterm':'count',
                           'within_range':'sum'}
    cols = cols_for_groupby + list(aggregate_columns_dict.keys())
    t3_aggregate = t3[cols].groupby(by=cols_for_groupby).agg(aggregate_columns_dict)

    # Reset Index
    t3_aggregate = t3_aggregate.reset_index()

    # Calculate the number of days since the last consent
    t3_aggregate['days_since_consent'] = (end_report_date.date() - t3_aggregate['date_and_time'].dt.date).astype(str)

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

    return t3, t3_aggregate

# ----------------------------------------------------------------------------
# Study Status Tables
# ----------------------------------------------------------------------------
def get_tables_5_6(df):
    # Get patients who rescinded consent, i.e. have a value in the 'ewdateterm' column
    rescinded = df.dropna(subset=['ewdateterm'])
    rescinded_cols = ['redcap_data_access_group_display','record_id','date_and_time','ewdateterm','ewprimaryreason','ewcomments','sp_surg_date']
    rescinded = rescinded[rescinded_cols]
    # Display record id as int
    rescinded.record_id = rescinded.record_id.astype('int32')
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
def get_deviation_records(df, multi_data, display_terms_dict):
    # Get Data on Protocol deviations
    deviation_flag_cols = ['erep_prot_dev']
    deviations_cols = ['record_id', 'instance','erep_local_dtime',
           'erep_protdev_type', 'erep_protdev_desc',
           'erep_protdev_caplan']
    deviations = multi_data.dropna(subset=deviation_flag_cols)[deviations_cols ]

    # Merge deviations with center info
    deviations = deviations.merge(df[['redcap_data_access_group','redcap_data_access_group_display','record_id','sp_v1_preop_date']], how='left', on = 'record_id')

    # Convert deviation type to text
    deviation_terms = display_terms_dict['erep_protdev_type']
    deviation_terms.columns = ['erep_protdev_type','Deviation']
    deviations = deviations.merge(deviation_terms, how='outer', on='erep_protdev_type')

    return deviations

def get_deviations_by_center(df, deviations, display_terms_dict):
    dev_cols = ['record_id','redcap_data_access_group','screening_id','sp_v1_preop_date']
    baseline = df.dropna(subset=['sp_v1_preop_date'])[dev_cols]
    baseline = baseline.reset_index()

    # Flag patients who have an associated deviation
    records_with_deviation = deviations.record_id.unique()
    baseline_with_dev = baseline[baseline.record_id.isin(records_with_deviation)]

    # Calculate total baseline participants
    baseline_total = baseline.groupby(by=['redcap_data_access_group'],as_index=False).size()
    baseline_total = baseline_total.rename(columns={'size':'Total Subjects'})

    # Calculate total baseline participants with 1+ deviations
    baseline_dev_total = baseline_with_dev.groupby(by=['redcap_data_access_group'],as_index=False).size()
    baseline_dev_total = baseline_dev_total.rename(columns={'size':'Total Subjects with Deviation'})

    # Merge dataframes
    baseline_total = baseline_total.merge(baseline_dev_total, how='outer', on = 'redcap_data_access_group')

    # Calculate Perent Column
    baseline_total['Percent with 1+ Deviation'] = 100 * (baseline_total['Total Subjects with Deviation'] / baseline_total['Total Subjects'])

    # Add count of all deviations for a given center
    center_count = pd.DataFrame(deviations.value_counts(subset=['redcap_data_access_group'])).reset_index()
    center_count.columns =['redcap_data_access_group','Total Deviations']
    baseline_total = baseline_total.merge(center_count, how='left', on = 'redcap_data_access_group')

    # Merge data with full list of centers
    centers = display_terms_dict['redcap_data_access_group']
    baseline_total = centers.merge(baseline_total,how='left', on='redcap_data_access_group')

    # Get list of deviation type by center
    dev_by_center = deviations[['record_id','Deviation', 'instance','redcap_data_access_group']]

    # Group and count by center
    dev_by_center = dev_by_center.groupby(by=['redcap_data_access_group','Deviation'],as_index=False).size()

    # Pivot deviation rows into columns
    dev_by_center_pivot =  pd.pivot_table(dev_by_center, index=["redcap_data_access_group"], columns=["Deviation"], values=["size"])

    # Clean up column levels and naming
    dev_by_center_pivot.columns = dev_by_center_pivot.columns.droplevel()
    dev_by_center_pivot.columns.name = ''
    dev_by_center_pivot = dev_by_center_pivot.reset_index()

    # Merge baseline total and specific deviation information into one table
    baseline_total = baseline_total.merge(dev_by_center_pivot, how='left', on='redcap_data_access_group')

    # Drop center database name and rename display colum
    baseline_total = baseline_total.drop(columns=['redcap_data_access_group'])
    baseline_total = baseline_total.rename(columns={'redcap_data_access_group_display':'Center Name'})

    return baseline_total


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

# ----------------------------------------------------------------------------
# Demographics Tables
# ----------------------------------------------------------------------------
