import logging
import random
import asyncio
import re
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

logger = logging.getLogger("python_scraper.scrapers.internshala")

class InternshalaScraper(BaseScraper):
    def __init__(self):
        super().__init__("Internshala")
        self.pages_scraped = 0

    async def handle_popup(self, page) -> bool:
        """
        Detects and attempts to close the signup popup using multiple cascading strategies.
        Returns True if a popup was detected and handled, False otherwise.
        """
        logger.info("[Internshala] Checking for signup popup...")

        modal_selectors = [
            ".modal", 
            "[role='dialog']", 
            ".modal-dialog", 
            ".signup-modal", 
            ".popup", 
            ".modal-backdrop",
            "#registration-modal"
        ]

        # Wait up to 1000ms for modal to appear in the DOM
        try:
            await page.wait_for_selector(
                ".modal, [role='dialog'], .modal-dialog, .signup-modal, .popup, #registration-modal", 
                timeout=1000
            )
        except Exception:
            pass

        async def is_popup_visible() -> bool:
            for selector in modal_selectors:
                try:
                    if await page.locator(selector).is_visible():
                        return True
                except Exception:
                    pass
            try:
                if await page.locator("text=Sign up now").is_visible() or await page.locator("text=FREE AI Career Guide").is_visible():
                    return True
            except Exception:
                pass
            return False

        if not await is_popup_visible():
            logger.info("[Internshala] Popup status: Not visible.")
            return False

        logger.info("[Internshala] Signup popup detected. Initiating closing strategies...")

        async def wait_for_modal_hidden(timeout_ms=1500) -> bool:
            for selector in modal_selectors:
                try:
                    locator = page.locator(selector)
                    if await locator.is_visible():
                        await locator.wait_for(state="hidden", timeout=timeout_ms)
                        if not await is_popup_visible():
                            return True
                except Exception:
                    pass
            return not await is_popup_visible()

        # STRATEGY 1: Known close selectors
        close_selectors = [
            "button[aria-label='Close']",
            "button.close",
            ".modal-close",
            "[class*='close']",
            "svg",
            "button:has(svg)",
            ".close-button",
            "#close_popup"
        ]
        
        for sel in close_selectors:
            try:
                locators = page.locator(sel)
                count = await locators.count()
                for i in range(count):
                    loc = locators.nth(i)
                    if await loc.is_visible():
                        logger.info(f"[Internshala] Strategy 1 (Selector): Found visible close element '{sel}'. Clicking it.")
                        await loc.click(timeout=1500)
                        if await wait_for_modal_hidden(1000):
                            logger.info("[Internshala] Popup successfully closed using Strategy 1 (Selector).")
                            return True
            except Exception as e:
                logger.debug(f"[Internshala] Strategy 1 selector '{sel}' click failed: {e}")

        # STRATEGY 2: ESC key fallback
        try:
            logger.info("[Internshala] Strategy 2: Pressing Escape key.")
            await page.keyboard.press("Escape")
            if await wait_for_modal_hidden(1000):
                logger.info("[Internshala] Popup successfully closed using Strategy 2 (Escape key).")
                return True
        except Exception as e:
            logger.debug(f"[Internshala] Strategy 2 (Escape key) failed: {e}")

        # STRATEGY 3: Click outside modal dismissal
        try:
            logger.info("[Internshala] Strategy 3: Clicking outside modal at (50, 50).")
            await page.mouse.click(50, 50)
            if await wait_for_modal_hidden(1000):
                logger.info("[Internshala] Popup successfully closed using Strategy 3 (Click outside).")
                return True
        except Exception as e:
            logger.debug(f"[Internshala] Strategy 3 (Click outside) failed: {e}")

        # STRATEGY 4: DOM removal (failsafe)
        try:
            logger.info("[Internshala] Strategy 4 (Failsafe): Removing modal elements from DOM.")
            await page.evaluate("""() => {
                document.querySelectorAll(
                    '.modal, .overlay, .backdrop, [role="dialog"], .modal-backdrop, #registration-modal, .signup-modal'
                ).forEach(el => el.remove());
                document.body.style.overflow = 'auto';
            }""")
            await asyncio.sleep(0.3)
            if not await is_popup_visible():
                logger.info("[Internshala] Popup successfully removed using Strategy 4 (JavaScript).")
                return True
        except Exception as e:
            logger.warning(f"[Internshala] Strategy 4 (JavaScript) execution failed: {e}")

        if await is_popup_visible():
            logger.warning("[Internshala] Popup STILL visible after applying all strategies.")
            return False
        return True

    async def safe_navigate(self, page, url, max_retries=3) -> bool:
        """
        Navigates to a URL with exponential backoff retry and navigation failure recovery.
        """
        backoff = 2.0
        for attempt in range(1, max_retries + 1):
            try:
                start_time = asyncio.get_event_loop().time()
                response = await page.goto(url, wait_until="domcontentloaded", timeout=PLAYWRIGHT_TIMEOUT)
                elapsed = asyncio.get_event_loop().time() - start_time
                if response and response.status == 200:
                    logger.info(f"[Internshala] Navigation successful in {elapsed:.2f}s (Attempt {attempt}/{max_retries}).")
                    return True
                else:
                    status = response.status if response else 'None'
                    logger.warning(f"[Internshala] Navigation status code {status} for {url} (Attempt {attempt}/{max_retries}).")
            except Exception as e:
                logger.warning(f"[Internshala] Navigation failed on attempt {attempt}/{max_retries}: {e}")
            
            if attempt < max_retries:
                sleep_time = backoff ** attempt + random.uniform(0.5, 1.5)
                logger.info(f"[Internshala] Retrying in {sleep_time:.2f}s...")
                await asyncio.sleep(sleep_time)
        return False

    async def extract_internships(self, page, cat, page_num) -> tuple[list[dict], bool]:
        """
        Extracts internships from the current page content using BeautifulSoup.
        Returns a list of extracted raw internship dicts and a boolean indicating if pagination should stop.
        """
        html = await page.content()
        soup = BeautifulSoup(html, 'html.parser')
        
        listings = soup.select('.individual_internship') or soup.select('[class*="individual_internship"]')
        if not listings:
            logger.info(f"[Internshala] [Category: {cat} | Page {page_num}] No listings found in DOM. Reached end of pagination.")
            return [], True

        results = []
        page_raw_count = 0

        for card in listings:
            try:
                # Role Title
                role_el = (
                    card.select_one('.job-title-href') or 
                    card.select_one('.profile a') or 
                    card.select_one('a[href*="/internship/detail/"]') or
                    card.select_one('.heading_4_5 a')
                )
                if not role_el:
                    continue

                role = role_el.text.strip()

                if cat == "machine-learning-internship":
                    role_lower = role.lower()
                    if not any(x in role_lower for x in ["data", "analytics", "analyst"]):
                        continue

                # Apply link
                link_suffix = role_el.get('href') or card.get('data-href') or ""
                apply_link = f"https://internshala.com{link_suffix}" if link_suffix else ""

                # Company Name
                company_el = (
                    card.select_one('.company-name') or 
                    card.select_one('.company_name a') or
                    card.select_one('.heading_6 a') or
                    card.select_one('.company_and_premium a')
                )
                company_name = company_el.text.strip() if company_el else ""

                # Location
                location_el = (
                    card.select_one('.locations span a') or 
                    card.select_one('.location_link') or 
                    card.select_one('.locations') or
                    card.select_one('#location_names')
                )
                location = location_el.text.strip() if location_el else "Remote"

                # Stipend
                stipend_el = card.select_one('.stipend') or card.select_one('.stipend_container')
                stipend = stipend_el.text.strip() if stipend_el else "Unspecified"

                # Duration
                duration = "Not Specified"
                duration_icon = card.select_one('.ic-16-calendar') or card.select_one('.duration')
                if duration_icon and duration_icon.parent:
                    duration = duration_icon.parent.text.strip()

                # Skills
                skills = [skill.text.strip() for skill in card.select('.job_skill') or card.select('[class*="job_skill"]')]
                skills_str = ", ".join(skills)

                # Relative Posted Time Parsing
                # Look for posted date container
                posted_text = "Just now"
                posted_el = (
                    card.select_one('.posted_by_date') or 
                    card.select_one('.status-inactive') or 
                    card.select_one('.status-success') or 
                    card.select_one('.status-container') or
                    card.select_one('.posted-date')
                )
                if posted_el:
                    posted_text = posted_el.text.strip()
                
                # Parse relative date
                from datetime import datetime, timedelta
                posted_at = datetime.utcnow()
                posted_lower = posted_text.lower()
                
                if "just now" in posted_lower or "few hours" in posted_lower or "today" in posted_lower:
                    pass
                elif "yesterday" in posted_lower:
                    posted_at = datetime.utcnow() - timedelta(days=1)
                else:
                    match = re.search(r'(\d+)\s+day', posted_lower)
                    if match:
                        days = int(match.group(1))
                        posted_at = datetime.utcnow() - timedelta(days=days)
                    elif "week" in posted_lower:
                        match_w = re.search(r'(\d+)\s+week', posted_lower)
                        weeks = int(match_w.group(1)) if match_w else 1
                        posted_at = datetime.utcnow() - timedelta(days=weeks * 7)
                    elif "month" in posted_lower:
                        posted_at = datetime.utcnow() - timedelta(days=30)
                
                if role and company_name and apply_link:
                    results.append({
                        "company_name": company_name,
                        "role": role,
                        "stipend": stipend,
                        "location": location,
                        "duration": duration,
                        "skills": skills_str,
                        "apply_link": apply_link,
                        "source": "Internshala",
                        "posted_at": posted_at.strftime("%Y-%m-%d %H:%M:%S")
                    })
                    page_raw_count += 1
            except Exception as e:
                logger.error(f"[Internshala] [Category: {cat} | Page {page_num}] Error parsing card details: {e}")
                continue

        logger.info(f"[Internshala] [Category: {cat} | Page {page_num}] Successfully extracted {page_raw_count} raw items.")
        return results, False

    async def scrape_page(self, browser_context, cat: str, page_num: int) -> list[dict]:
        """Scrapes a single page of Internshala asynchronously."""
        url = f"https://internshala.com/internships/{cat}/page-{page_num}/"
        logger.info(f"[Internshala] [Category: {cat} | Page {page_num}] Initiating scrape page: {url}")
        
        # Throttling delay to prevent spamming
        await asyncio.sleep(random.uniform(0.1, 1.2))
        
        page = await browser_context.new_page()
        await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        # Routing performance optimization (abort unnecessary assets)
        async def block_resources(route):
            if route.request.resource_type in ["image", "media", "font"]:
                await route.abort()
            elif any(track in route.request.url for track in ["analytics", "google-analytics", "doubleclick", "facebook"]):
                await route.abort()
            else:
                await route.continue_()
        
        await page.route("**/*", block_resources)

        try:
            success = await self.safe_navigate(page, url)
            if not success:
                logger.error(f"[Internshala] [Category: {cat} | Page {page_num}] Failed to load page: {url}")
                return []

            await self.handle_popup(page)
            
            # Dynamic scroll
            for _ in range(2):
                scroll_distance = random.randint(200, 400)
                await page.evaluate(f"window.scrollBy(0, {scroll_distance})")
                await asyncio.sleep(random.uniform(0.2, 0.4))

            # Extract internships
            page_items, _ = await self.extract_internships(page, cat, page_num)
            return page_items
        except Exception as e:
            logger.error(f"[Internshala] [Category: {cat} | Page {page_num}] Error during async page scraping: {e}")
            return []
        finally:
            await page.close()

    async def scrape_live(self, browser_context) -> list[dict]:
        """
        Scrapes live technical internships from Internshala by iterating over categories in parallel.
        """
        categories = [
            "data-analytics-internship",
            "data-science-internship",
            "machine-learning-internship",
        ]

        logger.info("[Internshala] Starting parallel scraping for categories...")
        tasks = []
        
        # Add tasks for categories and pages to scrape concurrently
        for cat in categories:
            for page_num in range(1, PAGES_TO_SCRAPE + 1):
                tasks.append(self.scrape_page(browser_context, cat, page_num))

        results_batches = await asyncio.gather(*tasks)
        
        # Flatten results list
        all_results = []
        for batch in results_batches:
            all_results.extend(batch)
            
        self.pages_scraped = PAGES_TO_SCRAPE * len(categories)
        logger.info(f"[Internshala] Total extracted raw listings: {len(all_results)}")
        return all_results
