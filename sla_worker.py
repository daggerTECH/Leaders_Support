from app import create_app
from app.utils.sla_checker import check_overdue_tickets
import time

app = create_app()

print("⏳ SLA Worker running...")

while True:
    with app.app_context():
        session = app.session()
        check_overdue_tickets(session)
        session.close()

    time.sleep(300)  # every 5 minutes