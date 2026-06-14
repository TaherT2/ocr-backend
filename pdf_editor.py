import fitz
import os
import arabic_reshaper
from bidi.algorithm import get_display

def rebuild_pdf(original_pdf_bytes, ocr_data):
    pdf = fitz.open(stream=original_pdf_bytes, filetype="pdf")

    # Locate the Arabic font
    font_path = "fonts/NotoNaskhArabic-Regular.ttf"
    has_arabic_font = os.path.exists(font_path)

    for page_data in ocr_data["pages"]:
        page_index = page_data["page"] - 1
        page = pdf[page_index]

        # Embed the Arabic font into this page
        if has_arabic_font:
            page.insert_font(fontname="arab", fontfile=font_path)

        # ==========================================
        # STEP 1: Add redactions
        # ==========================================
        redactions = []

        for block in page_data["blocks"]:
            if "edited_text" not in block:
                continue

            x0, y0, x1, y1 = block["box"]
            rect = fitz.Rect(x0, y0, x1, y1)

            page.add_redact_annot(rect, fill=(1, 1, 1))
            redactions.append(block)

        # Permanently remove original content
        if redactions:
            page.apply_redactions()

        # ==========================================
        # STEP 2: Draw replacement text
        # ==========================================
        for block in redactions:
            new_text = block["edited_text"]
            script = block.get("script", "latin")
            
            x0, y0, x1, y1 = block["box"]
            font_size = block.get("size", 12)
            rect = fitz.Rect(x0, y0, x1, y1)

            # Handle Arabic shaping and RTL translation
            if script == "arabic":
                reshaped_text = arabic_reshaper.reshape(new_text)
                final_text = get_display(reshaped_text)
                active_font = "arab" if has_arabic_font else "helv"
            else:
                final_text = new_text
                active_font = "helv"

            # Use insert_textbox with align=1 to perfectly center the new text
            page.insert_textbox(
                rect,
                final_text,
                fontsize=font_size,
                fontname=active_font,
                color=(0, 0, 0),
                align=1 
            )

    output = pdf.tobytes()
    pdf.close()

    return output
