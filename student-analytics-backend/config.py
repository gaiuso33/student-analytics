"""Business rules and settings. Override with environment variables."""
import os


class Config:
    DATABASE = os.environ.get("DATABASE", "students.db")
    CORS_ORIGINS = [
        o.strip()
        for o in os.environ.get(
            "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
        ).split(",")
        if o.strip()
    ]
    # A record passes when score >= PASS_MARK (keep in sync with src/utils/grades.js)
    PASS_MARK = float(os.environ.get("PASS_MARK", 60))
    # A student is at risk when cumulative GPA is below this value
    AT_RISK_GPA = float(os.environ.get("AT_RISK_GPA", 2.0))
    # Fill an empty database with demo data on startup
    SEED_IF_EMPTY = True
