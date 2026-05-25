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

logger = logging.getLogger("internship_agent.scrapers.internshala")

class InternshalaScraper(BaseScraper):
    def __init__(self):
        super().__init__("Internshala")
        self.pages_scraped = 0

    def close_intershala_popup(self, page):
        """
        Detects and attempts to close the signup popup using multiple strategies.
        """
        logger.info("[Internshala] Checking for signup popup...")
        
        # Give a small delay so popup has time to load if any transition occurs
        time.sleep(1.0)

        # Define a list of modal indicators to check visibility
        # If any of these are visible, we try to close the popup.
        modal_selectors = [
            ".modal", 
            "[role='dialog']", 
            ".modal-dialog", 
            ".signup-modal", 
            ".popup", 
            ".modal-backdrop",
            "#registration-modal"
        ]

        def is_popup_visible() -> bool:
            for selector in modal_selectors:
                try:
                    if page.locator(selector).is_visible():
                        return True
                except Exception:
                    pass
            # Also check text indicators
            try:
                if page.locator("text=Sign up now").is_visible() or page.locator("text=FREE AI Career Guide").is_visible():
                    return True
            except Exception:
                pass
            return False

        if not is_popup_visible():
            logger.info("[Internshala] No signup popup detected.")
            return

        logger.info("[Internshala] Signup popup detected. Attempting to close it...")

        # ----------------------------------------------------
        # STRATEGY 1 (PRIMARY) - Click top-right X button
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
        
        # Try selectors first
        for sel in close_selectors:
            try:
                locators = page.locator(sel)
                count = locators.count()
                for i in range(count):
                    loc = locators.nth(i)
                    if loc.is_visible():
                        logger.info(f"[Internshala] Strategy 1 (Selector): Found visible close element with selector '{sel}'. Clicking it.")
                        loc.click(timeout=3000)
                        time.sleep(1.5)
                        if not is_popup_visible():
                            logger.info("[Internshala] Signup popup successfully closed using Strategy 1 (Selector).")
                            return
            except Exception as e:
                logger.debug(f"[Internshala] Strategy 1 selector '{sel}' failed: {e}")

        # Or locate by position near modal top-right
        for modal_sel in modal_selectors:
            try:
                modal_loc = page.locator(modal_sel)
                if modal_loc.is_visible():
                    box = modal_loc.bounding_box()
                    if box:
                        # Click near the top-right corner of the modal
                        click_x = box['x'] + box['width'] - 15
                        click_y = box['y'] + 15
                        logger.info(f"[Internshala] Strategy 1 (Position): Bounding box found. Clicking near top-right at ({click_x}, {click_y})")
                        page.mouse.click(click_x, click_y)
                        time.sleep(1.5)
                        if not is_popup_visible():
                            logger.info("[Internshala] Signup popup successfully closed using Strategy 1 (Position).")
                            return
            except Exception as e:
                logger.debug(f"[Internshala] Strategy 1 position click for selector '{modal_sel}' failed: {e}")

        # ----------------------------------------------------
        # STRATEGY 2 - ESC key
        # ----------------------------------------------------
        try:
            logger.info("[Internshala] Strategy 2: Pressing Escape key.")
            page.keyboard.press("Escape")
            time.sleep(1.5)
            if not is_popup_visible():
                logger.info("[Internshala] Signup popup successfully closed using Strategy 2 (Escape key).")
                return
        except Exception as e:
            logger.debug(f"[Internshala] Strategy 2 (Escape key) failed: {e}")

        # ----------------------------------------------------
        # STRATEGY 3 - Click outside modal
        # ----------------------------------------------------
        try:
            logger.info("[Internshala] Strategy 3: Clicking outside modal at (50, 50).")
            page.mouse.click(50, 50)
            time.sleep(1.5)
            if not is_popup_visible():
                logger.info("[Internshala] Signup popup successfully closed using Strategy 3 (Click outside).")
                return
        except Exception as e:
            logger.debug(f"[Internshala] Strategy 3 (Click outside) failed: {e}")

        # ----------------------------------------------------
        # STRATEGY 4 (FAILSAFE) - Remove modal using JavaScript
        # ----------------------------------------------------
        try:
            logger.info("[Internshala] Strategy 4 (Failsafe): Removing modal elements via page.evaluate().")
            page.evaluate("""() => {
                document.querySelectorAll(
                    '.modal, .overlay, .backdrop, [role="dialog"], .modal-backdrop, #registration-modal, .signup-modal'
                ).forEach(el => el.remove());
                document.body.style.overflow = 'auto';
            }""")
            time.sleep(1.5)
            if not is_popup_visible():
                logger.info("[Internshala] Signup popup successfully removed using Strategy 4 (JavaScript).")
                return
        except Exception as e:
            logger.warning(f"[Internshala] Strategy 4 (JavaScript) execution failed: {e}")

        # Final check
        if is_popup_visible():
            logger.warning("[Internshala] Signup popup STILL visible after applying all strategies.")
        else:
            logger.info("[Internshala] Signup popup is no longer visible.")

    def scrape_live(self) -> list[dict]:
        """
        Scrapes live technical internships from Internshala by iterating over categories.
        Uses Playwright chromium browser and dynamic page rendering.
        """
        results = []
        self.pages_scraped = 0

        categories = [
            "python-development-internship",
            "data-science-internship",
            "machine-learning-internship",
            "artificial-intelligence-ai-internship",
            "software-development-internship",
            "backend-development-internship",
            "full-stack-development-internship",
            "data-analytics-internship",
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

                # Open a single page tab for the entire session
                page = context.new_page()
                page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

                try:
                    for cat in categories:
                        for page_num in range(1, PAGES_TO_SCRAPE + 1):
                            url = f"https://internshala.com/internships/{cat}/page-{page_num}/"
                            logger.info(f"[Internshala] Scraping category '{cat}', page {page_num}: {url}")

                            try:
                                # Anti-bot delay
                                delay = random.uniform(2.0, 4.0)
                                time.sleep(delay)

                                response = page.goto(url, wait_until="domcontentloaded", timeout=PLAYWRIGHT_TIMEOUT)
                                if not response or response.status != 200:
                                    logger.warning(f"[Internshala] Received status code {response.status if response else 'None'} for {url}")
                                    continue

                                # Detect and close the popup
                                self.close_intershala_popup(page)

                                # Wait 1-2 seconds
                                recovery_delay = random.uniform(1.0, 2.0)
                                time.sleep(recovery_delay)

                                # Wait for networkidle
                                try:
                                    page.wait_for_load_state("networkidle", timeout=10000)
                                except Exception as e:
                                    logger.debug(f"[Internshala] wait_for_load_state('networkidle') timed out/failed: {e}")

                                # Scroll page slowly
                                for _ in range(3):
                                    page.evaluate("window.scrollBy(0, 300)")
                                    time.sleep(0.5)

                                # Check if signup popup still blocks scraping
                                popup_still_visible = False
                                try:
                                    if page.locator("text=Sign up now").is_visible() or page.locator("text=FREE AI Career Guide").is_visible():
                                        popup_still_visible = True
                                except Exception:
                                    pass

                                if popup_still_visible:
                                    logger.warning("[Internshala] Popup still blocks scraping. Saving debug screenshots/html before extraction.")
                                    import os
                                    os.makedirs("debug_screenshots", exist_ok=True)
                                    os.makedirs("debug_html", exist_ok=True)
                                    try:
                                        page.screenshot(path="debug_screenshots/internshala_popup.png")
                                    except Exception as screenshot_err:
                                        logger.error(f"[Internshala] Failed to save debug screenshot: {screenshot_err}")
                                    try:
                                        with open("debug_html/internshala_popup.html", "w", encoding="utf-8") as f:
                                            f.write(page.content())
                                    except Exception as html_err:
                                        logger.error(f"[Internshala] Failed to save debug html: {html_err}")

                                self.pages_scraped += 1

                                html = page.content()
                                soup = BeautifulSoup(html, 'html.parser')
                                listings = soup.select('.individual_internship')

                                if not listings:
                                    logger.info(f"[Internshala] No listings found for category '{cat}' on page {page_num}.")
                                    continue

                                page_raw_count = 0
                                for card in listings:
                                    try:
                                        # Filter out ad cards (they don't have .job-title-href or .profile a)
                                        role_el = card.select_one('.job-title-href') or card.select_one('.profile a')
                                        if not role_el:
                                            continue

                                        role = role_el.text.strip()
                                        link_suffix = role_el.get('href') or card.get('data-href') or ""
                                        apply_link = f"https://internshala.com{link_suffix}" if link_suffix else ""

                                        company_el = card.select_one('.company-name') or card.select_one('.company_name a')
                                        company_name = company_el.text.strip() if company_el else ""

                                        location_el = card.select_one('.locations span a') or card.select_one('.location_link') or card.select_one('.locations')
                                        location = location_el.text.strip() if location_el else "Remote"

                                        stipend_el = card.select_one('.stipend')
                                        stipend = stipend_el.text.strip() if stipend_el else "Unspecified"

                                        duration = "Not Specified"
                                        duration_icon = card.select_one('.ic-16-calendar')
                                        if duration_icon and duration_icon.parent:
                                            duration = duration_icon.parent.text.strip()

                                        skills = [skill.text.strip() for skill in card.select('.job_skill')]
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
                                        logger.error(f"[Internshala] Error parsing card details: {e}")
                                        continue

                                logger.info(f"[Internshala] Category '{cat}', page {page_num} successfully yielded {page_raw_count} raw items.")

                            except Exception as e:
                                logger.error(f"[Internshala] Error scraping category '{cat}', page {page_num}: {e}")
                                self.save_debug_artifacts(page, f"internshala_{cat}_p{page_num}")

                finally:
                    page.close()

                browser.close()
        except Exception as e:
            logger.error(f"[Internshala] Playwright execution failed: {e}", exc_info=True)
            return []

        return results
