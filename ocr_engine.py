from pdf2image import convert_from_bytes
from paddleocr import PaddleOCR

ocr = PaddleOCR(use_angle_cls=True, lang='en')

def detect_script(text):
    for c in text:
        if '\u0600' <= c <= '\u06FF':
            return "arabic"
    return "latin"

def assign_font(script):
    return "Noto Naskh Arabic" if script == "arabic" else "Arial"


def process_pdf(pdf_bytes):
    images = convert_from_bytes(pdf_bytes)

    result = {"pages": []}

    for i, img in enumerate(images):
        ocr_result = ocr.ocr(img, cls=True)

        blocks = []

        for line in ocr_result[0]:
            box = line[0]
            text = line[1][0]
            conf = line[1][1]

            script = detect_script(text)

            blocks.append({
                "text": text,
                "box": box,
                "script": script,
                "font": assign_font(script),
                "confidence": conf
            })

        result["pages"].append({
            "page": i + 1,
            "blocks": blocks
        })

    return result
