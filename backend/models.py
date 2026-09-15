from pydantic import BaseModel
from typing import Optional, List


class POData(BaseModel):
    vendor_name: Optional[str] = None
    po_number: Optional[str] = None
    po_date: Optional[str] = None
    delivery_date: Optional[str] = None
    payment_terms: Optional[str] = None
    shipping_address: Optional[str] = None
    vendor_email: Optional[str] = None
    buyer_name: Optional[str] = None
    items: Optional[list] = None
    total_amount: Optional[str] = None
    raw_text: Optional[str] = None


class EmailDraft(BaseModel):
    to: str
    subject: str
    body: str
    cc: Optional[str] = None
    bcc: Optional[str] = None
    po_data: Optional[POData] = None


class SendEmailRequest(BaseModel):
    to: str
    subject: str
    body: str
    cc: Optional[str] = None
    bcc: Optional[str] = None
    attachment_name: Optional[str] = None


class ExtractResponse(BaseModel):
    success: bool
    po_data: Optional[POData] = None
    email_draft: Optional[EmailDraft] = None
    error: Optional[str] = None
