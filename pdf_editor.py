import fitz
import os
import gc
import arabic_reshaper
from bidi.algorithm import get_display

def rebuild_pdf(original_pdf_bytes, ocr_data):
    input_path = "/tmp/rebuild_in.pdf"
    output_path = "/tmp/rebuild_out.pdf"
    with open(input_path, "wb") as f: f.write(original_pdf_bytes)
    
    pdf = fitz.open(input_path)
    font_path = "fonts/NotoNaskhArabic-Regular.ttf"
    has_arabic_font = os.path.exists(font_path)

    for page_data in ocr_data["pages"]:
        page = pdf[page_data["page"] - 1]
        if has_arabic_font: page.insert_font(fontname="arab", fontfile=font_path)

        to_replace = [b for b in page_data["blocks"] if "edited_text" in b]
        if to_replace:
            # Apply redactions
            for block in to_replace:
                page.add_redact_annot(fitz.Rect(block["box"]), fill=(1, 1, 1))
            page.apply_redactions()

            # Insert new text
            for block in to_replace:
                new_text = block["edited_text"]
                if block.get("script") == "arabic":
                    final_text = get_display(arabic_reshaper.reshape(new_text))
                    font = "arab"
                else:
                    final_text = new_text
                    font = "helv"
                page.insert_textbox(fitz.Rect(block["box"]), final_text, fontsize=12, fontname=font, align=1)
        
        gc.collect()

    pdf.save(output_path)
    pdf.close()
    return output_path
