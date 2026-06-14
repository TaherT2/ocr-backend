import os
import gc
import fitz
from paddleocr import PaddleOCR

# Force single-threaded CPU operation to prevent memory spikes
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

def assign_font(script):
    return "Noto Naskh Arabic" if script == "arabic" else "Arial"

def clean_text(text):
    return "".join(ch for ch in text if ord(ch) >= 32).strip()

def merge_nearby_blocks(blocks):
    """Merges blocks that overlap horizontally or are very close."""
    if not blocks:
        return []
    
    # Sort by Y position first, then X position
    blocks.sort(key=lambda b: (b["y"], b["x"]))
    
    merged = []
    for b in blocks:
        if not merged:
            merged.append(b)
            continue
            
        last = merged[-1]
        # Check if they are on the same line (within a 5-pixel threshold)
        if abs(b["y"] - last["y"]) < 5 and abs(b["height"] - last["height"]) < 5:
            last["text"] += " " + b["text"]
            last["box"][2] = max(last["box"][2], b["box"][2]) # Update x1
            last["width"] = last["box"][2] - last["box"][0]
            last["center_x"] = last["box"][0] + last["width"] / 2
        else:
            merged.append(b)
    return merged

def build_block(block_id, text, bbox, script, font, size, confidence, source):
    x0, y0, x1, y1 = bbox
    width = x1 - x0
    height = y1 - y0
    return {
        "id": block_id,
        "text": text,
        "box": [x0, y0, x1, y1],
        "x": x0, "y": y0, "width": width, "height": height,
        "center_x": x0 + width / 2, "center_y": y0 + height / 2,
        "script": script, "font": font, "size": size,
        "confidence": confidence, "source": source, "editable": True
    }

def process_pdf(pdf_bytes):
    result = {"pages": []}
    pdf = fitz.open(stream=pdf_bytes, filetype="pdf")
    block_id = 0

    for page_index in range(len(pdf)):
        page = pdf[page_index]
        blocks = []
        
        # High DPI conversion (2.0) for better OCR accuracy on complex Arabic forms
        pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
        img_path = f"/tmp/page_{page_index}.png"
        pix.save(img_path)

        try:
            ocr_result = ocr.ocr(img_path)
            raw_blocks = []
            if ocr_result and ocr_result[0]:
                for line in ocr_result[0]:
                    box = line[0]
                    text = clean_text(line[1][0])
                    conf = float(line[1][1])
                    if not text: continue
                    
                    xs = [p[0] / 2.0 for p in box]
                    ys = [p[1] / 2.0 for p in box]
                    bbox = [min(xs), min(ys), max(xs), max(ys)]
                    script = detect_script(text)
                    
                    raw_blocks.append(build_block(0, text, bbox, script, assign_font(script), 12, conf, "ocr"))
            
            # Apply the Merge algorithm
            merged_blocks = merge_nearby_blocks(raw_blocks)
            for b in merged_blocks:
                b["id"] = block_id
                blocks.append(b)
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
    gc.collect()
    return result
