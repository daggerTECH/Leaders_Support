from flask import Blueprint, render_template, request, current_app, redirect, url_for
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from itsdangerous import URLSafeTimedSerializer
from flask_mail import Message

from app import mail

user_bp = Blueprint("user", __name__, url_prefix="/user")


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
        # CHECK DUPLICATE EMAIL
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
        # INSERT USER
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

        # ============================
        # SEND VERIFICATION EMAIL
        # ============================
        try:
            serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
            token = serializer.dumps(email, salt="email-verify")

            verify_url = url_for(
                "auth.verify_email",
                token=token,
                _external=True
            )

            msg = Message(
                subject="Verify Your Leaders Account",
                recipients=[email],
                html=verification_email_html(verify_url)
            )

            mail.send(msg)
            print("📨 Verification email sent to:", email)

        except Exception as e:
            # Email failure should NEVER block user creation
            print("⚠️ Verification email failed:", e)

        return redirect(url_for("ticket.dashboard"))

    return render_template("create_user.html")
