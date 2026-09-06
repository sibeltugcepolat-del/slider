import os
import requests
import logging
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

class TelegramNotifier:
    def __init__(self):
        self.bot_token = TELEGRAM_BOT_TOKEN
        self.chat_id = TELEGRAM_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"

        if not self.bot_token or not self.chat_id:
            logging.warning("Telegram Bot Token veya Chat ID eksik! Bildirimler gönderilemeyebilir.")

    def send_message(self, text: str):
        """Telegram üzerinden düz metin mesajı gönderir."""
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text
        }
        try:
            res = requests.post(url, data=payload, timeout=30)
            if not res.ok:
                logging.error(f"Telegram Mesaj Hatası Detayı: {res.text}")
            res.raise_for_status()
            return res.json()
        except Exception as e:
            logging.error(f"Telegram mesajı gönderilemedi: {e}")
            raise e

    def send_document(self, file_path: str, caption: str = ""):
        """Telegram üzerinden dosya (PPTX vb.) ve açıklama metni gönderir."""
        url = f"{self.base_url}/sendDocument"
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Gönderilecek dosya bulunamadı: {file_path}")

        payload = {
            "chat_id": self.chat_id,
            "caption": caption
        }

        try:
            with open(file_path, "rb") as doc:
                files = {"document": doc}
                res = requests.post(url, data=payload, files=files, timeout=120)
                if not res.ok:
                    logging.error(f"Telegram Dosya Gönderim Hatası Detayı: {res.text}")
                res.raise_for_status()
                return res.json()
        except Exception as e:
            logging.error(f"Telegram dosya gönderimi başarısız: {e}")
            raise e