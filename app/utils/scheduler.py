import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.memory import MemoryJobStore

# IMPORTANT: import inside function to avoid circular imports
# from app.utils.slack_notifier import notify_overdue_tickets


# ============================================================
# SINGLETON SCHEDULER
# ============================================================
scheduler = BackgroundScheduler(
    jobstores={"default": MemoryJobStore()},
    executors={"default": ThreadPoolExecutor(max_workers=1)},
    timezone="UTC",
)

_scheduler_started = False


# ============================================================
# SAFE JOB WRAPPER
# ============================================================
def _run_overdue_notifier(app):
    """
    Runs inside Flask app context.
    Must never crash the scheduler.
    """
    try:
        from app.utils.slack_notifier import notify_overdue_tickets

        with app.app_context():
            notify_overdue_tickets()

    except Exception as e:
        # Never crash APScheduler
        print("⚠️ Scheduler job error:", e)


# ============================================================
# START SCHEDULER (ONCE ONLY)
# ============================================================
def start_scheduler(app):
    """
    Starts background scheduler safely.
    Will not start twice (Flask reload-safe).
    """
    global _scheduler_started

    # Prevent duplicate scheduler (Flask debug reload, imports, etc.)
    if _scheduler_started or scheduler.running:
        return

    scheduler.add_job(
        id="overdue_ticket_notifier",
        func=_run_overdue_notifier,
        args=[app],
        trigger="interval",
        minutes=5,
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    scheduler.start()
    _scheduler_started = True

    # Silence APScheduler noise
    logging.getLogger("apscheduler").setLevel(logging.WARNING)

    print("✅ Background scheduler started (Overdue Ticket Notifier)")
