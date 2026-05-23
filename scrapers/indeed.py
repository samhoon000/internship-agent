import logging
import random
import time
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from internship_agent.scrapers.base_scraper import BaseScraper
from internship_agent.config import (
    PAGES_TO_SCRAPE,
    USER_AGENTS,
    PLAYWRIGHT_HEADLESS,
    PLAYWRIGHT_SLOW_MO,
    PLAYWRIGHT_VIEWPORT,
    PLAYWRIGHT_TIMEOUT,
)

logger = logging.getLogger("internship_agent.scrapers.indeed")

class IndeedScraper(BaseScraper):
    def __init__(self):
        super().__init__("Indeed India")

    def scrape_live(self) -> list[dict]:
        """
        Scrapes live technical internships from Indeed India.
        Uses Playwright for dynamic browser rendering, anti-bot handling, and human-like delays.
        """
        results = []
        query = "python+internship"
        logger.info(f"[Indeed India] Launching Playwright to scrape.")
        
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
                
                for page_num in range(PAGES_TO_SCRAPE):
                    start = page_num * 10
                    url = f"https://in.indeed.com/jobs?q={query}&l=India&start={start}"
                    logger.info(f"[Indeed India] Navigating to page {page_num + 1}: {url}")
                    
                    try:
                        page.goto(url, timeout=PLAYWRIGHT_TIMEOUT)
                        page.wait_for_load_state("networkidle")
                    except Exception as e:
                        logger.error(f"[Indeed India] Navigation failed for page {page_num + 1}: {e}")
                        continue
                        
                    time.sleep(random.uniform(3.0, 6.0))
                    
                    logger.info(f"[Indeed India] Simulating human scroll on page {page_num + 1}...")
                    for _ in range(2):
                        scroll_distance = random.randint(400, 800)
                        page.evaluate(f"window.scrollBy(0, {scroll_distance})")
                        time.sleep(random.uniform(1.0, 2.0))
                    
                    try:
                        page.wait_for_selector('.job_seen_beacon', timeout=10000)
                    except Exception:
                        logger.warning(f"[Indeed India] Selector '.job_seen_beacon' not found on page {page_num + 1}. IP might be blocked or Cloudflare challenge active.")
                    
                    html = page.content()
                    soup = BeautifulSoup(html, 'html.parser')
                    job_cards = soup.select('.job_seen_beacon')
                    
                    logger.info(f"[Indeed India] Found {len(job_cards)} job cards on page {page_num + 1}.")
                    
                    if not job_cards:
                        break
                        
                    for card in job_cards:
                        try:
                            role_el = card.select_one('h2.jobTitle a') or card.select_one('h2.jobTitle span')
                            role = ""
                            apply_link = ""
                            
                            if role_el:
                                role = role_el.text.strip()
                                if 'href' in role_el.attrs:
                                    apply_link = f"https://in.indeed.com{role_el['href']}"
                                    
                            company_el = card.select_one('[data-testid="company-name"]') or card.select_one('.companyName')
                            company_name = company_el.text.strip() if company_el else ""
                            
                            location_el = card.select_one('[data-testid="text-location"]') or card.select_one('.companyLocation')
                            location = location_el.text.strip() if location_el else "India"
                            
                            stipend = ""
                            salary_el = card.select_one('.salary-snippet-container') or card.select_one('.metadata.salarySnippet')
                            if salary_el:
                                stipend = salary_el.text.strip()
                                
                            skills = []
                            desc_el = card.select_one('.job-snippet')
                            if desc_el:
                                desc_text = desc_el.text.lower()
                                for kw in ["python", "sql", "aws", "react", "javascript", "node", "django", "flask", "ml", "ai"]:
                                    if kw in desc_text:
                                        skills.append(kw.capitalize())
                                        
                            skills_str = ", ".join(skills) if skills else ""
                            duration = ""
                            
                            if role and company_name and apply_link:
                                results.append({
                                    "company_name": company_name,
                                    "role": role,
                                    "stipend": stipend,
                                    "location": location,
                                    "duration": duration,
                                    "skills": skills_str,
                                    "apply_link": apply_link,
                                    "source": "Indeed India"
                                })
                        except Exception as e:
                            logger.error(f"[Indeed India] Error parsing card details: {e}")
                            continue
                            
                browser.close()
        except Exception as e:
            logger.error(f"[Indeed India] Playwright scraping failed: {e}", exc_info=True)
            return []
            
        return results

