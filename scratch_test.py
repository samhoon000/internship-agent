from bs4 import BeautifulSoup

def inspect_full_job_container():
    with open("debug_html/yc_test.html", "r", encoding="utf-8") as f:
        html = f.read()
        
    soup = BeautifulSoup(html, 'html.parser')
    
    target_link = None
    for a in soup.find_all('a'):
        href = a.get('href', '')
        if href.startswith('/jobs/') and href.replace('/jobs/', '').isdigit():
            target_link = a
            break
            
    if not target_link:
        print("No job detail link found.")
        return
        
    # Parent Level 2 is the card container
    card = target_link.parent.parent
    print("Prettified full HTML of the YC Job card container:")
    print(card.prettify())

if __name__ == '__main__':
    inspect_full_job_container()
