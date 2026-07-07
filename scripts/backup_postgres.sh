#!/usr/bin/env bash
set -Eeuo pipefail

BACKUP_DIR="${CCWBOT_BACKUP_DIR:-/opt/backups}"
RETENTION_COUNT="${CCWBOT_BACKUP_RETENTION_COUNT:-14}"
COMPOSE_SERVICE="${CCWBOT_POSTGRES_SERVICE:-postgres}"
POSTGRES_DB_NAME="${POSTGRES_DB:-ccwbot}"
POSTGRES_USER_NAME="${POSTGRES_USER:-ccwbot}"

if ! [[ "${RETENTION_COUNT}" =~ ^[0-9]+$ ]] || [ "${RETENTION_COUNT}" -lt 7 ]; then
  echo "Backup failed: CCWBOT_BACKUP_RETENTION_COUNT must be a number >= 7." >&2
  exit 1
fi

umask 077
mkdir -p "${BACKUP_DIR}"

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup_path="${BACKUP_DIR}/ccwbot-postgres-${timestamp}.sql.gz"
tmp_path="${backup_path}.tmp"

cleanup() {
  rm -f "${tmp_path}"
}
trap cleanup EXIT

echo "Starting CCWBot PostgreSQL backup to ${backup_path}"

docker compose exec -T "${COMPOSE_SERVICE}" \
  pg_dump --no-owner --no-privileges -U "${POSTGRES_USER_NAME}" -d "${POSTGRES_DB_NAME}" \
  | gzip -9 > "${tmp_path}"

gzip -t "${tmp_path}"
chmod 600 "${tmp_path}"
mv "${tmp_path}" "${backup_path}"
trap - EXIT

echo "Backup completed: ${backup_path}"

mapfile -t old_backups < <(
  find "${BACKUP_DIR}" -maxdepth 1 -type f -name "ccwbot-postgres-*.sql.gz" \
    -printf "%T@ %p\n" \
    | sort -rn \
    | awk -v keep="${RETENTION_COUNT}" 'NR > keep {print $2}'
)

if [ "${#old_backups[@]}" -gt 0 ]; then
  rm -f -- "${old_backups[@]}"
  echo "Retention complete: removed ${#old_backups[@]} old CCWBot backup(s)."
else
  echo "Retention complete: no old CCWBot backups removed."
fi
