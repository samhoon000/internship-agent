import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "database" / "internship.db"

# Database Configuration
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# Ensure database directory exists
DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

# Scraper Settings
REQUEST_TIMEOUT = 15  # seconds
SCRAPE_DELAY_MIN = 2  # seconds
SCRAPE_DELAY_MAX = 5  # seconds
PAGES_TO_SCRAPE = 3  # default number of pages per source

# User Agents list for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

# Strict Filter Keywords
TECH_KEYWORDS = [
    "python", "sql", "data", "machine learning", "ai", "analytics", "backend",
    "software engineer", "react", "javascript", "node", "deep learning", 
    "computer science", "full stack", "frontend", "c++", "java", "golang", "devops",
    "data engineering", "data analyst", "data science"
]

EXCLUDE_KEYWORDS = [
    "sales", "marketing", "hr", "campus ambassador", "business development", 
    "telecalling", "unpaid", "certificate-only", "graphic design", "content writing",
    "social media", "seo", "recruiting", "talent acquisition"
]

# Legitimacy Scoring Settings
MIN_LEGITIMACY_TO_KEEP = 0  # We store all scraped, but filter them in the UI or scoring thresholds.
# Buckets:
# 80-100 = Highly Legit
# 60-79 = Good
# 40-59 = Risky
# 0-39 = Avoid
