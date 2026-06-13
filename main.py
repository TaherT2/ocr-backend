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

from pydantic import BaseModel

class EditRequest(BaseModel):
    text: str

from pdf_editor import replace_text_in_pdf
from fastapi.responses import Response
from pydantic import BaseModel

class ReplaceRequest(BaseModel):
    old_text: str
    new_text: str

@app.post("/replace-text")
async def replace_text(file: UploadFile = File(...),old_text: str = "",new_text: str = ""):

    pdf_bytes = await file.read()

    edited_pdf = replace_text_in_pdf(pdf_bytes,old_text,new_text)

    return Response(content=edited_pdf,media_type="application/pdf",headers={"Content-Disposition":"attachment;filename=edited.pdf"})


@app.post("/test-edit")
def test_edit(data: EditRequest):

    return {"original": data.text,"edited": data.text.upper()}
