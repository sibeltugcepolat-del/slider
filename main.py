import json
import logging
import traceback
from pathlib import Path
from config import CHAPTERS_DIR, STATE_FILE_PATH
from modules.pdf_parser import PDFParserEngine
from modules.llm_translator import LLMTranslationEngine
from modules.pptx_builder import PPTXBuilderEngine
from modules.telegram_notifier import TelegramNotifier

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def load_state() -> dict:
    if Path(STATE_FILE_PATH).exists():
        with open(STATE_FILE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"current_chapter_index": 1, "total_chapters_processed": 0}

def save_state(state: dict):
    with open(STATE_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

def get_chapter_files():
    """chapters klasöründeki pdf dosyalarını sıralı olarak getirir."""
    pdf_files = sorted(list(CHAPTERS_DIR.glob("*.pdf")))
    return pdf_files

def main():
    notifier = TelegramNotifier()
    state = load_state()

    current_idx = state.get("current_chapter_index", 1)
    chapter_files = get_chapter_files()

    if not chapter_files:
        logging.error("❌ 'chapters/' klasöründe işlenecek PDF dosyası bulunamadı!")
        return

    if current_idx > len(chapter_files):
        logging.info("🎉 Kitaptaki tüm bölümler başarıyla işlendi ve tamamlandı!")
        notifier.send_message("🎉 **Tebrikler!** Kitaptaki tüm bölümlerin sunumları başarıyla oluşturuldu ve tamamlandı.")
        return

    # Sıradaki PDF dosyasını seç (0 tabanlı indeks için current_idx - 1)
    target_pdf = chapter_files[current_idx - 1]
    chapter_name = target_pdf.stem  # Dosya adı (ör: 01-Introduction)

    logging.info(f"--- BÖLÜM {current_idx}/{len(chapter_files)} İŞLEMESİ BAŞLADI: {chapter_name} ---")

    try:
        # 1. Seçilen Bölüm PDF'ini Parse Et
        parser = PDFParserEngine(str(target_pdf))
        raw_text, images_metadata = parser.extract_chapter_data()

        if not raw_text.strip():
            notifier.send_message(f"⚠️ **{chapter_name}**: PDF'ten okunacak metin bulunamadı.")
            return

        # 2. LLM Çeviri ve Slayt Yapısı Üretimi
        llm_engine = LLMTranslationEngine()
        slides_data = llm_engine.process_full_chapter(raw_text, images_metadata)

        # 3. PPTX Oluşturma
        output_filename = f"{chapter_name}.pptx"
        builder = PPTXBuilderEngine(images_metadata)
        generated_pptx = builder.create_presentation(slides_data, output_filename)

        # 4. State Güncelleme (Sonraki bölüm için kaydet)
        state["current_chapter_index"] = current_idx + 1
        state["total_chapters_processed"] = state.get("total_chapters_processed", 0) + 1
        save_state(state)
        logging.info(f"Bölüm {current_idx} ({chapter_name}) kaydedildi. Sonraki indeks: {current_idx + 1}")

        # 5. Telegram Gönderimi
        caption = (
            f"📚 **Anestezi Referans Kitabı**\n"
            f"📖 **Bölüm {current_idx}/{len(chapter_files)}:** {chapter_name}\n\n"
            f"✅ **Toplam Slayt:** {len(slides_data)}\n"
            f"🖼️ **Aktif Görsel Sayısı:** {len(images_metadata)}"
        )
        notifier.send_document(generated_pptx, caption=caption)

        logging.info("--- BÖLÜM BAŞARIYLA TAMAMLANDI VE TELEGRAM'A GÖNDERİLDİ ---")

    except Exception as e:
        error_msg = f"❌ **{chapter_name} İşlenirken Hata Oluştu!**\n\n`{str(e)}`\n\n```\n{traceback.format_exc()[:1000]}\n```"
        logging.error(f"Sistem Hatası: {e}")
        try:
            notifier.send_message(error_msg)
        except Exception as notify_err:
            logging.error(f"Telegram bildirim hatası: {notify_err}")
        raise e

if __name__ == "__main__":
    main()