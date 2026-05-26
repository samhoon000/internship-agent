import logging
import random
import time
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from python_scraper.scrapers.base_scraper import BaseScraper
from python_scraper.config import (
    USER_AGENTS,
    PLAYWRIGHT_HEADLESS,
    PLAYWRIGHT_SLOW_MO,
    PLAYWRIGHT_VIEWPORT,
    PLAYWRIGHT_TIMEOUT,
)

logger = logging.getLogger("python_scraper.scrapers.yc_jobs")

class YCJobsScraper(BaseScraper):
    def __init__(self):
        super().__init__("YC Jobs")

    def scrape_live(self) -> list[dict]:
        """
        Attempts to scrape YC Work at a Startup jobs.
        Uses Playwright for dynamic browser rendering, anti-bot handling, and human-like delays.
        """
        results = []
        url = "https://www.workatastartup.com/jobs?demands_remote=any&job_types[]=internship"
        logger.info(f"[YC Jobs] Launching Playwright to scrape: {url}")
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=PLAYWRIGHT_HEADLESS,
                    slow_mo=PLAYWRIGHT_SLOW_MO,
                )
                
                user_agent = random.choice(USER_AGENTS)
                context = browser.new_context(
                    user_agent=user_agent,
                    viewport=PLAYWRIGHT_VIEWPORT,
                    extra_http_headers={
                        "Accept-Language": "en-US,en;q=0.9",
                    }
                )
                
                page = context.new_page()
                page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                
                logger.info(f"[YC Jobs] Navigating to {url}...")
                page.goto(url, timeout=PLAYWRIGHT_TIMEOUT)
                page.wait_for_load_state("networkidle")
                
                time.sleep(random.uniform(2.0, 5.0))
                
                logger.info("[YC Jobs] Simulating human scroll loading...")
                for _ in range(3):
                    scroll_distance = random.randint(300, 700)
                    page.evaluate(f"window.scrollBy(0, {scroll_distance})")
                    time.sleep(random.uniform(1.0, 2.0))
                
                try:
                    page.wait_for_selector('.bg-beige-lighter, p.job-details, .flex.h-full.cursor-pointer.flex-col', timeout=10000)
                except Exception:
                    logger.warning("[YC Jobs] Selector fallbacks not found. Page might have blocked requests or structure changed.")
                
                html = page.content()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Retrieve job cards using multiple fallbacks
                job_cards = (
                    soup.select('div.bg-beige-lighter') or 
                    [p.parent.parent for p in soup.select('p.job-details')] or 
                    soup.select('div.flex.h-full.cursor-pointer.flex-col')
                )
                logger.info(f"[YC Jobs] Found {len(job_cards)} job cards in rendered DOM.")
                
                if not job_cards:
                    logger.warning("[YC Jobs] No job cards found. Saving debug artifacts.")
                    self.save_debug_artifacts(page)
                
                for card in job_cards:
                    try:
                        role_el = card.select_one('a[href^="/jobs/"]')
                        # Extract only digit-terminated job links to avoid category paths
                        href = role_el.get('href', '') if role_el else ""
                        is_job_detail = href.startswith('/jobs/') and href.replace('/jobs/', '').isdigit()
                        if not is_job_detail:
                            continue
                            
                        role = role_el.text.strip() if role_el else ""
                        apply_link = f"https://www.workatastartup.com{href}" if href else ""
                        
                        company_el = card.select_one('.font-bold') or card.select_one('a[href^="/companies/"]') or card.select_one('.company-name')
                        company_name = company_el.text.strip() if company_el else ""
                        # clean suffix like (S15) or similar if needed (e.g. SnapMagic(S15) -> SnapMagic)
                        # The pipeline is robust, but cleaning here is very clean.
                        if company_name and "(" in company_name:
                            company_name = company_name.split("(")[0].strip()
                        
                        # Extract location, stipend, duration from spans in .job-details
                        stipend = ""
                        location = ""
                        duration = ""
                        
                        spans = [span.text.strip() for span in card.select('p.job-details span')]
                        for text in spans:
                            if any(c in text for c in ['$', '€', '₹', 'salary', '/yr', '/mo']):
                                stipend = text
                            elif any(c in text.lower() for c in ['fulltime', 'parttime', 'internship', 'contract', 'months', 'weeks']):
                                duration = text
                            elif ',' in text or 'remote' in text.lower() or text in ['US', 'IN', 'Remote']:
                                location = text
                        
                        # Fallback checks if spans are not structured
                        if not location:
                            loc_el = card.select_one('.job-location') or card.select_one('.location')
                            if loc_el:
                                location = loc_el.text.strip()
                                
                        if not stipend:
                            salary_el = card.select_one('.salary-estimate') or card.select_one('.compensation')
                            if salary_el:
                                stipend = salary_el.text.strip()
                                
                        if not duration:
                            duration_el = card.select_one('.job-duration')
                            if duration_el:
                                duration = duration_el.text.strip()

                        # Skills (infer from title if not directly listed in DOM)
                        skills_found = []
                        tags_el = card.select('.tag, .skill')
                        for tag in tags_el:
                            skills_found.append(tag.text.strip())
                        
                        skills_str = ", ".join(skills_found) if skills_found else ""
                        
                        if role and company_name and apply_link:
                            results.append({
                                "company_name": company_name,
                                "role": role,
                                "stipend": stipend if stipend else "Unspecified",
                                "location": location if location else "Remote",
                                "duration": duration if duration else "Not Specified",
                                "skills": skills_str,
                                "apply_link": apply_link,
                                "source": "YC Jobs"
                            })
                    except Exception as e:
                        logger.error(f"[YC Jobs] Error parsing job listing: {e}")
                        continue
                        
                browser.close()
        except Exception as e:
            logger.error(f"[YC Jobs] Playwright scraping failed: {e}", exc_info=True)
            return []
            
        return results

