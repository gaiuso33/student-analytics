import datetime
import math
import re

USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,32}$")
ROLES = ("admin", "staff", "viewer")
INTERVENTION_KINDS = ("meeting", "tutoring", "counselling", "parent_contact", "referral", "other")
INTERVENTION_STATUSES = ("open", "done")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class ValidationError(Exception):
    def __init__(self, message, field=None):
        super().__init__(message)
        self.message = message
        self.field = field


def clean_text(value, field, max_len, label=None):
    """Trim, collapse whitespace, and enforce 1..max_len characters with no control characters."""
    label = label or field
    if not isinstance(value, str):
        raise ValidationError(f"{label} is required", field)
    value = " ".join(value.split())
    if not value:
        raise ValidationError(f"{label} is required", field)
    if len(value) > max_len:
        raise ValidationError(f"{label} must be at most {max_len} characters", field)
    if any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ValidationError(f"{label} contains invalid characters", field)
    return value


def clean_score(value, field="score"):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValidationError("Score must be a number between 0 and 100", field)
    if not 0 <= value <= 100:
        raise ValidationError("Score must be a number between 0 and 100", field)
    return round(float(value), 2)


def clean_username(value):
    if not isinstance(value, str) or not USERNAME_RE.match(value.strip()):
        raise ValidationError(
            "Username must be 3-32 characters: letters, numbers, dot, dash or underscore", "username"
        )
    return value.strip()


def clean_role(value):
    if value not in ROLES:
        raise ValidationError(f"Role must be one of: {', '.join(ROLES)}", "role")
    return value


def password_problem(password, min_len):
    """Return a message if the password is unacceptable, else None."""
    if not isinstance(password, str) or len(password) < min_len:
        return f"Password must be at least {min_len} characters"
    if len(password) > 128:
        return "Password must be at most 128 characters"
    return None


def clean_note(value, field="note", max_len=1000, label="Note"):
    """Multi-line text: trims the ends, keeps line breaks, rejects other control characters."""
    if not isinstance(value, str):
        raise ValidationError(f"{label} is required", field)
    value = value.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not value:
        raise ValidationError(f"{label} is required", field)
    if len(value) > max_len:
        raise ValidationError(f"{label} must be at most {max_len} characters", field)
    if any((ord(c) < 32 and c not in "\n\t") or ord(c) == 127 for c in value):
        raise ValidationError(f"{label} contains invalid characters", field)
    return value


def clean_choice(value, choices, field, label):
    if value not in choices:
        raise ValidationError(f"{label} must be one of: {', '.join(choices)}", field)
    return value


def clean_date(value, field="due_date", label="Due date"):
    """Optional ISO date (YYYY-MM-DD). None or an empty string means 'no date'."""
    if value is None or value == "":
        return None
    if not isinstance(value, str) or not DATE_RE.match(value):
        raise ValidationError(f"{label} must be a valid date (YYYY-MM-DD)", field)
    try:
        datetime.date.fromisoformat(value)
    except ValueError:
        raise ValidationError(f"{label} must be a valid date (YYYY-MM-DD)", field)
    return value
