from flask import Blueprint, render_template, request, redirect, url_for, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Message
from sqlalchemy import text
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature

from app import login_manager, mail
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from app.email_templates import verification_email_html, reset_password_email_html
from models import User

auth_bp = Blueprint("auth", __name__)

# Limiter (attached in create_app)
limiter = Limiter(key_func=get_remote_address)


# ============================================================
# LOGIN
# ============================================================
@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per 10 minutes")
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        session = current_app.session()

        user = session.execute(
            text("""
                SELECT id, email, password, role, is_verified
                FROM users
                WHERE email = :email
            """),
            {"email": email}
        ).fetchone()

        session.close()

        if not user:
            return render_template("login.html", error="User not found")

        if not check_password_hash(user.password, password):
            return render_template("login.html", error="Incorrect password")

        if not user.is_verified:
            return render_template(
                "login.html",
                error="Please verify your email first. Check your inbox."
            )

        login_user(User(user.id, user.email, user.role))
        return redirect(url_for("ticket.dashboard"))

    return render_template("login.html")


# ============================================================
# LOGOUT
# ============================================================
@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


# ============================================================
# SEND VERIFICATION EMAIL (SAFE)
# ============================================================
def send_verification_email(email: str):
    serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    token = serializer.dumps(email, salt="email-verify")

    verify_url = url_for(
        "auth.verify_email",
        token=token,
        _external=True
    )

    msg = Message(
        subject="Verify Your Leaders.st Account",
        sender=current_app.config["EMAIL_USERNAME"],
        recipients=[email],
        html=verification_email_html(verify_url)
    )

    mail.send(msg)


# ============================================================
# VERIFY EMAIL
# ============================================================
@auth_bp.route("/verify/<token>")
def verify_email(token):
    serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])

    try:
        email = serializer.loads(
            token,
            salt="email-verify",
            max_age=3600
        )
    except (SignatureExpired, BadSignature):
        return "Verification link is invalid or expired."

    session = current_app.session()
    session.execute(
        text("UPDATE users SET is_verified = 1 WHERE email = :email"),
        {"email": email}
    )
    session.commit()
    session.close()

    return render_template("verify_notification.html")


# ============================================================
# FORGOT PASSWORD
# ============================================================
@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form["email"].strip().lower()

        session = current_app.session()
        user = session.execute(
            text("SELECT id FROM users WHERE email = :email"),
            {"email": email}
        ).fetchone()
        session.close()

        if not user:
            return render_template(
                "forgot_password.html",
                error="Email not found"
            )

        serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
        token = serializer.dumps(email, salt="reset-password")

        reset_url = url_for(
            "auth.reset_password",
            token=token,
            _external=True
        )

        msg = Message(
            subject="Reset Your Leaders.st Password",
            sender=current_app.config["EMAIL_USERNAME"],
            recipients=[email],
            html=reset_password_email_html(reset_url)
        )

        mail.send(msg)

        return render_template(
            "forgot_password.html",
            success="Password reset email sent!"
        )

    return render_template("forgot_password.html")


# ============================================================
# RESET PASSWORD
# ============================================================
@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])

    try:
        email = serializer.loads(
            token,
            salt="reset-password",
            max_age=3600
        )
    except (SignatureExpired, BadSignature):
        return "Reset link expired or invalid."

    if request.method == "POST":
        hashed = generate_password_hash(request.form["password"])

        session = current_app.session()
        session.execute(
            text("""
                UPDATE users
                SET password = :pw
                WHERE email = :email
            """),
            {"pw": hashed, "email": email}
        )
        session.commit()
        session.close()

        return redirect(url_for("auth.login"))

    return render_template("reset_password.html")
