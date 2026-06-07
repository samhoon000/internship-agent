#!/bin/bash
# ==========================================
# Automated MySQL Database Backup Script
# Retention Policy: 7 days
# ==========================================

# Exit on any error
set -e

# Configuration
DB_HOST="${DB_HOST:-localhost}"
DB_USER="${DB_USER:-root}"
DB_PASSWORD="${DB_PASSWORD:-}"
DB_NAME="${DB_NAME:-internship}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS=7

echo "=========================================="
echo "Starting MySQL Database Backup"
echo "Timestamp: $(date '+%Y-%m-%d %H:%M:%S')"
echo "Database: ${DB_NAME} on ${DB_HOST}"
echo "=========================================="

# Ensure backup directory exists
mkdir -p "${BACKUP_DIR}"

# Define backup filename with timestamp
TIMESTAMP=$(date '+%Y-%m-%d_%H-%M-%S')
BACKUP_FILE="${BACKUP_DIR}/backup_${TIMESTAMP}.sql"
GZIP_FILE="${BACKUP_FILE}.gz"

# Run mysqldump
echo "Dumping database..."
if [ -z "${DB_PASSWORD}" ]; then
  mysqldump -h "${DB_HOST}" -u "${DB_USER}" "${DB_NAME}" > "${BACKUP_FILE}"
else
  mysqldump -h "${DB_HOST}" -u "${DB_USER}" -p"${DB_PASSWORD}" "${DB_NAME}" > "${BACKUP_FILE}"
fi

# Compress the backup file
echo "Compressing backup file..."
gzip -f "${BACKUP_FILE}"

# Verify backup success
if [ -f "${GZIP_FILE}" ] && [ -s "${GZIP_FILE}" ]; then
  echo "Backup successfully created: ${GZIP_FILE} ($(du -sh "${GZIP_FILE}" | cut -f1))"
else
  echo "ERROR: Backup file is empty or missing!" >&2
  exit 1
fi

# Enforce retention policy: delete files older than 7 days
echo "Enforcing retention policy (older than ${RETENTION_DAYS} days)..."
find "${BACKUP_DIR}" -name "backup_*.sql.gz" -type f -mtime +"${RETENTION_DAYS}" -exec rm -v {} \;

echo "Backup process completed successfully."
