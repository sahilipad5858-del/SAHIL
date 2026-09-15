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

    # Normalize: add space after colons, fix merged words
    # "City :Sangamner" -> "City : Sangamner"
    # "PurchaseOrderNo" -> "Purchase Order No"
    normalized = raw_text
    normalized = re.sub(r'(\w)(:\s)', r'\1 ', normalized)
    normalized = re.sub(r'(\w)(:)', r'\1 ', normalized)

    lines = [line.strip() for line in normalized.split("\n") if line.strip()]
    full_text = "\n".join(lines)

    # --- PO Number ---
    # "PurchaseOrderNo : 40008434" or "Purchase Order No : 40008434"
    m = re.search(
        r'(?:Purchase\s*Order\s*No|P\.?O\.?\s*(?:No|Number|#))\s*[:=\-]?\s*(\d{4,})',
        full_text, re.IGNORECASE
    )
    if m:
        po_data.po_number = m.group(1).strip()

    # --- PO Date ---
    # "Date : 15.09.2026"
    m = re.search(
        r'(?:^|\n)\s*Date\s*[:=\-]?\s*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})',
        full_text, re.IGNORECASE
    )
    if m:
        po_data.po_date = m.group(1).strip()

    # --- Vendor Name ---
    # "TO, VendorCode-10011388\nMohitComputers" - TO can be mid-line
    m = re.search(
        r'TO[,:\s]*(?:Vendor\s*Code\s*[-=\s]*)?\d+\s*\n\s*(.+)',
        full_text, re.IGNORECASE
    )
    if m:
        val = m.group(1).strip()
        val = re.split(r'\n|(?:YAshwant|Vidyanagar|City|District|Phone|Email|GSTN)', val, flags=re.IGNORECASE)[0].strip()
        val = re.sub(r'([a-z])([A-Z])', r'\1 \2', val)
        po_data.vendor_name = val
    else:
        # Fallback: line after "TO," that's not a field label
        for i, line in enumerate(lines):
            if re.search(r'TO[,:\s]', line, re.IGNORECASE):
                # Check next few lines for vendor name
                for j in range(i+1, min(i+4, len(lines))):
                    candidate = lines[j].strip()
                    if candidate and not re.match(r'(?:YAshwant|Vidyanagar|City|District|Phone|Email|GSTN|Date|GST|Plant|Our|Your)', candidate, re.IGNORECASE):
                        val = re.sub(r'([a-z])([A-Z])', r'\1 \2', candidate)
                        po_data.vendor_name = val
                        break
                break

    # --- Vendor Email ---
    # Find the TO block and get email from there
    to_match = re.search(r'TO[,:\s].*?(?=Purchase\s*Order|We\s*are\s*pleased)', full_text, re.IGNORECASE | re.DOTALL)
    if to_match:
        to_block = to_match.group(0)
        m = re.search(r'Email\s*[:=\-]?\s*([\w\.\-]+@[\w\.\-]+\.\w{2,})', to_block, re.IGNORECASE)
        if m:
            po_data.vendor_email = m.group(1)
    if not po_data.vendor_email:
        # Fallback: find all emails, use the second one (first is buyer)
        all_emails = re.findall(r'([\w\.\-]+@[\w\.\-]+\.\w{2,})', full_text, re.IGNORECASE)
        if len(all_emails) >= 2:
            po_data.vendor_email = all_emails[1]  # Second email is vendor
        elif all_emails:
            po_data.vendor_email = all_emails[0]

    # --- Delivery Date ---
    m = re.search(r'Delivery\s*Period\s*[:=\-]?\s*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})', full_text, re.IGNORECASE)
    if m:
        po_data.delivery_date = m.group(1).strip()

    # --- Payment Terms ---
    m = re.search(r'Payment\s*Terms?\s*[:=\-]?\s*(.+?)(?:\n|$)', full_text, re.IGNORECASE)
    if m:
        val = m.group(1).strip()
        # Clean merged words
        val = re.sub(r'(\d+)(Working)', r'\1 \2', val)
        val = re.sub(r'(Working)(days)', r'\1 \2', val)
        val = re.sub(r'(days)(from)', r'\1 \2', val)
        val = re.sub(r'(from)(the)', r'\1 \2', val)
        val = re.sub(r'(the)(Gate)', r'\1 \2', val)
        val = re.sub(r'(Gate)(Entry)', r'\1 \2', val)
        val = re.sub(r'(Entry)(date)', r'\1 \2', val)
        po_data.payment_terms = val

    # --- Shipping Address (To be delivered at) ---
    m = re.search(r'To\s*be\s*delivered\s*at\s*[:=\-]?\s*(.+?)(?:\n|$)', full_text, re.IGNORECASE)
    if m:
        val = m.group(1).strip()
        # Fix double commas
        val = re.sub(r',,+', ',', val)
        po_data.shipping_address = val
    else:
        # Fallback: build from City/District/State/Pin
        city = re.search(r'City\s*[:=\-]?\s*(\w+)', full_text, re.IGNORECASE)
        dist = re.search(r'District\s*[:=\-]?\s*(\w+)', full_text, re.IGNORECASE)
        state = re.search(r'State\s*[:=\-]?\s*(\w+)', full_text, re.IGNORECASE)
        pin = re.search(r'Pin\s*[:=\-]?\s*(\d+)', full_text, re.IGNORECASE)
        parts = []
        if city: parts.append(city.group(1))
        if dist: parts.append(dist.group(1))
        if state: parts.append(state.group(1))
        if pin: parts.append(pin.group(1))
        if parts:
            po_data.shipping_address = ", ".join(parts)

    # --- Buyer Name ---
    m = re.search(r'M/s\s*([A-Za-z][\w\s&]+?)(?:\s*\n|\s*50/2|\s*Regd)', full_text, re.IGNORECASE)
    if m:
        val = m.group(1).strip()
        val = re.sub(r'([a-z])([A-Z])', r'\1 \2', val)
        po_data.buyer_name = val

    # --- Items ---
    items = []

    # Try space-separated format: "1 DataCable5mtr 1.00 EA 650.00 -99.15 550.85"
    # Must start with line number (small integer) followed by description
    item_rows = re.findall(
        r'(?:^|\n)\s*(\d{1,3})\s+([A-Za-z][\w\s]+?)\s+([\d,.]+)\s+(EA|NOS|PCS|KG|MT|SET|BOX|UNT|NO|Nos|EA)\s+([\d,.]+)\s+([-\d,.]+)\s+([\d,.]+)',
        full_text, re.IGNORECASE
    )
    for row in item_rows:
        sr, desc, qty, unit, rate, disc, value = row
        desc = re.sub(r'([a-z])([A-Z])', r'\1 \2', desc.strip())
        desc = re.sub(r'([a-z])(\d)', r'\1 \2', desc)  # "Cable5mtr" -> "Cable 5mtr"
        desc = re.sub(r'(\d)([a-zA-Z])', r'\1 \2', desc)  # "5mtr" -> "5 mtr"
        desc = re.sub(r'Remark.*', '', desc, flags=re.IGNORECASE).strip()
        items.append({
            'sr_no': sr.strip(),
            'description': desc,
            'quantity': qty.strip(),
            'unit': unit.strip(),
            'rate': rate.strip(),
            'discount': disc.strip().split('\n')[0].strip(),
            'value': value.strip().split('\n')[0].strip(),
        })

    # Fallback: pipe-separated table rows
    if not items:
        pipe_rows = re.findall(
            r'(\d{1,3})\s*\|\s*(.+?)\s*\|.*?([\d,.]+)\s*\|\s*(EA|NOS|PCS|KG|MT|SET|BOX|UNT|NO|Nos)\s*\|\s*([\d,.]+)\s*\|.*?([-\d,.]+)\s*\|.*?([\d,.]+)',
            full_text, re.IGNORECASE
        )
        for row in pipe_rows:
            sr, desc, qty, unit, rate, disc, value = row
            desc = re.sub(r'([a-z])([A-Z])', r'\1 \2', desc.strip().split('\n')[0])
            desc = re.sub(r'([a-z])(\d)', r'\1 \2', desc)
            desc = re.sub(r'(\d)([a-zA-Z])', r'\1 \2', desc)
            desc = re.sub(r'Remark.*', '', desc, flags=re.IGNORECASE).strip()
            items.append({
                'sr_no': sr.strip(),
                'description': desc,
                'quantity': qty.strip(),
                'unit': unit.strip(),
                'rate': rate.strip(),
                'discount': disc.strip(),
                'value': value.strip(),
            })

    po_data.items = items

    # --- Total Amount ---
    m = re.search(r'Total\s*Amount\s*[:=\-]?\s*([\d,.]+)', full_text, re.IGNORECASE)
    if m:
        po_data.total_amount = m.group(1).strip()
    else:
        m = re.search(r'(?:Grand\s*)?Total\s*[:=\-]?\s*([\d,.]+)', full_text, re.IGNORECASE)
        if m:
            po_data.total_amount = m.group(1).strip()

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
