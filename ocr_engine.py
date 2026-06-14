import fitz
from paddleocr import PaddleOCR

# FIX: remove cls dependency issues
ocr = PaddleOCR(
    use_angle_cls=True,
    lang="en"  # safer for mixed documents; we detect Arabic ourselves
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

    chars_per_pixel = round(text_length / width, 4) if width > 0 else 0

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
        "chars_per_pixel": chars_per_pixel,

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

        # -------------------------
        # PDF TEXT LAYER
        # -------------------------
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
                    bbox = span["bbox"]

                    blocks.append(build_block(
                        block_id,
                        text,
                        bbox,
                        script,
                        span.get("font", assign_font(script)),
                        span.get("size", 12),
                        1.0,
                        "pdf"
                    ))

                    block_id += 1

        # -------------------------
        # OCR FALLBACK
        # -------------------------
        if not has_real_text:

            print(f"Page {page_index + 1}: OCR fallback")

            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            image_path = f"/tmp/page_{page_index}.png"
            pix.save(image_path)

            ocr_result = ocr.ocr(image_path)  # FIXED (no cls)

            if ocr_result and ocr_result[0]:

                for line in ocr_result[0]:

                    try:
                        box = line[0]
                        text = clean_text(line[1][0])
                        conf = float(line[1][1])
                    except Exception:
                        continue

                    if not text:
                        continue

                    script = detect_script(text)

                    xs = [p[0] for p in box]
                    ys = [p[1] for p in box]

                    bbox = [min(xs), min(ys), max(xs), max(ys)]

                    blocks.append(build_block(
                        block_id,
                        text,
                        bbox,
                        script,
                        assign_font(script),
                        12,
                        conf,
                        "ocr"
                    ))

                    block_id += 1

        result["pages"].append({
            "page": page_index + 1,
            "width": page.rect.width,
            "height": page.rect.height,
            "blocks": blocks
        })

    pdf.close()
    return result
