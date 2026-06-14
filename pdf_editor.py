import fitz
import os
import gc
import arabic_reshaper
from bidi.algorithm import get_display

def rebuild_pdf(original_pdf_bytes, ocr_data):
    input_path = "/tmp/rebuild_in.pdf"
    output_path = "/tmp/rebuild_out.pdf"
    with open(input_path, "wb") as f: f.write(original_pdf_bytes)
    
    doc = fitz.open(input_path)
    font_path = "fonts/NotoNaskhArabic-Regular.ttf"
    has_arabic_font = os.path.exists(font_path)

    for page_data in ocr_data["pages"]:
        page_index = page_data["page"] - 1
        page = doc[page_index]
        
        # Calculate offset to handle PDFs that don't start at (0,0)
        # Often PDFs have a 'media_box' offset we need to account for
        offset_x, offset_y = page.rect.x0, page.rect.y0
        
        to_replace = [b for b in page_data["blocks"] if "edited_text" in b]
        
        if to_replace:
            # Apply redactions with offset
            for block in to_replace:
                x0, y0, x1, y1 = block["box"]
                rect = fitz.Rect(x0 + offset_x, y0 + offset_y, x1 + offset_x, y1 + offset_y)
                page.add_redact_annot(rect, fill=(1, 1, 1))
            page.apply_redactions()

            if has_arabic_font:
                page.insert_font(fontname="arab", fontfile=font_path)
                
            for block in to_replace:
                x0, y0, x1, y1 = block["box"]
                rect = fitz.Rect(x0 + offset_x, y0 + offset_y, x1 + offset_x, y1 + offset_y)
                
                # Draw DEBUG Box (with offset)
                page.draw_rect(rect, color=(1, 0, 0), width=1)
                
                new_text = block["edited_text"]
                if block.get("script") == "arabic":
                    final_text = get_display(arabic_reshaper.reshape(new_text))
                    font = "arab"
                else:
                    final_text = new_text
                    font = "helv"
                
                page.insert_textbox(rect, final_text, fontsize=block.get("size", 12), 
                                    fontname=font, color=(0,0,0), align=1)
        
        gc.collect()

    doc.save(output_path, garbage=4, deflate=True)
    doc.close()
    return output_path
