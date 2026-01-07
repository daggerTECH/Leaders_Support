import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret")

    # ============================
    # EMAIL (SMTP)
    # ============================
    MAIL_SERVER = "smtp.gmail.com"
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False

    MAIL_USERNAME = os.environ.get("EMAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = MAIL_USERNAME

    # ============================
    # DATABASE
    # ============================
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ============================
    # SLACK
    # ============================
    SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")

    # ============================
    # FILE UPLOADS
    # ============================
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB per file
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

    # Relative to Flask static folder → app/static/uploads
    UPLOAD_FOLDER = "uploads"

    # ============================
    # EMAIL → TICKET RULES
    # ============================
    TICKET_INBOX = "clientsupport@leaders.st"

    ALLOWED_SENDER_EMAILS = {
        "specialedflint@gmail.com",
        "joel@vecchio-law.com",
        "grandelaw@live.com",
        "mhumble@rhodes-humble.com",
    }

    ALLOWED_SENDER_DOMAINS = {
        "vecchio-law.com",
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
    }

