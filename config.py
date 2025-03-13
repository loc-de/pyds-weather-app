import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    TOKEN = os.getenv("TOKEN")
    API_KEY = os.getenv("API_KEY")
    AI_API_KEYS = os.getenv("AI_API_KEYS").split(',')
    API_URL = 'http://api.weatherapi.com/v1'
