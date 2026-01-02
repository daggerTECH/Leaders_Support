import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret")

    # Gmail SMTP
    MAIL_SERVER = "smtp.gmail.com"
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False

    MAIL_USERNAME = os.environ.get("EMAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")

    MAIL_DEFAULT_SENDER = MAIL_USERNAME

    # SQLAlchemy Database
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # SLACK NOTIFIER
    SLACK_WEBHOOK_URL = "SLACK_WEBHOOK_URL"

    # ATTACHMENTS
    UPLOAD_FOLDER = "static/uploads"
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB per file
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}












