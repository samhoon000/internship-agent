import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://root:@localhost/internship")

# Expiration and Liveness settings
ACTIVE_THRESHOLD_DAYS = 21
INACTIVE_THRESHOLD_DAYS = 30
ARCHIVED_THRESHOLD_DAYS = 90
PURGE_OLD_RECORDS = False
CONSECUTIVE_FAILURES_LIMIT = 3

# ── Scraper Settings ──────────────────────────────────────────────
REQUEST_TIMEOUT = 20  # seconds
SCRAPE_DELAY_MIN = 2  # seconds (anti-bot minimum delay)
SCRAPE_DELAY_MAX = 6  # seconds (anti-bot maximum delay)
PAGES_TO_SCRAPE = 3   # default number of pages per source

# User Agents list for rotation (realistic, modern browsers)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
]

# ── Playwright Browser Settings ──────────────────────────────────
PLAYWRIGHT_HEADLESS = False  # Set True for headless server environments
PLAYWRIGHT_SLOW_MO = 80     # milliseconds between Playwright actions (human-like pacing)
PLAYWRIGHT_VIEWPORT = {"width": 1366, "height": 768}
PLAYWRIGHT_TIMEOUT = 30000   # milliseconds – page navigation timeout

# ── Strict Filter Keywords ────────────────────────────────────────
ROLE_WHITELIST_KEYWORDS = [
    # Data Analytics
    "data analyst", "data analytics", "business analyst", "analytics intern", "reporting analyst",
    "business intelligence", "bi analyst", "mis analyst", "mis executive", "research analyst",
    "quantitative analyst", "operations analyst", "financial analyst", "market analyst", "risk analyst",
    "product analyst", "data specialist", "bi developer", "data architect", "data modeler",
    "data wrangler", "insights analyst", "analytics engineer",
    # Data Engineering
    "data engineer", "etl intern", "data pipeline", "sql developer", "database analyst",
    "database intern", "databricks", "cloud data engineer",
    # ML / AI / DS
    "machine learning", "ai intern", "data science", "nlp", "computer vision", "model evaluation",
    "annotation", "ai benchmarking", "llm evaluation", "synthetic data", "data labeling",
    # Tools / General
    "sql", "python", "pandas", "excel", "tableau", "power bi", "statistics", "visualization",
    "spark", "bigquery",
    # AI / ML / Startup Roles (YC Parity Whitelist)
    "ai engineer", "ml engineer", "founding engineer", "founding ai engineer", "product engineer", 
    "software engineer", "founding software engineer", "research engineer"
]

ROLE_CONTEXT_KEYWORDS = [
    "data", "analyst", "analytics", "sql", "business intelligence", "reporting", "analysis",
    "ai", "ml", "etl", "bi", "mis", "database", "python", "excel", "tableau", "power bi"
]

ROLE_HARD_EXCLUDE_KEYWORDS = [
    "marketing", "seo", "sales", "hr", "customer support", "content writing",
    "social media", "telecalling", "telecaller", "human resources"
]

ROLE_SOFT_EXCLUDE_KEYWORDS = [
    "software developer", "software engineer", "web development", "wordpress", "flutter",
    "java developer", "android", "ios", "ui ux", "campus ambassador",
    "business development", "react", "node", "frontend", "backend", "full stack",
    # Previous hard exclusions demoted to soft exclusions
    "recruiting", "talent acquisition", "bda", "bde", "receptionist", "graphic design",
    "educational consultant", "copywriter", "interior designer", "electronics engineer",
    "recruiter", "designer", "consultant"
]

STRONG_TECH_KEYWORDS = ROLE_WHITELIST_KEYWORDS
PARTIAL_TECH_KEYWORDS = []
TECH_KEYWORDS = STRONG_TECH_KEYWORDS + PARTIAL_TECH_KEYWORDS

BOOST_SKILLS = [
    "sql", "python", "excel", "power bi", "tableau", "pandas", "numpy",
    "data visualization", "statistics", "machine learning", "etl", "dashboarding",
    "google sheets", "reporting", "data cleaning"
]

RESCUE_KEYWORDS = [
    "sql", "python", "excel", "pandas", "numpy", "tableau", "power bi",
    "powerbi", "dashboard", "reporting", "data cleaning", "analytics",
    "etl", "bigquery", "spark", "databricks", "data science", "machine learning",
    "data analysis", "data pipeline", "statistics", "data visualization", "data analyst",
    "business intelligence", "research", "database"
]

EXCLUDE_KEYWORDS = ROLE_HARD_EXCLUDE_KEYWORDS + ROLE_SOFT_EXCLUDE_KEYWORDS


# ── Source Domain Mappings (for URL validation) ───────────────────
# Each source's apply_link MUST contain one of its allowed domains.
SOURCE_DOMAIN_MAP = {
    "Internshala":   ["internshala.com"],
    "Wellfound":     ["wellfound.com"],
    "YC Jobs":       ["workatastartup.com"],
    "Indeed India":  ["indeed.com", "in.indeed.com"],
}

# ── Suspicious Company Name Patterns ──────────────────────────────
# Heuristic patterns that indicate a generated / hallucinated company name.
SUSPICIOUS_COMPANY_PATTERNS = [
    "dummy", "test company", "sample corp", "example inc", "fake", "placeholder",
    "lorem ipsum", "acme corp",
]

# ── Legitimacy Scoring Settings ───────────────────────────────────
# Minimum legitimacy score required to INSERT into SQL.
# Internships scoring below this threshold are AUTO-REJECTED.
MIN_LEGITIMACY_TO_KEEP = 45

# Score buckets:
# 80+ HIGH_CONFIDENCE
# 60-79 MEDIUM_CONFIDENCE
# 45-59 LOW_CONFIDENCE
# <45 REJECT

# Validate configuration on startup
from urllib.parse import urlparse
import sys

if not DATABASE_URL:
    print("\n❌ FATAL CONFIGURATION ERROR: DATABASE_URL is not set.\n", file=sys.stderr)
    sys.exit(1)

parsed_db = urlparse(DATABASE_URL)
allowed_schemes = {"postgresql", "postgresql+psycopg2", "postgres", "mysql+pymysql"}
if parsed_db.scheme not in allowed_schemes and not any(DATABASE_URL.startswith(f"{s}://") for s in allowed_schemes):
    print(f"\n❌ FATAL CONFIGURATION ERROR:\nDATABASE_URL must use a supported PostgreSQL/MySQL scheme. Got: '{DATABASE_URL}'\n", file=sys.stderr)
    sys.exit(1)


