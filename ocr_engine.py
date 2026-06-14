import os
import gc
import fitz
from paddleocr import PaddleOCR
import arabic_reshaper
from bidi.algorithm import get_display

# Strict CPU threading to stay under 500MB
os.environ["FLAGS_use_mkldnn"] = "0"
os.environ["FLAGS_enable_pir_api"] = "0"
os.environ["FLAGS_allocator_strategy"] = "auto_growth"
os.environ["OMP_NUM_THREADS"] = "1"

ocr = PaddleOCR(
    use_angle_cls=False,
    lang="ar",
    show_log=False,
    use_gpu=False,
    cpu_threads=1,
    enable_mkldnn=False
)

def detect_script(text):
    # Detects if there is any Arabic character
    for c in text:
        if "\u0600" <= c <= "\u06FF":
            return "arabic"
    return "latin"

def assign_font(script):
    return "Noto Naskh Arabic" if script == "arabic" else "Arial"

def build_block(block_id, text, bbox, script):
    x0, y0, x1, y1 = bbox
    width = x1 - x0
    height = y1 - y0
    
    # Fix Arabic directly in the OCR output so the JSON is readable
    if script == "arabic":
        display_text = get_display(arabic_reshaper.reshape(text))
    else:
        display_text = text

    return {
        "id": block_id,
        "text": display_text,
        "box": [round(coord, 2) for coord in bbox],
        "x": round(x0, 2),
        "y": round(y0, 2),
        "width": round(width, 2),
        "height": round(height, 2),
        "text_length": len(text),
        "script": script,
        "font": assign_font(script),
        "size": 12,
        "editable": True
    }

def process_pdf(pdf_bytes):
    # Save the input to a temp file to avoid keeping bytes in memory
    input_path = "/tmp/input.pdf"
    with open(input_path, "wb") as f: 
        f.write(pdf_bytes)
    
    result = {"pages": []}
    pdf = fitz.open(input_path)
    block_id = 0

    for page_index in range(len(pdf)):
        page = pdf[page_index]
        blocks = []
        
        # 1.5 DPI scale protects RAM usage
        pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
        img_path = f"/tmp/page_{page_index}.png"
        pix.save(img_path)

        try:
            ocr_result = ocr.ocr(img_path)
            if ocr_result and ocr_result[0]:
                for line in ocr_result[0]:
                    box = line[0]
                    raw_text = line[1][0].strip()
                    if not raw_text: 
                        continue
                    
                    # Back-calculate coordinates to original PDF scale
                    x0 = min([p[0] for p in box]) / 1.5
                    y0 = min([p[1] for p in box]) / 1.5
                    x1 = max([p[0] for p in box]) / 1.5
                    y1 = max([p[1] for p in box]) / 1.5
                    
                    bbox = [x0, y0, x1, y1]
                    script = detect_script(raw_text)
                    
                    blocks.append(build_block(block_id, raw_text, bbox, script))
                    block_id += 1
                
        finally:
            if os.path.exists(img_path): 
                os.remove(img_path)

        result["pages"].append({
            "page": page_index + 1,
            "blocks": blocks
        })

    pdf.close()
    os.remove(input_path)
    gc.collect()
    return result
