"""Email digests of follow-ups that need attention.

    python manage.py send-reminders            # send
    python manage.py send-reminders --dry-run  # print what would be sent

Each active staff member or administrator with an email address gets ONE email listing how many of the
follow-ups assigned to them are overdue or due soon. Privacy by design: emails never contain notes, and
student names only appear if REMINDER_INCLUDE_NAMES is switched on. Run it once a day from cron.
"""
import smtplib
from email.message import EmailMessage

KIND_LABELS = {
    "meeting": "Meeting", "tutoring": "Tutoring", "counselling": "Counselling",
    "parent_contact": "Parent or guardian contact", "referral": "Referral", "other": "Other",
}


class ReminderError(Exception):
    pass


def collect(conn, days):
    """One digest per recipient: {username, email, overdue: [...], due_soon: [...]} (only people with something due)."""
    rows = conn.execute(
        f"""
        SELECT u.username, u.email, s.name AS student_name, i.kind, i.due_date,
               (i.due_date < date('now')) AS overdue
        FROM users u
        JOIN interventions i ON i.assigned_to = u.username COLLATE NOCASE
        JOIN students s ON s.id = i.student_id
        WHERE u.active = 1 AND u.role IN ('admin', 'staff')
          AND u.email IS NOT NULL AND TRIM(u.email) <> ''
          AND (u.role = 'admin' OR u.scope = 'all'
               OR s.class_name COLLATE NOCASE IN (SELECT class_name FROM user_classes WHERE user_id = u.id))
          AND i.status = 'open' AND i.due_date IS NOT NULL
          AND i.due_date <= date('now', '+{int(days)} days')
        ORDER BY u.username COLLATE NOCASE, i.due_date, i.id
        """
    ).fetchall()
    digests = {}
    for username, email, student_name, kind, due_date, overdue in rows:
        digest = digests.setdefault(username, {"username": username, "email": email, "overdue": [], "due_soon": []})
        item = {"student_name": student_name, "kind": kind, "due_date": due_date}
        digest["overdue" if overdue else "due_soon"].append(item)
    return list(digests.values())


def compose(digest, config, days):
    n_over, n_soon = len(digest["overdue"]), len(digest["due_soon"])
    parts = ([f"{n_over} overdue"] if n_over else []) + ([f"{n_soon} due soon"] if n_soon else [])
    lines = [f"Hello {digest['username']},", "", f"You have {n_over + n_soon} student follow-up(s) that need attention:"]
    if n_over:
        lines.append(f"  - {n_over} overdue")
    if n_soon:
        lines.append(f"  - {n_soon} due within the next {days} day(s)")
    if config.REMINDER_INCLUDE_NAMES:
        for title, items in (("Overdue", digest["overdue"]), ("Due soon", digest["due_soon"])):
            if items:
                lines += ["", f"{title}:"]
                lines += [f"  - {i['student_name']}: {KIND_LABELS.get(i['kind'], i['kind'])}, due {i['due_date']}" for i in items]
    lines += [
        "",
        f"Open the dashboard to see them: {config.SITE_URL}/interventions",
        "",
        "You receive this because an email address is set on your account. "
        "To stop these emails, clear the address on the Account page.",
    ]
    message = EmailMessage()
    message["To"] = digest["email"]
    message["From"] = config.MAIL_FROM
    message["Subject"] = f"Student follow-ups: {', '.join(parts)}"
    message.set_content("\n".join(lines))
    return message


def _connect(config):
    try:
        if config.SMTP_SECURITY == "ssl":
            server = smtplib.SMTP_SSL(config.SMTP_HOST, config.SMTP_PORT, timeout=20)
        else:
            server = smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=20)
            if config.SMTP_SECURITY == "starttls":
                server.starttls()
        if config.SMTP_USER:
            server.login(config.SMTP_USER, config.SMTP_PASSWORD or "")
        return server
    except (OSError, smtplib.SMTPException) as exc:
        raise ReminderError(f"Could not connect to the mail server: {exc}")


def run(config, conn, dry_run=False, days=None, out=print):
    """Returns {"recipients": n, "sent": n, "failed": n}. Raises ReminderError when email is not set up."""
    days = config.REMINDER_DAYS_AHEAD if days is None else days
    digests = collect(conn, days)
    result = {"recipients": len(digests), "sent": 0, "failed": 0}
    if not digests:
        out("No reminders to send.")
        return result
    messages = [compose(d, config, days) for d in digests]

    if dry_run:
        for message in messages:
            out(f"--- To: {message['To']}\nSubject: {message['Subject']}\n\n{message.get_content()}")
        return result
    if not config.SMTP_HOST:
        raise ReminderError("SMTP_HOST is not set, so no email can be sent. Use --dry-run to preview the emails.")

    server = _connect(config)
    try:
        for message in messages:
            try:
                server.send_message(message)
                result["sent"] += 1
            except (OSError, smtplib.SMTPException) as exc:
                result["failed"] += 1
                out(f"Could not send to {message['To']}: {exc}")
    finally:
        try:
            server.quit()
        except (OSError, smtplib.SMTPException):
            pass
    conn.execute(
        "INSERT INTO audit_log (username, action, detail) VALUES ('system', 'reminders.sent', ?)",
        (f"sent={result['sent']} failed={result['failed']}",),
    )
    conn.commit()
    out(f"Sent {result['sent']} reminder email(s), {result['failed']} failed.")
    return result
