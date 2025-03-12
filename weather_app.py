import datetime
import json
import re

import requests
from flask import Flask, jsonify, request

TOKEN = 'Sdu3s@Dso'
API_KEY = '3b3d412a8fe1439a8a4193821251203'
# API_KEY = 'd2466d3c1e344a93929140829250703'
API_URL = 'http://api.weatherapi.com/v1'

app = Flask(__name__)


class InvalidUsage(Exception):
    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv["message"] = self.message
        return rv

def get_weather(part: str, location: str, params: dict):
    params['key'] = API_KEY
    params['q'] = location

    response = requests.get(
        url=API_URL + part,
        params=params
    )

    if response.status_code == requests.codes.ok:
        return json.loads(response.text)
    else:
        raise InvalidUsage(response.text, status_code=response.status_code)

def get_date(date: str):
    if date is None:
        date = datetime.datetime.now().strftime('%Y-%m-%d')

    pattern = r"\d{4}-\d{2}-\d{2}"
    match = re.search(pattern, date)
    if not match:
        raise InvalidUsage('wrong date', status_code=403)

    try:
        return datetime.datetime.strptime(match.group(0), '%Y-%m-%d').date()
    except ValueError:
        raise InvalidUsage('wrong date', status_code=403)

@app.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


@app.route("/")
def home_page():
    return "<p><h2>KMA HW1: python weather Saas.</h2></p>"


@app.route("/content/api/v1/weather", methods=["POST"])
def weather_endpoint():
    json_data = request.get_json()

    required_fields = ['token', 'requester_name', 'location']
    for field in required_fields:
        if json_data.get(field) is None:
            raise InvalidUsage(f'{field} is required', status_code=400)

    if json_data.get('token') != TOKEN:
        raise InvalidUsage('wrong api token', status_code=403)

    date = get_date(json_data.get('date'))
    forecast_days = json_data.get('forecast_days')
    if forecast_days is None:
        forecast_days = 0
    location = json_data.get('location')
    now = datetime.datetime.now().date()

    if 0 > forecast_days > 14:
        raise InvalidUsage('too many forecast_days', status_code=403)

    if forecast_days == 0:
        if date == now:
            part = '/current.json'
            params = {}
        elif date < now:
            part = '/history.json'
            params = {'dt': date}
        elif date <= now + datetime.timedelta(days=14):
            part = '/forecast.json'
            params = {'days': (date - now).days + 1}
        else:
            part = '/future.json'
            params = {'dt': date}

        weather = get_weather(part, location, params)
        if weather.get('forecast'):
            weather.pop('current', None)
        if params.get('days') is not None:
            weather['forecast']['forecastday'] = [weather['forecast']['forecastday'][params.get('days') - 1]]

    else:
        part = '/forecast.json'
        params = {'days': forecast_days + 1}
        weather = get_weather(part, location, params)
        weather.pop('current', None)
        weather['forecast']['forecastday'].pop(0)

    result = {
        'requester_name': json_data.get('requester_name'),
        'timestamp': datetime.datetime.now(),
        'location': location,
        'date': (date if forecast_days == 0 else now).strftime('%Y-%m-%d'),
        'weather': weather
    }

    return result


if __name__ == '__main__':
    app.run()
