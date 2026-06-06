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
from python_scraper.scoring.scoring_service import calculate_legitimacy_score, get_legitimacy_bucket

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

    async def save_debug_artifacts(self, page, custom_name: str = None):
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
            await page.screenshot(path=screenshot_path)
            logger.info(f"[{self.source_name}] Saved debug screenshot to {screenshot_path}")
        except Exception as e:
            logger.error(f"[{self.source_name}] Failed to save debug screenshot: {e}")
            
        try:
            content = await page.content()
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"[{self.source_name}] Saved debug HTML to {html_path}")
        except Exception as e:
            logger.error(f"[{self.source_name}] Failed to save debug HTML: {e}")



    @abstractmethod
    async def scrape_live(self, browser_context) -> list[dict]:
        """Performs the live web scraping logic. Returns a list of raw internship dictionaries."""
        pass

    async def scrape(self, browser_context=None) -> list[dict]:
        """
        Public orchestrator:
        1. Attempts to scrape live data.
        2. If live scraping fails or is blocked, returns [].
        3. Standardizes columns, applies the 5-stage validation pipeline (skipping HTTP liveness check), and calculates legitimacy score.
        4. Performs Quality Assurance checks (detecting scoring bugs or synthetic data).
        """
        logger.info(f"[{self.source_name}] Initiating live scraping process...")
        raw_results = []
        
        # Load existing links from DB to calculate duplicate saturation
        try:
            from python_scraper.database.db import get_db_session, Internship
            db_session = get_db_session()
            self.existing_links = {r[0] for r in db_session.query(Internship.apply_link).all()}
            db_session.close()
        except Exception as e:
            logger.warning(f"[{self.source_name}] Failed to load existing links from DB: {e}")
            self.existing_links = set()
        
        # Reset metrics on each scraping run
        self.scraped_count = 0
        self.rejected_suspicious = 0
        self.broken_urls = 0
        self.non_tech_roles = 0
        self.unpaid_or_cert = 0
        self.missing_fields = 0
        self.score_below_threshold = 0
        self.blocked = False

        local_playwright = None
        local_browser = None
        local_context = None

        try:
            if browser_context is None:
                from playwright.async_api import async_playwright
                from python_scraper.config import PLAYWRIGHT_HEADLESS
                logger.info(f"[{self.source_name}] No shared browser context provided. Launching local Playwright instance.")
                local_playwright = await async_playwright().start()
                local_browser = await local_playwright.chromium.launch(headless=PLAYWRIGHT_HEADLESS)
                local_context = await local_browser.new_context()
                browser_context = local_context

            import asyncio
            max_attempts = 3
            base_delay = 2.0
            backoff_factor = 2.0
            
            for attempt in range(1, max_attempts + 1):
                try:
                    logger.info(f"[{self.source_name}] Scraping attempt {attempt} of {max_attempts}...")
                    raw_results = await self.scrape_live(browser_context)
                    if raw_results:
                        logger.info(f"[{self.source_name}] Scraping successful on attempt {attempt}. Retrieved {len(raw_results)} items.")
                        break
                    else:
                        logger.warning(f"[{self.source_name}] Attempt {attempt} returned 0 results.")
                except Exception as attempt_err:
                    logger.error(f"[{self.source_name}] Attempt {attempt} failed with error: {attempt_err}")
                
                if attempt < max_attempts:
                    sleep_time = base_delay * (backoff_factor ** (attempt - 1)) + random.uniform(0.1, 1.0)
                    logger.info(f"[{self.source_name}] Retrying in {sleep_time:.2f}s...")
                    await asyncio.sleep(sleep_time)

        except Exception as e:
            logger.error(f"[{self.source_name}] Critical error during scraping lifecycle: {e}", exc_info=True)
        finally:
            if local_context:
                try:
                    await local_context.close()
                except Exception as e:
                    logger.error(f"[{self.source_name}] Error closing local context: {e}")
            if local_browser:
                try:
                    await local_browser.close()
                except Exception as e:
                    logger.error(f"[{self.source_name}] Error closing local browser: {e}")
            if local_playwright:
                try:
                    await local_playwright.stop()
                except Exception as e:
                    logger.error(f"[{self.source_name}] Error stopping local playwright: {e}")

        if not raw_results:
            logger.warning(f"[{self.source_name}] Live scraper returned 0 items. No internships retrieved.")
            self.blocked = True
            return []

        from python_scraper.utils.validators import log_rejection
        from python_scraper.scoring.scoring_service import get_legitimacy_bucket

        processed_results = []
        self.scraped_count = len(raw_results)
        
        for item in raw_results:
            # 1. Clean & Standardize
            cleaned = clean_internship(item)
            
            # 2. Run through the strict 5-stage validation pipeline (without slow sync HEAD checks)
            is_valid, validation_reasons = run_validation_pipeline(cleaned, check_liveness=False)
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
                log_rejection(cleaned.get('company_name'), cleaned.get('role'), 0, validation_reasons, source=cleaned.get('source', 'Unknown'))
                continue
                
            # 3. Apply legitimacy scoring engine
            score = calculate_legitimacy_score(cleaned)
            cleaned['legitimacy_score'] = score
            
            if cleaned.get('confidence') != 'NEEDS_RESCUE':
                cleaned['confidence'] = get_legitimacy_bucket(score)
            
            # 4. Strict SQL insert safety gate check (score must be >= MIN_LEGITIMACY_TO_KEEP (45))
            # Relax check for borderline roles awaiting description-based rescue
            if cleaned.get('confidence') != 'NEEDS_RESCUE' and score < MIN_LEGITIMACY_TO_KEEP:
                logger.warning(f"[{self.source_name}] Internship at '{cleaned.get('company_name')}' rejected: score {score} is below required {MIN_LEGITIMACY_TO_KEEP}")
                self.score_below_threshold += 1
                log_rejection(cleaned.get('company_name'), cleaned.get('role'), score, [f"Legitimacy Score Below Threshold ({score} < {MIN_LEGITIMACY_TO_KEEP})"], source=cleaned.get('source', 'Unknown'))
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
            hundred_scores = sum(1 for item in processed_results if item['legitimacy_score'] == 100)
            percentage_hundred = (hundred_scores / len(processed_results)) * 100
            if percentage_hundred > 80:
                logger.warning(f"[{self.source_name}] QA WARNING: Potential scoring bug detected. {percentage_hundred:.1f}% of internships scored exactly 100.")
            
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


