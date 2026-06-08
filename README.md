# 🚀 Premium Internship Discovery & Analytics Engine

[![React](https://img.shields.io/badge/React-19-blue?logo=react)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-6.0-blue?logo=typescript)](https://www.typescriptlang.org/)
[![Node.js](https://img.shields.io/badge/Node.js-20-green?logo=node.js)](https://nodejs.org/)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python)](https://www.python.org/)
[![MySQL](https://img.shields.io/badge/MySQL-8.0-orange?logo=mysql)](https://www.mysql.com/)
[![Redis](https://img.shields.io/badge/Redis-7-red?logo=redis)](https://redis.io/)
[![Docker](https://img.shields.io/badge/Docker-Compose-blue?logo=docker)](https://www.docker.com/)

An automated, enterprise-grade internship discovery aggregator, processing pipeline, and analytics dashboard. The platform crawls major portals (Internshala, Wellfound, YC Jobs, Indeed India) using Playwright, normalizes and validates role properties, computes dynamic relevance and legitimacy scores, performs asynchronous URL audits, and serves clean results via a cached Express API to a modern React dashboard.

---

## 📋 Table of Contents
1. [Overview](#-overview)
2. [Features](#-features)
3. [Architecture](#-architecture)
4. [Tech Stack](#-tech-stack)
5. [Project Structure](#-project-structure)
6. [Workflow](#-workflow)
7. [Scoring System](#-scoring-system)
8. [Installation](#-installation)
9. [Environment Variables](#-environment-variables)
10. [Docker Deployment](#-docker-deployment)
11. [API Documentation](#-api-documentation)
12. [Testing](#-testing)
13. [Security](#-security)
14. [Monitoring](#-monitoring)
15. [Roadmap](#-roadmap)
16. [Contributing](#-contributing)
17. [License](#-license)

---

## 🔍 Overview

The **Premium Internship Discovery & Analytics Engine** exists to address a major gap in entry-level tech recruitment: the clutter, spam, duplicate listings, and unpaid roles that dominate common job boards. By focusing specifically on high-quality roles within **Data/AI** (Analytics, Data Science, Data Engineering, Machine Learning, Business Intelligence) and **Software Engineering**, the engine curates a clean list of paid opportunities.

### Key Differentiators:
* **Strict Quality Gates:** Every scraped internship must pass a multi-stage validation pipeline that filters out non-tech roles, unpaid positions, spam, and certificate-only schemes.
* **Unified Double Scoring:** Features separate mathematical algorithms to compute **Relevance** (matching required skills and categories) and **Legitimacy** (analyzing domain resolution, payment realistic values, and online presence).
* **Fuzzy Deduplication:** Ensures that identical or highly similar postings (different title variations or slight changes) are consolidated in memory before database insert.
* **Production-Ready Operations:** Spawns asynchronous scraper runs inside a BullMQ task queue backed by Redis, checks liveness with automatic soft-deactivation (soft-delete), and performs daily backup self-tests.

---

## ⚡ Features

* **Multi-Source Crawling:** Scrapes roles concurrently from [Internshala](https://internshala.com), [Wellfound](https://wellfound.com), [YC Jobs (Work at a Startup)](https://www.workatastartup.com), and [Indeed India](https://in.indeed.com) under a single, optimized headless browser context.
* **AI/Data vs. Software Separation:** Internships are dynamically grouped into **Data/AI** or **Software** categories based on keyword mappings, falling back to description/skill scanning for ambiguous titles.
* **AI Resume Matcher:** A React frontend matcher scanning user-submitted resumes/summaries for keyword overlaps, dynamically applying matching filters directly to the exploration sidebar.
* **Faceted Search & Filters:** Sidebar navigation offering location checklists, remote/onsite/hybrid radio buttons, stipend ranges, duration thresholds, specific skills chips, platforms, legitimacy sliders, and date posted.
* **Recharts Analytics Panel:** Charts detailing top hiring companies, popular skills demand, location distributions, remote vs. onsite ratios, top paying companies, and average stipend trends.
* **Live Scraper Console:** Real-time log streaming inside the dashboard, enabling admins to queue, inspect, and monitor background scraper execution.
* **Soft-Delete Archival Architecture:** Stale listings older than 21 days are soft-deleted (`is_active = 0`), listings older than 30 days are archived, and 90-day-old records are purged if enabled.
* **Automated Health & Backup Self-Audit:** An integrated `/health` endpoint validating database response latency, Redis connection, individual scraper status history, and verifying compressed SQL backup gzip headers, age, and file size.

---

## 🏗️ Architecture

The application is split into three main layers running in isolated containers:
1. **Frontend Client:** Built with React, TypeScript, and Vite; served via Nginx.
2. **Backend API Server:** Node.js/Express.js, providing routes, ioredis caching, and task queue triggers.
3. **Queue Workers & Python Scraper:** BullMQ listening for tasks on Redis, spawning `run.py` to scrape, validate, score, and bulk insert into MySQL.

```mermaid
graph TD
    subgraph Client Panel (React / Nginx)
        UI[React Dashboard] <--> |HTTPS / WSS| Express[Express.js API Server]
    end

    subgraph Memory & Queue (Redis)
        Redis[(Redis Cache & Queues)]
        Express <--> |Queue Job / Fetch Cache| Redis
    end

    subgraph Background Workers (Node.js & Python)
        Worker[BullMQ Worker Service] <--> |Pulls Job| Redis
        Worker --> |Spawns child_process| PyRun[run.py Runner]
        PyRun --> |Playwright Async API| Sites[Job Portals]
    end

    subgraph Relational Storage (MySQL)
        MySQL[(MySQL DB)]
        PyRun --> |SQLAlchemy Bulk Writes| MySQL
        Express <--> |mysql2 Connection Pool| MySQL
        BackupCron[db_backup container] --> |mysqldump cron| MySQL
        BackupCron --> |Daily Gzip| BackupsVolume[(Gzipped SQL Backups)]
    end
```

---

## 🛠️ Tech Stack

### Frontend
* **Core:** React 19, TypeScript 6.0, Vite 8.0
* **Styling:** Tailwind CSS 4.0 (PostCSS integration)
* **State & Fetching:** TanStack React Query v5, React Router DOM v7
* **Charts & Animation:** Recharts v3.8, Framer Motion v12, Lucide Icons

### Backend
* **Core:** Node.js v20, Express v4.19
* **Database Pool:** `mysql2` (promise-based connection pooling)
* **Caching:** `ioredis` v5.4
* **Queue Orchestration:** `bullmq` v5.8 (scraper-queue, cleanup-queue, liveness-queue)
* **Security & Logging:** Helmet v8.2, Express Rate Limit v7.2, Winston v3.19 (Daily Rotate File), Sanitize-HTML v2.13

### Python Scraper
* **Core:** Python 3.9+, Playwright Async API
* **Database Access:** SQLAlchemy (ORM), PyMySQL driver
* **NLP & Text Extraction:** BeautifulSoup4, RapidFuzz, Difflib
* **CLI Runner:** `argparse` orchestrating custom steps

### Database & Operations
* **Relational Database:** MySQL 8.0
* **Storage Cache:** Redis 7 (alpine)
* **Containerization:** Docker, Docker Compose

---

## 📁 Project Structure

Below is an overview of the key folders and files in the repository:

```text
├── backend/                       # Node.js Express Backend
│   ├── config/
│   │   └── env.js                 # Environment variable validation
│   ├── tests/
│   │   └── api.test.js            # API integration tests
│   ├── db.js                      # MySQL pool initialization
│   ├── logger.js                  # Winston logger configuration
│   ├── routes.js                  # API routing, caching, and queue triggers
│   ├── server.js                  # Express application entry point
│   ├── worker.js                  # BullMQ background task workers
│   └── package.json
├── frontend/                      # React Frontend Application
│   ├── public/
│   ├── src/
│   │   ├── components/            # UI components (cards, metrics, charts)
│   │   ├── pages/                 # ExplorePage, DetailsPage, AdminConsole
│   │   ├── api.ts                 # Axios fetch client config
│   │   └── main.tsx
│   ├── nginx.conf                 # Nginx serving config for Docker
│   ├── package.json
│   └── vite.config.ts
├── python_scraper/                # Python Processing & Scraper Engine
│   ├── database/
│   │   ├── db.py                  # Session management and bulk insertion
│   │   ├── models.py              # SQLAlchemy schemas (Internships, Rejections, Health)
│   │   └── cleanup_service.py     # Soft-delete cleanup and dead-link check
│   ├── scrapers/
│   │   ├── base_scraper.py        # Abstract base containing validation and scoring triggers
│   │   ├── indeed.py              # Playwright Indeed scraper
│   │   ├── internshala.py         # Playwright Internshala scraper
│   │   ├── wellfound.py           # Playwright Wellfound scraper
│   │   └── yc_jobs.py             # Playwright YC Jobs scraper
│   ├── scoring/
│   │   └── scoring_service.py     # Algorithms for relevance and legitimacy scoring
│   ├── utils/
│   │   ├── deduplication.py       # Fuzzy matching and canonical key helpers
│   │   ├── filters.py             # Basic cleaning and normalization
│   │   └── validators.py          # 5-stage validation pipeline
│   ├── tests/
│   │   └── test_discovery.py      # Pytest coverage for scoring and filters
│   └── requirements.txt
├── docs/                          # Architecture guides and specifications
│   ├── Architecture/
│   │   └── system-architecture.png
│   ├── backups.md                 # Backup restore and recovery guide
│   └── deployment_guide.md        # Production VPS and cloud guides
├── scripts/                       # Maintenance scripts
│   ├── verify_backup.js           # Gzip/age backup verification script
│   └── backup_db.sh               # Cron database backup script
├── docker-compose.yml             # Docker services orchestrator
├── Dockerfile.backend             # Backend Docker build instructions
├── Dockerfile.frontend            # Frontend Nginx Docker build instructions
├── Dockerfile.scraper             # Scraper Worker Docker build instructions
└── run.py                         # CLI entry point to run scraper pipelines
```

---

## 🔄 Workflow

The platform processes internships through a sequential 8-stage lifecycle to guarantee data cleanliness and accuracy:

```text
[Playwright Scrapers] ──(Raw Data)──> [Validation Pipeline (5 Stages)] ──(Pass)──> [Unified Relevance & Legitimacy Scoring]
                                                                                            │
[Frontend Dashboard] <──(Cached JSON)── [Express API / Redis] <──(MySQL)── [Fuzzy Deduplication & Bulk Insert]
```

1. **Scrape Sources:** Python Playwright scripts crawl job portals concurrently. To optimize performance and bandwidth, the browser blocks heavy visual elements (images, fonts, stylesheets) and rotates random `USER_AGENTS`. If duplicate saturation exceeds **80%** on a single page, the crawler stops.
2. **Standardize & Clean:** Raw scraped listings are run through [filters.py](file:///c:/Users/lenovo/OneDrive/Desktop/Internship-Tracker/python_scraper/utils/filters.py) to clean spacing, extract stipend numbers, and identify remote location keywords.
3. **5-Stage Validation:** Standardized dicts enter [validators.py](file:///c:/Users/lenovo/OneDrive/Desktop/Internship-Tracker/python_scraper/utils/validators.py):
   * *Completeness:* Checks for `company_name`, `role`, `apply_link`, and `source`.
   * *Role Quality:* Screens out non-tech fields (sales, marketing, HR) and whitelists tech titles.
   * *Company Legitimacy:* Evaluates names for placeholders; runs DNS lookup validations on generic titles.
   * *Payment Check:* Rejects unpaid, volunteer, commission, or certificate-only posts.
   * *URL check:* Validates HTTPS protocol and matches the portal domain structure.
4. **Relevance Scoring:** Computes a score based on title keyword boosting, core skill mappings, and description text analysis. Ambiguous roles are assigned to the `NEEDS_RESCUE` tier.
5. **Legitimacy Scoring:** Analyzes metadata trust factors (DNS resolution status, realistic stipend values, location flags, specific skill presence). Roles scoring below **45** are rejected and logged to the `internship_rejections` table.
6. **Description Rescue:** Borderline roles classified as `NEEDS_RESCUE` undergo a localized `GET` request. If the description contains threshold skill words, they are promoted to `MEDIUM_CONFIDENCE` and whitelisted for insertion.
7. **Deduplication & Insertion:** Computes canonical keys `(company||role)` and performs fuzzy similarity checks. Duplicate listings update existing entries with better information. Valid items are saved in bulk using SQLAlchemy `bulk_insert_mappings`.
8. **API Delivery:** Express.js retrieves listings, applies local sanitization against XSS, caches responses for 10 minutes in Redis, and calculates a personalized Match Score dynamically based on the user's specific skill filter query.

---

## 📊 Scoring System

### 1. Relevance Score & Category
Determines if an internship matches tech criteria, categorizing it as **Data/AI** or **Software**. Calculated in [scoring_service.py](file:///c:/Users/lenovo/OneDrive/Desktop/Internship-Tracker/python_scraper/scoring/scoring_service.py):
* **Base Points (+30):** Awarded for matching target categories.
* **Title Matching (Max +55):** Boosts roles containing terms like `Data Scientist`, `ML Engineer`, `Software Engineer`, `Full Stack`.
* **Skills Overlap (Max +20):** Matches exact skills (preventing collisions like Java matching JavaScript) against whitelists (e.g., Python, SQL, React, Node.js).
* **Description Overlap (Max +15):** Scans the description body for matching keywords.
* **Company Domain & Source (+5 to +10):** Boosts domains not matching generic job boards, and prioritizes Wellfound/YC Jobs source platforms.

**Tiers:**
* `HIGHLY_RELEVANT` (Score >= 80)
* `RELEVANT` (Score >= 60)
* `MARGINALLY_RELEVANT` (Score >= 40)
* `IRRELEVANT` (Score < 40) -> *Auto-Rejected*

### 2. Legitimacy Score
Measures trust and credibility from 0 to 100:
* **Paid Check (+20 / -20):** Adds points if marked paid with a valid salary; penalizes if unpaid.
* **DNS Verification (+15 / -15):** Resolves the company domain name to ensure it has a live server.
* **Online Presence (+15 / -5):** Evaluates company name lengths and spacing structures.
* **Tech Skills Listed (+10 / -5):** Adds points if specific tech skills are mentioned in the requirements.
* **URL Security (+10 / -25):** Confirms absolute HTTPS paths and rejects short URLs.
* **Flexibility Boosts (+5 to +15):** Gives boosts for remote flexibility and startup origins.
* **Exclusions / Penalties (-15 to -20):** Imposes penalties for generic roles ("intern", "trainee"), scam terms ("certificate only", "pay for training"), and suspicious company patterns.

**Legitimacy Buckets:**
* `HIGH_CONFIDENCE` (Score >= 80)
* `MEDIUM_CONFIDENCE` (Score 60-79)
* `LOW_CONFIDENCE` (Score 45-59)
* `REJECT` (Score < 45) -> *Blocked from Database*

### 3. User Match Score
Calculated dynamically in Express [routes.js](file:///c:/Users/lenovo/OneDrive/Desktop/Internship-Tracker/backend/routes.js) on every request based on search query parameters:
* **Skills Overlap (40%):** Matches the user's filtered skills against the internship requirements.
* **Role Relevance (25%):** Inherits the pipeline's computed relevance score.
* **Experience Alignment (15%):** Penalizes roles requiring years of experience (detected via regex).
* **Location Preference (10%):** Checks for location or remote preference match.
* **Stipend Alignment (10%):** Checks if the internship stipend exceeds the user's minimum query threshold.

---

## ⚙️ Installation

### Prerequisites
* **Node.js** (v20+ recommended)
* **Python** (v3.9+ with pip)
* **MySQL Server** (v8.0+)
* **Redis Server** (v7.0+)

### Setup Commands

#### 1. Database Initialization
Log into MySQL and execute:
```sql
CREATE DATABASE internship;
```

#### 2. Python Scraper Setup
Install Python dependencies and set up Playwright's browser binaries:
```bash
cd python_scraper
pip install -r requirements.txt
playwright install chromium
```

#### 3. Backend Setup
Install Node dependencies:
```bash
cd ../backend
npm install
```

#### 4. Frontend Setup
Install Vite client dependencies:
```bash
cd ../frontend
npm install
```

---

## 🔒 Environment Variables

Create a `.env` file at the root of the project. A template is provided in [.env.example](file:///c:/Users/lenovo/OneDrive/Desktop/Internship-Tracker/.env.example):

```env
# Backend Express Settings
PORT=5000
FRONTEND_URL=http://localhost:5173
ADMIN_API_KEY=super-secret-admin-key

# Database Connection (MySQL)
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_secure_password
DB_NAME=internship

# Redis Connection (BullMQ & Cache)
REDIS_HOST=127.0.0.1
REDIS_PORT=6379

# Python Scraper Configuration (also used by Docker worker)
DATABASE_URL=mysql+pymysql://root:your_secure_password@localhost/internship
PLAYWRIGHT_HEADLESS=True
```

---

## 🐳 Docker Deployment

The application is fully containerized and ready for production deployment using Docker Compose.

```bash
# Start all containers in detached mode
docker-compose up -d --build
```

### Deployed Services:
* **db:** MySQL database instance hosting relational tables.
* **redis:** Redis caching and queue store.
* **backend:** Express API server (accessible on host port 5000).
* **worker:** BullMQ worker listening for tasks, running playwright in headless Linux.
* **db_backup:** Cron service generating gzip SQL dumps daily at midnight with a 7-day retention policy.
* **frontend:** React client built and served by Nginx (accessible on host port 5173).

### Host Reverse Proxy (Nginx) and SSL
To expose your deployment securely, configure Nginx on the host server:

```nginx
server {
    listen 80;
    server_name internships.yourdomain.com;

    location / {
        proxy_pass http://localhost:5173; # Frontend container
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
    }

    location /api/ {
        proxy_pass http://localhost:5000/api/; # Backend API container
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Generate SSL certificates using Certbot:
```bash
sudo certbot --nginx -d internships.yourdomain.com
```

Block MySQL (3306) and Redis (6379) ports from external access using UFW:
```bash
sudo ufw default deny incoming
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

---

## 📡 API Documentation

### 1. `GET /api/internships`
Fetches a paginated, sorted, and filtered list of internships.

#### Query Parameters:
* `page`: Page number (default: `1`)
* `limit`: Items per page (default: `10`, max: `100`)
* `sort`: Sort criteria (`newest`, `stipend`, `remote_first`, `company`, `legitimacy`, `recently_added`)
* `category`: Filter by role category (`Data/AI` or `Software`)
* `search`: Full-text search string
* `location`: Comma-separated list of locations
* `remote`: Filter by type (`remote`, `onsite`, `hybrid`)
* `skills`: Comma-separated list of skills (matches all selected)
* `stipendMin`: Minimum numeric stipend (default: `0`)
* `legitimacyMin`: Minimum legitimacy score (default: `45`)
* `datePosted`: Posted range (`today`, `3days`, `7days`, `30days`)

#### Response Example (200 OK):
```json
{
  "internships": [
    {
      "apply_link": "https://wellfound.com/jobs/data-analyst",
      "company_name": "Stripe",
      "role": "Data Analyst Intern",
      "stipend": "₹25,000 /month",
      "stipend_numeric": 25000,
      "paid": true,
      "location": "Bangalore",
      "remote": false,
      "duration": "3 Months",
      "skills": "SQL, Python, Excel",
      "skills_list": ["SQL", "Python", "Excel"],
      "source": "Wellfound",
      "legitimacy_score": 85,
      "relevance_score": 90,
      "relevance_tier": "HIGHLY_RELEVANT",
      "confidence": "HIGH_CONFIDENCE",
      "match_score": 95,
      "posted_at": "2026-06-08T12:00:00.000Z",
      "created_at": "2026-06-08T12:00:00.000Z"
    }
  ],
  "total": 1,
  "page": 1,
  "limit": 10,
  "totalPages": 1
}
```

### 2. `GET /api/internships/:applyLink`
Fetches detailed internship metadata and recommends 3 similar positions. Accepts base64 encoded links or decoded strings.

#### Response Example (200 OK):
```json
{
  "internship": {
    "apply_link": "https://wellfound.com/jobs/data-analyst",
    "company_name": "Stripe",
    "role": "Data Analyst Intern",
    "skills_list": ["SQL", "Python", "Excel"],
    "description": "We are looking for a Data Analyst intern...",
    "legitimacy_score": 85,
    "relevance_score": 90
  },
  "similar": [
    {
      "apply_link": "https://internshala.com/jobs/analytics-intern",
      "company_name": "Razorpay",
      "role": "Analytics Intern",
      "stipend": "₹20,000 /month",
      "stipend_numeric": 20000,
      "skills_list": ["SQL", "Excel"]
    }
  ]
}
```

### 3. `GET /api/filters`
Returns popular filter lists extracted from active database listings. Cached for 10 minutes.

#### Response Example (200 OK):
```json
{
  "locations": ["Bangalore", "Mumbai", "Delhi", "Hyderabad"],
  "sources": ["Indeed India", "Internshala", "Wellfound", "YC Jobs"],
  "skills": [
    { "name": "Python", "count": 124 },
    { "name": "SQL", "count": 98 }
  ]
}
```

### 4. `GET /api/stats`
Retrieves aggregated metrics and chart coordinates. Cached for 10 minutes.

#### Response Example (200 OK):
```json
{
  "metrics": {
    "totalScraped": 1280,
    "highlyLegit": 240,
    "avgLegitimacy": 72.4,
    "aiDataCount": 182,
    "softwareCount": 115,
    "rejectedNonTech": 650
  },
  "charts": {
    "skillsDemand": [{ "name": "Python", "value": 124 }],
    "topPaying": [{ "company": "Stripe", "role": "Data Analyst Intern", "stipend": 25000 }],
    "remoteDistribution": [
      { "name": "Remote", "value": 110 },
      { "name": "On-site", "value": 187 }
    ]
  }
}
```

### 5. `POST /api/scrapers/run`
Queues a scraper run task in BullMQ. Requires authentication.

#### Headers:
* `X-Admin-API-Key`: `your_secure_admin_key`

#### Response Example (200 OK):
```json
{
  "status": "running",
  "message": "Scraper run queued successfully.",
  "jobId": "1"
}
```

---

## 🧪 Testing

### Python Scraper Tests
Run unit tests checking canonical keys, fuzzy duplicate ratios, exact word boundaries, relevance categories, and legitimacy scores:
```bash
cd python_scraper
pytest
```

### Backend API Tests
Run Express integration tests using the native Node test runner. Ensure the backend is running locally before executing:
```bash
cd backend
npm test
```

### Local Load Testing
A load-test script is located in `scripts/load-test.js`. Execute it to test concurrency performance:
```bash
node scripts/load-test.js
```

---

## 🔒 Security

* **Rate Limiting:** Every endpoint is protected by `express-rate-limit`, constraining API requests to a maximum of 100 requests per 15 minutes per IP address.
* **Admin Verification:** Action endpoints (`/scrapers/run`, `/scrapers/cleanup`, `/scrapers/liveness`) are protected by the `verifyAdminKey` middleware which rejects requests missing the `X-Admin-API-Key` header.
* **XSS Sanitization:** Page descriptions are run through `sanitize-html` before delivery to scrub scripting blocks, attributes, and tags.
* **Database Injection Prevention:** MySQL queries in the API use parameterized prepared statements; Python queries are written using SQLAlchemy core ORM constructs.
* **Secure HTTP Headers:** Express applies Helmet middleware to inject standard security headers.

---

## 📈 Monitoring

The backend exposes diagnostic endpoints for infrastructure monitoring (e.g., Kubernetes probes or UptimeRobot):
* **Liveness Probe (`GET /api/live`):** Verifies Express router responsiveness.
* **Readiness Probe (`GET /api/ready`):** Verifies the backend can fetch connections from the MySQL pool.
* **Health Probe (`GET /api/health`):** Aggregates:
  * Database latency check.
  * Redis cluster connection state.
  * Individual scraper health logs (from the `source_health` table).
  * Automated gzip database backup verification metrics.

---

## 🗺️ Roadmap

- [ ] **Semantic Vector Search:** Migrate the standard MySQL Full-Text search to an vector-based search using embeddings for roles and skills.
- [ ] **Daily Email Alerts:** Connect the frontend email alert modal to an active NodeMailer/SendGrid worker scheduling daily digest mailings.
- [ ] **Multi-Agent Resume Screening:** Expand the frontend resume matcher to use an LLM for parsing resume PDFs and recommending specific roles based on soft skills and projects.
- [ ] **Historical Salary Index:** Map aggregate stipend trends over quarters to compile an entry-level market intelligence report.

---

## 🤝 Contributing

We welcome contributions to expand the platform's capabilities:
1. Fork the repository.
2. Create a feature branch: `git checkout -b feature/amazing-feature`.
3. Commit your changes: `git commit -m 'feat: add support for new job portal'`.
4. Push to the branch: `git push origin feature/amazing-feature`.
5. Open a Pull Request.

---

## 📄 License

Distributed under the MIT License. See [LICENSE](LICENSE) for more information.
