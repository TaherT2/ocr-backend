from fastapi import FastAPI, UploadFile, File
from ocr_engine import process_pdf

app = FastAPI()

# Store the last OCR result in memory
last_result = None


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
