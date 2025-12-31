from werkzeug.security import generate_password_hash
from sqlalchemy import text
from app import create_app

app = create_app()
session = app.session()

email = input("Email: ")
password = input("Password: ")
role = input("Role (admin/agent): ")

hashed = generate_password_hash(password)

session.execute(
    text("""
        INSERT INTO users (email, password, role, is_verified)
        VALUES (:email, :password, :role, :verified)
    """),
    {"email": email, "password": hashed, "role": role, "verified": 1}  # verified user
)

session.commit()
session.close()

print("\nUser created successfully!\n")
