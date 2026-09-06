import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

# Dosya Yolları
CHAPTERS_DIR = BASE_DIR / "chapters"
STATE_FILE_PATH = os.getenv("STATE_FILE_PATH", str(BASE_DIR / "state.json"))
TEMP_IMAGE_DIR = BASE_DIR / "temp_images"

# API Anahtarları ve Secret'lar
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Slayt Parametreleri
CHUNK_SLIDE_SIZE = 25

# Dizin Oluşturma
TEMP_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
CHAPTERS_DIR.mkdir(parents=True, exist_ok=True)