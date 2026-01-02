import imaplib
import email
from email.header import decode_header
from sqlalchemy import text
import socket
import re
import time
import os


# ============================================================
# IMAP CONFIG (FROM ENV)
# ============================================================
IMAP_HOST = "imap.gmail.com"
EMAIL_USER = os.getenv("EMAIL_USERNAME")
EMAIL_PASS = os.getenv("EMAIL_PASSWORD")

if not EMAIL_USER or not EMAIL_PASS:
    raise RuntimeError("❌ EMAIL_USERNAME or EMAIL_PASSWORD not set")


socket.setdefaulttimeout(30)


# ============================================================
# ALLOWED SENDERS
# ============================================================
ALLOWED_SENDERS = {
    "fromit8@gmail.com",
    "danny.villanueva@leaders.st",
    "momitabaligya@gmail.com",
}


# ============================================================
# UTIL: CLEAN SENDER
# ============================================================
def normalize_sender(raw_sender):
    sender = email.utils.parseaddr(raw_sender)[1]
    sender = sender.lower().strip()
    sender = re.sub(r"[ \u200b\u200c\u200d\u2060]+", "", sender)
    return sender


# ============================================================
# PRIORITY DETECTION
# ============================================================
def detect_priority(subject, body):
    text_data = f"{subject} {body}".lower()
    if any(k in text_data for k in ["urgent", "asap", "critical"]):
        return "High"
    if any(k in text_data for k in ["important", "soon"]):
        return "Medium"
    return "Low"


# ============================================================
# CREATE TICKET
# ============================================================
def create_ticket(session, sender, subject, body, message_id):
    exists = session.execute(
        text("SELECT 1 FROM tickets WHERE message_id = :mid"),
        {"mid": message_id}
    ).fetchone()

    if exists:
        return None

    result = session.execute(
        text("""
            INSERT INTO tickets
            (email, description, status, priority, message_id, created_at, updated_at)
            VALUES
            (:email, :desc, 'Open', :priority, :mid, NOW(), NOW())
        """),
        {
            "email": sender,
            "desc": body,
            "priority": detect_priority(subject, body),
            "mid": message_id
        }
    )

    ticket_id = result.lastrowid
    ticket_code = f"TCK-{ticket_id:05d}"

    session.execute(
        text("UPDATE tickets SET ticket_code = :code WHERE id = :id"),
        {"code": ticket_code, "id": ticket_id}
    )

    session.commit()
    print(f"✅ Ticket created: {ticket_code}")
    return ticket_code


# ============================================================
# AUTO REPLY
# ============================================================
def send_auto_reply(to_email, ticket_code, original_msg):
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    msg = MIMEMultipart()
    msg["From"] = "Leaders Support <primeadsdigital@gmail.com>"
    msg["To"] = to_email
    msg["Subject"] = f"Re: Ticket {ticket_code} received"

    if original_msg.get("Message-ID"):
        msg["In-Reply-To"] = original_msg.get("Message-ID")
        msg["References"] = original_msg.get("Message-ID")

    body = f"""
Hello,

Your support ticket has been received.

Ticket Number: {ticket_code}

We will get back to you shortly.

Regards,
Leaders Support
"""
    msg.attach(MIMEText(body, "plain"))

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(EMAIL_USER, EMAIL_PASS)
    server.sendmail(EMAIL_USER, to_email, msg.as_string())
    server.quit()


# ============================================================
# PROCESS EMAIL
# ============================================================
def process_latest_email(mail, session):
    result, data = mail.search(None, "UNSEEN")
    if result != "OK" or not data[0]:
        return

    for num in data[0].split():
        _, msg_data = mail.fetch(num, "(RFC822)")
        msg = email.message_from_bytes(msg_data[0][1])

        sender = normalize_sender(msg.get("From"))
        if sender not in ALLOWED_SENDERS:
            continue

        subject, enc = decode_header(msg.get("Subject"))[0]
        subject = subject.decode(enc or "utf-8") if isinstance(subject, bytes) else subject

        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode(errors="ignore")
                    break
        else:
            body = msg.get_payload(decode=True).decode(errors="ignore")

        message_id = msg.get("Message-ID", f"fallback-{num.decode()}")

        ticket_code = create_ticket(session, sender, subject, body, message_id)
        if ticket_code:
            send_auto_reply(sender, ticket_code, msg)


# ============================================================
# MAIN LOOP
# ============================================================
def run_listener(app):
    with app.app_context():
        session = app.session()
        print("📩 Email listener started")

        while True:
            try:
                mail = imaplib.IMAP4_SSL(IMAP_HOST)
                mail.login(EMAIL_USER, EMAIL_PASS)
                mail.select("INBOX")

                process_latest_email(mail, session)

                mail.logout()
                time.sleep(15)

            except Exception as e:
                print("🔄 IMAP error:", e)
                time.sleep(30)


# ============================================================
# START
# ============================================================
if __name__ == "__main__":
    from app import create_app
    flask_app = create_app()
    run_listener(flask_app)
