import requests
from sqlalchemy import text
from flask import current_app

# ============================================================
# SLACK SENDER
# ============================================================
def send_slack_message(message: str) -> bool:
    webhook = current_app.config.get("SLACK_WEBHOOK_URL")

    if not webhook:
        print("❌ SLACK_WEBHOOK_URL not set")
        return False

    try:
        res = requests.post(webhook, json={"text": message}, timeout=10)
        if res.status_code != 200:
            print("❌ Slack API error:", res.text)
            return False
        return True

    except Exception as e:
        print("❌ Slack request failed:", e)
        return False


# ============================================================
# IN-APP NOTIFICATION
# ============================================================
def notify_user(session, user_id, ticket_id, ticket_code, message):
    session.execute(
        text("""
            INSERT INTO notifications (user_id, ticket_id, ticket_code, message)
            VALUES (:user_id, :ticket_id, :ticket_code, :message)
        """),
        {
            "user_id": user_id,
            "ticket_id": ticket_id,
            "ticket_code": ticket_code,
            "message": message
        }
    )


# ============================================================
# OVERDUE NOTIFIER (SOURCE OF TRUTH)
# ============================================================
def notify_overdue_tickets():
    """
    Run INSIDE app.app_context()
    Execute manually with:
        python -m app.utils.slack_notifier
    """
    session = current_app.session()

    tickets = session.execute(
        text("""
            SELECT
                t.id,
                t.ticket_code,
                t.sla_hours,
                t.slack_notified,
                TIMESTAMPDIFF(HOUR, t.created_at, NOW()) AS elapsed_hours,
                u.id AS agent_id,
                u.email AS agent_email
            FROM tickets t
            LEFT JOIN users u ON t.assigned_to = u.id
            WHERE t.status != 'Resolved'
        """)
    ).fetchall()

    if not tickets:
        print("ℹ️ No active tickets found")
        session.close()
        return

    sent = 0

    for t in tickets:
        # ----------------------------
        # Skip if not overdue
        # ----------------------------
        if t.elapsed_hours <= t.sla_hours:
            continue

        # ----------------------------
        # Skip if already notified
        # ----------------------------
        if t.slack_notified:
            continue

        overdue_by = t.elapsed_hours - t.sla_hours
        print(f"🚨 OVERDUE: {t.ticket_code} ({overdue_by}h)")

        # ----------------------------
        # Slack alert
        # ----------------------------
        slack_msg = (
            "🚨 *OVERDUE TICKET ALERT*\n"
            f"*Ticket:* {t.ticket_code}\n"
            f"*Overdue By:* {overdue_by}h\n"
            f"*Agent:* {t.agent_email or 'Unassigned'}\n"
            "⚠️ Immediate action required"
        )

        send_slack_message(slack_msg)

        # ----------------------------
        # Notify assigned agent
        # ----------------------------
        if t.agent_id:
            notify_user(
                session,
                t.agent_id,
                t.id,
                t.ticket_code,
                f"Ticket {t.ticket_code} is overdue"
            )

        # ----------------------------
        # Notify admins
        # ----------------------------
        admins = session.execute(
            text("SELECT id FROM users WHERE role = 'admin'")
        ).fetchall()

        for admin in admins:
            notify_user(
                session,
                admin.id,
                t.id,
                t.ticket_code,
                f"Overdue ticket {t.ticket_code} requires attention"
            )

        # ----------------------------
        # Lock notification
        # ----------------------------
        session.execute(
            text("UPDATE tickets SET slack_notified = 1 WHERE id = :id"),
            {"id": t.id}
        )

        sent += 1

    session.commit()
    session.close()

    print(f"🔔 Overdue notifications sent: {sent}")
