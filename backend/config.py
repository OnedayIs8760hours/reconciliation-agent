import os
from dotenv import load_dotenv
load_dotenv()

class Config:
    DEEPSEEK_BASE_URL = "https://api.deepseek.com"
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
    