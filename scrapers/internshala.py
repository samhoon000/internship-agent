import logging
from bs4 import BeautifulSoup
from internship_agent.scrapers.base_scraper import BaseScraper
from internship_agent.config import PAGES_TO_SCRAPE

logger = logging.getLogger("internship_agent.scrapers.internshala")

class InternshalaScraper(BaseScraper):
    def __init__(self):
        super().__init__("Internshala")

    def scrape_live(self) -> list[dict]:
        """Scrapes live technical internships from Internshala."""
        results = []
        # Target keywords related to tech
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
                logger.warning(f"[Internshala] No listings found on page {page}. Dynamic structure might have changed or access was blocked.")
                continue
                
            for card in listings:
                try:
                    # Role/Profile
                    role_el = card.select_one('.profile a')
                    role = role_el.text.strip() if role_el else ""
                    
                    # Apply Link
                    link_suffix = role_el['href'] if role_el and 'href' in role_el.attrs else ""
                    apply_link = f"https://internshala.com{link_suffix}" if link_suffix else ""
                    
                    # Company Name
                    company_el = card.select_one('.company_name a')
                    company_name = company_el.text.strip() if company_el else ""
                    
                    # Location
                    location_el = card.select_one('.location_link')
                    location = location_el.text.strip() if location_el else "Remote"
                    
                    # Duration & Stipend (Internshala puts them inside detail rows)
                    stipend = "Unspecified"
                    duration = "Not Specified"
                    skills = []
                    
                    # Extract items from other_detail_item_row
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
                                
                    # Attempt to extract skills (some cards list keywords, or we infer from the title)
                    # Let's infer skills from role and surrounding tags
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
                        
                    if not skills:
                        skills = ["Python", "SQL", "Git"]

                    if role and company_name and apply_link:
                        results.append({
                            "company_name": company_name,
                            "role": role,
                            "stipend": stipend,
                            "location": location,
                            "duration": duration,
                            "skills": ", ".join(skills),
                            "apply_link": apply_link,
                            "source": "Internshala"
                        })
                except Exception as e:
                    logger.error(f"[Internshala] Error parsing job card: {e}")
                    continue
                    
        return results
