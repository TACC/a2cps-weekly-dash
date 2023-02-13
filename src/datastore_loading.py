import os
import requests
import json
import traceback

# ---------------------------------
#   MOVE THIS TO REFERENCE FROM ENV
# ---------------------------------
DATASTORE_URL =  os.getenv('DATASTORE_URL')

# ---------------------------------
#   Get Data From datastore
# ---------------------------------

def get_api_data(api_address):
    api_json = {}
    try:
        try:
            response = requests.get(api_address)
        except:
            return('error: {}'.format(e))
        request_status = response.status_code
        if request_status == 200:
            api_json = response.json()
            return api_json
        else:
            return request_status
    except Exception as e:
        traceback.print_exc()
        api_json['json'] = 'error: {}'.format(e)
        return api_json
