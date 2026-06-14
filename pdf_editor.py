import fitz
import os
import arabic_reshaper
from bidi.algorithm import get_display

def rebuild_pdf(original_pdf_bytes, ocr_data):
    pdf = fitz.open(stream=original_pdf_bytes, filetype="pdf")
    font_path = "fonts/NotoNaskhArabic-Regular.ttf"
    has_arabic_font = os.path.exists(font_path)

    for page_data in ocr_data["pages"]:
        page = pdf[page_data["page"] - 1]
        if has_arabic_font: page.insert_font(fontname="arab", fontfile=font_path)

        redactions = []
        for block in page_data["blocks"]:
            if "edited_text" not in block: continue
            page.add_redact_annot(fitz.Rect(block["box"]), fill=(1, 1, 1))
            redactions.append(block)

        if redactions: page.apply_redactions()

        for block in redactions:
            rect = fitz.Rect(block["box"])
            new_text = block["edited_text"]
            
            if block.get("script") == "arabic":
                final_text = get_display(arabic_reshaper.reshape(new_text))
                font = "arab" if has_arabic_font else "helv"
            else:
                final_text = new_text
                font = "helv"

            page.insert_textbox(rect, final_text, fontsize=block.get("size", 12), 
                                fontname=font, color=(0, 0, 0), align=1)

    output = pdf.tobytes()
    pdf.close()
    return output
