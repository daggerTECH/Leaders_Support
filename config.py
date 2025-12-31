import os

class Config:
    SECRET_KEY = "leaders_secret"

    # Gmail SMTP
    MAIL_SERVER = "smtp.gmail.com"
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False

    MAIL_USERNAME = "danny.villanueva@leaders.st"
    MAIL_PASSWORD = "wsut sfvc ctja yofz"

    # SQLAlchemy Database
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # SLACK NOTIFIER
    SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/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"
