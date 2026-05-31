# 🚀 Internship Discovery & Tracking Engine

An automated, high-performance internship discovery engine and analytics dashboard. It crawls major platforms (Internshala, Wellfound, YC Jobs, Indeed India), validates and filters positions using custom NLP/role-quality heuristics, checks for dead links asynchronously, and serves them via an Express API with an interactive React & TypeScript dashboard.

---

## 🌟 Key Features

### 1. **Scraping Pipeline (Python & Playwright)**
* **Concurrency & Efficiency:** Parallel scrapers run concurrently under a single, lightweight browser instance using Playwright Async API.
* **Smart Pagination:** Sequential page crawling monitors duplicate saturation relative to active database links. Crawling automatically ceases when duplicate saturation on a single page exceeds **80%** or no listings are found.
* **Anti-Detection:** Human-like pacing (slow-mo inputs), randomized desktop user-agent rotation, and header spoofing.
* **Resource Optimization:** Playwright is configured to block irrelevant media/stylesheet resources, reducing bandwidth and speed overhead.

### 2. **Rule-Based Legitimacy & Verification Engine**
* **Fuzzy Role Classification:** Resolves noisy role titles (e.g. "Marketing Analytics Intern") by normalizing punctuation and performing fuzzy keyword checks via `rapidfuzz` token matching. Classified into confidence tiers: `HIGH` (direct data roles), `MEDIUM` (potential matches), and `LOW` (weak signals).
* **Description-Based Rescue:** Borderline roles (e.g., "Operations Intern") are loaded via HTTP `GET` to download page HTML. The engine extracts text and checks it against `RESCUE_KEYWORDS` (e.g., SQL, Excel, Python, Tableau). If a threshold of skills is matched, the role is saved and promoted to `MEDIUM` confidence.
* **Liveness Gate:** Automatically audits URLs during liveness checks and description rescue to ensure forms/URLs are active before DB insertion.
* **Stale Cleanup:** Runs a cron/cleanup phase to purge listings older than 4 days and periodically audits existing database links for HTTP status codes (2xx/3xx).

### 3. **Express.js API Layer**
* **Memory Caching:** Features a fast 30-second local caching layer that dramatically reduces query overhead for high-frequency dashboard users.
* **Robust Query Filtering:** Full support for multi-faceted filters (e.g. min/max stipend, date posted, multi-select locations, specific skills, platforms, remote/hybrid flags, and **relevance confidence tiers**).
* **Scraper Trigger Host:** Exposes background process spawning (`child_process.spawn`) so the web frontend can initiate, stream, and log scraper runs dynamically.

### 4. **Modern Admin Dashboard (React & TypeScript)**
* **Analytics Panel:** Visualize hiring trends, top paying companies, popular skills demand, and remote distributions using interactive **Recharts**.
* **Faceted Search:** Refined sidebar search with dynamic filters populated straight from active database aggregates.
* **Relevance Badges:** Internship listings automatically display visual badges indicating match strength (`Highly Relevant`, `Potential Match`, `Possible Match`).
* **Scraper Console:** A live-streaming execution terminal inside the browser to run and watch scraper metrics in real-time.

---

## 🏗️ Architecture

```mermaid
graph TD
    subgraph Scraping Pipeline (Python)
        A[run.py Runner] --> B[Playwright Headless Browser]
        B --> C1[Internshala Scraper]
        B --> C2[Wellfound Scraper]
        B --> C3[YC Jobs Scraper]
        B --> C4[Indeed India Scraper]
        C1 & C2 & C3 & C4 --> D[Liveness Gate, Fuzzy Role Match & Description Rescue]
        D --> E[(MySQL Database)]
    end
    
    subgraph Web App Service
        E --> F[Express.js Backend API]
        F --> G[30s Memory Cache]
        G --> H[Router Endpoints]
        H --> I[React Frontend Dashboard]
        I -->|Triggers Scraper Run| H
    end
```

---

## 🛠️ Tech Stack

* **Frontend:** React 18, TypeScript, Tailwind CSS, Recharts, Lucide Icons, Axios.
* **Backend:** Node.js, Express, MySQL (`mysql2` wrapper with connection pools).
* **Scraping Engine:** Python 3, Playwright Async, SQLAlchemy (ORM), BeautifulSoup4, RapidFuzz.
* **Database:** MySQL.

---

