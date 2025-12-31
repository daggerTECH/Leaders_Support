from sqlalchemy import text
from app.utils.slack_notifier import send_slack_alert

def check_overdue_tickets(session):
    overdue_tickets = session.execute(
        text("""
            SELECT 
                t.id,
                t.ticket_code,
                t.email AS client_email,
                u.email AS agent_email
            FROM tickets t
            LEFT JOIN users u ON t.assigned_to = u.id
            WHERE 
                t.status != 'Resolved'
                AND t.created_at < NOW() - INTERVAL 72 HOUR
                AND t.slack_notified = 0
        """)
    ).fetchall()

    for t in overdue_tickets:
        message = (
            f"🚨 *OVERDUE TICKET ALERT*\n"
            f"*Ticket:* {t.ticket_code}\n"
            f"*Client:* {t.client_email}\n"
            f"*Assigned Agent:* {t.agent_email or 'Unassigned'}\n"
            f"*Status:* OVERDUE\n"
        )

        send_slack_alert(message)

        # Mark as notified
        session.execute(
            text("UPDATE tickets SET slack_notified = 1 WHERE id = :id"),
            {"id": t.id}
        )

    session.commit()