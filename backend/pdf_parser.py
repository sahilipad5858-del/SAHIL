import re
import pdfplumber
from models import POData


def extract_po_data(pdf_path: str) -> POData:
    """Extract structured data from a Purchase Order PDF."""
    raw_text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                raw_text += text + "\n"

    po_data = POData(raw_text=raw_text)

    # Extract PO Number
    po_num_match = re.search(
        r'(?:Purchase\s*Order\s*(?:Number|No|#|Number:|No:|#:)?)\s*[:\-]?\s*([A-Z0-9\-]+)',
        raw_text, re.IGNORECASE
    )
    if po_num_match:
        po_data.po_number = po_num_match.group(1).strip()

    # Extract PO Date
    date_match = re.search(
        r'(?:Date|Order\s*Date|PO\s*Date)\s*[:\-]?\s*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}|\d{1,2}\s+\w+\s+\d{2,4})',
        raw_text, re.IGNORECASE
    )
    if date_match:
        po_data.po_date = date_match.group(1).strip()

    # Extract Vendor / Supplier Name
    vendor_match = re.search(
        r'(?:Vendor|Supplier|Sold\s*To|Bill\s*To)\s*[:\-]?\s*\n?\s*(.+?)(?:\n|$)',
        raw_text, re.IGNORECASE
    )
    if vendor_match:
        po_data.vendor_name = vendor_match.group(1).strip()

    # Extract Vendor Email
    email_match = re.search(
        r'[\w\.-]+@[\w\.-]+\.\w+',
        raw_text, re.IGNORECASE
    )
    if email_match:
        po_data.vendor_email = email_match.group(0).strip()

    # Extract Delivery Date
    delivery_match = re.search(
        r'(?:Delivery\s*Date|Ship\s*Date|Required\s*By|Expected\s*Delivery)\s*[:\-]?\s*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}|\d{1,2}\s+\w+\s+\d{2,4})',
        raw_text, re.IGNORECASE
    )
    if delivery_match:
        po_data.delivery_date = delivery_match.group(1).strip()

    # Extract Payment Terms
    payment_match = re.search(
        r'(?:Payment\s*Terms?|Terms?\s*of\s*Payment)\s*[:\-]?\s*(.+?)(?:\n|$)',
        raw_text, re.IGNORECASE
    )
    if payment_match:
        po_data.payment_terms = payment_match.group(1).strip()

    # Extract Shipping Address
    ship_match = re.search(
        r'(?:Ship\s*To|Shipping\s*Address|Delivery\s*Address)\s*[:\-]?\s*\n?\s*(.+?)(?:\n\n|\n(?:Phone|Email|Fax|Tel))',
        raw_text, re.IGNORECASE | re.DOTALL
    )
    if ship_match:
        po_data.shipping_address = ship_match.group(1).strip()

    return po_data


def generate_email_draft(po_data: POData) -> dict:
    """Generate a draft email based on extracted PO data."""
    vendor = po_data.vendor_name or "Vendor"
    po_num = po_data.po_number or "N/A"
    po_date = po_data.po_date or "N/A"
    delivery = po_data.delivery_date or "N/A"
    terms = po_data.payment_terms or "N/A"
    address = po_data.shipping_address or "N/A"

    subject = f"Purchase Order Acknowledgment - PO#{po_num}"

    body = f"""Dear {vendor},

Thank you for your Purchase Order #{po_num} dated {po_date}.

We acknowledge receipt of your order and confirm the following details:

- PO Number: {po_num}
- PO Date: {po_date}
- Delivery Date: {delivery}
- Payment Terms: {terms}
- Shipping Address: {address}

We will process your order promptly. If you have any questions, please don't hesitate to reach out.

Best Regards,
[Your Company Name]
[Your Name]
"""

    to_email = po_data.vendor_email or ""

    return {
        "to": to_email,
        "subject": subject,
        "body": body,
        "po_data": po_data
    }
