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

logger = logging.getLogger("python_scraper.scrapers.wellfound")

class WellfoundScraper(BaseScraper):
    def __init__(self):
        super().__init__("Wellfound")

    async def scrape_live(self, browser_context) -> list[dict]:
        """
        Attempts to scrape Wellfound (formerly AngelList) technical internships.
        Uses Playwright async_api within the shared browser context.
        """
        results = []
        url = "https://wellfound.com/role/l/data-analyst-internship"
        logger.info(f"[Wellfound] Scrape target: {url}")
        
        page = await browser_context.new_page()
        await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        # Route to block heavy resources (allow script, xhr, fetch)
        async def block_resources(route):
            if route.request.resource_type in ["image", "media", "font"]:
                await route.abort()
            else:
                await route.continue_()
                
        await page.route("**/*", block_resources)

        try:
            logger.info(f"[Wellfound] Navigating to {url}...")
            await page.goto(url, timeout=PLAYWRIGHT_TIMEOUT)
            await page.wait_for_load_state("networkidle")
            
            await asyncio.sleep(random.uniform(1.0, 2.5))
            
            logger.info("[Wellfound] Simulating scroll loading...")
            for _ in range(3):
                scroll_distance = random.randint(300, 600)
                await page.evaluate(f"window.scrollBy(0, {scroll_distance})")
                await asyncio.sleep(random.uniform(0.5, 1.2))
            
            # Use generous wait strategy for resilient selectors
            try:
                await page.wait_for_selector(
                    '[data-test="StartupResult"], [data-test="JobSearchResultCard"], [data-testid*="job"], [data-test*="Job"], .styles_jobCard__, .styles_result__, [class*="styles_result__"], [class*="styles_jobCard__"]',
                    timeout=10000
                )
            except Exception:
                logger.warning("[Wellfound] Selector fallbacks not found. Page might have blocked requests or structure changed.")
            
            html = await page.content()
            try:
                import os
                os.makedirs("debug_html", exist_ok=True)
                with open("debug_html/debug_wellfound.html", "w", encoding="utf-8") as f:
                    f.write(html)
                logger.info("[Wellfound] Saved debug page HTML to debug_html/debug_wellfound.html")
            except Exception as e:
                logger.debug(f"[Wellfound] Failed to write debug HTML: {e}")

            soup = BeautifulSoup(html, 'html.parser')
            
            job_cards = (
                soup.select('[data-test="StartupResult"]') or 
                soup.select('[data-test="JobSearchResultCard"]') or 
                soup.select('[data-testid*="job"]') or 
                soup.select('[data-test*="Job"]') or 
                soup.select('.styles_jobCard__') or 
                soup.select('.styles_result__') or
                soup.select('[class*="styles_result__"]') or 
                soup.select('[class*="styles_jobCard__"]') or
                soup.select('[class*="styles_startupCard__"]')
            )
            logger.info(f"[Wellfound] Found {len(job_cards)} job cards in DOM.")
            
            if not job_cards:
                logger.warning("[Wellfound] No job cards found. Saving debug screenshot.")
                try:
                    await page.screenshot(path="debug_screenshots/wellfound_empty.png")
                except Exception as screenshot_err:
                    logger.debug(f"[Wellfound] Screenshot fail: {screenshot_err}")
            
            for card in job_cards:
                try:
                    role_el = (
                        card.select_one('[data-test="job-name"]') or 
                        card.select_one('[data-test="job-title"]') or 
                        card.select_one('[data-testid*="job"]') or 
                        card.select_one('[data-test*="job"]') or 
                        card.select_one('.styles_title__') or 
                        card.select_one('a[href*="/jobs/"]') or
                        card.select_one('[class*="job-title"]') or
                        card.select_one('[class*="job-name"]')
                    )
                    role = role_el.text.strip() if role_el else ""
                    
                    company_el = (
                        card.select_one('[data-test="startup-name"]') or 
                        card.select_one('[data-test="company-name"]') or 
                        card.select_one('[data-testid*="company"]') or 
                        card.select_one('[data-test*="company"]') or 
                        card.select_one('.styles_name__') or
                        card.select_one('[class*="company-name"]') or
                        card.select_one('[class*="startup-name"]')
                    )
                    company_name = company_el.text.strip() if company_el else ""
                    
                    link_el = card.select_one('a[href*="/jobs/"]') or card.select_one('a')
                    apply_link = link_el['href'] if link_el and 'href' in link_el.attrs else ""
                    if apply_link and not apply_link.startswith('http'):
                        apply_link = f"https://wellfound.com{apply_link}"
                        
                    stipend = ""
                    salary_el = card.select_one('[data-test="compensation"]') or card.select_one('.styles_salary__')
                    if salary_el:
                        stipend = salary_el.text.strip()
                        
                    location = ""
                    loc_el = card.select_one('[data-test="location"]') or card.select_one('.styles_location__')
                    if loc_el:
                        location = loc_el.text.strip()
                    
                    skills_found = []
                    tags_el = (
                        card.select('[class*="styles_tag__"]') or 
                        card.select('[data-test="job-tag"]') or
                        card.select('.styles_tag__')
                    )
                    for tag in tags_el:
                        skills_found.append(tag.text.strip())
                    
                    skills_str = ", ".join(skills_found) if skills_found else ""
                    
                    duration = ""
                    duration_el = card.select_one('.styles_duration__') or card.select_one('[data-test="duration"]')
                    if duration_el:
                        duration = duration_el.text.strip()
                    
                    # Parse relative time from text (look for text like 'active 2 days ago' or 'posted 1 day ago')
                    posted_at = datetime.utcnow()
                    card_text = card.text.lower()
                    
                    # Look for date patterns in the text of the card
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
                            "source": "Wellfound",
                            "posted_at": posted_at.strftime("%Y-%m-%d %H:%M:%S")
                        })
                except Exception as e:
                    logger.error(f"[Wellfound] Error parsing job listing card: {e}")
                    continue
        except Exception as e:
            logger.error(f"[Wellfound] Playwright scraping failed: {e}", exc_info=True)
        finally:
            await page.close()
            
        return results
