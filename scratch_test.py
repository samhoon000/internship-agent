import sys
import time
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

def test_urls():
    candidates = [
        ("python-development", "https://internshala.com/internships/python-development-internship/"),
        ("data-science", "https://internshala.com/internships/data-science-internship/"),
        ("machine-learning", "https://internshala.com/internships/machine-learning-internship/"),
        ("artificial-intelligence-ai", "https://internshala.com/internships/artificial-intelligence-ai-internship/"),
        ("ai-keyword", "https://internshala.com/internships/keywords-ai/"),
        ("software-development", "https://internshala.com/internships/software-development-internship/"),
        ("backend-development", "https://internshala.com/internships/backend-development-internship/"),
        ("full-stack-development", "https://internshala.com/internships/full-stack-development-internship/"),
        ("data-analytics", "https://internshala.com/internships/data-analytics-internship/"),
    ]
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            context = browser.new_context(
                user_agent=user_agent,
                viewport={"width": 1366, "height": 768},
            )
            page = context.new_page()
            page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            for name, url in candidates:
                try:
                    response = page.goto(url, wait_until="domcontentloaded", timeout=15000)
                    time.sleep(2)
                    html = page.content()
                    soup = BeautifulSoup(html, 'html.parser')
                    listings = soup.select('.individual_internship')
                    
                    # Filter out ads
                    real_count = 0
                    for c in listings:
                        if c.select_one('.job-title-href') or c.select_one('.profile a'):
                            real_count += 1
                            
                    print(f"URL: {url} -> Status: {response.status if response else 'No Resp'}, Title: {page.title()}, Total listings: {len(listings)}, Real listings: {real_count}")
                except Exception as e:
                    print(f"URL: {url} -> Failed with error: {e}")
            
            browser.close()
    except Exception as e:
        print("Playwright launch error:", e)

if __name__ == '__main__':
    test_urls()
