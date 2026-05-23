import logging
from bs4 import BeautifulSoup
from internship_agent.scrapers.base_scraper import BaseScraper

logger = logging.getLogger("internship_agent.scrapers.wellfound")

class WellfoundScraper(BaseScraper):
    def __init__(self):
        super().__init__("Wellfound")

    def scrape_live(self) -> list[dict]:
        """
        Attempts to scrape Wellfound (formerly AngelList) technical internships.
        Note: Wellfound uses aggressive Cloudflare protection. Standard requests will 
        usually be blocked (403). This function will attempt a clean fetch, but handles 
        it gracefully, allowing the BaseScraper to load curated backup data.
        """
        results = []
        url = "https://wellfound.com/role/l/software-engineer-internship"
        logger.info(f"[Wellfound] Attempting to access live page: {url}")
        
        html = self.fetch_url(url)
        if not html:
            logger.warning("[Wellfound] Page fetch failed or was blocked by Cloudflare.")
            return []  # Triggers the premium fallback automatically
            
        soup = BeautifulSoup(html, 'html.parser')
        # Typical job cards on Wellfound (structural selectors vary and change often)
        job_cards = soup.select('.styles_jobCard__') or soup.select('[data-test="JobSearchResultCard"]')
        
        if not job_cards:
            logger.info("[Wellfound] No job cards found in HTML. Activating emulated fallback.")
            return []
            
        for card in job_cards:
            try:
                role_el = card.select_one('.styles_title__') or card.select_one('[data-test="job-title"]')
                role = role_el.text.strip() if role_el else ""
                
                company_el = card.select_one('.styles_name__') or card.select_one('[data-test="company-name"]')
                company_name = company_el.text.strip() if company_el else ""
                
                link_el = card.select_one('a')
                apply_link = link_el['href'] if link_el and 'href' in link_el.attrs else ""
                if apply_link and not apply_link.startswith('http'):
                    apply_link = f"https://wellfound.com{apply_link}"
                    
                stipend = "Unspecified"
                salary_el = card.select_one('.styles_salary__')
                if salary_el:
                    stipend = salary_el.text.strip()
                    
                location = "Remote"
                loc_el = card.select_one('.styles_location__')
                if loc_el:
                    location = loc_el.text.strip()

                if role and company_name:
                    results.append({
                        "company_name": company_name,
                        "role": role,
                        "stipend": stipend,
                        "location": location,
                        "duration": "6 Months",
                        "skills": "Python, SQL, AWS, Javascript",
                        "apply_link": apply_link or "https://wellfound.com/jobs",
                        "source": "Wellfound"
                    })
            except Exception as e:
                logger.error(f"[Wellfound] Error parsing job listing: {e}")
                continue
                
        return results
