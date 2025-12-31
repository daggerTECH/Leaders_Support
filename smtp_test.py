import smtplib

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "primeadsdigital@gmail.com"
SMTP_PASS = "mwwe grms mazj yqeg"

server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
server.starttls()
server.login(SMTP_USER, SMTP_PASS)
server.sendmail(
    SMTP_USER,
    SMTP_USER,
    "Subject: SMTP Test\n\nThis is a test email."
)
server.quit()

print("SMTP TEST SUCCESS")
