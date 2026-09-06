import time
import functools
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def retry_with_backoff(retries=5, backoff_in_seconds=5):
    """
    LLM veya API çağrılarında rate-limit / ağ hatalarında otomatik retry yapar.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            x = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if x == retries:
                        logging.error(f"[Retry Limit Error] {retries} deneme sonrası fonksiyon başarısız oldu: {func.__name__}")
                        raise e
                    sleep_time = (backoff_in_seconds * (2 ** x))
                    logging.warning(f"[API Warning] {func.__name__} hata aldı: {e}. {sleep_time} saniye bekleniyor... (Deneme {x+1}/{retries})")
                    time.sleep(sleep_time)
                    x += 1
        return wrapper
    return decorator
