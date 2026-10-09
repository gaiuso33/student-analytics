#!/usr/bin/env sh
# Consistent copy of the database (safe while the app is running).
#   ./backup.sh            -> ./backups/students-YYYY-MM-DD-HHMM.db
set -eu
mkdir -p backups
STAMP="$(date +%Y-%m-%d-%H%M)"
docker compose exec -T backend python -c "
import sqlite3
src = sqlite3.connect('/data/students.db')
dst = sqlite3.connect('/data/backup.tmp.db')
src.backup(dst); dst.close(); src.close()"
docker compose cp backend:/data/backup.tmp.db "backups/students-$STAMP.db"
docker compose exec -T backend rm -f /data/backup.tmp.db
echo "Saved backups/students-$STAMP.db"
