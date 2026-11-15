#!/usr/bin/env sh
# Restore the database from a backup made by ./backup.sh.
#   ./restore.sh backups/students-2026-11-01-0200.db
# The backup is checked first (nothing is touched if it is damaged or isn't ours), your CURRENT data is saved to
# backups/ before it is replaced, and the app is stopped for a few seconds while the file is swapped.
set -eu
if [ "$#" -ne 1 ]; then
  echo "Usage: ./restore.sh backups/students-YYYY-MM-DD-HHMM.db"
  exit 1
fi
FILE="$1"
[ -f "$FILE" ] || { echo "No such file: $FILE"; exit 1; }

echo "1/5 Checking the backup..."
docker compose cp "$FILE" backend:/data/restore.tmp.db
if ! docker compose exec -T backend python verify_backup.py /data/restore.tmp.db; then
  docker compose exec -T backend rm -f /data/restore.tmp.db
  echo "Nothing was changed."
  exit 1
fi

echo "2/5 Saving the current data first (just in case)..."
./backup.sh || echo "(could not save the current data; continuing because the backup you chose is valid)"

echo "3/5 Stopping the app..."
docker compose stop backend

echo "4/5 Swapping in the backup..."
docker compose run --rm --no-deps backend sh -c \
  'mv /data/restore.tmp.db /data/students.db && rm -f /data/students.db-wal /data/students.db-shm'

echo "5/5 Starting the app..."
docker compose start backend
echo "Restored from $FILE. Sign in and check that your data is back."
