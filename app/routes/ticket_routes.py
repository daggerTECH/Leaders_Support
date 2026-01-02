from flask import Blueprint, render_template, request, current_app, redirect, url_for
from flask_login import login_required
from sqlalchemy import text
from datetime import datetime
from flask_login import current_user
from app.utils.slack_notifier import notify_user
import os
from werkzeug.utils import secure_filename

ticket_bp = Blueprint("ticket", __name__)

def allowed_file(filename):
    return (
        "." in filename and
        filename.rsplit(".", 1)[1].lower()
        in current_app.config.get("ALLOWED_EXTENSIONS", {"png", "jpg", "jpeg", "gif"})
    )


# ============================
# DASHBOARD (Enhanced with Search + Filters + KPIs + Chart Data)
# ============================
@ticket_bp.route("/", methods=["GET"])
@login_required
def dashboard():
    session = current_app.session()

    # -------------------------
    # INPUTS
    # -------------------------
    search = request.args.get("search", "").strip()
    filter_status = request.args.get("filter", "").strip()
    my_only = request.args.get("my")

    params = {}

    # -------------------------
    # BASE WHERE CLAUSE
    # -------------------------
    where_clause = "WHERE 1=1"

    # -------------------------
    # ROLE-BASED VISIBILITY
    # -------------------------
    if current_user.role == "agent":
        where_clause += " AND t.assigned_to = :agent_id"
        params["agent_id"] = current_user.id

    # -------------------------
    # MY TICKETS (AGENT ONLY)
    # -------------------------
    if my_only and current_user.role == "agent":
        where_clause += " AND t.assigned_to = :agent_id"

    # -------------------------
    # SEARCH
    # -------------------------
    if search:
        where_clause += """
            AND (
                t.ticket_code LIKE :s
                OR t.email LIKE :s
                OR t.description LIKE :s
            )
        """
        params["s"] = f"%{search}%"

    # -------------------------
    # FILTERS
    # -------------------------
    if filter_status == "resolved":
        where_clause += " AND t.status = 'Resolved'"

    elif filter_status == "unresolved":
        where_clause += " AND t.status IN ('Open','In Progress')"

    elif filter_status == "overdue":
        where_clause += """
            AND t.status != 'Resolved'
            AND (
                (t.priority = 'High' AND t.created_at < NOW() - INTERVAL 24 HOUR)
                OR (t.priority = 'Medium' AND t.created_at < NOW() - INTERVAL 48 HOUR)
                OR (t.priority = 'Low' AND t.created_at < NOW() - INTERVAL 72 HOUR)
            )
        """

    # -------------------------
    # FETCH TICKETS + SLA DATA
    # -------------------------
    tickets = session.execute(
        text(f"""
            SELECT
                t.*,
                u.email AS agent_email,
                TIMESTAMPDIFF(HOUR, t.created_at, NOW()) AS elapsed_hours,
                CASE
                    WHEN t.priority = 'High' THEN 24
                    WHEN t.priority = 'Medium' THEN 48
                    ELSE 72
                END AS sla_hours
            FROM tickets t
            LEFT JOIN users u ON t.assigned_to = u.id
            {where_clause}
            ORDER BY t.created_at DESC
        """),
        params
    ).fetchall()

    # -------------------------
    # NOTIFIES USERS
    # -------------------------
    notifications = session.execute(
        text("""
            SELECT * FROM notifications
            WHERE user_id = :uid AND is_read = 0
            ORDER BY created_at DESC
        """),
        {"uid": current_user.id}
    ).fetchall()

    # -------------------------
    # KPI METRICS (CONSISTENT)
    # -------------------------
    total = session.execute(
        text(f"SELECT COUNT(*) FROM tickets t {where_clause}"),
        params
    ).scalar()

    unresolved = session.execute(
        text(f"""
            SELECT COUNT(*) FROM tickets t
            {where_clause} AND t.status IN ('Open','In Progress')
        """),
        params
    ).scalar()

    resolved = session.execute(
        text(f"""
            SELECT COUNT(*) FROM tickets t
            {where_clause} AND t.status = 'Resolved'
        """),
        params
    ).scalar()

    overdue = session.execute(
        text(f"""
            SELECT COUNT(*) FROM tickets t
            {where_clause}
            AND t.status != 'Resolved'
            AND (
                (t.priority = 'High' AND t.created_at < NOW() - INTERVAL 24 HOUR)
                OR (t.priority = 'Medium' AND t.created_at < NOW() - INTERVAL 48 HOUR)
                OR (t.priority = 'Low' AND t.created_at < NOW() - INTERVAL 72 HOUR)
            )
        """),
        params
    ).scalar()

    # -------------------------
    # PRIORITY COUNTS
    # -------------------------
    high = session.execute(
        text(f"SELECT COUNT(*) FROM tickets t {where_clause} AND t.priority = 'High'"),
        params
    ).scalar()

    medium = session.execute(
        text(f"SELECT COUNT(*) FROM tickets t {where_clause} AND t.priority = 'Medium'"),
        params
    ).scalar()

    low = session.execute(
        text(f"SELECT COUNT(*) FROM tickets t {where_clause} AND t.priority = 'Low'"),
        params
    ).scalar()

    session.close()

    return render_template(
        "dashboard.html",
        notifications=notifications,
        tickets=tickets,
        total=total,
        unresolved=unresolved,
        resolved=resolved,
        overdue=overdue,
        high=high,
        medium=medium,
        low=low,
        search=search,
        filter_status=filter_status
    )

