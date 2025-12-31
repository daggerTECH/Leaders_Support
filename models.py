from flask_login import UserMixin
from app import login_manager
from sqlalchemy import text
from flask import current_app

class User(UserMixin):
    def __init__(self, id, email, role):
        self.id = id
        self.email = email
        self.role = role


# 🔥 REQUIRED BY FLASK–LOGIN
@login_manager.user_loader
def load_user(user_id):
    session = current_app.session()
    user = session.execute(
        text("SELECT id, email, role FROM users WHERE id = :id"),
        {"id": user_id}
    ).fetchone()
    session.close()

    if user:
        return User(user[0], user[1], user[2])
    return None
