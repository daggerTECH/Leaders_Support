from sqlalchemy import text
from datetime import datetime


def notify_user(session, user_id, ticket_id, ticket_code, message):
    """
    Creates an in-app notification for a user.
    - Prevents duplicate unread notifications for the same ticket & message
    - Does NOT auto-commit (caller controls transaction)
    """

    # ----------------------------
    # Prevent duplicate unread notifications
    # ----------------------------
    exists = session.execute(
        text("""
            SELECT 1 FROM notifications
            WHERE user_id = :user_id
              AND ticket_id = :ticket_id
              AND message = :message
              AND is_read = 0
            LIMIT 1
        """),
        {
            "user_id": user_id,
            "ticket_id": ticket_id,
            "message": message
        }
    ).fetchone()

    if exists:
        return False  # Skip duplicate notification

    # ----------------------------
    # Insert notification
    # ----------------------------
    session.execute(
        text("""
            INSERT INTO notifications (
                user_id,
                ticket_id,
                ticket_code,
                message,
                is_read,
                created_at
            )
            VALUES (
                :user_id,
                :ticket_id,
                :ticket_code,
                :message,
                0,
                NOW()
            )
        """),
        {
            "user_id": user_id,
            "ticket_id": ticket_id,
            "ticket_code": ticket_code,
            "message": message
        }
    )

    return True
