import os
from dotenv import load_dotenv
load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
    # DB / Celery 等設定日後加入
