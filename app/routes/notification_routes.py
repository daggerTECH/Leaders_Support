from flask import Blueprint, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy import text

notification_bp = Blueprint(
    "notification",
    __name__,
    url_prefix="/notifications"
)

# ============================================================
# GET UNREAD NOTIFICATIONS (LIST)
# ============================================================
@notification_bp.route("/unread", methods=["GET"])
@login_required
def unread_notifications():
    session = current_app.session()

    rows = session.execute(
        text("""
            SELECT
                id,
                ticket_id,
                ticket_code,
                message,
                created_at
            FROM notifications
            WHERE user_id = :uid
              AND is_read = 0
            ORDER BY created_at DESC
            LIMIT 10
        """),
        {"uid": current_user.id}
    ).fetchall()

    session.close()

    return jsonify({
        "count": len(rows),
        "notifications": [
            {
                "id": n.id,
                "ticket_id": n.ticket_id,
                "ticket_code": n.ticket_code,
                "message": n.message,
                "created_at": n.created_at.strftime("%Y-%m-%d %H:%M")
            }
            for n in rows
        ]
    })


# ============================================================
# MARK ALL NOTIFICATIONS AS READ
# ============================================================
@notification_bp.route("/mark-read", methods=["POST"])
@login_required
def mark_all_read():
    session = current_app.session()

    session.execute(
        text("""
            UPDATE notifications
            SET is_read = 1
            WHERE user_id = :uid
              AND is_read = 0
        """),
        {"uid": current_user.id}
    )

    session.commit()
    session.close()

    return jsonify({"success": True})


# ============================================================
# MARK SINGLE NOTIFICATION AS READ
# ============================================================
@notification_bp.route("/mark-read/<int:notification_id>", methods=["POST"])
@login_required
def mark_single_read(notification_id):
    session = current_app.session()

    session.execute(
        text("""
            UPDATE notifications
            SET is_read = 1
            WHERE id = :nid
              AND user_id = :uid
              AND is_read = 0
        """),
        {
            "nid": notification_id,
            "uid": current_user.id
        }
    )

    session.commit()
    session.close()

    return jsonify({"success": True})


# ============================================================
# GET UNREAD COUNT ONLY (FAST POLLING)
# ============================================================
@notification_bp.route("/count", methods=["GET"])
@login_required
def unread_count():
    session = current_app.session()

    count = session.execute(
        text("""
            SELECT COUNT(*)
            FROM notifications
            WHERE user_id = :uid
              AND is_read = 0
        """),
        {"uid": current_user.id}
    ).scalar()

    session.close()

    return jsonify({"count": count})

# ============================================================
# GET ALL NOTIFICATIONS (READ + UNREAD)
# ============================================================
@notification_bp.route("/all")
@login_required
def all_notifications():
    session = current_app.session()

    rows = session.execute(
        text("""
            SELECT 
                id,
                ticket_id,
                ticket_code,
                message,
                is_read,
                created_at
            FROM notifications
            WHERE user_id = :uid
            ORDER BY created_at DESC
            LIMIT 50
        """),
        {"uid": current_user.id}
    ).fetchall()

    session.close()

    return jsonify({
        "notifications": [
            {
                "id": n.id,
                "ticket_id": n.ticket_id,
                "ticket_code": n.ticket_code,
                "message": n.message,
                "is_read": n.is_read,
                "created_at": n.created_at.strftime("%Y-%m-%d %H:%M")
            }
            for n in rows
        ]
    })