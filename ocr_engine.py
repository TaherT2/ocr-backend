import os
import gc
import fitz
from paddleocr import PaddleOCR

# Strict memory limits
os.environ["FLAGS_use_mkldnn"] = "0"
os.environ["FLAGS_enable_pir_api"] = "0"
os.environ["FLAGS_allocator_strategy"] = "auto_growth"
os.environ["OMP_NUM_THREADS"] = "1"

# 🔴 CRITICAL FIX: det_limit_side_len=4000 stops Paddle from secretly resizing the image
ocr = PaddleOCR(
    use_angle_cls=False,
    lang="ar",
    show_log=False,
    use_gpu=False,
    cpu_threads=1,
    enable_mkldnn=False,
    det_limit_side_len=4000  
)

def detect_script(text):
    for c in text:
        if "\u0600" <= c <= "\u06FF":
            return "arabic"
    return "latin"

def assign_font(script):
    return "Noto Naskh Arabic" if script == "arabic" else "Arial"

def clean_text(text):
    return "".join(ch for ch in text if ord(ch) >= 32).strip()

def build_block(block_id, text, bbox, script, font, size, confidence, source):
    x0, y0, x1, y1 = bbox
    width = x1 - x0
    height = y1 - y0
    text_length = len(text)
    
    return {
        "id": block_id,
        "text": text,
        "box": bbox,
        
        # Frontend Mapping Variables Restored
        "x": round(x0, 2),
        "y": round(y0, 2),
        "width": round(width, 2),
        "height": round(height, 2),
        "center_x": round(x0 + width / 2, 2),
        "center_y": round(y0 + height / 2, 2),
        "text_length": text_length,
        "chars_per_pixel": round(text_length / width, 4) if width > 0 else 0,
        
        "script": script,
        "font": font,
        "size": size,
        "confidence": round(confidence, 4),
        "source": source,
        "editable": True
    }

def process_pdf(pdf_bytes):
    input_path = "/tmp/ocr_input.pdf"
    with open(input_path, "wb") as f:
        f.write(pdf_bytes)
        
    result = {"pages": []}
    pdf = fitz.open(input_path)
    block_id = 0

    for page_index in range(len(pdf)):
        page = pdf[page_index]
        blocks = []
        
        scale = 2.0
        mat = fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=mat)
        
        img_path = f"/tmp/page_{page_index}.png"
        pix.save(img_path)

        try:
            ocr_result = ocr.ocr(img_path)
            if ocr_result and ocr_result[0]:
                for line in ocr_result[0]:
                    box = line[0]  # PaddleOCR 4-point polygon
                    raw_text = clean_text(line[1][0])
                    conf = float(line[1][1])
                    
                    if not raw_text: continue
                    
                    script = detect_script(raw_text)
                    
                    # Map the 4-point image coordinates back to absolute PDF points
                    p0 = fitz.Point(box[0]) / scale
                    p1 = fitz.Point(box[1]) / scale
                    p2 = fitz.Point(box[2]) / scale
                    p3 = fitz.Point(box[3]) / scale
                    
                    # Quad creates a perfect bounding box even if the text is rotated
                    bbox_rect = fitz.Quad(p0, p1, p2, p3).rect
                    
                    # Ensure alignment with cropbox offset (if any)
                    x0 = bbox_rect.x0 + page.cropbox.x0
                    y0 = bbox_rect.y0 + page.cropbox.y0
                    x1 = bbox_rect.x1 + page.cropbox.x0
                    y1 = bbox_rect.y1 + page.cropbox.y0
                    
                    bbox = [x0, y0, x1, y1]
                    
                    blocks.append(build_block(
                        block_id, raw_text, bbox, script, 
                        assign_font(script), 12, conf, "ocr"
                    ))
                    block_id += 1
        finally:
            if os.path.exists(img_path): os.remove(img_path)

        result["pages"].append({
            "page": page_index + 1,
            "width": page.rect.width,
            "height": page.rect.height,
            "blocks": blocks
        })

    pdf.close()
    os.remove(input_path)
    gc.collect()
    return result
