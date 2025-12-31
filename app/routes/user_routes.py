from flask import Blueprint, render_template, request, current_app, redirect, url_for
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer
from app.email_templates import verification_email_html
from app import mail

user_bp = Blueprint("user", __name__, url_prefix="/user")

ts = URLSafeTimedSerializer("leaders_secret")


# ============================
# ADMIN CREATE USER
# ============================
@user_bp.route("/create", methods=["GET", "POST"])
@login_required
def create_user():
    if current_user.role != "admin":
        return "Unauthorized", 403

    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        role = request.form["role"]

        hashed = generate_password_hash(password)

        session = current_app.session()

        # -------------------------
        # PRE-CHECK: EMAIL EXISTS
        # -------------------------
        existing = session.execute(
            text("SELECT id FROM users WHERE email = :email"),
            {"email": email}
        ).fetchone()

        if existing:
            session.close()
            return render_template(
                "create_user.html",
                error="A user with this email already exists."
            )

        # -------------------------
        # INSERT USER (SAFE)
        # -------------------------
        try:
            session.execute(
                text("""
                    INSERT INTO users (email, password, role, is_verified)
                    VALUES (:email, :password, :role, 0)
                """),
                {
                    "email": email,
                    "password": hashed,
                    "role": role
                }
            )
            session.commit()

        except IntegrityError:
            session.rollback()
            session.close()
            return render_template(
                "create_user.html",
                error="A user with this email already exists."
            )

        session.close()

        # -------------------------
        # SEND VERIFICATION EMAIL
        # -------------------------
        try:
            token = ts.dumps(email, salt="email-verify")
            verify_url = url_for(
                "auth.verify_email",
                token=token,
                _external=True
            )

            msg = Message(
                subject="Verify Your Leaders.st Account",
                sender=current_app.config["MAIL_USERNAME"],
                recipients=[email],
                html=verification_email_html(verify_url)
            )

            mail.send(msg)

        except Exception as e:
            # Email failure should NOT break user creation
            print("⚠️ Verification email failed:", e)

        return redirect(url_for("ticket.dashboard"))

    return render_template("create_user.html")
