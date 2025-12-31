from flask import Blueprint, render_template, request, redirect, url_for, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Message
from sqlalchemy import text
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature

# Correct imports for your project structure
from app import login_manager, mail
from models import User           # FIXED HERE
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Correct email template imports
from app.email_templates import verification_email_html, reset_password_email_html

auth_bp = Blueprint("auth", __name__)

# Serializer for secure tokens
ts = URLSafeTimedSerializer("leaders_secret")

# Rate limiter (5 attempts per 10 minutes ONLY for login)
limiter = Limiter(key_func=get_remote_address)


# ============================
# LOGIN (RATE LIMITED)
# ============================
@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per 10 minutes")
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        session = current_app.session()

        user = session.execute(
            text("SELECT id, email, password, role, is_verified FROM users WHERE email = :email"),
            {"email": email}
        ).fetchone()

        if not user:
            return render_template("login.html", error="User not found")

        if not check_password_hash(user[2], password):
            return render_template("login.html", error="Incorrect password")

        if not user[4]:  # is_verified == 0
            return render_template("login.html",
                                   error="Please verify your email first. Check your inbox.")

        user_obj = User(user[0], user[1], user[3])
        login_user(user_obj)

        next_page = request.args.get("next")
        return redirect(next_page or url_for("ticket.dashboard"))

    return render_template("login.html")


# ============================
# LOGOUT
# ============================
@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


# ============================
# SEND VERIFICATION EMAIL
# ============================
def send_verification_email(email):
    token = ts.dumps(email, salt="email-verify")
    verify_url = f"http://localhost:5000/verify/{token}"

    msg = Message(
        subject="Verify Your Leaders.st Account",
        sender=current_app.config["MAIL_USERNAME"],
        recipients=[email],
        html=verification_email_html(verify_url)
    )
    mail.send(msg)


# ============================
# VERIFY EMAIL LINK
# ============================
@auth_bp.route("/verify/<token>")
def verify_email(token):
    try:
        email = ts.loads(token, salt="email-verify", max_age=3600)
    except Exception:
        return "Verification link is invalid or expired."

    session = current_app.session()
    session.execute(
        text("UPDATE users SET is_verified = 1 WHERE email = :email"),
        {"email": email}
    )
    session.commit()
    session.close()

    return render_template("verify_notification.html")

# ============================
# FORGOT PASSWORD PAGE
# ============================
@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form["email"]

        session = current_app.session()
        user = session.execute(
            text("SELECT email FROM users WHERE email = :email"),
            {"email": email}
        ).fetchone()

        if not user:
            return render_template("forgot_password.html",
                                   error="Email not found")

        token = ts.dumps(email, salt="reset-password")
        reset_url = f"http://localhost:5000/reset-password/{token}"

        msg = Message(
            subject="Reset Your Leaders.st Password",
            sender=current_app.config["MAIL_USERNAME"],
            recipients=[email],
            html=reset_password_email_html(reset_url)
        )
        mail.send(msg)

        return render_template("forgot_password.html",
                               success="Password reset email sent!")

    return render_template("forgot_password.html")


# ============================
# RESET PASSWORD PAGE
# ============================
@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    try:
        email = ts.loads(token, salt="reset-password", max_age=3600)
    except (SignatureExpired, BadSignature):
        return "Reset link expired or invalid"

    if request.method == "POST":
        new_password = request.form["password"]
        hashed = generate_password_hash(new_password)

        session = current_app.session()
        session.execute(
            text("UPDATE users SET password = :pw WHERE email = :email"),
            {"pw": hashed, "email": email}
        )
        session.commit()
        session.close()

        return redirect(url_for("auth.login"))

    return render_template("reset_password.html")
