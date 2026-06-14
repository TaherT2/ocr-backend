from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel
import gc, os
from ocr_engine import process_pdf
from pdf_editor import rebuild_pdf

app = FastAPI()
pdf_bytes_store = None
ocr_store = None

class EditRequest(BaseModel):
    block_id: int
    new_text: str

@app.post("/ocr")
async def ocr(file: UploadFile = File(...)):
    global pdf_bytes_store, ocr_store
    pdf_bytes_store = await file.read()
    ocr_store = process_pdf(pdf_bytes_store)
    gc.collect()
    # CRITICAL CHANGE: Return the full store so you can see IDs and box coordinates
    return ocr_store 

@app.post("/edit")
def edit_block(request: EditRequest):
    global ocr_store
    if not ocr_store: return {"error": "No PDF loaded"}
    
    for page in ocr_store["pages"]:
        for block in page["blocks"]:
            if block["id"] == request.block_id:
                block["edited_text"] = request.new_text
                print(f"DEBUG: Updated Block {request.block_id} to '{request.new_text}'")
                return {"success": True}
    return {"error": "Block not found"}

@app.get("/export")
def export_pdf():
    global pdf_bytes_store, ocr_store
    if not pdf_bytes_store or not ocr_store:
        return {"error": "No PDF loaded"}
    path = rebuild_pdf(pdf_bytes_store, ocr_store)
    return FileResponse(path, media_type="application/pdf", filename="edited.pdf")
