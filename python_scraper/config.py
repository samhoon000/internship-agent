import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent

# Database Configuration
# Local SQL connection: Database Name: internship, Table Name: internships, Host: localhost, no password
DATABASE_URL = "mysql+pymysql://root:@localhost/internship"

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
    "data analyst", "business analyst", "data analytics", "analytics", "sql",
    "power bi", "tableau", "bi analyst", "research analyst", "reporting analyst",
    "data engineer", "data science", "machine learning", "quant analyst",
    "quantitative analyst", "technical analyst", "financial analyst",
    "statistics", "data visualization", "excel", "python", "pandas", "databricks",
    "data analysis", "data specialist", "bi developer", "data architect",
    "data modeler", "data wrangler", "insights analyst", "product analyst",
    "analytics engineer"
]

ROLE_CONTEXT_KEYWORDS = [
    "data", "analyst", "analytics", "sql", "business intelligence", "reporting", "analysis"
]

ROLE_HARD_EXCLUDE_KEYWORDS = [
    "marketing", "seo", "wordpress", "react", "node", "frontend", "backend",
    "full stack", "sales", "hr", "customer support", "content writing",
    "social media", "recruiting", "talent acquisition", "telecalling",
    "telecaller", "bda", "bde", "receptionist", "graphic design"
]

ROLE_SOFT_EXCLUDE_KEYWORDS = [
    "software developer", "software engineer", "web development", "wordpress", "flutter",
    "java developer", "android", "ios", "ui ux", "operations", "campus ambassador",
    "business development"
]

STRONG_TECH_KEYWORDS = ROLE_WHITELIST_KEYWORDS
PARTIAL_TECH_KEYWORDS = []
TECH_KEYWORDS = STRONG_TECH_KEYWORDS + PARTIAL_TECH_KEYWORDS

BOOST_SKILLS = [
    "sql", "python", "excel", "power bi", "tableau", "pandas", "numpy",
    "data visualization", "statistics", "machine learning", "etl", "dashboarding",
    "google sheets", "reporting", "data cleaning"
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
    "techcorp", "ai labs inc", "futuretech", "neural ai corp",
    "tech solutions", "global tech", "digital solutions",
    "innovation labs", "synergy", "nexgen", "quantum solutions",
    "alpha tech", "beta systems", "dummy", "test company",
    "sample corp", "example inc", "fake", "placeholder",
    "lorem ipsum", "acme corp", "xyz company", "abc technologies",
]

# ── Legitimacy Scoring Settings ───────────────────────────────────
# Minimum legitimacy score required to INSERT into SQL.
# Internships scoring below this threshold are AUTO-REJECTED.
MIN_LEGITIMACY_TO_KEEP = 60

# Score buckets:
# 90-100 = Excellent
# 75-89  = High Confidence
# 60-74  = Good
# 40-59  = Risky (auto-rejected before SQL insert)
# 0-39   = Reject (auto-rejected before SQL insert)
