import os
import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from dotenv import load_dotenv

load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.office365.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() == "true"


async def send_email(
    to: str,
    subject: str,
    body: str,
    cc: str = None,
    bcc: str = None,
    attachment_path: str = None,
    attachment_name: str = None,
) -> dict:
    """Send an email via Outlook SMTP."""
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        return {
            "success": False,
            "error": "SMTP credentials not configured. Set SMTP_USERNAME and SMTP_PASSWORD in .env"
        }

    msg = MIMEMultipart()
    msg["From"] = SMTP_USERNAME
    msg["To"] = to
    msg["Subject"] = subject

    if cc:
        msg["Cc"] = cc

    msg.attach(MIMEText(body, "plain"))

    if attachment_path and os.path.exists(attachment_path):
        with open(attachment_path, "rb") as f:
            att = MIMEApplication(f.read(), _subtype="pdf")
            att_name = attachment_name or os.path.basename(attachment_path)
            att.add_header("Content-Disposition", "attachment", filename=att_name)
            msg.attach(att)

    recipients = [to]
    if cc:
        recipients.extend(cc.split(","))
    if bcc:
        recipients.extend(bcc.split(","))

    try:
        await aiosmtplib.send(
            msg,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            username=SMTP_USERNAME,
            password=SMTP_PASSWORD,
            use_tls=SMTP_USE_TLS,
            recipients=recipients,
        )
        return {"success": True, "message": f"Email sent to {to}"}
    except Exception as e:
        return {"success": False, "error": str(e)}
