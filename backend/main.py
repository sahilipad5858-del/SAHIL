import os
import uuid
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pdf_parser import extract_po_data, generate_email_draft
from email_service import send_email
from models import POData, EmailDraft, SendEmailRequest

app = FastAPI(title="PO Mailer", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.post("/api/upload-po")
async def upload_po(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    file_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{file_id}.pdf")

    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    try:
        po_data = extract_po_data(file_path)
        email_draft = generate_email_draft(po_data)

        return {
            "success": True,
            "file_id": file_id,
            "filename": file.filename,
            "po_data": po_data.dict(),
            "email_draft": email_draft,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse PDF: {str(e)}")


@app.post("/api/send-email")
async def send_email_endpoint(request: SendEmailRequest, file_id: str = None):
    attachment_path = None
    if file_id:
        candidate = os.path.join(UPLOAD_DIR, f"{file_id}.pdf")
        if os.path.exists(candidate):
            attachment_path = candidate

    result = await send_email(
        to=request.to,
        subject=request.subject,
        body=request.body,
        cc=request.cc,
        bcc=request.bcc,
        attachment_path=attachment_path,
        attachment_name=request.attachment_name,
    )

    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])

    return result


@app.get("/api/download/{file_id}")
async def download_po(file_id: str):
    file_path = os.path.join(UPLOAD_DIR, f"{file_id}.pdf")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, media_type="application/pdf", filename=f"PO_{file_id}.pdf")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
