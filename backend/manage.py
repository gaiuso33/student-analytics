"""Account management from the command line.

    python manage.py create-user alice --role admin
    python manage.py set-password alice
    python manage.py send-reminders [--dry-run] [--days N]
"""
import argparse
import getpass
import sqlite3
import sys

from werkzeug.security import generate_password_hash

from config import Config
from db import init_db
import reminder_emails
from validation import ROLES, ValidationError, clean_username, password_problem


def ask_password():
    pw = getpass.getpass("Password: ")
    if pw != getpass.getpass("Repeat password: "):
        sys.exit("Passwords did not match.")
    problem = password_problem(pw, Config.MIN_PASSWORD_LENGTH)
    if problem:
        sys.exit(problem)
    return pw


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create-user")
    create.add_argument("username")
    create.add_argument("--role", choices=ROLES, default="viewer")
    setpw = sub.add_parser("set-password")
    setpw.add_argument("username")
    rem = sub.add_parser("send-reminders", help="email people their follow-ups that are overdue or due soon")
    rem.add_argument("--dry-run", action="store_true", help="print the emails instead of sending them")
    rem.add_argument("--days", type=int, help="also include follow-ups due within this many days")
    args = parser.parse_args()

    init_db(Config.DATABASE)
    conn = sqlite3.connect(Config.DATABASE)
    try:
        if args.command == "create-user":
            try:
                username = clean_username(args.username)
            except ValidationError as e:
                sys.exit(e.message)
            try:
                conn.execute(
                    "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                    (username, generate_password_hash(ask_password()), args.role),
                )
            except sqlite3.IntegrityError:
                sys.exit("That username already exists.")
            print(f"Created {args.role} account '{username}'.")
        elif args.command == "send-reminders":
            try:
                result = reminder_emails.run(Config, conn, dry_run=args.dry_run, days=args.days)
            except reminder_emails.ReminderError as exc:
                sys.exit(str(exc))
            if result["failed"]:
                sys.exit(1)
        else:
            cur = conn.execute(
                "UPDATE users SET password_hash = ?, token_version = token_version + 1 WHERE username = ?",
                (generate_password_hash(ask_password()), args.username),
            )
            if cur.rowcount == 0:
                sys.exit("No such user.")
            print("Password updated; existing sessions were signed out.")
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
