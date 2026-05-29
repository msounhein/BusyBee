import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))


class Config:
    ZAI_API_KEY = os.getenv('ZAI_API_KEY', '')
    MINIMAX_API_KEY = os.getenv('ZAI_API_KEY', '')
    MINIMAX_API_URL = "https://api.z.ai/api/coding/paas/v4/chat/completions"
    MINIMAX_MODEL = "glm-5.1"
    FLASK_PORT = int(os.getenv('FLASK_PORT', '5100'))
    FLASK_HOST = os.getenv('FLASK_HOST', '0.0.0.0')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '-1003791430087')
    LOCATION = os.getenv('LOCATION', 'Appleton, WI')
    MAX_DISTANCE = int(os.getenv('MAX_DISTANCE', '25'))
    DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'jobs.db')
