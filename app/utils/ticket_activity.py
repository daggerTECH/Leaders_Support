from sqlalchemy import text
from flask_login import current_user

def log_ticket_activity(session, ticket_id, message):
    """
    Logs system-level ticket activity (viewed, status change, assignment, etc.)
    """
    session.execute(
        text("""
            INSERT INTO ticket_notes (ticket_id, user_id, note, is_system)
            VALUES (:ticket_id, :user_id, :note, 1)
        """),
        {
            "ticket_id": ticket_id,
            "user_id": current_user.id,
            "note": message
        }
    )
