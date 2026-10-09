FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN useradd --create-home appuser && mkdir /data && chown appuser /data
USER appuser

ENV DATABASE=/data/students.db
EXPOSE 8000

# Listens on $PORT when the host provides one (Render, etc.), otherwise 8000.
# One worker with threads: the failed-sign-in counter lives in process memory and SQLite
# allows a single writer anyway. Plenty for a school/department-sized tool.
CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT:-8000} --workers 1 --threads 8 --access-logfile - wsgi:app"]
