# Production Launch Checklist

This checklist contains all the operations, security, configuration, and monitoring requirements that must be verified before declaring the Internship Discovery Platform live.

---

## 1. Environment & Configuration Hardening
- [ ] **Dotenv Integrity**: Ensure the production `.env` file exists and is populated with strong production credentials (not developer defaults).
- [ ] **Admin Key Security**: The `ADMIN_API_KEY` is set to a cryptographically secure random string (minimum 32 characters).
- [ ] **Startup Validator**: Verify that backend starts up successfully and that `validateEnv()` passes without exceptions.
- [ ] **CORS Settings**: Verify that `FRONTEND_URL` is set to the final production domain name (e.g. `https://internships.yourdomain.com`).

---

## 2. Database & Data Resiliency
- [ ] **Schema Migrations**: Verify that all Alembic migrations have been applied to the production database:
  ```bash
  alembic upgrade head
  ```
- [ ] **Scheduled Backups**: Check that the `db_backup` container is running and that database dumps are written to the `/backups` volume daily.
- [ ] **Backup Verification**: Manually trigger `scripts/verify_backup.js` and verify it checks for gzip integrity, file size, and timestamp liveness.
- [ ] **Retention Rules**: Verify that backups older than 7 days are automatically purged by the backup loop.

---

## 3. Cache & Queue Infrastructure
- [ ] **Redis Connection**: Confirm that the Redis instance is healthy and that BullMQ queues (`scraper-queue`, `cleanup-queue`, `liveness-queue`) are initialized.
- [ ] **Graceful Degradation**: Stop the Redis container and verify that:
  - Public routes serve listings directly from MySQL instead of hanging.
  - Scraper run routes fail immediately with a `503 Service Unavailable` status instead of blocking Express.
- [ ] **Cache Clearance**: Verify that completing a scraper job clears `stats` and `filters:*` keys from Redis.

---

## 4. Web Crawler & Scraper Validation
- [ ] **Playwright Dependencies**: Ensure Chromium is installed inside the scraper container.
- [ ] **Scraper Source Health**: Verify that the `source_health` table in the database contains records for all crawler sources (LinkedIn, Internshala, Wellfound, YC Jobs, Indeed India).
- [ ] **Daily Cron Scheduler**: Verify that background workers are active and scheduled to execute scraper cycles once every 24 hours.

---

## 5. Security & Network Hardening
- [ ] **Rate Limiting**: Verify that `apiLimiter` is active and blocks requests after exceeding 100 requests per 15 minutes per IP address.
- [ ] **Helmet Headers**: Confirm that security response headers are returned in server headers (e.g., `X-Frame-Options: SAMEORIGIN`).
- [ ] **Input Sanitization**: Confirm that HTML inputs are sanitized via `sanitize-html` before being committed to the database.
- [ ] **Host Firewall (UFW)**: Confirm that ports 3306 (MySQL) and 6379 (Redis) are blocked from public internet access.

---

## 6. Monitoring & Diagnostics
- [ ] **Detailed Health Check Endpoint**: Verify that `/api/health` queries and reports uptime, database response latency, Redis status, backups age, and individual crawler health.
- [ ] **Interactive Dashboard**: Navigate to `/health` in the frontend and verify that the glassmorphism UI displays all status variables, active warning/critical alerts, and has a functioning "Refresh" action.
