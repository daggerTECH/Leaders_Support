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
# INIT FLASK APP (ISOLATED, SAFE)
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
EMAIL_USER = "primeadsdigital@gmail.com"
EMAIL_PASS = "mwwe grms mazj yqeg"

socket.setdefaulttimeout(30)

# ============================================================
# SMTP CONFIG (AUTO-REPLY)
# ============================================================
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = EMAIL_USER
SMTP_PASS = EMAIL_PASS


ALLOWED_SENDER_EMAILS = {
    "specialedflint@gmail.com",
    "joel@vecchio-law.com",
    "grandelaw@live.com",
    "mhumble@rhodes-humble.com",
}

ALLOWED_SENDER_DOMAINS = {
    "kplitigators.com",
    "kksblaw.com",
    "aavlawfirm.com",
    "grittonlaw.com",
    "brandpeters.com",
    "kahnlawfirm.com",
    "madialawfirm.com",
    "foleygriffin.com",
    "morganbourque.com",
    "woodlandsattorneys.com",
    "tedfordlaw.com",
    "texascountrytitle.com",
    "shanehinch.com",
    "fortheworkers.com",
    "ufkeslaw.com",
    "webbstokessparks.com",
    "amatteroflaw.com",
    "edwardflintlawyer.com",
    "jdsmithlaw.com",
    "adllaw.org",
    "davesautosarasota.com",
    "longwelllawyers.com",
    "perniklaw.com",
    "vecchio-law.com",
    "vecchioinjurylaw.com",
    "rhodes-humble.com",
    "awclawyer.com",
    "fresnodefense.com",
    "nh-lawyers.com",
    "kaleitalawfirm.com",
    "juliolawfirm.com",
    "skierlawfirm.com",
    "mccormackpc.com",
    "snowlawfirm.com",
    "grandelaw.com",
    "frederickslaw.net",
    "caworkinjurylaw.com",
    "nathanmillerlaw.com",
    "willislaw.com",
    "restivolaw.com",
    "lannenlawpllc.com",
}

# ============================================================
# TICKET GENERATION FILTER
# ============================================================
def should_generate_ticket(sender_email: str, recipient_email: str) -> bool:
    sender_email = sender_email.lower().strip()
    recipient_email = recipient_email.lower().strip()

    # 1️⃣ Must be sent TO leaders.st
    if not recipient_email.endswith("@leaders.st"):
        return False

    # 2️⃣ Prevent internal loops
    if sender_email.endswith("@leaders.st"):
        return False

    sender_domain = sender_email.split("@")[-1]

    # 3️⃣ Explicit allow
    if sender_email in ALLOWED_SENDER_EMAILS:
        return True

    # 4️⃣ Domain allow
    if sender_domain in ALLOWED_SENDER_DOMAINS:
        return True

    print(f"🚫 Blocked sender: {sender_email}")
    return False


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
# CREATE TICKET (SAFE + DEDUPLICATED)
# ============================================================
def create_ticket(session, sender, subject, body, message_id):
    # ----------------------------
    # Prevent duplicate email
    # ----------------------------
    exists = session.execute(
        text("SELECT id FROM tickets WHERE message_id = :mid LIMIT 1"),
        {"mid": message_id}
    ).fetchone()

    if exists:
        print(f"🔁 Duplicate email ignored (message_id={message_id})")
        return None

    try:
        # ----------------------------
        # Insert ticket FIRST
        # ----------------------------
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

        # ----------------------------
        # Update ticket_code
        # ----------------------------
        session.execute(
            text("""
                UPDATE tickets
                SET ticket_code = :code
                WHERE id = :id
            """),
            {"code": ticket_code, "id": ticket_id}
        )

        # ----------------------------
        # 🔔 NOTIFY ALL ADMINS
        # ----------------------------
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

        print(f"✅ NEW TICKET CREATED: {ticket_code} from {sender}")
        return ticket_code

    except Exception as e:
        session.rollback()
        print("❌ Ticket creation failed:", e)
        return None

# ============================================================
# AUTO REPLY
# ============================================================
#def send_auto_reply(to_email, ticket_code, original_msg):
#    import smtplib
#    from email.mime.text import MIMEText
#    from email.mime.multipart import MIMEMultipart
#    import time

#    print("📨 Preparing auto-reply...")

#    try:
        # ⏳ Small delay prevents Gmail suppression
#        time.sleep(3)

#        msg = MIMEMultipart()
#        msg["From"] = "Leaders Support <danny.villanueva@leaders.st>"
#        msg["To"] = to_email
#        msg["Subject"] = f"Re: Ticket {ticket_code} received"
#        msg["Reply-To"] = "primeadsdigital@gmail.com"

        # 🔗 Reference original email (CRITICAL)
