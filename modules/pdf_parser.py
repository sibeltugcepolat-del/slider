import pymupdf as fitz  # PyMuPDF
import os
from pathlib import Path
from typing import Tuple, List, Dict
from config import TEMP_IMAGE_DIR

class PDFParserEngine:
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF dosyası bulunamadı: {pdf_path}")
        self.doc = fitz.open(self.pdf_path)

    def extract_chapter_data(self) -> Tuple[str, List[Dict]]:
        full_text = ""
        images_metadata = []
        
        temp_dir = Path(TEMP_IMAGE_DIR)
        temp_dir.mkdir(parents=True, exist_ok=True)

        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            page_text = page.get_text()
            full_text += f"\n--- SAYFA {page_num + 1} ---\n" + page_text

            # Görsel ayıklama
            image_list = page.get_images(full=True)
            for img_index, img in enumerate(image_list):
                xref = img[0]
                try:
                    base_image = self.doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]

                    # Çok küçük ikonları/çizgileri ele (Genişlik ve yükseklik en az 100px olmalı)
                    if base_image["width"] < 100 or base_image["height"] < 100:
                        continue

                    image_name = f"img_p{page_num + 1}_{img_index + 1}.{image_ext}"
                    image_path = temp_dir / image_name

                    with open(image_path, "wb") as f:
                        f.write(image_bytes)

                    # Sayfadaki ilk 250 karakteri görsel konusu için ipucu olarak ver
                    snippet = page_text[:250].replace("\n", " ").strip()

                    images_metadata.append({
                        "image_id": image_name,
                        "page_num": page_num + 1,
                        "file_path": str(image_path),
                        "caption": f"Sayfa {page_num + 1} konusu: {snippet}"
                    })
                except Exception:
                    continue

        return full_text, images_metadata