# ============================
# SINGLE TICKET PAGE
# ============================
@ticket_bp.route("/ticket/<int:id>", methods=["GET", "POST"])
@login_required
def view_ticket(id):
    session = current_app.session()

    # ============================
    # LOAD TICKET
    # ============================
    ticket = session.execute(
        text("""
            SELECT t.*, u.email AS agent_email
            FROM tickets t
            LEFT JOIN users u ON t.assigned_to = u.id
            WHERE t.id = :id
        """),
        {"id": id}
    ).fetchone()

    if not ticket:
        session.close()
        return "Ticket not found", 404

    # ============================
    # HANDLE POST
    # ============================
    if request.method == "POST":

        # ============================
        # ADD NOTE (+ IMAGES)
        # ============================
        if "note" in request.form:
            note_text = request.form.get("note", "").strip()
            files = request.files.getlist("images")

            if note_text:
                # Insert note
                result = session.execute(
                    text("""
                        INSERT INTO ticket_notes (ticket_id, user_id, note)
                        VALUES (:ticket_id, :user_id, :note)
                    """),
                    {
                        "ticket_id": id,
                        "user_id": current_user.id,
                        "note": note_text
                    }
                )
                note_id = result.lastrowid

                # Save images
                upload_root = current_app.config.get("UPLOAD_FOLDER", "static/uploads")
                note_folder = os.path.join(
                    upload_root,
                    "tickets",
                    f"ticket_{id}",
                    f"note_{note_id}"
                )
                os.makedirs(note_folder, exist_ok=True)

                for file in files:
                    if file and allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        filepath = os.path.join(note_folder, filename)
                        file.save(filepath)

                        session.execute(
                            text("""
                                INSERT INTO note_attachments
                                (note_id, file_path, file_type)
                                VALUES (:note_id, :path, :type)
                            """),
                            {
                                "note_id": note_id,
                                "path": filepath,
                                "type": file.mimetype
                            }
                        )

                session.commit()

            session.close()
            return redirect(url_for("ticket.view_ticket", id=id))

        # ============================
        # UPDATE TICKET
        # ============================
        status = request.form.get("status")
        priority = request.form.get("priority")
        assigned_to = request.form.get("assigned_to")

        old_assigned_to = ticket.assigned_to
        old_status = ticket.status

        # ----------------------------
        # ADMIN
        # ----------------------------
        if current_user.role == "admin":
            session.execute(
                text("""
                    UPDATE tickets
                    SET status = :status,
                        priority = :priority,
                        assigned_to = :assigned_to,
                        updated_at = NOW()
                    WHERE id = :id
                """),
                {
                    "status": status,
                    "priority": priority,
                    "assigned_to": assigned_to if assigned_to else None,
                    "id": id
                }
            )

            if assigned_to and str(old_assigned_to) != str(assigned_to):
                notify_user(
                    session,
                    int(assigned_to),
                    id,
                    ticket.ticket_code,
                    f"You have been assigned ticket {ticket.ticket_code}"
                )

        # ----------------------------
        # AGENT
        # ----------------------------
        elif current_user.role == "agent":
            if ticket.assigned_to != current_user.id:
                session.close()
                return "Unauthorized", 403

            session.execute(
                text("""
                    UPDATE tickets
                    SET status = :status,
                        updated_at = NOW()
                    WHERE id = :id
                """),
                {
                    "status": status,
                    "id": id
                }
            )

        # Notify admins on status change
        if status != old_status:
            admins = session.execute(
                text("SELECT id FROM users WHERE role = 'admin'")
            ).fetchall()

            for admin in admins:
                notify_user(
                    session,
                    admin.id,
                    id,
                    ticket.ticket_code,
                    f"Ticket {ticket.ticket_code} status changed to {status}"
                )

        session.commit()
        session.close()
        return redirect(url_for("ticket.view_ticket", id=id))

    # ============================
    # LOAD AGENTS
    # ============================
    agents = []
    if current_user.role == "admin":
        agents = session.execute(
            text("SELECT id, email FROM users WHERE role = 'agent'")
        ).fetchall()

    # ============================
    # LOAD NOTES + IMAGES
    # ============================
    notes = session.execute(
        text("""
            SELECT 
                n.id,
                n.note,
                n.created_at,
                u.email,
                u.role
            FROM ticket_notes n
            JOIN users u ON n.user_id = u.id
            WHERE n.ticket_id = :tid
            ORDER BY n.created_at DESC
        """),
        {"tid": id}
    ).fetchall()

    attachments = session.execute(
        text("""
            SELECT note_id, file_path
            FROM note_attachments
            WHERE note_id IN (
                SELECT id FROM ticket_notes WHERE ticket_id = :tid
            )
        """),
        {"tid": id}
    ).fetchall()

    # Group images by note
    images_by_note = {}
    for a in attachments:
        images_by_note.setdefault(a.note_id, []).append(a.file_path)

    session.close()

    return render_template(
        "ticket.html",
        ticket=ticket,
        agents=agents,
        notes=notes,
        images_by_note=images_by_note
    )
