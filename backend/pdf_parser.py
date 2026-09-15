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
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    if row:
                        raw_text += " | ".join([str(c) if c else "" for c in row]) + "\n"

    po_data = POData(raw_text=raw_text)

    # Normalize: collapse multiple spaces, strip lines
    lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
    normalized = "\n".join(lines)

    # --- PO Number ---
    # Matches: "Purchase Order No: 40008434", "P.O. No: 12345", "PO#: ABC-123"
    m = re.search(
        r'(?:Purchase\s*Order|P\.?O\.?)\s*(?:Number|No|#|\.?)\s*[:=\-]?\s*([A-Za-z0-9][\w\-/]*)',
        normalized, re.IGNORECASE
    )
    if m:
        po_data.po_number = m.group(1).strip()

    # --- PO Date ---
    # Matches: "Date: 15.09.2026", "Date: 15/09/2026", "Dated: 15 Sep 2026"
    m = re.search(
        r'(?:Date|Dated|Order\s*Date|PO\s*Date)\s*[:=\-]?\s*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})',
        normalized, re.IGNORECASE
    )
    if m:
        po_data.po_date = m.group(1).strip()
    else:
        m = re.search(
            r'(?:Date|Dated)\s*[:=\-]?\s*(\d{1,2}\s+\w+\s+\d{2,4})',
            normalized, re.IGNORECASE
        )
        if m:
            po_data.po_date = m.group(1).strip()

    # --- Vendor Name (the "TO:" section vendor) ---
    # Format: "TO: Vendor Code - XXXX\nVendorName\nAddress..."
    m = re.search(
        r'TO:\s*(?:Vendor\s*Code\s*[:=\-]?\s*[\w\-]+\s*\n\s*)(.+)',
        normalized, re.IGNORECASE
    )
    if m:
        po_data.vendor_name = m.group(1).strip()
    else:
        # Fallback: look for vendor name after "TO:" on same line
        m = re.search(r'TO:\s*(.+)', normalized, re.IGNORECASE)
        if m:
            val = m.group(1).strip()
            if val and not re.match(r'Vendor\s*Code', val, re.IGNORECASE):
                po_data.vendor_name = val

    # --- Vendor Email (in the TO: vendor block) ---
    # Find the TO: block and extract email from it
    to_block_match = re.search(r'TO:.*?(?=Purchase\s*Order|Items|ITEMS|\n\n\n)', normalized, re.IGNORECASE | re.DOTALL)
    if to_block_match:
        to_block = to_block_match.group(0)
        email_match = re.search(r'Email:\s*([\w\.\-]+@[\w\.\-]+\.\w{2,})', to_block, re.IGNORECASE)
        if email_match:
            po_data.vendor_email = email_match.group(1)
        else:
            # Fallback: any email in the block
            email_match = re.search(r'([\w\.\-]+@[\w\.\-]+\.\w{2,})', to_block, re.IGNORECASE)
            if email_match:
                po_data.vendor_email = email_match.group(1)
    else:
        # Fallback: find all emails, skip buyer emails
        all_emails = re.findall(r'([\w\.\-]+@[\w\.\-]+\.\w{2,})', normalized, re.IGNORECASE)
        buyer_emails = re.findall(r'Email:\s*([\w\.\-]+@[\w\.\-]+\.\w{2,})', normalized[:normalized.find('TO:') if 'TO:' in normalized else 0], re.IGNORECASE)
        vendor_emails = [e for e in all_emails if e not in buyer_emails]
        if vendor_emails:
            po_data.vendor_email = vendor_emails[0]

    # --- Delivery Date ---
    m = re.search(
        r'(?:Delivery|Ship|Expected|Required|Need|ETA)\s*(?:Date|By)?\s*[:=\-]?\s*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})',
        normalized, re.IGNORECASE
    )
    if m:
        po_data.delivery_date = m.group(1).strip()

    # --- Payment Terms ---
    payment_patterns = [
        r'(?:Payment\s*Terms?|Terms?\s*(?:of\s*)?Payment|P\.?T\.?)\s*[:=\-]?\s*(.+)',
        r'(Net\s*\d+)',
        r'(COD|CIA|CWO|CAD)',
    ]
    for pat in payment_patterns:
        m = re.search(pat, normalized, re.IGNORECASE)
        if m:
            val = m.group(1).strip().split("\n")[0].strip()
            if val:
                po_data.payment_terms = val
                break

    # --- Shipping Address ---
    ship_patterns = [
        r'(?:Ship\s*To|Shipping\s*(?:Address|Location)|Delivery\s*Address|Deliver\s*To)\s*[:=\-]?\s*\n?\s*(.+?)(?:\n\s*\n|\n(?:(?:Phone|Tel|Email|Fax|Contact)\s*[:=\-]))',
        r'(?:Ship\s*To|Shipping\s*Address|Delivery\s*Address)\s*[:=\-]?\s*\n?\s*(.+)',
    ]
    for pat in ship_patterns:
        m = re.search(pat, normalized, re.IGNORECASE | re.DOTALL)
        if m:
            val = re.sub(r'\s+', ' ', m.group(1)).strip()
            if val and len(val) > 2:
                po_data.shipping_address = val
                break

    # --- Buyer Name (the company issuing the PO) ---
    # First line after "PURCHASE ORDER" header is usually the buyer
    buyer_match = re.search(r'(?:M/s\.?|M/s)\s*(.+)', normalized, re.IGNORECASE)
    if buyer_match:
        po_data.buyer_name = buyer_match.group(1).strip().split("\n")[0].strip()

    # --- Items (line items with description, qty, rate) ---
    items = []
    item_blocks = re.split(r'Sr\s*No\s*[:=\-]?\s*\d+', normalized, flags=re.IGNORECASE)
    for block in item_blocks[1:]:  # Skip first (before any Sr No)
        item = {}
        desc_m = re.search(r'(?:Item\s*)?Description\s*[:=\-]?\s*(.+)', block, re.IGNORECASE)
        if desc_m:
            item['description'] = desc_m.group(1).strip().split("\n")[0].strip()
        qty_m = re.search(r'Quantity\s*[:=\-]?\s*([\d.]+)', block, re.IGNORECASE)
        if qty_m:
            item['quantity'] = qty_m.group(1)
        rate_m = re.search(r'Rate\s*(?:/\s*Unit)?\s*(?:\(INR\))?\s*[:=\-]?\s*([\d,.]+)', block, re.IGNORECASE)
        if rate_m:
            item['rate'] = rate_m.group(1)
        value_m = re.search(r'Value\s*[:=\-]?\s*([\d,.]+)', block, re.IGNORECASE)
        if value_m:
            item['value'] = value_m.group(1)
        if item:
            items.append(item)
    po_data.items = items

    # --- Total Amount ---
    total_patterns = [
        r'(?:Grand\s*)?Total\s*(?:Value|Amount|INR)?\s*[:=\-]?\s*[\$₹]?\s*([\d,]+\.?\d*)',
        r'(?:Sub\s*Total|Amount\s*Payable)\s*[:=\-]?\s*[\$₹]?\s*([\d,]+\.?\d*)',
    ]
    for pat in total_patterns:
        m = re.search(pat, normalized, re.IGNORECASE)
        if m:
            po_data.total_amount = m.group(1).strip()
            break

    return po_data


