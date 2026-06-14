import os
import gc

# 🔴 CRITICAL: Aggressive memory constraints for 500MB limit
os.environ["FLAGS_use_mkldnn"] = "0"
os.environ["FLAGS_enable_pir_api"] = "0"
os.environ["FLAGS_allocator_strategy"] = "auto_growth"
os.environ["OMP_NUM_THREADS"] = "1"

import fitz
from paddleocr import PaddleOCR

# Initialize OCR in STRICT SAFE MODE (CPU only, 1 thread)
ocr = PaddleOCR(
    use_angle_cls=False,
    lang="ar",  # Must be 'ar' to read Arabic properly
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

def build_block(block_id, text, bbox, script, font, size, confidence, source):
    x0, y0, x1, y1 = bbox
    width = x1 - x0
    height = y1 - y0

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
        "text_length": len(text),
        "chars_per_pixel": round(len(text) / width, 4) if width > 0 else 0,
        "script": script,
        "font": font,
        "size": size,
        "confidence": confidence,
        "source": source,
        "editable": True
    }

def process_pdf(pdf_bytes):
    result = {"pages": []}
    pdf = fitz.open(stream=pdf_bytes, filetype="pdf")
    block_id = 0

    for page_index in range(len(pdf)):
        page = pdf[page_index]
        blocks = []
        text_dict = page.get_text("dict")
        has_real_text = False

        for block in text_dict.get("blocks", []):
            if "lines" not in block:
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    text = clean_text(span.get("text", ""))
                    if not text:
                        continue

                    has_real_text = True
                    bbox = span["bbox"]
                    script = detect_script(text)

                    blocks.append(
                        build_block(
                            block_id, text, bbox, script,
                            span.get("font", assign_font(script)),
                            span.get("size", 12), 1.0, "pdf"
                        )
                    )
                    block_id += 1

        if not has_real_text:
            print(f"Page {page_index + 1}: OCR fallback")
            
            # Reduced DPI scale (1.5) to protect the 500MB RAM limit
            pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
            img_path = f"/tmp/page_{page_index}.png"
            pix.save(img_path)

            try:
                ocr_result = ocr.ocr(img_path)
                if ocr_result and ocr_result[0]:
                    for line in ocr_result[0]:
                        box = line[0]
                        text = clean_text(line[1][0])
                        conf = float(line[1][1])

                        if not text:
                            continue

                        # Adjust bbox because we scaled the image by 1.5
                        xs = [p[0] / 1.5 for p in box]
                        ys = [p[1] / 1.5 for p in box]
                        bbox = [min(xs), min(ys), max(xs), max(ys)]
                        script = detect_script(text)

                        blocks.append(
                            build_block(
                                block_id, text, bbox, script,
                                assign_font(script), 12, conf, "ocr"
                            )
                        )
                        block_id += 1
            except Exception as e:
                print("OCR ERROR:", str(e))
            finally:
                if os.path.exists(img_path):
                    os.remove(img_path)

        result["pages"].append({
            "page": page_index + 1,
            "width": page.rect.width,
            "height": page.rect.height,
            "blocks": blocks
        })

    pdf.close()
    
    # Force OS to reclaim memory immediately
    gc.collect()
    return result
