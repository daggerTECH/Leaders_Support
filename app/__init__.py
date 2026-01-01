from flask import Flask
from flask_mail import Mail
from flask_login import LoginManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import Config
import os

mail = Mail()
login_manager = LoginManager()
login_manager.login_view = "auth.login"


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # init extensions
    mail.init_app(app)
    login_manager.init_app(app)

    engine = create_engine(app.config["SQLALCHEMY_DATABASE_URI"], pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine)
    app.session = SessionLocal

    from app.routes.auth_routes import auth_bp
    from app.routes.user_routes import user_bp
    from app.routes.ticket_routes import ticket_bp
    from app.routes.notification_routes import notification_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(ticket_bp)
    app.register_blueprint(notification_bp)

    # ✅ START SCHEDULER ONLY ONCE
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        from app.utils.scheduler import start_scheduler
        start_scheduler(app)


    return app


