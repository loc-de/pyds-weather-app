import openai
from typing import List
from config import Config

client = openai.OpenAI(
    base_url='https://api.aimlapi.com/v1',
    api_key=Config.AI_API_KEYS[0]
)

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

    inx = Config.AI_API_KEYS.index(client.api_key) + 1
    for ai_api_key in Config.AI_API_KEYS[inx:] + Config.AI_API_KEYS[:inx]:
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

def get_advice(weather: dict) -> List[str]:
    advices = []

    location = weather['location']['name']
    for inx, day in enumerate(weather['days']):
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
