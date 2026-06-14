import fitz
import os
import gc
import arabic_reshaper
from bidi.algorithm import get_display

def rebuild_pdf(original_pdf_bytes, ocr_data):
    pdf = fitz.open(stream=original_pdf_bytes, filetype="pdf")
    font_path = "fonts/NotoNaskhArabic-Regular.ttf"
    has_arabic_font = os.path.exists(font_path)

    for page_data in ocr_data["pages"]:
        page = pdf[page_data["page"] - 1]
        
        # Register font once per page if needed
        if has_arabic_font:
            page.insert_font(fontname="arab", fontfile=font_path)

        # 1. Redact existing text
        blocks_to_replace = [b for b in page_data["blocks"] if "edited_text" in b]
        for block in blocks_to_replace:
            page.add_redact_annot(fitz.Rect(block["box"]), fill=(1, 1, 1))
        
        if blocks_to_replace:
            page.apply_redactions()

        # 2. Insert new text
        for block in blocks_to_replace:
            rect = fitz.Rect(block["box"])
            new_text = block["edited_text"]
            
            # Proper Arabic processing only at insertion time
            if block.get("script") == "arabic":
                final_text = get_display(arabic_reshaper.reshape(new_text))
                font = "arab" if has_arabic_font else "helv"
            else:
                final_text = new_text
                font = "helv"

            page.insert_textbox(rect, final_text, fontsize=block.get("size", 12), 
                                fontname=font, color=(0, 0, 0), align=1)
        
        # Critical memory cleanup per page
        gc.collect()

    output = pdf.tobytes()
    pdf.close()
    return output
