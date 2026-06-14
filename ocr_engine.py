import os
import gc
import fitz
from paddleocr import PaddleOCR
import arabic_reshaper
from bidi.algorithm import get_display

# Strict memory limits
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
    for c in text:
        if "\u0600" <= c <= "\u06FF":
            return "arabic"
    return "latin"

def format_arabic_text(text, script):
    if script == "arabic":
        # Make Arabic readable in the JSON output
        return get_display(arabic_reshaper.reshape(text))
    return text

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
        "x": x0,
        "y": y0,
        "width": width,
        "height": height,
        "center_x": x0 + width / 2,
        "center_y": y0 + height / 2,
        "text_length": text_length,
        "chars_per_pixel": round(text_length / width, 4) if width > 0 else 0,
        "script": script,
        "font": font,
        "size": size,
        "confidence": confidence,
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
        
        # Capture the offset if the PDF cropbox doesn't start at 0,0
        crop_x = page.cropbox.x0
        crop_y = page.cropbox.y0
        
        scale = 1.5
        pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale))
        img_path = f"/tmp/page_{page_index}.png"
        pix.save(img_path)

        try:
            ocr_result = ocr.ocr(img_path)
            if ocr_result and ocr_result[0]:
                for line in ocr_result[0]:
                    box = line[0]
                    raw_text = clean_text(line[1][0])
                    conf = float(line[1][1])
                    if not raw_text: continue
                    
                    script = detect_script(raw_text)
                    readable_text = format_arabic_text(raw_text, script)
                    
                    # Convert from scaled image pixels to absolute PDF points
                    x0 = (min([p[0] for p in box]) / scale) + crop_x
                    y0 = (min([p[1] for p in box]) / scale) + crop_y
                    x1 = (max([p[0] for p in box]) / scale) + crop_x
                    y1 = (max([p[1] for p in box]) / scale) + crop_y
                    bbox = [x0, y0, x1, y1]
                    
                    blocks.append(build_block(
                        block_id, readable_text, bbox, script, 
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
