import logging
import random
import time
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from internship_agent.scrapers.base_scraper import BaseScraper
from internship_agent.config import (
    USER_AGENTS,
    PLAYWRIGHT_HEADLESS,
    PLAYWRIGHT_SLOW_MO,
    PLAYWRIGHT_VIEWPORT,
    PLAYWRIGHT_TIMEOUT,
)

logger = logging.getLogger("internship_agent.scrapers.yc_jobs")

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
                    page.wait_for_selector('.job-card, .job-listing', timeout=10000)
                except Exception:
                    logger.warning("[YC Jobs] Selector '.job-card' or '.job-listing' not found. Page might have blocked requests or structure changed.")
                
                html = page.content()
                soup = BeautifulSoup(html, 'html.parser')
                
                job_cards = soup.select('.job-card') or soup.select('.job-listing')
                logger.info(f"[YC Jobs] Found {len(job_cards)} job cards in rendered DOM.")
                
                for card in job_cards:
                    try:
                        role_el = card.select_one('.job-title') or card.select_one('h4')
                        role = role_el.text.strip() if role_el else ""
                        
                        company_el = card.select_one('.company-name') or card.select_one('.company-title')
                        company_name = company_el.text.strip() if company_el else ""
                        
                        link_el = card.select_one('a')
                        apply_link = link_el['href'] if link_el and 'href' in link_el.attrs else ""
                        if apply_link and not apply_link.startswith('http'):
                            apply_link = f"https://www.workatastartup.com{apply_link}"
                            
                        stipend = ""
                        salary_el = card.select_one('.salary-estimate') or card.select_one('.compensation')
                        if salary_el:
                            stipend = salary_el.text.strip()
                            
                        location = ""
                        loc_el = card.select_one('.job-location') or card.select_one('.location')
                        if loc_el:
                            location = loc_el.text.strip()
                        
                        skills_found = []
                        tags_el = card.select('.tag, .skill')
                        for tag in tags_el:
                            skills_found.append(tag.text.strip())
                        
                        skills_str = ", ".join(skills_found) if skills_found else ""
                        
                        duration = ""
                        duration_el = card.select_one('.job-duration')
                        if duration_el:
                            duration = duration_el.text.strip()
                        
                        if role and company_name and apply_link:
                            results.append({
                                "company_name": company_name,
                                "role": role,
                                "stipend": stipend,
                                "location": location,
                                "duration": duration,
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

