import os
import gc
import fitz
from paddleocr import PaddleOCR

os.environ["FLAGS_use_mkldnn"] = "0"
os.environ["FLAGS_enable_pir_api"] = "0"
os.environ["FLAGS_allocator_strategy"] = "auto_growth"
os.environ["OMP_NUM_THREADS"] = "1"

ocr = PaddleOCR(use_angle_cls=False, lang="ar", show_log=False, use_gpu=False, cpu_threads=1, enable_mkldnn=False)

def detect_script(text):
    for c in text:
        if "\u0600" <= c <= "\u06FF": return "arabic"
    return "latin"

def process_pdf(pdf_bytes):
    # Save the input to a temp file to avoid keeping bytes in memory
    input_path = "/tmp/input.pdf"
    with open(input_path, "wb") as f: f.write(pdf_bytes)
    
    result = {"pages": []}
    pdf = fitz.open(input_path)
    block_id = 0

    for page_index in range(len(pdf)):
        page = pdf[page_index]
        blocks = []
        pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
        img_path = f"/tmp/page_{page_index}.png"
        pix.save(img_path)

        try:
            ocr_result = ocr.ocr(img_path)
            if ocr_result and ocr_result[0]:
                for line in ocr_result[0]:
                    box = line[0]
                    text = line[1][0].strip()
                    if not text: continue
                    
                    xs = [p[0] / 1.5 for p in box]
                    ys = [p[1] / 1.5 for p in box]
                    bbox = [min(xs), min(ys), max(xs), max(ys)]
                    
                    blocks.append({
                        "id": block_id, "text": text, "box": bbox,
                        "script": detect_script(text), "size": 12, "editable": True
                    })
                    block_id += 1
        finally:
            if os.path.exists(img_path): os.remove(img_path)

        result["pages"].append({"page": page_index + 1, "blocks": blocks})

    pdf.close()
    os.remove(input_path)
    gc.collect()
    return result
