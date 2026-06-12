import fitz
from paddleocr import PaddleOCR

ocr = PaddleOCR(use_angle_cls=True,lang="arabic",show_log=False)

def detect_script(text):
    for c in text:
        if "\u0600" <= c <= "\u06FF":
            return "arabic"
    return "latin"

def assign_font(script):
    return "Noto Naskh Arabic" if script == "arabic" else "Arial"

def process_pdf(pdf_bytes):
    result = {"pages": []}

    pdf = fitz.open(stream=pdf_bytes, filetype="pdf")

    for page_index in range(len(pdf)):
        page = pdf[page_index]

        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        image_path = f"/tmp/page_{page_index}.png"
        pix.save(image_path)

        ocr_result = ocr.ocr(image_path, cls=True)

        blocks = []

        if ocr_result and ocr_result[0]:
            for line in ocr_result[0]:
                box = line[0]
                text = line[1][0]
                conf = float(line[1][1])

                script = detect_script(text)

                blocks.append({
                    "text": text,
                    "box": box,
                    "script": script,
                    "font": assign_font(script),
                    "confidence": conf
                })

        result["pages"].append({
            "page": page_index + 1,
            "width": page.rect.width,
            "height": page.rect.height,
            "blocks": blocks
        })

    return result
