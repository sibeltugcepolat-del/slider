import json
import re
import time
import logging
from typing import List, Dict, Any
from google import genai
from google.genai import types
from config import GEMINI_API_KEY, CHUNK_SLIDE_SIZE
from utils.retry_handler import retry_with_backoff

class LLMTranslationEngine:
    def __init__(self):
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY tanımlanmamış! Lütfen .env dosyanızı kontrol edin.")
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.model_name = "gemini-3.6-flash"

    def _clean_json_response(self, text: str) -> str:
        text = re.sub(r"^```json\s*", "", text, flags=re.MULTILINE)
        text = re.sub(r"^```\s*", "", text, flags=re.MULTILINE)
        return text.strip()

    @retry_with_backoff(retries=5, backoff_in_seconds=8)
    def generate_outline(self, raw_text: str, images_metadata: List[Dict]) -> List[Dict]:
        images_summary = [
            {
                "image_id": img["image_id"],
                "found_on_page": img["page_num"],
                "context": img.get("caption", "")
            } 
            for img in images_metadata
        ]

        prompt = f"""
Sen uzman bir Anesteziyoloji ve Yoğun Bakım öğretim üyesisin. 
Aşağıda verilen İngilizce anestezi ders kitabı bölümünü analiz ederek 75 ile 125 slayt arasında detaylı bir Türkçe sunum taslağı (outline) oluştur.

KULLANILABİLİR GÖRSELLER VE BULUNDUKLARI SAYFALAR:
{json.dumps(images_summary, ensure_ascii=False)}

KURALLAR:
1. Hiçbir klinik detayı atlama.
2. Slayt sayısı tam olarak 75 ile 125 arasında olmalıdır.
3. Çıktı SADECE geçerli bir JSON liste nesnesi olmalıdır.

JSON FORMATI:
[
  {{
    "slide_id": 1,
    "suggested_title": "Slayt Başlığı",
    "section_name": "Bölüm Adı"
  }}
]

BÖLÜM METNİ:
{raw_text[:120000]}
"""

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                response_mime_type="application/json"
            )
        )

        clean_text = self._clean_json_response(response.text)
        return json.loads(clean_text)

    @retry_with_backoff(retries=5, backoff_in_seconds=8)
    def generate_chunk_content(self, raw_text: str, outline_chunk: List[Dict], available_visuals: List[Dict]) -> List[Dict]:
        prompt = f"""
Sen kıdemli bir anestezi uzmanısın. Aşağıda belirtilen slayt grubu için DETAYLI, ZENGİN ve AKADEMİK Türkçe slayt içerikleri üret.

HEDEF SLAYTLAR:
{json.dumps(outline_chunk, ensure_ascii=False)}

KULLANILABİLİR GÖRSELLER (SADECE BU LİSTEDEKİLERİ KULLANABİLİRSİN):
{json.dumps(available_visuals, ensure_ascii=False)}

STRICT GÖRSELLERİ EŞLEŞTİRME KURALLARI:
1. TEK KULLANIM KURALI: Her `image_id` EN FAZLA 1 KEZ kullanılabilir. 
2. ZORUNLULUK YOKTUR: Her slayta görsel eklemek ZORUNDA DEĞİLSİN. Slayttaki konu doğrudan görselin bulunduğu sayfadaki tablo/şema ile uyuşmuyorsa `assigned_image_id` değerini KESİNLİKLE null yap.
3. Bir görseli emin değilsen atama! Rastgele veya tekrar eden resim seçimi yasaktır.

SLAYT İÇERİK KURALLARI:
1. Her slayt için en az 4-6 detaylı akademik madde (bullet_points) yaz.
2. Eğer klinik bir uyarı, dozaj veya kritik püf noktası varsa "clinical_pearl" alanına ekle, yoksa null bırak.
3. Tablo yapmaya uygun veriler varsa "table" alanına ekle (headers ve rows şeklinde), yoksa null bırak.

JSON FORMATI:
[
  {{
    "slide_id": 1,
    "title": "Başlık",
    "bullet_points": ["Madde 1", "Madde 2"],
    "clinical_pearl": "Klinik Önemli Nokta (veya null)",
    "assigned_image_id": "IMG_X_Y veya null",
    "table": {{
        "headers": ["Parametre", "Normal Değer"],
        "rows": [["Kalp Debisi", "4-8 L/dk"]]
    }}
  }}
]

REFERANS METİN:
{raw_text[:100000]}
"""

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                response_mime_type="application/json"
            )
        )

        clean_text = self._clean_json_response(response.text)
        return json.loads(clean_text)

    def process_full_chapter(self, raw_text: str, images_metadata: List[Dict]) -> List[Dict]:
        logging.info("Aşama 1: LLM ile Sunum Taslağı (Outline) oluşturuluyor...")
        outline = self.generate_outline(raw_text, images_metadata)
        logging.info(f"Taslak oluşturuldu. Toplam hedef slayt sayısı: {len(outline)}")

        full_slides_content = []
        used_image_ids = set()

        for i in range(0, len(outline), CHUNK_SLIDE_SIZE):
            chunk = outline[i:i + CHUNK_SLIDE_SIZE]
            logging.info(f"Aşama 2: Chunk işleniyor ({i+1} - {i+len(chunk)} / {len(outline)} slaytlar)...")
            
            # Daha önce kullanılmamış görselleri filtrele
            available_images = [
                {
                    "image_id": img["image_id"],
                    "found_on_page": img["page_num"],
                    "context": img.get("caption", "")
                }
                for img in images_metadata if img["image_id"] not in used_image_ids
            ]

            chunk_result = self.generate_chunk_content(raw_text, chunk, available_images)
            
            # Kullanılan resimleri kaydet ve tekrar kullanılmasını engelle
            for slide in chunk_result:
                assigned_id = slide.get("assigned_image_id")
                if assigned_id and assigned_id != "null" and assigned_id not in used_image_ids:
                    used_image_ids.add(assigned_id)
                elif assigned_id in used_image_ids:
                    # Çift atanmayı kod seviyesinde de engelle
                    slide["assigned_image_id"] = None

            full_slides_content.extend(chunk_result)
            time.sleep(6)

        return full_slides_content
