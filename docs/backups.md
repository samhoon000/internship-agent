# MySQL Database Backup & Restoration Guide

This document outlines the backup configuration, restore procedures, retention policies, and disaster recovery verification checks for the Internship Aggregator platform.

---

## 1. Backup Strategy Overview
- **Type**: Compressed MySQL logical dumps (`mysqldump` + `gzip`).
- **Frequency**: Automated daily execution (at midnight UTC / container startup).
- **Storage Location**: 
  - Docker volume: `mysql_backups` (mapped to `/backups` inside containers).
  - Manual backups path: `./backups/`.
- **Retention Policy**: 7 days. Backups older than 7 days are automatically purged.

---

## 2. Restore Procedure Instructions

To restore a database from a compressed backup file, follow these steps:

### A. Restoring in a Docker Environment
1. Identify the backup file you wish to restore from under the `mysql_backups` volume path or `./backups/`. Let's assume the file is `backup_2026-06-07_22-30-00.sql.gz`.
2. Copy the file into the database container or execute from the host:
   ```bash
   # Decompress the backup file
   gunzip -c ./backups/backup_2026-06-07_22-30-00.sql.gz > ./backups/restore.sql

   # Stream the SQL dump into the running MySQL container
   docker exec -i internship_db mysql -u root internship < ./backups/restore.sql
   ```
3. Verify that the restore succeeded by inspecting the row counts:
   ```bash
   docker exec -it internship_db mysql -u root internship -e "SELECT COUNT(*) FROM internships;"
   ```
4. Clean up the temporary uncompressed file:
   ```bash
   rm ./backups/restore.sql
   ```

### B. Restoring in a Non-Docker Environment
1. Extract the backup file:
   ```bash
   gunzip backup_2026-06-07_22-30-00.sql.gz
   ```
2. Import the SQL file into MySQL:
   ```bash
   mysql -h localhost -u root -p internship < backup_2026-06-07_22-30-00.sql
   ```

---

## 3. Automated Backup Health Verification

A Node.js test script is available under `scripts/verify_backup.js` to verify backup integrity. It runs checks to ensure that:
1. The backup file exists.
2. The file is a valid `.gz` archive.
3. The size is greater than 1KB (ensures non-empty dumps).

### Running Verification Manually:
```bash
node scripts/verify_backup.js
```
This check is integrated into our monitoring API and will alert administrators if the backup verification fails.
