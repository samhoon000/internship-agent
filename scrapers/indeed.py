import logging
from bs4 import BeautifulSoup
from internship_agent.scrapers.base_scraper import BaseScraper
from internship_agent.config import PAGES_TO_SCRAPE

logger = logging.getLogger("internship_agent.scrapers.indeed")

class IndeedScraper(BaseScraper):
    def __init__(self):
        super().__init__("Indeed India")

    def scrape_live(self) -> list[dict]:
        """Scrapes live technical internships from Indeed India."""
        results = []
        # Construct search query for tech internships in India
        query = "python+internship"
        
        for page in range(PAGES_TO_SCRAPE):
            # Indeed pagination uses start=0, 10, 20...
            start = page * 10
            url = f"https://in.indeed.com/jobs?q={query}&l=India&start={start}"
            logger.info(f"[Indeed India] Scraping page {page + 1}: {url}")
            
            html = self.fetch_url(url)
            if not html:
                logger.warning(f"[Indeed India] Failed to fetch page {page + 1} or blocked by anti-bot.")
                continue
                
            soup = BeautifulSoup(html, 'html.parser')
            job_cards = soup.select('.job_seen_beacon')
            
            if not job_cards:
                logger.warning(f"[Indeed India] No job cards found on page {page + 1}. IP might be soft-blocked.")
                continue
                
            for card in job_cards:
                try:
                    # Role / Title
                    role_el = card.select_one('h2.jobTitle a') or card.select_one('h2.jobTitle span')
                    role = ""
                    apply_link = "https://in.indeed.com"
                    
                    if role_el:
                        role = role_el.text.strip()
                        if 'href' in role_el.attrs:
                            apply_link = f"https://in.indeed.com{role_el['href']}"
                            
                    # Company Name
                    company_el = card.select_one('[data-testid="company-name"]') or card.select_one('.companyName')
                    company_name = company_el.text.strip() if company_el else ""
                    
                    # Location
                    location_el = card.select_one('[data-testid="text-location"]') or card.select_one('.companyLocation')
                    location = location_el.text.strip() if location_el else "India"
                    
                    # Stipend / Salary
                    stipend = "Unspecified"
                    salary_el = card.select_one('.salary-snippet-container') or card.select_one('.metadata.salarySnippet')
                    if salary_el:
                        stipend = salary_el.text.strip()
                        
                    # Extract skills keywords from job description preview
                    skills = []
                    desc_el = card.select_one('.job-snippet')
                    if desc_el:
                        desc_text = desc_el.text.lower()
                        for kw in ["python", "sql", "aws", "react", "javascript", "node", "django", "flask", "ml", "ai"]:
                            if kw in desc_text:
                                skills.append(kw.capitalize())
                                
                    if not skills:
                        skills = ["Python", "SQL"]

                    if role and company_name:
                        results.append({
                            "company_name": company_name,
                            "role": role,
                            "stipend": stipend,
                            "location": location,
                            "duration": "6 Months",
                            "skills": ", ".join(skills),
                            "apply_link": apply_link,
                            "source": "Indeed India"
                        })
                except Exception as e:
                    logger.error(f"[Indeed India] Error parsing card details: {e}")
                    continue
                    
        return results
