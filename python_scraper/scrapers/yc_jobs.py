import logging
import random
import asyncio
import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
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

    async def scrape_live(self, browser_context) -> list[dict]:
        """
        Attempts to scrape YC Work at a Startup jobs.
        Uses Playwright async_api within the shared browser context.
        """
        results = []
        url = "https://www.workatastartup.com/jobs?demands_remote=any&job_types[]=internship"
        logger.info(f"[YC Jobs] Scrape target: {url}")
        
        page = await browser_context.new_page()
        await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        # Route to block heavy resources
        async def block_resources(route):
            if route.request.resource_type in ["image", "media", "font"]:
                await route.abort()
            elif any(track in route.request.url for track in ["analytics", "google-analytics", "doubleclick"]):
                await route.abort()
            else:
                await route.continue_()
                
        await page.route("**/*", block_resources)

        try:
            logger.info(f"[YC Jobs] Navigating to {url}...")
            await page.goto(url, timeout=PLAYWRIGHT_TIMEOUT)
            await page.wait_for_load_state("networkidle")
            
            await asyncio.sleep(random.uniform(1.0, 2.5))
            
            logger.info("[YC Jobs] Simulating scroll loading...")
            for _ in range(3):
                scroll_distance = random.randint(300, 600)
                await page.evaluate(f"window.scrollBy(0, {scroll_distance})")
                await asyncio.sleep(random.uniform(0.5, 1.2))
            
            try:
                await page.wait_for_selector('.bg-beige-lighter, p.job-details, .flex.h-full.cursor-pointer.flex-col', timeout=5000)
            except Exception:
                logger.warning("[YC Jobs] Selector fallbacks not found. Page structure might have changed.")
            
            html = await page.content()
            soup = BeautifulSoup(html, 'html.parser')
            
            job_cards = (
                soup.select('div.bg-beige-lighter') or 
                [p.parent.parent for p in soup.select('p.job-details')] or 
                soup.select('div.flex.h-full.cursor-pointer.flex-col') or
                soup.select('[class*="job-card"]') or
                soup.select('.job-card') or
                soup.select('article') or
                soup.select('div[role="listitem"]')
            )
            logger.info(f"[YC Jobs] Found {len(job_cards)} job cards in DOM.")
            
            if not job_cards:
                logger.warning("[YC Jobs] No job cards found. Saving debug screenshot.")
                try:
                    await page.screenshot(path="debug_screenshots/yc_empty.png")
                except Exception as screenshot_err:
                    logger.debug(f"[YC Jobs] Screenshot fail: {screenshot_err}")
            
            for card in job_cards:
                try:
                    role_el = card.select_one('a[href^="/jobs/"]')
                    href = role_el.get('href', '') if role_el else ""
                    is_job_detail = href.startswith('/jobs/') and href.replace('/jobs/', '').isdigit()
                    if not is_job_detail:
                        continue
                        
                    role = role_el.text.strip() if role_el else ""
                    apply_link = f"https://www.workatastartup.com{href}" if href else ""
                    
                    company_el = card.select_one('.font-bold') or card.select_one('a[href^="/companies/"]') or card.select_one('.company-name')
                    company_name = company_el.text.strip() if company_el else ""
                    if company_name and "(" in company_name:
                        company_name = company_name.split("(")[0].strip()
                    
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

                    skills_found = []
                    tags_el = card.select('.tag, .skill')
                    for tag in tags_el:
                        skills_found.append(tag.text.strip())
                    
                    skills_str = ", ".join(skills_found) if skills_found else ""
                    
                    # Parse relative time from text (e.g. 'posted 2 days ago' or 'active 1 day ago')
                    posted_at = datetime.utcnow()
                    card_text = card.text.lower()
                    
                    match = re.search(r'(?:active|posted)\s+(\d+)\s+day', card_text)
                    if match:
                        days = int(match.group(1))
                        posted_at = datetime.utcnow() - timedelta(days=days)
                    elif "yesterday" in card_text:
                        posted_at = datetime.utcnow() - timedelta(days=1)
                    
                    if role and company_name and apply_link:
                        results.append({
                            "company_name": company_name,
                            "role": role,
                            "stipend": stipend if stipend else "Unspecified",
                            "location": location if location else "Remote",
                            "duration": duration if duration else "Not Specified",
                            "skills": skills_str,
                            "apply_link": apply_link,
                            "source": "YC Jobs",
                            "posted_at": posted_at.strftime("%Y-%m-%d %H:%M:%S")
                        })
                except Exception as e:
                    logger.error(f"[YC Jobs] Error parsing job listing card: {e}")
                    continue
        except Exception as e:
            logger.error(f"[YC Jobs] Playwright scraping failed: {e}", exc_info=True)
        finally:
            await page.close()
            
        return results
