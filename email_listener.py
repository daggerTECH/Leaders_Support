import imaplib
import email
from email.header import decode_header
from sqlalchemy import text
from app import create_app
import socket
import re
import time
from app.utils.notifier import notify_user

# ============================================================
# INIT FLASK APP
# ============================================================
flask_app = create_app()

# ============================================================
# UID Tracker
# ============================================================
UID_FILE = "last_uid.txt"

def get_last_uid():
    try:
        with open(UID_FILE, "r") as f:
            return int(f.read().strip())
    except:
        return 0

def save_last_uid(uid):
    with open(UID_FILE, "w") as f:
        f.write(str(uid))

# ============================================================
# IMAP CONFIG
# ============================================================
IMAP_HOST = "imap.gmail.com"
EMAIL_USER = "danny.villanueva@leaders.st"
EMAIL_PASS = "gewm ihry cfgn jnds"

socket.setdefaulttimeout(30)

# ============================================================
# LOAD CONFIG
# ============================================================
ALLOWED_SENDER_EMAILS = set(
    e.lower() for e in flask_app.config.get("ALLOWED_SENDER_EMAILS", [])
)

ALLOWED_SENDER_DOMAINS = set(
    d.lower() for d in flask_app.config.get("ALLOWED_SENDER_DOMAINS", [])
)

ALLOWED_INTERNAL_RECIPIENTS = {
    "madison@leaders.st",
    "cain@leaders.st",
}

# ============================================================
# UTILITIES
# ============================================================
def normalize_sender(raw_sender):
    sender = email.utils.parseaddr(raw_sender)[1]
    sender = sender.lower().strip()
    sender = re.sub(r"[ \u200b\u200c\u200d\u2060]+", "", sender)
    return sender

def extract_recipients(msg):
    fields = ["To", "Cc", "Delivered-To", "X-Original-To"]
    recipients = []

    for f in fields:
        raw = msg.get(f, "")
        if raw:
            addresses = email.utils.getaddresses([raw])
            recipients.extend(addr.lower() for _, addr in addresses)

    return recipients

def is_allowed_client(sender_email):
    domain = sender_email.split("@")[-1]
    return (
        sender_email in ALLOWED_SENDER_EMAILS
        or domain in ALLOWED_SENDER_DOMAINS
    )

def sent_to_monitored_staff(recipients):
    return any(r in recipients for r in ALLOWED_INTERNAL_RECIPIENTS)

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
        print("🔁 Duplicate email ignored")
        return None

    try:
        result = session.execute(
            text("""
                INSERT INTO tickets
                (email, description, status, priority, message_id, created_at, updated_at)
                VALUES (:email, :desc, 'Open', :priority, :mid, NOW(), NOW())
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

        admins = session.execute(
            text("SELECT id FROM users WHERE role = 'admin'")
        ).fetchall()

        for admin in admins:
            notify_user(
                session,
                admin.id,
                ticket_id,
                ticket_code,
                f"New ticket created: {ticket_code}"
            )

        session.commit()
        print(f"✅ Ticket created: {ticket_code}")
        return ticket_code

    except Exception as e:
        session.rollback()
        print("❌ Ticket creation failed:", e)
        return None

# ============================================================
# PROCESS EMAIL
# ============================================================
def process_latest_email(mail, session):
    last_uid = get_last_uid()

    result, data = mail.uid("search", None, f"(UID {last_uid + 1}:*)")
    uids = data[0].split()

    if not uids:
        return False

    uid = uids[-1]

    _, msg_data = mail.uid("fetch", uid, "(RFC822)")
    msg = email.message_from_bytes(msg_data[0][1])

    message_id = msg.get("Message-ID") or f"fallback-{uid.decode()}"

    sender = normalize_sender(msg.get("From"))
    recipients = extract_recipients(msg)

    # 🚫 Ignore internal senders
    if sender.endswith("@leaders.st"):
        save_last_uid(int(uid))
        return False

    # 🚫 Sender not allowed
    if not is_allowed_client(sender):
        save_last_uid(int(uid))
        return False

    # 🚫 Not sent to monitored staff
    if not sent_to_monitored_staff(recipients):
        save_last_uid(int(uid))
        return False

    subject_raw, encoding = decode_header(msg.get("Subject"))[0]
    subject = (
        subject_raw.decode(encoding or "utf-8")
        if isinstance(subject_raw, bytes)
        else subject_raw
    ) or "(No Subject)"

    # 🚫 Ignore replies
    if msg.get("In-Reply-To") or msg.get("References") or subject.lower().startswith("re:"):
        save_last_uid(int(uid))
        return False

    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                body = part.get_payload(decode=True).decode(errors="ignore")
                break
    else:
        body = msg.get_payload(decode=True).decode(errors="ignore")

    body = body or "(No content)"

    create_ticket(session, sender, subject, body, message_id)
    save_last_uid(int(uid))
    return True

# ============================================================
# IMAP LOOP
# ============================================================
def idle_listener():
    with flask_app.app_context():
        session = flask_app.session()
        print("📩 Listening for new emails...")

        while True:
            try:
                mail = imaplib.IMAP4_SSL(IMAP_HOST)
                mail.login(EMAIL_USER, EMAIL_PASS)
                mail.select("INBOX")

                mail.send(b"IDLE\r\n")
                try:
                    mail.readline()
                except socket.timeout:
                    pass
                finally:
                    mail.send(b"DONE\r\n")

                process_latest_email(mail, session)
                mail.logout()

            except Exception as e:
                print("🔄 IMAP reconnect:", e)
                time.sleep(10)

# ============================================================
# START
# ============================================================
if __name__ == "__main__":
    idle_listener()
