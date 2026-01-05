from datetime import datetime, timedelta

def time_ago(dt):
    if not dt:
        return ""

    now = datetime.utcnow()
    diff = now - dt

    seconds = diff.total_seconds()
    minutes = seconds / 60
    hours = minutes / 60
    days = hours / 24

    if seconds < 60:
        return "Just now"
    elif minutes < 60:
        return f"{int(minutes)} minute{'s' if minutes >= 2 else ''} ago"
    elif hours < 24:
        return f"{int(hours)} hour{'s' if hours >= 2 else ''} ago"
    elif days < 2:
        return "Yesterday"
    elif days < 7:
        return f"{int(days)} days ago"
    else:
        return dt.strftime("%b %d")  # Jan 5
