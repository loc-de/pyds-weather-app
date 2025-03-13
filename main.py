import datetime
from flask import Flask, jsonify, request

from config import Config
from exceptions.invalid_usage import InvalidUsage
from services.weather import get_weather, get_date, determine_params
from services.ai import get_advice

app = Flask(__name__)

@app.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response

@app.route('/')
def home_page():
    return '<p><h2>KMA HW1: python weather Saas.</h2></p>'

@app.route('/content/api/v1/weather', methods=['POST'])
def weather_endpoint():
    json_data = request.get_json()

    required_fields = ['token', 'requester_name', 'location']
    for field in required_fields:
        if json_data.get(field) is None:
            raise InvalidUsage(f'{field} is required', status_code=400)

    if json_data.get('token') != Config.TOKEN:
        raise InvalidUsage('wrong api token', status_code=403)

    date = get_date(json_data.get('date'))
    forecast_days = json_data.get('forecast_days') or 0
    location = json_data.get('location')
    now = datetime.datetime.now().date()
    return_advice = json_data.get('return_advice') or False

    if 0 > forecast_days or forecast_days > 13:
        raise InvalidUsage('too many forecast_days', status_code=403)

    part, params = determine_params(date, forecast_days, now)
    weather = get_weather(part, location, params)

    weather.pop('current', None)
    if forecast_days != 0:
        weather['forecast']['forecastday'].pop(0)
        weather['days'] = weather['forecast']['forecastday']


    else:
        weather['days'] = [weather['forecast']['forecastday'][-1]]
    weather.pop('forecast', None)

    result = {
        'requester_name': json_data.get('requester_name'),
        'timestamp': datetime.datetime.now(),
        'location': location,
        'date': (date if forecast_days == 0 else now).strftime('%Y-%m-%d'),
        'weather': weather
    }
    if return_advice:
        result['ai_advice'] = get_advice(weather)

    return jsonify(result)
