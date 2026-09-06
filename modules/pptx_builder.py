import os
import logging
from typing import List, Dict
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

class PPTXBuilderEngine:
    def __init__(self, images_metadata: List[Dict]):
        self.prs = Presentation()
        self.prs.slide_width = Inches(13.333)
        self.prs.slide_height = Inches(7.5)  # 16:9 Widescreen
        self.image_map = {img["image_id"]: img["file_path"] for img in images_metadata}

        # Renk Paleti (Medikal Tema)
        self.COLOR_PRIMARY = RGBColor(16, 44, 87)     # Koyu Lacivert
        self.COLOR_ACCENT = RGBColor(234, 84, 85)     # Klinik Vurgu Kırmızısı/Turuncusu
        self.COLOR_BG_CARD = RGBColor(245, 247, 250)   # Açık Gri Kart Arka Planı
        self.COLOR_TEXT_DARK = RGBColor(33, 37, 41)   # Metin Rengi

    def create_presentation(self, slides_data: List[Dict], output_filename: str) -> str:
        logging.info(f"PPTX Sunumu oluşturuluyor. Toplam slayt: {len(slides_data)}")

        # Kapak Slaytı
        blank_layout = self.prs.slide_layouts[6]
        cover_slide = self.prs.slides.add_slide(blank_layout)
        self._build_cover_slide(cover_slide, slides_data[0]["title"] if slides_data else "Anestezi Referans Kitabı")

        for slide_info in slides_data:
            slide = self.prs.slides.add_slide(blank_layout)
            self._build_content_slide(slide, slide_info)

        self.prs.save(output_filename)
        logging.info(f"PPTX başarıyla kaydedildi: {output_filename}")
        return output_filename

    def _build_cover_slide(self, slide, title_text: str):
        # Arka plan rengi
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = self.COLOR_PRIMARY

        txBox = slide.shapes.add_textbox(Inches(1), Inches(2.5), Inches(11.333), Inches(2))
        tf = txBox.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = "ANESTEZİYOLOJİ VE YOĞUN BAKIM"
        p.font.size = Pt(24)
        p.font.bold = True
        p.font.color.rgb = self.COLOR_ACCENT

        p2 = tf.add_paragraph()
        p2.text = "Günlük Detaylı Referans Sunumu"
        p2.font.size = Pt(40)
        p2.font.bold = True
        p2.font.color.rgb = RGBColor(255, 255, 255)

    def _build_content_slide(self, slide, data: Dict):
        title = data.get("title", "Başlıksız Slayt")
        bullets = data.get("bullet_points", [])
        pearl = data.get("clinical_pearl")
        image_id = data.get("assigned_image_id")
        table_data = data.get("table")

        img_path = self.image_map.get(image_id) if image_id else None
        has_image = img_path is not None and os.path.exists(img_path)

        # 1. Slayt Başlığı
        title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.5), Inches(11.7), Inches(0.8))
        tf = title_box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = title
        p.font.size = Pt(24)
        p.font.bold = True
        p.font.color.rgb = self.COLOR_PRIMARY

        # Düzen Hesaplaması: Resim varsa metin genişliği %55, yoksa %90
        text_width = Inches(6.8) if has_image else Inches(11.7)

        # 2. Bullet Points
        content_box = slide.shapes.add_textbox(Inches(0.8), Inches(1.5), text_width, Inches(4.2))
        ctf = content_box.text_frame
        ctf.word_wrap = True

        for i, bp in enumerate(bullets):
            p = ctf.add_paragraph() if i > 0 else ctf.paragraphs[0]
            p.text = f"• {bp}"
            p.font.size = Pt(14)
            p.font.color.rgb = self.COLOR_TEXT_DARK
            p.space_after = Pt(8)

        # 3. Görsel Ekleme (Sağ Panele)
        if has_image:
            try:
                slide.shapes.add_picture(img_path, Inches(8.0), Inches(1.5), width=Inches(4.5))
            except Exception as e:
                logging.warning(f"Görsel eklenirken hata oluştu ({img_path}): {e}")

        # 4. Klinik Pearl (Vurgu Kutusu)
        if pearl:
            top_pos = Inches(5.8)
            shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), top_pos, text_width, Inches(1.1))
            shape.fill.solid()
            shape.fill.fore_color.rgb = self.COLOR_BG_CARD
            shape.line.color.rgb = self.COLOR_ACCENT
            shape.line.width = Pt(1.5)

            ptf = shape.text_frame
            ptf.word_wrap = True
            pp = ptf.paragraphs[0]
            pp.text = f"KLİNİK BİLGİ / PEARL: {pearl}"
            pp.font.size = Pt(12)
            pp.font.bold = True
            pp.font.color.rgb = self.COLOR_ACCENT

        # 5. Tablo Ekleme (Varsa)
        if table_data and "headers" in table_data and "rows" in table_data:
            headers = table_data["headers"]
            rows = table_data["rows"]
            if headers and rows:
                num_rows = len(rows) + 1
                num_cols = len(headers)
                table_shape = slide.shapes.add_table(num_rows, num_cols, Inches(0.8), Inches(4.5), text_width, Inches(1.5))
                table = table_shape.table

                for col_idx, header in enumerate(headers):
                    cell = table.cell(0, col_idx)
                    cell.text = header
                    cell.fill.solid()
                    cell.fill.fore_color.rgb = self.COLOR_PRIMARY
                    for p in cell.text_frame.paragraphs:
                        p.font.size = Pt(11)
                        p.font.bold = True
                        p.font.color.rgb = RGBColor(255, 255, 255)

                for row_idx, row in enumerate(rows):
                    for col_idx, val in enumerate(row):
                        if col_idx < num_cols:
                            cell = table.cell(row_idx + 1, col_idx)
                            cell.text = str(val)
                            for p in cell.text_frame.paragraphs:
                                p.font.size = Pt(10)
                                p.font.color.rgb = self.COLOR_TEXT_DARK