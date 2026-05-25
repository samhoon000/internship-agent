import logging
import random
import time
import re
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

logger = logging.getLogger("internship_agent.scrapers.internshala")

class InternshalaScraper(BaseScraper):
    def __init__(self):
        super().__init__("Internshala")
        self.pages_scraped = 0

    def handle_popup(self, page) -> bool:
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

        # Wait up to 1500ms for modal to appear in the DOM
        try:
            page.wait_for_selector(
                ".modal, [role='dialog'], .modal-dialog, .signup-modal, .popup, #registration-modal", 
                timeout=1500
            )
        except Exception:
            pass

        def is_popup_visible() -> bool:
            for selector in modal_selectors:
                try:
                    if page.locator(selector).is_visible():
                        return True
                except Exception:
                    pass
            try:
                if page.locator("text=Sign up now").is_visible() or page.locator("text=FREE AI Career Guide").is_visible():
                    return True
            except Exception:
                pass
            return False

        if not is_popup_visible():
            logger.info("[Internshala] Popup status: Not visible.")
            return False

        logger.info("[Internshala] Signup popup detected. Initiating closing strategies...")

        def wait_for_modal_hidden(timeout_ms=2000) -> bool:
            # Helper to wait until the modal is hidden
            for selector in modal_selectors:
                try:
                    locator = page.locator(selector)
                    if locator.is_visible():
                        locator.wait_for(state="hidden", timeout=timeout_ms)
                        if not is_popup_visible():
                            return True
                except Exception:
                    pass
            return not is_popup_visible()

        # ----------------------------------------------------
        # STRATEGY 1: Known close selectors / Generic close buttons / aria-label close
        # ----------------------------------------------------
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
                count = locators.count()
                for i in range(count):
                    loc = locators.nth(i)
                    if loc.is_visible():
                        logger.info(f"[Internshala] Strategy 1 (Selector): Found visible close element '{sel}'. Clicking it.")
                        loc.click(timeout=2000)
                        if wait_for_modal_hidden(1500):
                            logger.info("[Internshala] Popup successfully closed using Strategy 1 (Selector).")
                            return True
            except Exception as e:
                logger.debug(f"[Internshala] Strategy 1 selector '{sel}' click failed: {e}")

        # Strategy 1 (Position): Locate by position near modal top-right
        for modal_sel in modal_selectors:
            try:
                modal_loc = page.locator(modal_sel)
                if modal_loc.is_visible():
                    box = modal_loc.bounding_box()
                    if box:
                        click_x = box['x'] + box['width'] - 15
                        click_y = box['y'] + 15
                        logger.info(f"[Internshala] Strategy 1 (Position): Clicking near top-right at ({click_x}, {click_y})")
                        page.mouse.click(click_x, click_y)
                        if wait_for_modal_hidden(1500):
                            logger.info("[Internshala] Popup successfully closed using Strategy 1 (Position).")
                            return True
            except Exception as e:
                logger.debug(f"[Internshala] Strategy 1 position click for selector '{modal_sel}' failed: {e}")

        # ----------------------------------------------------
        # STRATEGY 2: ESC key fallback
        # ----------------------------------------------------
        try:
            logger.info("[Internshala] Strategy 2: Pressing Escape key.")
            page.keyboard.press("Escape")
            if wait_for_modal_hidden(1500):
                logger.info("[Internshala] Popup successfully closed using Strategy 2 (Escape key).")
                return True
        except Exception as e:
            logger.debug(f"[Internshala] Strategy 2 (Escape key) failed: {e}")

        # ----------------------------------------------------
        # STRATEGY 3: Click outside modal dismissal
        # ----------------------------------------------------
        try:
            logger.info("[Internshala] Strategy 3: Clicking outside modal at (50, 50).")
            page.mouse.click(50, 50)
            if wait_for_modal_hidden(1500):
                logger.info("[Internshala] Popup successfully closed using Strategy 3 (Click outside).")
                return True
        except Exception as e:
            logger.debug(f"[Internshala] Strategy 3 (Click outside) failed: {e}")

        # ----------------------------------------------------
        # STRATEGY 4: DOM removal (failsafe)
        # ----------------------------------------------------
        try:
            logger.info("[Internshala] Strategy 4 (Failsafe): Removing modal elements from DOM.")
            page.evaluate("""() => {
                document.querySelectorAll(
                    '.modal, .overlay, .backdrop, [role="dialog"], .modal-backdrop, #registration-modal, .signup-modal'
                ).forEach(el => el.remove());
                document.body.style.overflow = 'auto';
            }""")
            # Give short timeout to check removal
            page.wait_for_timeout(500)
            if not is_popup_visible():
                logger.info("[Internshala] Popup successfully removed using Strategy 4 (JavaScript).")
                return True
        except Exception as e:
            logger.warning(f"[Internshala] Strategy 4 (JavaScript) execution failed: {e}")

        if is_popup_visible():
            logger.warning("[Internshala] Popup STILL visible after applying all strategies.")
            return False
        return True

    def safe_navigate(self, page, url, max_retries=3) -> bool:
        """
        Navigates to a URL with exponential backoff retry and navigation failure recovery.
        """
        backoff = 2.0
        for attempt in range(1, max_retries + 1):
            try:
                start_time = time.time()
                response = page.goto(url, wait_until="domcontentloaded", timeout=PLAYWRIGHT_TIMEOUT)
                elapsed = time.time() - start_time
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
                logger.info(f"[Internshala] Retrying in {sleep_time:.2f}s (exponential backoff)...")
                time.sleep(sleep_time)
        return False

    def extract_internships(self, page, cat, page_num) -> tuple[list[dict], bool]:
        """
        Extracts internships from the current page content using hardened BeautifulSoup selectors.
        Returns a list of extracted raw internship dicts and a boolean indicating if pagination should stop.
        """
        html = page.content()
        soup = BeautifulSoup(html, 'html.parser')
        
        # Hardened listings selector with fallback
        listings = soup.select('.individual_internship') or soup.select('[class*="individual_internship"]')
        if not listings:
            # If no listings are found at all, stop pagination in this category
            logger.info(f"[Internshala] [Category: {cat} | Page {page_num}] No listings found in DOM. Reached end of pagination.")
            return [], True

        results = []
        page_raw_count = 0

        for card in listings:
            try:
                # Role Title with fallback semantic selectors
                role_el = (
                    card.select_one('.job-title-href') or 
                    card.select_one('.profile a') or 
                    card.select_one('a[href*="/internship/detail/"]') or
                    card.select_one('.heading_4_5 a')
                )
                if not role_el:
                    continue

                role = role_el.text.strip()

                # Category-level Machine Learning filter
                if cat == "machine-learning-internship":
                    role_lower = role.lower()
                    if not any(x in role_lower for x in ["data", "analytics", "analyst"]):
                        continue

                # Apply link
                link_suffix = role_el.get('href') or card.get('data-href') or ""
                apply_link = f"https://internshala.com{link_suffix}" if link_suffix else ""

                # Company Name with fallback semantic selectors
                company_el = (
                    card.select_one('.company-name') or 
                    card.select_one('.company_name a') or
                    card.select_one('.heading_6 a') or
                    card.select_one('.company_and_premium a')
                )
                company_name = company_el.text.strip() if company_el else ""

                # Location with fallback selectors
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

                if role and company_name and apply_link:
                    results.append({
                        "company_name": company_name,
                        "role": role,
                        "stipend": stipend,
                        "location": location,
                        "duration": duration,
                        "skills": skills_str,
                        "apply_link": apply_link,
                        "source": "Internshala"
                    })
                    page_raw_count += 1
            except Exception as e:
                logger.error(f"[Internshala] [Category: {cat} | Page {page_num}] Error parsing card details: {e}")
                continue

        logger.info(f"[Internshala] [Category: {cat} | Page {page_num}] Successfully extracted {page_raw_count} raw items.")
        return results, False

    def scrape_category(self, page, cat, max_pages) -> list[dict]:
        """
        Scrapes a single category from Internshala page-by-page.
        Implements smart pagination stopping and progress logging.
        """
        category_results = []
        logger.info(f"[Internshala] Starting scraping for Category: '{cat}'...")
        start_time = time.time()

        for page_num in range(1, max_pages + 1):
            url = f"https://internshala.com/internships/{cat}/page-{page_num}/"
            logger.info(f"[Internshala] [Category: {cat} | Page {page_num}] Target: {url}")

            # 1. Anti-bot randomized delay before navigation
            delay = random.uniform(2.0, 4.0)
            time.sleep(delay)

            # 2. Safe navigation with retries
            success = self.safe_navigate(page, url)
            if not success:
                logger.error(f"[Internshala] [Category: {cat} | Page {page_num}] Failed to load page after max retries. Skipping.")
                continue

            # 3. Popup handling
            popup_handled = self.handle_popup(page)
            logger.info(f"[Internshala] [Category: {cat} | Page {page_num}] Popup status: {'Closed' if popup_handled else 'None'}")

            # 4. Wait for networkidle
            try:
                page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                pass

            # 5. Anti-bot human-like scrolling
            for _ in range(3):
                scroll_distance = random.randint(200, 400)
                page.evaluate(f"window.scrollBy(0, {scroll_distance})")
                time.sleep(random.uniform(0.3, 0.7))

            # 6. Check if popup still blocks scraping
            popup_still_visible = False
            try:
                if page.locator("text=Sign up now").is_visible() or page.locator("text=FREE AI Career Guide").is_visible():
                    popup_still_visible = True
            except Exception:
                pass

            if popup_still_visible:
                logger.warning(f"[Internshala] [Category: {cat} | Page {page_num}] Popup still blocks scraping! Capturing debug assets.")
                import os
                os.makedirs("debug_screenshots", exist_ok=True)
                os.makedirs("debug_html", exist_ok=True)
                try:
                    page.screenshot(path="debug_screenshots/internshala_popup.png")
                except Exception as e:
                    logger.error(f"[Internshala] Failed to save screenshot: {e}")
                try:
                    with open("debug_html/internshala_popup.html", "w", encoding="utf-8") as f:
                        f.write(page.content())
                except Exception as e:
                    logger.error(f"[Internshala] Failed to save HTML: {e}")

            # 7. Extract internships
            page_items, stop_pagination = self.extract_internships(page, cat, page_num)
            category_results.extend(page_items)
            self.pages_scraped += 1

            # Smart pagination stop
            if stop_pagination:
                break

        elapsed = time.time() - start_time
        logger.info(f"[Internshala] [Category: {cat}] Completion summary: Scraped {page_num} pages, yielded {len(category_results)} internships in {elapsed:.2f}s.")
        return category_results

    def scrape_live(self) -> list[dict]:
        """
        Scrapes live technical internships from Internshala by iterating over categories.
        Uses Playwright chromium browser with robust recovery and performance optimizations.
        """
        results = []
        self.pages_scraped = 0

        categories = [
            "data-analytics-internship",
            "data-science-internship",
            "machine-learning-internship",
        ]

        logger.info(f"[Internshala] Launching Playwright to scrape.")

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

                # Open a single page tab for the session
                page = context.new_page()
                page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

                # Throttling & Performance: Route to block heavy assets (images, media, fonts)
                def block_resources(route):
                    if route.request.resource_type in ["image", "media", "font"]:
                        route.abort()
                    else:
                        route.continue_()
                
                page.route("**/*", block_resources)

                try:
                    for cat in categories:
                        # Graceful recovery: Check if browser is disconnected or page is closed
                        if not browser.is_connected():
                            logger.warning("[Internshala] Browser session crashed/disconnected. Re-launching...")
                            browser = p.chromium.launch(
                                headless=PLAYWRIGHT_HEADLESS,
                                slow_mo=PLAYWRIGHT_SLOW_MO,
                            )
                            context = browser.new_context(
                                user_agent=random.choice(USER_AGENTS),
                                viewport=PLAYWRIGHT_VIEWPORT,
                                extra_http_headers={"Accept-Language": "en-US,en;q=0.9"}
                            )
                            page = context.new_page()
                            page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                            page.route("**/*", block_resources)
                        elif page.is_closed():
                            logger.warning("[Internshala] Scraper page tab was closed/crashed. Re-creating page...")
                            page = context.new_page()
                            page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                            page.route("**/*", block_resources)

                        cat_results = self.scrape_category(page, cat, PAGES_TO_SCRAPE)
                        results.extend(cat_results)

                finally:
                    if not page.is_closed():
                        page.close()

                browser.close()
        except Exception as e:
            logger.error(f"[Internshala] Playwright execution failed: {e}", exc_info=True)
            return []

        return results
