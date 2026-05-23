import time
import random
import logging
import requests
from abc import ABC, abstractmethod
from internship_agent.config import USER_AGENTS, REQUEST_TIMEOUT, SCRAPE_DELAY_MIN, SCRAPE_DELAY_MAX
from internship_agent.utils.filters import clean_internship, is_tech_role
from internship_agent.scoring.legitimacy import calculate_legitimacy_score

logger = logging.getLogger("internship_agent.scrapers.base")

class BaseScraper(ABC):
    def __init__(self, source_name: str):
        self.source_name = source_name
        self.session = requests.Session()

    def get_headers(self) -> dict:
        """Generates realistic headers mimicking a standard desktop browser."""
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0"
        }

    def fetch_url(self, url: str) -> str:
        """Fetches HTML from a URL with retries, random delays, and custom headers."""
        retries = 3
        backoff = 2

        for attempt in range(retries):
            # Anti-bot delay
            delay = random.uniform(SCRAPE_DELAY_MIN, SCRAPE_DELAY_MAX)
            logger.info(f"[{self.source_name}] Waiting {delay:.2f}s before request (anti-bot delay)...")
            time.sleep(delay)

            try:
                logger.info(f"[{self.source_name}] Fetching URL (Attempt {attempt + 1}/{retries}): {url}")
                headers = self.get_headers()
                response = self.session.get(url, headers=headers, timeout=REQUEST_TIMEOUT)

                if response.status_code == 200:
                    return response.text
                elif response.status_code == 403:
                    logger.warning(f"[{self.source_name}] Access Forbidden (403) - Potential Cloudflare block.")
                    break  # Stop retrying if explicitly forbidden
                else:
                    logger.warning(f"[{self.source_name}] Received status code {response.status_code} from server.")

            except requests.RequestException as e:
                logger.error(f"[{self.source_name}] Request error on attempt {attempt + 1}: {e}")
            
            # Backoff before retry
            time.sleep(backoff)
            backoff *= 2

        return ""

    @abstractmethod
    def scrape_live(self) -> list[dict]:
        """Performs the live web scraping logic. Returns a list of raw internship dictionaries."""
        pass

    def scrape(self) -> list[dict]:
        """
        Public orchestrator:
        1. Attempts to scrape live data.
        2. If live scraping fails or is blocked (returns empty list), activates the Premium Fallback Engine.
        3. Filters internships (keeps only tech roles).
        4. Cleans and standardizes columns.
        5. Computes the legitimacy score.
        """
        logger.info(f"[{self.source_name}] Initiating scraping process...")
        raw_results = []
        
        try:
            raw_results = self.scrape_live()
        except Exception as e:
            logger.error(f"[{self.source_name}] Critical error during live scraping: {e}", exc_info=True)

        # No fallback data; return empty list if live scraping yields no results
        if not raw_results:
            logger.warning(f"[{self.source_name}] Live scraper returned 0 items (blocked or offline). No fallback data available.")
            # raw_results remains empty
        processed_results = []
        for item in raw_results:
            # 1. Clean & Standardize
            cleaned = clean_internship(item)
            
            # 2. Tech Role Filter check
            if not is_tech_role(cleaned['role']):
                logger.debug(f"[{self.source_name}] Filtering out non-tech role: {cleaned['role']} at {cleaned['company_name']}")
                continue
                
            # 3. Apply legitimacy scoring engine
            score = calculate_legitimacy_score(cleaned)
            cleaned['legitimacy_score'] = score
            
            processed_results.append(cleaned)

        logger.info(f"[{self.source_name}] Scraping complete. Filtered down to {len(processed_results)} legit tech internships.")
        return processed_results

    # Fallback data method removed as per requirements; scrapers must return real data only.
