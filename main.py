from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel

from ocr_engine import process_pdf
from pdf_editor import export_pdf_from_blocks

app = FastAPI()

# =========================
# MEMORY STORAGE (TEMP DB)
# =========================
stored_pdf_bytes = None
stored_ocr_result = None


class EditRequest(BaseModel):
    block_id: int
    new_text: str


@app.get("/")
def home():
    return {"status": "OCR + EDIT + EXPORT backend running"}


# =========================
# 1. UPLOAD + OCR
# =========================
@app.post("/ocr")
async def ocr(file: UploadFile = File(...)):
    global stored_pdf_bytes, stored_ocr_result

    stored_pdf_bytes = await file.read()

    stored_ocr_result = process_pdf(stored_pdf_bytes)

    return stored_ocr_result


# =========================
# DEBUG VIEW BLOCKS
# =========================
@app.get("/blocks")
def get_blocks():

    if stored_ocr_result is None:
        return {"error": "No PDF loaded"}

    return stored_ocr_result


# =========================
# EDIT BLOCK
# =========================
@app.post("/edit")
def edit_block(request: EditRequest):

    global stored_ocr_result

    if stored_ocr_result is None:
        return {"error": "No PDF loaded"}

    for page in stored_ocr_result["pages"]:
        for block in page["blocks"]:

            if block["id"] == request.block_id:
                old = block["text"]
                block["text"] = request.new_text

                return {
                    "success": True,
                    "block_id": request.block_id,
                    "old_text": old,
                    "new_text": request.new_text
                }

    return {"error": "Block not found"}


# =========================
# 3. EXPORT FINAL PDF
# =========================
@app.get("/export")
def export_pdf():

    global stored_pdf_bytes, stored_ocr_result

    if stored_pdf_bytes is None or stored_ocr_result is None:
        return {"error": "No PDF loaded"}

    final_pdf = export_pdf_from_blocks(
        stored_pdf_bytes,
        stored_ocr_result
    )

    return {
        "file": final_pdf.hex()
    }
