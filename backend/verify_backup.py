"""Check that a file is a usable backup of the database, without changing it.

    python verify_backup.py /data/restore.tmp.db

Used by restore.sh before anything is replaced. Exits with status 1 and a plain message if the file is not a
healthy SQLite database with this application's tables.
"""
import sqlite3
import sys

REQUIRED_TABLES = {"students", "records", "users"}


def verify(path):
    """Return {"students": n, "records": n, "users": n}, or raise ValueError saying what is wrong."""
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    except sqlite3.Error as exc:
        raise ValueError(f"Cannot open the file: {exc}")
    try:
        try:
            if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("The database file is damaged (integrity check failed)")
            tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
            missing = REQUIRED_TABLES - tables
            if missing:
                raise ValueError(f"This is not a backup of the student database (missing: {', '.join(sorted(missing))})")
            counts = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in sorted(REQUIRED_TABLES)}
        except sqlite3.DatabaseError as exc:
            raise ValueError(f"The file is not a readable SQLite database: {exc}")
        if counts["users"] == 0:
            raise ValueError("The backup has no user accounts, so nobody could sign in after restoring it")
        return counts
    finally:
        conn.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python verify_backup.py <backup file>")
    try:
        found = verify(sys.argv[1])
    except ValueError as exc:
        sys.exit(f"Backup rejected: {exc}")
    print(f"Backup looks valid: {found['students']} students, {found['records']} results, {found['users']} users")
