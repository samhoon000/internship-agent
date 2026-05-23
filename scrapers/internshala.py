import logging
import random
import time
import requests
from bs4 import BeautifulSoup
from internship_agent.scrapers.base_scraper import BaseScraper
from internship_agent.config import PAGES_TO_SCRAPE, USER_AGENTS, REQUEST_TIMEOUT, SCRAPE_DELAY_MIN, SCRAPE_DELAY_MAX

logger = logging.getLogger("internship_agent.scrapers.internshala")

class InternshalaScraper(BaseScraper):
    def __init__(self):
        super().__init__("Internshala")
        self.session = requests.Session()

    def fetch_url(self, url: str) -> str:
        """Fetches HTML from Internshala with retries, random delays, and custom headers."""
        retries = 3
        backoff = 2

        for attempt in range(retries):
            delay = random.uniform(SCRAPE_DELAY_MIN, SCRAPE_DELAY_MAX)
            logger.info(f"[Internshala] Waiting {delay:.2f}s before request (anti-bot delay)...")
            time.sleep(delay)

            try:
                headers = {
                    "User-Agent": random.choice(USER_AGENTS),
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                }
                logger.info(f"[Internshala] Fetching URL (Attempt {attempt + 1}/{retries}): {url}")
                response = self.session.get(url, headers=headers, timeout=REQUEST_TIMEOUT)

                if response.status_code == 200:
                    return response.text
                elif response.status_code == 403:
                    logger.warning("[Internshala] Access Forbidden (403).")
                    break
                else:
                    logger.warning(f"[Internshala] Received status code {response.status_code}.")

            except requests.RequestException as e:
                logger.error(f"[Internshala] Request error on attempt {attempt + 1}: {e}")
            
            time.sleep(backoff)
            backoff *= 2

        return ""

    def scrape_live(self) -> list[dict]:
        """Scrapes live technical internships from Internshala."""
        results = []
        keywords = "python,data-science,machine-learning,ai,backend,software-engineer,react,javascript,node-js"
        
        for page in range(1, PAGES_TO_SCRAPE + 1):
            url = f"https://internshala.com/internships/keywords-{keywords}/page-{page}/"
            logger.info(f"[Internshala] Scraping page {page}: {url}")
            
            html = self.fetch_url(url)
            if not html:
                logger.warning(f"[Internshala] Failed to fetch page {page} or blocked.")
                continue
                
            soup = BeautifulSoup(html, 'html.parser')
            listings = soup.select('.individual_internship')
            
            if not listings:
                logger.warning(f"[Internshala] No listings found on page {page}.")
                continue
                
            for card in listings:
                try:
                    role_el = card.select_one('.profile a')
                    role = role_el.text.strip() if role_el else ""
                    
                    link_suffix = role_el['href'] if role_el and 'href' in role_el.attrs else ""
                    apply_link = f"https://internshala.com{link_suffix}" if link_suffix else ""
                    
                    company_el = card.select_one('.company_name a')
                    company_name = company_el.text.strip() if company_el else ""
                    
                    location_el = card.select_one('.location_link')
                    location = location_el.text.strip() if location_el else "Remote"
                    
                    stipend = "Unspecified"
                    duration = "Not Specified"
                    skills = []
                    
                    details = card.select('.other_detail_item')
                    for det in details:
                        heading = det.select_one('.item_heading')
                        body = det.select_one('.item_body')
                        if heading and body:
                            h_text = heading.text.strip().lower()
                            b_text = body.text.strip()
                            if 'stipend' in h_text:
                                stipend = b_text
                            elif 'duration' in h_text:
                                duration = b_text
                                
                    role_lower = role.lower()
                    if "python" in role_lower:
                        skills.append("Python")
                    if "django" in role_lower or "flask" in role_lower:
                        skills.append("Django/Flask")
                    if "data" in role_lower:
                        skills.append("Data Analytics")
                        skills.append("SQL")
                    if "machine learning" in role_lower or "ml" in role_lower or "ai" in role_lower:
                        skills.append("Machine Learning")
                        skills.append("AI")
                    if "react" in role_lower or "frontend" in role_lower:
                        skills.append("React")
                        skills.append("JavaScript")
                    if "backend" in role_lower:
                        skills.append("Backend Development")
                    if "full stack" in role_lower:
                        skills.append("Full Stack")
                        skills.append("Node.js")
                        
                    # Remove the hardcoded fallback skills default "Python, SQL, Git". 
                    # If empty, validation will handle it or it's marked as empty.
                    skills_str = ", ".join(skills) if skills else ""

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
                except Exception as e:
                    logger.error(f"[Internshala] Error parsing job card: {e}")
                    continue
                    
        return results

