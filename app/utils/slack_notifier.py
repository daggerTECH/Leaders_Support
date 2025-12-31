import requests
from sqlalchemy import text
from flask import current_app

# ============================================================
# SLACK SENDER
# ============================================================
def send_slack_message(message: str) -> bool:
    webhook = current_app.config.get("SLACK_WEBHOOK_URL")

    if not webhook:
        print("❌ SLACK_WEBHOOK_URL not set in config.py")
        return False

    try:
        response = requests.post(
            webhook,
            json={"text": message},
            timeout=10
        )

        if response.status_code != 200:
            print("❌ Slack API error:", response.text)
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
# OVERDUE + SLA WARNING NOTIFIER
# ============================================================
def notify_overdue_tickets():
    """
    This function MUST be called inside app.app_context()
    (handled by scheduler.py)
    """
    session = current_app.session()

    tickets = session.execute(
        text("""
            SELECT 
                t.id,
                t.ticket_code,
                t.email AS client_email,
                t.priority,
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
        print("✅ No active tickets")
        session.close()
        return

    sent = 0

    for t in tickets:
        sla = 24 if t.priority == "High" else 48 if t.priority == "Medium" else 72
        elapsed = t.elapsed_hours
        remaining = sla - elapsed

        # ================================
        # SLA WARNING (80%)
        # ================================
        if remaining > 0 and remaining <= sla * 0.2:
            warning_msg = (
                "⏳ *SLA WARNING*\n"
                f"*Ticket:* {t.ticket_code}\n"
                f"*Client:* {t.client_email}\n"
                f"*Remaining:* {remaining}h\n"
                "⚠️ SLA almost breached"
            )

            print(f"⚠️ SLA warning for {t.ticket_code}")
            send_slack_message(warning_msg)

            if t.agent_id:
                notify_user(
                    session,
                    t.agent_id,
                    t.id,
                    t.ticket_code,
                    f"SLA warning: ticket {t.ticket_code} nearing deadline"
                )

        # ================================
        # OVERDUE (ONCE ONLY)
        # ================================
        if elapsed > sla and t.slack_notified == 0:
            over_by = elapsed - sla

            overdue_msg = (
                "🚨 *OVERDUE TICKET ALERT*\n"
                f"*Ticket:* {t.ticket_code}\n"
                f"*Client:* {t.client_email}\n"
                f"*Agent:* {t.agent_email or 'Unassigned'}\n"
                f"*Overdue By:* {over_by}h\n"
                "🔥 Immediate action required"
            )

            print(f"🚨 Overdue alert for {t.ticket_code}")

            if send_slack_message(overdue_msg):
                session.execute(
                    text("""
                        UPDATE tickets
                        SET slack_notified = 1
                        WHERE id = :id
                    """),
                    {"id": t.id}
                )

                # Notify assigned agent
                if t.agent_id:
                    notify_user(
                        session,
                        t.agent_id,
                        t.id,
                        t.ticket_code,
                        f"Ticket {t.ticket_code} is overdue"
                    )

                # Notify admins
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

                sent += 1

    session.commit()
    session.close()

    print(f"🔔 Slack alerts sent: {sent}")
