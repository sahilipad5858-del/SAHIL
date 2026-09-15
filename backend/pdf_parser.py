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
            # Also try table extraction
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    if row:
                        raw_text += " | ".join([str(c) if c else "" for c in row]) + "\n"

    po_data = POData(raw_text=raw_text)

    # Normalize text: collapse multiple spaces, strip each line
    lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
    normalized = "\n".join(lines)

    # --- PO Number ---
    po_patterns = [
        r'P\.?O\.?\s*(?:Number|No|#|\.?:)\s*[:=\-]?\s*([A-Za-z0-9][\w\-/]*)',
        r'Purchase\s+Order\s*(?:Number|No|#)?\s*[:=\-]?\s*([A-Za-z0-9][\w\-/]*)',
        r'Order\s*(?:Number|No|#)\s*[:=\-]?\s*([A-Za-z0-9][\w\-/]*)',
        r'(?:PO|P\.O\.?)\s*[:=\-]\s*([A-Za-z0-9][\w\-/]*)',
    ]
    for pat in po_patterns:
        m = re.search(pat, normalized, re.IGNORECASE)
        if m:
            po_data.po_number = m.group(1).strip()
            break

    # --- PO Date ---
    date_patterns = [
        r'(?:Order|PO|P\.O\.?)\s*Date\s*[:=\-]?\s*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})',
        r'(?:Order|PO|P\.O\.?)\s*Date\s*[:=\-]?\s*(\d{1,2}\s+\w+\s+\d{2,4})',
        r'Date\s*(?:of\s+Order)?\s*[:=\-]?\s*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})',
        r'Date\s*(?:of\s+Order)?\s*[:=\-]?\s*(\d{1,2}\s+\w+\s+\d{2,4})',
        r'(?:Dated|Issue\s*Date)\s*[:=\-]?\s*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})',
    ]
    for pat in date_patterns:
        m = re.search(pat, normalized, re.IGNORECASE)
        if m:
            po_data.po_date = m.group(1).strip()
            break

    # --- Vendor / Supplier ---
    vendor_patterns = [
        r'(?:Vendor|Supplier|Seller|Vend(?:or)?|Sold\s*To|Bill\s*To)\s*[:=\-]?\s*\n?\s*(.+)',
        r'(?:From|Company)\s*[:=\-]?\s*\n?\s*(.+)',
    ]
    for pat in vendor_patterns:
        m = re.search(pat, normalized, re.IGNORECASE)
        if m:
            val = m.group(1).strip()
            # Take only first line if multi-line
            val = val.split("\n")[0].strip()
            # Clean up: remove "Name:" prefix if present
            val = re.sub(r'^(?:Name|Company)\s*[:=\-]\s*', '', val, flags=re.IGNORECASE).strip()
            if val and len(val) > 1:
                po_data.vendor_name = val
                break

    # --- Email (find all, pick the vendor one) ---
    emails = re.findall(r'[\w\.\-]+@[\w\.\-]+\.\w{2,}', normalized, re.IGNORECASE)
    if emails:
        # Prefer email near vendor/supplier line
        vendor_context = ""
        for i, line in enumerate(lines):
            if re.search(r'vendor|supplier|seller|from', line, re.IGNORECASE):
                vendor_context = "\n".join(lines[max(0, i-1):i+3])
                break
        vendor_emails = re.findall(r'[\w\.\-]+@[\w\.\-]+\.\w{2,}', vendor_context, re.IGNORECASE)
        if vendor_emails:
            po_data.vendor_email = vendor_emails[0]
        else:
            po_data.vendor_email = emails[0]

    # --- Delivery Date ---
    delivery_patterns = [
        r'(?:Delivery|Ship|Expected|Required|Need)\s*(?:Date|By)?\s*[:=\-]?\s*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})',
        r'(?:Delivery|Ship|Expected|Required|Need)\s*(?:Date|By)?\s*[:=\-]?\s*(\d{1,2}\s+\w+\s+\d{2,4})',
        r'(?:ETA|Est\.?\s*Arrival)\s*[:=\-]?\s*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})',
    ]
    for pat in delivery_patterns:
        m = re.search(pat, normalized, re.IGNORECASE)
        if m:
            po_data.delivery_date = m.group(1).strip()
            break

    # --- Payment Terms ---
    payment_patterns = [
        r'(?:Payment\s*Terms?|Terms?\s*(?:of\s*)?Payment|P\.?T\.?)\s*[:=\-]?\s*(.+)',
        r'(?:Terms|Conditions?)\s*[:=\-]?\s*(Net\s*\d+.+)',
        r'(Net\s*\d+)',
        r'(COD|CIA|CWO|CAD)',
    ]
    for pat in payment_patterns:
        m = re.search(pat, normalized, re.IGNORECASE)
        if m:
            val = m.group(1).strip()
            val = val.split("\n")[0].strip()
            if val:
                po_data.payment_terms = val
                break

    # --- Shipping Address ---
    ship_patterns = [
        r'(?:Ship\s*To|Shipping\s*(?:Address|Location)|Delivery\s*Address|Delivery\s*Location|Deliver\s*To)\s*[:=\-]?\s*\n?\s*(.+?)(?:\n\s*\n|\n(?:(?:Phone|Tel|Email|Fax|Contact|Phone\s*No|Tel\.?|Mob(?:ile)?)\s*[:=\-]))',
        r'(?:Ship\s*To|Shipping\s*Address|Delivery\s*Address)\s*[:=\-]?\s*\n?\s*(.+)',
    ]
    for pat in ship_patterns:
        m = re.search(pat, normalized, re.IGNORECASE | re.DOTALL)
        if m:
            val = m.group(1).strip()
            # Clean trailing junk
            val = re.sub(r'\s+', ' ', val).strip()
            if val and len(val) > 2:
                po_data.shipping_address = val
                break

    # --- Fallback: Extract amount/total if present (for display) ---
    total_match = re.search(
        r'(?:Grand\s*)?Total\s*[:=\-]?\s*[\$₹]?\s*([\d,]+\.?\d*)',
        normalized, re.IGNORECASE
    )
    if total_match:
        po_data.payment_terms = (po_data.payment_terms or "") + f" | Total: {total_match.group(1)}"

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
