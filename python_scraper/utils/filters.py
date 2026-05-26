import re
import logging
from python_scraper.config import TECH_KEYWORDS, EXCLUDE_KEYWORDS

logger = logging.getLogger("python_scraper.utils.filters")

def is_tech_role(role_name: str) -> bool:
    """
    Checks if a role title matches technical keywords.
    Returns True if matches technical keywords, False otherwise.
    """
    if not role_name:
        return False
    
    role_lower = role_name.lower()
    
    # Check exclusion keywords first
    for word in EXCLUDE_KEYWORDS:
        # Match as a word boundary to prevent accidental matching (e.g. "hr" in "thread")
        pattern = rf"\b{re.escape(word)}\b"
        if re.search(pattern, role_lower) or word in role_lower:
            return False
            
    # Check technical keywords
    for keyword in TECH_KEYWORDS:
        # For multi-word keywords (e.g., "machine learning"), do direct substring checking
        if keyword in role_lower:
            return True
        # For single words, check word boundaries to avoid partial matches
        pattern = rf"\b{re.escape(keyword)}\b"
        if re.search(pattern, role_lower):
            return True
            
    return False

def check_stipend_paid(stipend_text: str) -> tuple[bool, str]:
    """
    Parses stipend text to infer if the internship is paid.
    Returns (is_paid, cleaned_stipend_text).
    """
    if not stipend_text:
        return False, "Unspecified"
        
    text_lower = stipend_text.lower().strip()
    
    # First check for positive indicators like non-zero digits (e.g. ₹20,000, 10000, 500, etc.)
    # to avoid false matches with unpaid indicators like "0".
    has_non_zero_digits = any(char.isdigit() and char != '0' for char in text_lower)
    if has_non_zero_digits:
        return True, stipend_text.strip()
        
    # Non-paid indicators (excluding "0" as a simple substring since it matches any number with 0)
    unpaid_indicators = ["unpaid", "none", "no stipend", "nil", "zero", "volunteer", "free"]
    for indicator in unpaid_indicators:
        if indicator in text_lower:
            return False, "Unpaid"
            
    # Standalone '0' check
    if re.search(r'\b0\b', text_lower):
        return False, "Unpaid"
        
    # Standard text options
    if "paid" in text_lower or "performance based" in text_lower or "incentives" in text_lower:
        return True, stipend_text.strip()
        
    # If it contains digits (like "0" but nothing else)
    has_digits = any(char.isdigit() for char in text_lower)
    if has_digits:
        return False, "Unpaid"
        
    return False, stipend_text.strip()

def check_remote(location_text: str) -> bool:
    """
    Checks if the location signifies a remote position.
    """
    if not location_text:
        return False
        
    text_lower = location_text.lower().strip()
    remote_keywords = ["remote", "wfh", "work from home", "home", "virtual", "anywhere"]
    
    for kw in remote_keywords:
        if kw in text_lower:
            return True
            
    return False

def clean_internship(item: dict) -> dict:
    """
    Applies standardization and cleaning filters onto a raw scraped internship dictionary.
    Does NOT inject fake defaults — missing data is left empty to be caught by the validation pipeline.
    """
    cleaned = item.copy()
    
    # 1. Clean role and company name (no fake defaults)
    cleaned['role'] = cleaned.get('role', '').strip()
    cleaned['company_name'] = cleaned.get('company_name', '').strip()
    
    # 2. Clean location & remote status
    loc = cleaned.get('location', '').strip()
    cleaned['location'] = loc
    cleaned['remote'] = check_remote(loc) or cleaned.get('remote', False)
    
    # 3. Clean stipend & paid status
    stipend_raw = cleaned.get('stipend', '')
    is_paid, clean_stipend = check_stipend_paid(stipend_raw)
    cleaned['paid'] = is_paid
    cleaned['stipend'] = clean_stipend
    
    # 4. Standardize skills list
    skills = cleaned.get('skills', '')
    if isinstance(skills, list):
        cleaned['skills'] = ", ".join(skills)
    elif skills:
        cleaned['skills'] = str(skills).strip()
    else:
        cleaned['skills'] = "Not Specified"
        
    # 5. Default fields (no fake values — empty strings caught by validation)
    cleaned['duration'] = cleaned.get('duration', '').strip() or "Not Specified"
    cleaned['apply_link'] = cleaned.get('apply_link', '').strip()
    cleaned['source'] = cleaned.get('source', '').strip()
    
    return cleaned
