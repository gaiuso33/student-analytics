import math
import re

USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,32}$")
ROLES = ("admin", "viewer")


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