#        if original_msg.get("Message-ID"):
#            msg["In-Reply-To"] = original_msg.get("Message-ID")
#            msg["References"] = original_msg.get("Message-ID")

        # ✅ Mark as auto-reply (but NOT bulk)
#        msg["Auto-Submitted"] = "auto-replied"

#        body = f"""
#Hello,

#Thank you for contacting Leaders Support.

#We have received your request and created a support ticket.

#Ticket Number: {ticket_code}

#Our team will review your concern and get back to you shortly.
#You may reply to this email to add more information.

#Best regards,
#Leaders Support Team
#"""
#        msg.attach(MIMEText(body, "plain"))

#        server = smtplib.SMTP("smtp.gmail.com", 587, timeout=20)
#        server.ehlo()
#        server.starttls()
#        server.ehlo()
#        server.login(SMTP_USER, SMTP_PASS)

#        server.sendmail(
#            "primeadsdigital@gmail.com",
#            to_email,
#            msg.as_string()
#        )

#        server.quit()
#        print(f"✅ Auto-reply delivered to {to_email}")

#    except Exception as e:
#        print("❌ AUTO-REPLY FAILED")
#        print(type(e).__name__, ":", e)

# ============================================================
# PROCESS LATEST EMAIL ONLY
# ============================================================
def process_latest_email(mail, session):
    last_uid = get_last_uid()

    # ONLY fetch emails newer than last UID
    result, data = mail.uid("search", None, f"(UID {last_uid + 1}:*)")
    uids = data[0].split()

    if not uids:
        return False

    uid = uids[-1]  # newest ONLY

    result, msg_data = mail.uid("fetch", uid, "(RFC822)")
    msg = email.message_from_bytes(msg_data[0][1])

    message_id = msg.get("Message-ID")
    if not message_id:
        message_id = f"fallback-{uid.decode()}"

    # DB-level dedupe (final safety)
    exists = session.execute(
        text("SELECT 1 FROM tickets WHERE message_id = :mid"),
        {"mid": message_id}
    ).fetchone()

    if exists:
        save_last_uid(int(uid))
        return False

    sender = normalize_sender(msg.get("From"))
    recipient = email.utils.parseaddr(msg.get("To"))[1]
    
    if not should_generate_ticket(sender, recipient):
        save_last_uid(int(uid))
        return False

    subject_raw, encoding = decode_header(msg.get("Subject"))[0]
    subject = subject_raw.decode(encoding or "utf-8") if isinstance(subject_raw, bytes) else subject_raw
    subject = subject.strip() if subject else "(No Subject)"
    
    # --------------------------------------------------
    # 🚫 IGNORE REPLIES TO EXISTING TICKETS
    # --------------------------------------------------
    in_reply_to = msg.get("In-Reply-To")
    references = msg.get("References")

    # Subject-based reply detection
    is_reply_subject = subject.lower().startswith("re:")
    
    if in_reply_to or references or is_reply_subject:
        print("↩️ Email reply detected — no new ticket created")
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

    if not body:
        body = "(No content)"

    ticket_code = create_ticket(session, sender, subject, body, message_id)

    if ticket_code:
        send_auto_reply(sender, ticket_code, msg)

    # ✅ Update UID marker
    save_last_uid(int(uid))

    return True


# ============================================================
# IMAP IDLE LOOP (STABLE)
# ============================================================
def idle_listener():
    with flask_app.app_context():
        session = flask_app.session()
        backoff = 5

        print("📩 Waiting for NEW incoming email...")

        while True:
            try:
                mail = imaplib.IMAP4_SSL(IMAP_HOST)
                mail.login(EMAIL_USER, EMAIL_PASS)
                mail.select("INBOX")

                # Enter IDLE
                mail.send(b"IDLE\r\n")

                try:
                    line = mail.readline()  # block quietly

                except socket.timeout:
                    pass  # normal Gmail behavior

                finally:
                    # Exit IDLE cleanly
                    mail.send(b"DONE\r\n")

                # 🔑 ALWAYS check UNSEEN once after IDLE exits
                processed = process_latest_email(mail, session)

                mail.logout()

                if processed:
                    time.sleep(2)  # small cooldown after success

            except Exception as e:
                print(f"🔄 IMAP reconnect: {e}")
                time.sleep(backoff)
                backoff = min(backoff * 2, 120)


# ============================================================
# START
# ============================================================
if __name__ == "__main__":
    idle_listener()






