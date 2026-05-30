import logging
import random
import asyncio
import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from python_scraper.scrapers.base_scraper import BaseScraper
from python_scraper.config import (
    PAGES_TO_SCRAPE,
    USER_AGENTS,
    PLAYWRIGHT_HEADLESS,
    PLAYWRIGHT_SLOW_MO,
    PLAYWRIGHT_VIEWPORT,
    PLAYWRIGHT_TIMEOUT,
)

logger = logging.getLogger("python_scraper.scrapers.indeed")

class IndeedScraper(BaseScraper):
    def __init__(self):
        super().__init__("Indeed India")

    async def scrape_page(self, browser_context, query: str, page_num: int) -> list[dict]:
        """Scrapes a single page of Indeed India asynchronously."""
        start = page_num * 10
        url = f"https://in.indeed.com/jobs?q={query}&l=India&start={start}"
        logger.info(f"[Indeed India] Initiating scrape page {page_num + 1}: {url}")
        
        # Throttling delay to avoid rate limits
        await asyncio.sleep(random.uniform(0.1, 1.5))
        
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

        page_results = []
        try:
            await page.goto(url, timeout=PLAYWRIGHT_TIMEOUT)
            await page.wait_for_load_state("networkidle")
            
            await asyncio.sleep(random.uniform(1.0, 2.5))
            
            # Scroll dynamically
            for _ in range(2):
                scroll_distance = random.randint(300, 600)
                await page.evaluate(f"window.scrollBy(0, {scroll_distance})")
                await asyncio.sleep(random.uniform(0.3, 0.7))
            
            try:
                await page.wait_for_selector('.job_seen_beacon', timeout=5000)
            except Exception:
                logger.warning(f"[Indeed India] Selector '.job_seen_beacon' not found on page {page_num + 1}.")
            
            html = await page.content()
            soup = BeautifulSoup(html, 'html.parser')
            job_cards = soup.select('.job_seen_beacon')
            
            logger.info(f"[Indeed India] Found {len(job_cards)} job cards on page {page_num + 1}.")
            
            if not job_cards:
                logger.warning(f"[Indeed India] No job cards found on page {page_num + 1}. Saving screenshot.")
                try:
                    await page.screenshot(path=f"debug_screenshots/indeed_empty_p{page_num+1}.png")
                except Exception as screenshot_err:
                    logger.debug(f"[Indeed India] Screenshot fail: {screenshot_err}")
                return []
                
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
                    
                    # Parse relative time from text (look for elements containing 'posted' or 'ago')
                    posted_at = datetime.utcnow()
                    card_text = card.text.lower()
                    
                    # Look for date patterns
                    match = re.search(r'(?:active|posted)\s+(\d+)\s+day', card_text)
                    if match:
                        days = int(match.group(1))
                        posted_at = datetime.utcnow() - timedelta(days=days)
                    elif "yesterday" in card_text:
                        posted_at = datetime.utcnow() - timedelta(days=1)
                    
                    if role and company_name and apply_link:
                        page_results.append({
                            "company_name": company_name,
                            "role": role,
                            "stipend": stipend,
                            "location": location,
                            "duration": duration,
                            "skills": skills_str,
                            "apply_link": apply_link,
                            "source": "Indeed India",
                            "posted_at": posted_at.strftime("%Y-%m-%d %H:%M:%S")
                        })
                except Exception as e:
                    logger.error(f"[Indeed India] Error parsing card details: {e}")
                    continue
        except Exception as e:
            logger.error(f"[Indeed India] Error loading page {page_num + 1}: {e}")
        finally:
            await page.close()
            
        return page_results

    async def scrape_live(self, browser_context) -> list[dict]:
        """
        Scrapes live technical internships from Indeed India with sequential smart pagination based on duplicate saturation.
        """
        query = "data+analyst+internship"
        logger.info("[Indeed India] Starting smart sequential page scraping...")
        
        all_results = []
        session_seen_links = set()
        page_num = 0
        
        while page_num < 10:  # safety cap of 10 pages
            page_results = await self.scrape_page(browser_context, query, page_num)
            if not page_results:
                logger.info(f"[Indeed India] Page {page_num + 1} returned no listings. Stopping pagination.")
                break
                
            total_items = len(page_results)
            dup_items = 0
            
            for item in page_results:
                link = item.get('apply_link')
                if link in self.existing_links or link in session_seen_links:
                    dup_items += 1
                else:
                    session_seen_links.add(link)
                    
            all_results.extend(page_results)
            
            # Calculate duplicate saturation
            saturation = dup_items / total_items if total_items > 0 else 0
            logger.info(f"[Indeed India] [Page {page_num + 1}] Saturation: {saturation:.1%} ({dup_items}/{total_items} duplicate items).")
            
            if total_items > 0 and saturation > 0.8:
                logger.info(f"[Indeed India] Duplicate saturation reached > 80% on page {page_num + 1}. Stopping pagination.")
                break
                
            page_num += 1
            
        logger.info(f"[Indeed India] Total extracted raw listings: {len(all_results)}")
        return all_results
