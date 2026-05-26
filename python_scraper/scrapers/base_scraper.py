import time
import random
import logging
from abc import ABC, abstractmethod
from python_scraper.config import (
    USER_AGENTS,
    REQUEST_TIMEOUT,
    SCRAPE_DELAY_MIN,
    SCRAPE_DELAY_MAX,
    MIN_LEGITIMACY_TO_KEEP,
)
from python_scraper.utils.filters import clean_internship
from python_scraper.utils.validators import run_validation_pipeline
from python_scraper.scoring.legitimacy import calculate_legitimacy_score

logger = logging.getLogger("python_scraper.scrapers.base")

class BaseScraper(ABC):
    def __init__(self, source_name: str):
        self.source_name = source_name
        self.scraped_count = 0
        self.rejected_suspicious = 0
        self.broken_urls = 0
        self.non_tech_roles = 0
        self.unpaid_or_cert = 0
        self.missing_fields = 0
        self.score_below_threshold = 0
        self.blocked = False

    def save_debug_artifacts(self, page, custom_name: str = None):
        """Saves page screenshot and HTML content for debugging."""
        import os
        from datetime import datetime
        os.makedirs("debug_screenshots", exist_ok=True)
        os.makedirs("debug_html", exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name_prefix = custom_name or self.source_name.lower().replace(" ", "_")
        
        screenshot_path = f"debug_screenshots/{name_prefix}_{timestamp}.png"
        html_path = f"debug_html/{name_prefix}_{timestamp}.html"
        
        try:
            page.screenshot(path=screenshot_path)
            logger.info(f"[{self.source_name}] Saved debug screenshot to {screenshot_path}")
        except Exception as e:
            logger.error(f"[{self.source_name}] Failed to save debug screenshot: {e}")
            
        try:
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(page.content())
            logger.info(f"[{self.source_name}] Saved debug HTML to {html_path}")
        except Exception as e:
            logger.error(f"[{self.source_name}] Failed to save debug HTML: {e}")


    @abstractmethod
    def scrape_live(self) -> list[dict]:
        """Performs the live web scraping logic. Returns a list of raw internship dictionaries."""
        pass

    def scrape(self) -> list[dict]:
        """
        Public orchestrator:
        1. Attempts to scrape live data.
        2. If live scraping fails or is blocked, returns [].
        3. Standardizes columns, applies the 5-stage validation pipeline, and calculates legitimacy score.
        4. Performs Quality Assurance checks (detecting scoring bugs or synthetic data).
        """
        logger.info(f"[{self.source_name}] Initiating live scraping process...")
        raw_results = []
        
        # Reset metrics on each scraping run
        self.scraped_count = 0
        self.rejected_suspicious = 0
        self.broken_urls = 0
        self.non_tech_roles = 0
        self.unpaid_or_cert = 0
        self.missing_fields = 0
        self.score_below_threshold = 0
        self.blocked = False

        try:
            raw_results = self.scrape_live()
        except Exception as e:
            logger.error(f"[{self.source_name}] Critical error during live scraping: {e}", exc_info=True)

        if not raw_results:
            logger.warning(f"[{self.source_name}] Live scraper returned 0 items. No internships retrieved.")
            self.blocked = True
            return []

        processed_results = []
        self.scraped_count = len(raw_results)
        
        for item in raw_results:
            # 1. Clean & Standardize
            cleaned = clean_internship(item)
            
            # 2. Run through the strict 5-stage validation pipeline
            is_valid, validation_reasons = run_validation_pipeline(cleaned)
            if not is_valid:
                logger.warning(f"[{self.source_name}] Internship at '{cleaned.get('company_name')}' failed validation pipeline:")
                for reason in validation_reasons:
                    logger.warning(f"  - {reason}")
                    if "[COMPLETENESS]" in reason:
                        self.missing_fields += 1
                    elif "[ROLE]" in reason:
                        self.non_tech_roles += 1
                    elif "[COMPANY]" in reason:
                        self.rejected_suspicious += 1
                    elif "[PAYMENT]" in reason:
                        self.unpaid_or_cert += 1
                    elif "[URL]" in reason:
                        self.broken_urls += 1
                continue
                
            # 3. Apply legitimacy scoring engine
            score = calculate_legitimacy_score(cleaned)
            cleaned['legitimacy_score'] = score
            
            # 4. Strict SQL insert safety gate check (score must be >= MIN_LEGITIMACY_TO_KEEP (60))
            if score < MIN_LEGITIMACY_TO_KEEP:
                logger.warning(f"[{self.source_name}] Internship at '{cleaned.get('company_name')}' rejected: score {score} is below required {MIN_LEGITIMACY_TO_KEEP}")
                self.score_below_threshold += 1
                continue
                
            processed_results.append(cleaned)

        # Print the detailed production metrics for this scraper run
        logger.info(f"[{self.source_name}] --- Scraping Run Summary ---")
        logger.info(f"[{self.source_name}] Real internships scraped: {self.scraped_count}")
        logger.info(f"[{self.source_name}] Rejected non-tech roles: {self.non_tech_roles}")
        logger.info(f"[{self.source_name}] Rejected suspicious/invalid companies: {self.rejected_suspicious}")
        logger.info(f"[{self.source_name}] Rejected unpaid/commission opportunities: {self.unpaid_or_cert}")
        logger.info(f"[{self.source_name}] Broken/invalid URLs rejected: {self.broken_urls}")
        logger.info(f"[{self.source_name}] Missing critical fields: {self.missing_fields}")
        logger.info(f"[{self.source_name}] Rejected with low confidence (score < {MIN_LEGITIMACY_TO_KEEP}): {self.score_below_threshold}")
        logger.info(f"[{self.source_name}] Passed all gates & ready for SQL: {len(processed_results)}")

        # ── QUALITY ASSURANCE CHECK ──
        if processed_results:
            # QA 1: >80% internships score 100 check
            hundred_scores = sum(1 for item in processed_results if item['legitimacy_score'] == 100)
            percentage_hundred = (hundred_scores / len(processed_results)) * 100
            if percentage_hundred > 80:
                logger.warning(f"[{self.source_name}] QA WARNING: Potential scoring bug detected. {percentage_hundred:.1f}% of internships scored exactly 100.")
            
            # QA 2: Same patterns repeating check (Synthetic Data Issue)
            roles = [item['role'].lower() for item in processed_results]
            companies = [item['company_name'].lower() for item in processed_results]
            skills_list = [item['skills'].lower() for item in processed_results]
            
            if len(processed_results) >= 4:
                from collections import Counter
                most_common_company, company_count = Counter(companies).most_common(1)[0]
                most_common_role, role_count = Counter(roles).most_common(1)[0]
                most_common_skills, skills_count = Counter(skills_list).most_common(1)[0]
                
                pct_company = (company_count / len(processed_results)) * 100
                pct_role = (role_count / len(processed_results)) * 100
                pct_skills = (skills_count / len(processed_results)) * 100
                
                if pct_company >= 75 or pct_role >= 75 or pct_skills >= 75:
                    logger.warning(f"[{self.source_name}] QA WARNING: Potential synthetic data issue. Highly repetitive patterns detected. "
                                   f"(Most common company makes up {pct_company:.1f}%, role {pct_role:.1f}%, skills {pct_skills:.1f}%)")

        return processed_results


