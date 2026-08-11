#!/usr/bin/env bash
# PostgreSQL backup for the Study Planner database.
#
# Dumps the configured database to a timestamped file, then prunes backups
# older than BACKUP_RETENTION_DAYS (default 14). Designed for cron; safe to
# run repeatedly. Reads connection details from env so no secrets land in the
# script or in git.
#
# Env:
#   DATABASE_URL      CONSULT-DATABASE connection string (e.g. postgresql://user:pass@host:5432/dbname)
#                     Either this or the individual PG* vars must be set.
#   BACKUP_DIR        Directory to write dumps to (default: ./backups).
#   BACKUP_RETENTION_DAYS  Delete dumps older than this (default: 14).
#   GZIP              "1" to gzip the dump in-flight (default: 1).
#
# Cron example (daily 03:17, 14-day retention):
#   17 3 * * *  DATABASE_URL=...  BACKUP_DIR=/var/backups/study_planner  /path/to/study_planner/scripts/backup.sh >> /var/log/study_planner_backup.log 2>&1

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
GZIP="${GZIP:-1}"

if [[ -z "${DATABASE_URL:-}" ]] && [[ -z "${PGHOST:-}${PGPORT:-}${PGUSER:-}${PGDATABASE:-}" ]]; then
  echo "ERROR: set DATABASE_URL or PGHOST/PGPORT/PGUSER/PGDATABASE env vars." >&2
  exit 1
fi

mkdir -p "$BACKUP_DIR"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="${BACKUP_DIR}/study_planner_${TS}.sql"

# pg_dump picks up PG* vars from the environment; DATABASE_URL is parsed by
# psql but pg_dump needs the components. Support both by exporting parsed
# parts when only DATABASE_URL is given.
if [[ -n "${DATABASE_URL:-}" && -z "${PGHOST:-}" ]]; then
  PGHOST="$(printf '%s' "$DATABASE_URL" | sed -nE 's#.*@([^:/]+).*#\1#p')"
  PGPORT="$(printf '%s' "$DATABASE_URL" | sed -nE 's#.*:([0-9]+)/.*#\1#p')"
  PGUSER="$(printf '%s' "$DATABASE_URL" | sed -nE 's#.*//([^:]+).*#\1#p')"
  PGDATABASE="$(printf '%s' "$DATABASE_URL" | sed -nE 's#.*/([^?]+).*#\1#p')"
  PGPORT="${PGPORT:-5432}"
  export PGHOST PGPORT PGUSER PGDATABASE
  # PGPASSWORD still has to be exported separately by the caller for a URL
  # with an embedded password: parse it out.
  if [[ "$DATABASE_URL" =~ ://[^:]+:([^@]+)@ ]]; then
    export PGPASSWORD="${BASH_REMATCH[1]}"
  fi
fi

if [[ "$GZIP" == "1" ]]; then
  OUT="${OUT}.gz"
  pg_dump --format=plain --no-owner --no-privileges | gzip -9 > "$OUT"
else
  pg_dump --format=plain --no-owner --no-privileges --file="$OUT"
fi

echo "Wrote $OUT"

# Prune dumps older than retention window.
find "$BACKUP_DIR" -name 'study_planner_*.sql*' -type f -mtime "+$RETENTION_DAYS" -delete
echo "Pruned backups older than ${RETENTION_DAYS} days"
