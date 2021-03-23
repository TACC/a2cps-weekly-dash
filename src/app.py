import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
from flask import request
import plotly
import plotly.express as px
import pathlib
import os

################################################################################
##                                                                            ##
##  Devops                                                                    ##
##                                                                            ##
################################################################################

DATA_PATH = pathlib.Path(__file__).parent.joinpath("data") 
ASSETS_PATH = pathlib.Path(__file__).parent.joinpath("assets")
REQUESTS_PATHNAME_PREFIX = os.environ.get("REQUESTS_PATHNAME_PREFIX", "/")
DJANGO_LOGIN_HOST = os.environ.get("DJANGO_LOGIN_HOST", None)

app = dash.Dash(
    __name__,
    assets_folder=ASSETS_PATH,
    requests_pathname_prefix=REQUESTS_PATHNAME_PREFIX,
)

def get_django_user():
    """
    Utility function to retrieve logged in username
    from Django
    """
    try:
        session_id = request.cookies.get('sessionid')
        if not session_id:
            raise Exception("sessionid cookie is missing")
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
        return None

def get_layout():
    if DJANGO_LOGIN_HOST and not get_django_user():
        return html.Div("Please login at {django_login_host}".format(
            django_login_host=DJANGO_LOGIN_HOST
        ))
    return html.Div("A plotly-dash container")

app.layout = get_layout

if __name__ == '__main__':
    app.run_server(debug=True)
else:
    server = app.server
