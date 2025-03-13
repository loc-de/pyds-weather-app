import datetime
import json
import re
from typing import Tuple
from dotenv import load_dotenv
import os

import openai
import requests
from flask import Flask, jsonify, request

load_dotenv()

TOKEN = os.getenv("TOKEN")
API_KEY = os.getenv("API_KEY")
AI_API_KEYS = os.getenv("AI_API_KEYS").split(',')
API_URL = 'http://api.weatherapi.com/v1'

app = Flask(__name__)
client = openai.OpenAI(
    base_url='https://api.aimlapi.com/v1',
    api_key=AI_API_KEYS[0]
)


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
        rv['message'] = self.message
        return rv

def get_weather(part: str, location: str, params: dict) -> dict:
    params['key'] = API_KEY
    params['q'] = location
    params['lang'] = 'uk'

    response = requests.get(
        url=API_URL + part,
        params=params
    )

    if response.status_code == requests.codes.ok:
        return json.loads(response.text)
    else:
        raise InvalidUsage(response.text, status_code=response.status_code)

def get_date(date: str) -> datetime.date:
    if date is None:
        date = datetime.datetime.now().strftime('%Y-%m-%d')

    pattern = r'\d{4}-\d{2}-\d{2}'
    match = re.search(pattern, date)
    if not match:
        raise InvalidUsage('wrong date', status_code=403)

    try:
        return datetime.datetime.strptime(match.group(0), '%Y-%m-%d').date()
    except ValueError:
        raise InvalidUsage('wrong date', status_code=403)

def determine_params(date: datetime.date, fc_days: int, now: datetime.date) -> Tuple[str, dict]:
    if fc_days != 0:
        return '/forecast.json', {'days': fc_days + 1}
    if date == now:
        return '/current.json', {}

    elif date < now:
        return '/history.json', {'dt': date}

    elif date <= now + datetime.timedelta(days=14):
        return '/forecast.json', {'days': (date - now).days + 1}

    else:
        return '/future.json', {'dt': date}

def ai_request(content: str) -> str:
    messages = [
        {
            'role': 'system',
            'content': 'Ти стиліст. Твоя задача коротко радити, що вдягнути за погодою, дай рекомендації'
        },
        {
            'role': 'user',
            'content': content
        }
    ]

    inx = AI_API_KEYS.index(client.api_key) + 1
    for ai_api_key in AI_API_KEYS[inx:] + AI_API_KEYS[:inx]:
        try:
            response = client.chat.completions.create(
                model='gpt-4o',
                messages=messages,
                temperature=0.9
            )
            return response.choices[0].message.content

        except openai.RateLimitError:
            client.api_key = ai_api_key

        except openai.BadRequestError:
            return ''

    return ''

def get_advice(weather: dict) -> list[str]:
    advices = []

    if 'forecast' in weather:
        location = weather['location']['name']
        for inx, day in enumerate(weather['forecast']['forecastday']):
            date = day['date']
            condition = day['day']['condition']['text']
            min_temp = day['day']['mintemp_c']
            max_temp = day['day']['maxtemp_c']
            wind_speed = day['day']['maxwind_kph']
            humidity = day['day']['avghumidity']
            content = (
                f'{location} {date} {condition} {min_temp}- {max_temp}°C '
                f'{wind_speed}км/год {humidity}% '
                f'Що вдягнути та яка атмосфера?'
            )
            advices.append(ai_request(content))

        return advices

    location = weather['location']['name']
    condition = weather['current']['condition']['text']
    temp = weather['current']['temp_c']
    feels_like = weather['current']['feelslike_c']
    wind_speed = weather['current']['wind_kph']
    humidity = weather['current']['humidity']
    content = (
        f'{location} {condition} {temp}°C (як {feels_like}) '
        f'{wind_speed}км/год {humidity}% '
        f'Що вдягнути та яка атмосфера?'
    )
    return [ai_request(content)]

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

    if json_data.get('token') != TOKEN:
        raise InvalidUsage('wrong api token', status_code=403)

    date = get_date(json_data.get('date'))
    forecast_days = json_data.get('forecast_days') or 0
    location = json_data.get('location')
    now = datetime.datetime.now().date()
    return_advice = json_data.get('return_advice') or False

    if 0 > forecast_days > 14:
        raise InvalidUsage('too many forecast_days', status_code=403)

    part, params = determine_params(date, forecast_days, now)
    weather = get_weather(part, location, params)

    if weather.get('forecast'):
        weather.pop('current', None)
        if forecast_days != 0:
            weather['forecast']['forecastday'].pop(0)

    elif params.get('days') is not None:
        weather['forecast']['forecastday'] = [weather['forecast']['forecastday'][params.get('days') - 1]]

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

app.run()