def generate_email_draft(po_data: POData) -> dict:
    """Generate a draft email based on extracted PO data."""
    vendor = po_data.vendor_name or "Vendor"
    buyer = po_data.buyer_name or "Sir/Madam"
    po_num = po_data.po_number or "N/A"
    po_date = po_data.po_date or "N/A"
    delivery = po_data.delivery_date or "N/A"
    terms = po_data.payment_terms or "N/A"
    address = po_data.shipping_address or "N/A"
    total = po_data.total_amount or "N/A"

    subject = f"Acknowledgment of Purchase Order #{po_num}"

    # Build items list for email
    items_text = ""
    if po_data.items:
        for i, item in enumerate(po_data.items, 1):
            desc = item.get('description', 'N/A')
            qty = item.get('quantity', 'N/A')
            rate = item.get('rate', 'N/A')
            val = item.get('value', 'N/A')
            items_text += f"  {i}. {desc} - Qty: {qty}, Rate: INR {rate}, Value: INR {val}\n"
    else:
        items_text = "  (Please refer to attached PO)\n"

    body = f"""Dear {buyer},

Thank you for your Purchase Order #{po_num} dated {po_date}.

We acknowledge receipt of your order and confirm the following details:

PO Number: {po_num}
PO Date: {po_date}
Vendor: {vendor}
Delivery Date: {delivery}
Payment Terms: {terms}
Shipping Address: {address}

Order Items:
{items_text}
Total Amount: INR {total}

We will process your order promptly. If you have any questions, please don't hesitate to reach out.

Best Regards,
{vendor}
"""

    to_email = po_data.vendor_email or ""

    return {
        "to": to_email,
        "subject": subject,
        "body": body,
        "po_data": po_data
    }
