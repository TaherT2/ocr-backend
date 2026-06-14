import os
import fitz
from paddleocr import PaddleOCR

# ==================================================
# 🔧 Fix CPU / Paddle stability on Railway
# ==================================================
os.environ["FLAGS_use_mkldnn"] = "0"
os.environ["FLAGS_allocator_strategy"] = "auto_growth"


# ==================================================
# OCR INIT (MINIMAL SAFE MODE)
# IMPORTANT: NO use_gpu, NO cls, NO show_log
# ==================================================
ocr = PaddleOCR()


# ==================================================
# SCRIPT DETECTION
# ==================================================
def detect_script(text):
    for c in text:
        if "\u0600" <= c <= "\u06FF":
            return "arabic"
    return "latin"


def assign_font(script):
    return "Noto Naskh Arabic" if script == "arabic" else "Arial"


# ==================================================
# CLEAN TEXT
# ==================================================
def clean_text(text):
    if not text:
        return ""
    return "".join(ch for ch in str(text) if ord(ch) >= 32).strip()


# ==================================================
# BLOCK BUILDER
# ==================================================
def build_block(
    block_id,
    text,
    bbox,
    script,
    font,
    size,
    confidence,
    source
):
    x0, y0, x1, y1 = bbox

    width = x1 - x0

    return {
        "id": block_id,
        "text": text,
        "box": bbox,

        "x": x0,
        "y": y0,
        "width": width,
        "height": y1 - y0,

        "center_x": x0 + width / 2,
        "center_y": y0 + (y1 - y0) / 2,

        "script": script,
        "font": font,
        "size": size,
        "confidence": confidence,
        "source": source,

        "editable": True
    }


# ==================================================
# MAIN PIPELINE
# ==================================================
def process_pdf(pdf_bytes):
    result = {"pages": []}

    pdf = fitz.open(stream=pdf_bytes, filetype="pdf")

    block_id = 0

    for page_index in range(len(pdf)):
        page = pdf[page_index]
        blocks = []

        # ==========================================
        # 1. Extract embedded PDF text
        # ==========================================
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
                    script = detect_script(text)

                    blocks.append(
                        build_block(
                            block_id,
                            text,
                            span["bbox"],
                            script,
                            assign_font(script),
                            span.get("size", 12),
                            1.0,
                            "pdf"
                        )
                    )

                    block_id += 1

        # ==========================================
        # 2. OCR fallback
        # ==========================================
        if not has_real_text:
            print(f"Page {page_index + 1}: OCR fallback")

            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            image_path = f"/tmp/page_{page_index}.png"
            pix.save(image_path)

            # SAFE CALL (NO PARAMETERS)
            ocr_result = ocr.ocr(image_path)

            if ocr_result and ocr_result[0]:

                for line in ocr_result[0]:

                    box = line[0]
                    text = clean_text(line[1][0])
                    conf = float(line[1][1])

                    if not text:
                        continue

                    script = detect_script(text)

                    xs = [p[0] for p in box]
                    ys = [p[1] for p in box]

                    bbox = [
                        min(xs),
                        min(ys),
                        max(xs),
                        max(ys)
                    ]

                    blocks.append(
                        build_block(
                            block_id,
                            text,
                            bbox,
                            script,
                            assign_font(script),
                            12,
                            conf,
                            "ocr"
                        )
                    )

                    block_id += 1

        else:
            print(f"Page {page_index + 1}: PDF text extraction")

        result["pages"].append({
            "page": page_index + 1,
            "width": page.rect.width,
            "height": page.rect.height,
            "blocks": blocks
        })

    pdf.close()
    return result