## 💾 Database Schema

The SQLAlchemy model maps directly to the `internships` table structure:

| Column Name | Data Type | Nullable | Description |
| :--- | :--- | :--- | :--- |
| `apply_link` (PK) | `VARCHAR(500)` | No | Absolute URL of the listing (serves as primary key) |
| `company_name` | `VARCHAR(255)` | No | Name of hiring company |
| `role` | `VARCHAR(255)` | No | Title of the position |
| `stipend` | `VARCHAR(100)` | Yes | Formatted stipend string (e.g. "₹15,000 /month") |
| `stipend_numeric` | `INT` | No | Extracted numerical value for range queries |
| `paid` | `BOOLEAN` | No | Flag indicating if a stipend is provided |
| `location` | `VARCHAR(255)` | Yes | Work city or location detail |
| `remote` | `BOOLEAN` | No | Flag for remote working positions |
| `duration` | `VARCHAR(100)` | Yes | Duration of the internship (e.g. "6 Months") |
| `skills` | `VARCHAR(500)` | Yes | Comma-separated list of required tags |
| `source` | `VARCHAR(100)` | No | Source platform (e.g. Wellfound) |
| `legitimacy_score`| `INT` | No | Calculated score (0-100) for listing trust |
| `confidence` | `VARCHAR(50)` | No | Relevance confidence tier (`HIGH`, `MEDIUM`, `LOW`) |
| `freshness_score` | `INT` | No | Freshness scale based on timestamp age |
| `posted_at` | `DATETIME` | Yes | Date the position was published |
| `created_at` | `DATETIME` | No | Timestamp of database insertion |

---

## 🚀 Getting Started

### 📋 Prerequisites
* **Node.js** (v16+)
* **Python** (v3.8+)
* **MySQL Server** (running locally or remotely)

---

### 🔧 Installation & Setup

#### 1. Database Configuration
Create a database named `internship` in your MySQL server:
```sql
CREATE DATABASE internship;
```

#### 2. Scraping Engine Setup
Navigate to `python_scraper` directory, install packages, and install Playwright webkit/chrome:
```bash
# From the root directory
cd python_scraper
pip install -r requirements.txt
playwright install chromium
```
*Note: Config constants like DB credentials, threshold limits, and blacklist phrases can be tuned directly inside [config.py](file:///c:/Users/lenovo/OneDrive/Desktop/Internship-Tracker/python_scraper/config.py).*

#### 3. Backend Setup
Configure your environment variables in a `.env` file under the `/backend` directory:
```env
PORT=5000
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=yourpassword
DB_NAME=internship
```
Then install dependencies:
```bash
cd ../backend
npm install
```

#### 4. Frontend Setup
Navigate to the `/frontend` directory and install UI dependencies:
```bash
cd ../frontend
npm install
```

---

## 🏃 Running the Application

### Option A: Development Environment (Recommended)
You can run the web client and backend services concurrently:

1. **Start Backend API Server:**
   ```bash
   cd backend
   npm run dev
   ```
   *Logs will show connection details and cache load stats.*

2. **Start React Frontend Client:**
   ```bash
   cd frontend
   npm run dev
   ```
   *Usually spins up on `http://localhost:5173`.*

3. **Perform Initial Scraping Run:**
   To populate the database manually, you can run the standalone scraper pipeline from the root directory:
   ```bash
   python run.py
   ```
   *Alternatively, navigate to the **Scraper Console** tab on the React web dashboard and click **Run Scrapers**.*

---

## 📊 Pipeline Quality & Yield Metrics

With the upgrades to **Fuzzy Keyword Validation** and **Description-Based Rescue**, pipeline recall and database yields have increased significantly:

| Metric | Upgraded Pipeline Value | Description |
| :--- | :--- | :--- |
| **Raw Scraped Listings** | **~1000+** | Extracted across expanded categories and pagination |
| **Direct Whitelist Matches** | **~175+** | Directly classified as Highly Relevant (`HIGH`) |
| **Description Rescued Roles** | **~440+** | Borderline roles rescued and classified as Potential Matches (`MEDIUM`) |
| **Deduplicated Listings** | **~130+** | Duplicates skipped based on stipend matching |
| **Final MySQL Insertions** | **~480+** | High-quality internships inserted into database |
| **Collection Yield Rate** | **~47%** | Yield percentage of raw results stored in DB |
