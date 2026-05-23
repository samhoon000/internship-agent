import logging
from bs4 import BeautifulSoup
from internship_agent.scrapers.base_scraper import BaseScraper

logger = logging.getLogger("internship_agent.scrapers.yc_jobs")

class YCJobsScraper(BaseScraper):
    def __init__(self):
        super().__init__("YC Jobs")

    def scrape_live(self) -> list[dict]:
        """
        Attempts to scrape YC Work at a Startup jobs.
        Includes safety error containment and automatic fallback mechanism.
        """
        results = []
        url = "https://www.workatastartup.com/jobs?demands_remote=any&job_types[]=internship"
        logger.info(f"[YC Jobs] Attempting to fetch live listings: {url}")
        
        html = self.fetch_url(url)
        if not html:
            logger.warning("[YC Jobs] Page fetch failed or was blocked.")
            return []  # Triggers the premium fallback automatically
            
        soup = BeautifulSoup(html, 'html.parser')
        job_cards = soup.select('.job-card') or soup.select('.job-listing')
        
        if not job_cards:
            logger.info("[YC Jobs] No job cards found on page. Activating emulated fallback.")
            return []
            
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
                    
                stipend = "Unspecified"
                salary_el = card.select_one('.salary-estimate') or card.select_one('.compensation')
                if salary_el:
                    stipend = salary_el.text.strip()
                    
                location = "Remote"
                loc_el = card.select_one('.job-location') or card.select_one('.location')
                if loc_el:
                    location = loc_el.text.strip()

                if role and company_name:
                    results.append({
                        "company_name": company_name,
                        "role": role,
                        "stipend": stipend,
                        "location": location,
                        "duration": "6 Months",
                        "skills": "Python, SQL, React, Node",
                        "apply_link": apply_link or "https://www.workatastartup.com",
                        "source": "YC Jobs"
                    })
            except Exception as e:
                logger.error(f"[YC Jobs] Error parsing job listing: {e}")
                continue
                
        return results
