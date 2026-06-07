import fs from 'fs';
import path from 'path';

const BACKUP_DIR = process.env.BACKUP_DIR || './backups';

export function checkLatestBackup() {
  try {
    if (!fs.existsSync(BACKUP_DIR)) {
      return { status: 'UNHEALTHY', reason: 'Backup directory does not exist' };
    }

    const files = fs.readdirSync(BACKUP_DIR)
      .filter(f => f.startsWith('backup_') && f.endsWith('.sql.gz'))
      .map(f => ({
        name: f,
        path: path.join(BACKUP_DIR, f),
        time: fs.statSync(path.join(BACKUP_DIR, f)).mtime.getTime()
      }))
      .sort((a, b) => b.time - a.time);

    if (files.length === 0) {
      return { status: 'UNHEALTHY', reason: 'No backup files found' };
    }

    const latest = files[0];
    const stats = fs.statSync(latest.path);

    // Check size limit (should be at least 1KB for standard table structure)
    if (stats.size < 1024) {
      return { status: 'UNHEALTHY', reason: `Latest backup file ${latest.name} is too small (${stats.size} bytes)` };
    }

    // Verify magic gzip bytes [0x1f, 0x8b]
    const fd = fs.openSync(latest.path, 'r');
    const buffer = Buffer.alloc(2);
    fs.readSync(fd, buffer, 0, 2, 0);
    fs.closeSync(fd);

    if (buffer[0] !== 0x1f || buffer[1] !== 0x8b) {
      return { status: 'UNHEALTHY', reason: `Latest backup file ${latest.name} is not a valid gzip archive` };
    }

    // Verify age (should be within the last 25 hours to enforce daily backups)
    const ageHours = (Date.now() - latest.time) / (1000 * 60 * 60);
    if (ageHours > 25) {
      return { status: 'UNHEALTHY', reason: `Latest backup is stale (created ${ageHours.toFixed(1)} hours ago)` };
    }

    return {
      status: 'HEALTHY',
      fileName: latest.name,
      sizeBytes: stats.size,
      ageHours: parseFloat(ageHours.toFixed(1)),
      lastModified: new Date(latest.time).toISOString()
    };
  } catch (err) {
    return { status: 'UNHEALTHY', reason: `Backup verification failed: ${err.message}` };
  }
}

// Execute directly if run via CLI
if (process.argv[1] && (process.argv[1].endsWith('verify_backup.js') || process.argv[1].endsWith('verify_backup.ts'))) {
  const result = checkLatestBackup();
  console.log(JSON.stringify(result, null, 2));
  process.exit(result.status === 'HEALTHY' ? 0 : 1);
}
