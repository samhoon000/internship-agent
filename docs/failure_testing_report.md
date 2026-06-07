# Production Launch Failure & Resilience Report

This document reports on the system behaviors, failover mechanisms, and disaster recovery processes tested for the Internship Discovery Platform under component outages (MySQL database, Redis cache, and individual crawlers).

---

## 1. MySQL Database Outages

### Failure Simulation
Stopping the MySQL service daemon or database container.

### Observed System Behavior
- **API Health Check**: The `/api/health` endpoint detects database liveness failure. It sets `healthData.services.db.status` to `DOWN` and flags the overall status as `UNHEALTHY`. A `CRITICAL` alert is appended to the diagnostic payload. The endpoint returns a `503 Service Unavailable` status code.
- **Data Routes**: Public data routes (e.g. `/api/internships`) fail immediately. Because connection acquisition timeouts are configured in the connection pool, requests do not hang. They return a `500 Internal Server Error` with a structured JSON response.
- **Background Workers**: The worker process logs MySQL connection failures and rejects current scraping jobs, keeping the BullMQ jobs marked as failed.

### Recovery Behavior
- **Automatic Pool Re-connection**: Once the MySQL database container or service is restarted, the `mysql2` connection pool automatically reconnects on the next incoming query request without requiring an API server restart.

---

## 2. Redis Cache Outages

### Failure Simulation
Stopping the Redis cache engine or setting `REDIS_HOST` to an incorrect address.

### Observed System Behavior
- **Graceful Failover on Reads**: Public data fetching routes (like `/api/filters` and `/api/stats`) degrade gracefully. When the cache read fails, the system logs `[Redis Cache Read Error]` and queries data directly from MySQL. Requests complete successfully, albeit without caching optimization.
- **Fail Fast on Queue Triggers**: Administrative queue endpoints (`POST /api/scrapers/run`, etc.) require Redis for BullMQ. Normally, BullMQ commands hang indefinitely when Redis is offline. Under our hardened configuration:
  - We configure `enableOfflineQueue: false` on the Redis client.
  - The `checkRedisConnection` middleware checks `redisClient.status !== 'ready'` and immediately terminates requests with a `503 Service Unavailable` and the JSON error: `{ "error": "Service Unavailable: Redis queue server is offline" }`.
- **System Health Alerting**: `/api/health` reports the Redis connection status as `DOWN` or `connecting` and registers a `HIGH` alert.

### Recovery Behavior
- **Background Re-connection**: The `ioredis` client retries connecting in the background. Once the Redis instance is restored, the connection status updates back to `ready`, and caching/queue operations resume automatically.

---

## 3. Web Scraper / Crawler Failures

### Failure Simulation
Simulating target website changes (e.g. invalid HTML selectors, scraping blockages, or DNS timeouts).

### Observed System Behavior
- **Python Scraper Try-Catch**: Individual crawlers run inside try-catch scopes. If a crawler fails (e.g. Wellfound or Indeed), the traceback is written to the rotating scraper log and execution continues for remaining sources.
- **Source Health Logging**: On process completion, `run.py` calls `update_source_health()` to write the outcome into the `source_health` table. A success logs `health_status = 'HEALTHY'`, whereas a failure logs `health_status = 'UNHEALTHY'` and records the timestamp in `last_failure`.
- **System Health Alerting**: `/api/health` scans the `source_health` table. Any scraper marked `UNHEALTHY` triggers a `MEDIUM` diagnostics warning alert in the JSON payload, which is displayed directly in the System Health Dashboard.

### Recovery Behavior
- **Isolation**: Outages in a single crawler do not affect the storage or representation of other scraper sources. The next automated daily cron cycle (or admin manual run) will retry the scrape and automatically clear the unhealthy status upon success.
