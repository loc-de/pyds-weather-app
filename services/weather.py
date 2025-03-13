import datetime
import requests
import json
import re
from typing import Tuple

from config import Config
from exceptions.invalid_usage import InvalidUsage

def get_weather(part: str, location: str, params: dict) -> dict:
    params['key'] = Config.API_KEY
    params['q'] = location
    params['lang'] = 'uk'

    response = requests.get(
        url=Config.API_URL + part,
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
        return '/forecast.json', {'days': 1}

    elif date < now:
        return '/history.json', {'dt': date}

    elif date <= now + datetime.timedelta(days=14):
        return '/forecast.json', {'days': (date - now).days + 1}

    else:
        return '/future.json', {'dt': date}
