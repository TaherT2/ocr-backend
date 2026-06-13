from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel

from ocr_engine import process_pdf

app = FastAPI()

# Stores the latest OCR result in memory
last_result = None


class EditRequest(BaseModel):
    block_id: int
    new_text: str


@app.get("/")
def home():
    return {
        "status": "OCR backend running"
    }


@app.post("/ocr")
async def ocr(file: UploadFile = File(...)):
    global last_result

    pdf_bytes = await file.read()

    last_result = process_pdf(pdf_bytes)

    return last_result


@app.get("/blocks")
def get_all_blocks():

    global last_result

    if last_result is None:
        return {
            "error": "No PDF loaded"
        }

    return last_result


@app.get("/block/{block_id}")
def get_block(block_id: int):

    global last_result

    if last_result is None:
        return {
            "error": "No PDF loaded"
        }

    for page in last_result["pages"]:

        for block in page["blocks"]:

            if block["id"] == block_id:
                return block

    return {
        "error": f"Block {block_id} not found"
    }


@app.post("/edit")
def edit_block(request: EditRequest):

    global last_result

    if last_result is None:
        return {
            "error": "No PDF loaded"
        }

    for page in last_result["pages"]:

        for block in page["blocks"]:

            if block["id"] == request.block_id:

                old_text = block["text"]

                block["text"] = request.new_text

                return {
                    "success": True,
                    "block_id": request.block_id,
                    "old_text": old_text,
                    "new_text": request.new_text
                }

    return {
        "error": f"Block {request.block_id} not found"
    }
