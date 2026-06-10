from fastapi import FastAPI, UploadFile, File
from ocr_engine import process_pdf

app = FastAPI()

@app.get("/")
def home():
    return {"status": "OCR backend running"}

@app.post("/ocr")
async def ocr(file: UploadFile = File(...)):
    pdf_bytes = await file.read()
    return process_pdf(pdf_bytes)
