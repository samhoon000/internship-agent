"""
Centralized Scoring Service
===========================
Contains unified logic for calculating:
1. Legitimacy Score & Confidence Tier
2. Relevance Score, Relevance Tier, & Role Category

Includes exact token-based skill matching to prevent substring collisions (Java -> JavaScript, SQL -> NoSQL).
"""

import re
import socket
import logging
from functools import lru_cache
from python_scraper.config import SUSPICIOUS_COMPANY_PATTERNS, BOOST_SKILLS

logger = logging.getLogger("python_scraper.scoring_service")


# ── SKILL NORMALIZATION & EXACT MATCHING ───────────────────────────────────

def normalize_skill(skill: str) -> str:
    """Normalizes skill names to a canonical standard to ensure consistency."""
    s = skill.strip().lower()
    if not s:
        return ""
    if s == 'sql':
        return 'SQL'
    if s in ['python', 'py']:
        return 'Python'
    if s == 'pandas':
        return 'Pandas'
    if s in ['machine learning', 'ml']:
        return 'Machine Learning'
    if s in ['deep learning', 'dl']:
        return 'Deep Learning'
    if s in ['nlp', 'natural language processing']:
        return 'NLP'
    if s == 'tensorflow':
        return 'TensorFlow'
    if s == 'pytorch':
        return 'PyTorch'
    if s == 'power bi' or s == 'powerbi':
        return 'Power BI'
    if s == 'excel':
        return 'Excel'
    if s == 'tableau':
        return 'Tableau'
    if s == 'r':
        return 'R'
    if s == 'git':
        return 'Git'
    if s == 'javascript' or s == 'js':
        return 'JavaScript'
    if s == 'java':
        return 'Java'
    if s == 'react':
        return 'React'
    if s == 'node' or s == 'node.js':
        return 'Node'
    if s == 'html':
        return 'HTML'
    if s == 'css':
        return 'CSS'
    if s == 'c++':
        return 'C++'
    if s == 'flutter':
        return 'Flutter'
    if s == 'android':
        return 'Android'
    if s == 'ios':
        return 'iOS'
    if s == 'typescript' or s == 'ts':
        return 'TypeScript'
    return s.title()


def check_word_in_text(word: str, text: str) -> bool:
    """Checks if a specific word exists in a block of text using exact boundaries."""
    escaped = re.escape(word.lower())
    text_lower = text.lower()
    
    # Check if word is purely alphanumeric
    if re.match(r'^[a-zA-Z0-9_]+$', word):
        pattern = rf"\b{escaped}\b"
        matches = list(re.finditer(pattern, text_lower))
        for m in matches:
            _, end = m.span()
            # If followed immediately by '+' or '#', it's likely C++ or C# instead of C
            if end < len(text_lower) and text_lower[end] in ['+', '#']:
                continue
            return True
        return False
    else:
        # Handles c++, .net, etc. using space or punctuation boundaries
        pattern = rf"(?:^|\s|[.,;:!?'\"()\[\]])({escaped})(?:$|\s|[.,;:!?'\"()\[\]])"
        return bool(re.search(pattern, text_lower))


# ── LEGITIMACY & CONFIDENCE SCORING ────────────────────────────────────────

def calculate_legitimacy_score(item: dict) -> int:
    """
    Calculates a legitimacy score from 0 to 100 based on weighted positive
    and negative signals. Starts from 0 and adds/subtracts points.
    """
    score = 0

    role = (item.get("role") or "").lower().strip()
    company = (item.get("company_name") or "").lower().strip()
    stipend = (item.get("stipend") or "").lower().strip()
    paid = item.get("paid", False)
    location = (item.get("location") or "").lower().strip()
    remote = item.get("remote", False)
    duration = (item.get("duration") or "").lower().strip()
    skills = (item.get("skills") or "").lower().strip()
    apply_link = (item.get("apply_link") or "").strip()

    # 1. Paid Check (+20 / -20)
    if paid and stipend not in ["unpaid", "none", "unspecified", ""]:
        score += 20
    elif paid:
        score += 10
    else:
        score -= 20

    # 2. Company DNS Resolution Check (+15)
    company_domain_ok = False
    if company and company != "unknown company" and len(company) > 2:
        domain = _infer_company_domain(company)
        if domain and _quick_dns_check(domain):
            score += 15
            company_domain_ok = True
        else:
            score += 5
    else:
        score -= 15

    # 3. LinkedIn / Online Presence Heuristics (+15)
    if company_domain_ok:
        score += 10
    if len(company.split()) >= 2 and len(company) >= 5:
        score += 5
    else:
        score -= 5

    # 4. Skills Listed Check (+10)
    if skills and skills != "not specified" and len(skills) > 5:
        score += 10
    else:
        score -= 5

    # 5. Tech Skills Match (+10)
    # Refactored to use exact matching to prevent partial match issues
    tech_match = False
    for kw in BOOST_SKILLS:
        if check_word_in_text(kw, skills) or check_word_in_text(kw, role):
            tech_match = True
            break
    if tech_match:
        score += 10
    else:
        score -= 5

    # 6. Realistic Stipend Check (+10)
    has_real_amount = bool(re.search(r"\d{3,}", stipend))
    if has_real_amount:
        score += 10

    # 7. Valid URL Check (+10 / -25)
    if apply_link.startswith("https://") and len(apply_link) > 20:
        score += 10
    elif apply_link:
        score -= 10
    else:
        score -= 25

    # 8. Duration Specified Check (+5)
    if duration and duration != "not specified" and any(c.isdigit() for c in duration):
        score += 5

    # 9. Remote Flexibility Check (+5)
    if remote or "remote" in location or "wfh" in location:
        score += 5

    # 10. Suspicious Company Names Penalty (-20)
    for pattern in SUSPICIOUS_COMPANY_PATTERNS:
        if pattern in company:
            score -= 20
            break

    # 11. Vague Role Penalty (-15)
    generic_roles = ["intern", "trainee", "candidate", "associate"]
    role_words = role.split()
    if role_words and all(w in generic_roles for w in role_words):
        score -= 15
    elif len(role) < 5:
        score -= 10

    # 12. Scam / Certificate Wording Penalty (-20)
    scam_patterns = [
        "certificate only", "pay for training", "course bundle",
        "paid training", "security deposit", "registration fee",
        "buy certificate", "unpaid training",
    ]
    combined_text = f"{role} {skills} {stipend}"
    for pattern in scam_patterns:
        if pattern in combined_text:
            score -= 20
            break

    # ── AI Keywords Boost (+25) ──
    ai_kws = ["artificial intelligence", "ai", "machine learning", "ml", "llm", "generative ai", "deep learning", "neural network", "nlp", "computer vision"]
    has_ai = False
    for kw in ai_kws:
        if check_word_in_text(kw, role):
            has_ai = True
            break
    if has_ai:
        score += 25

    # ── Data Keywords Boost (+20) ──
    data_kws = ["data analyst", "business analyst", "mis analyst", "data science", "analytics", "business intelligence", "sql", "data engineer", "data specialist"]
    has_data = False
    for kw in data_kws:
        if check_word_in_text(kw, role):
            has_data = True
            break
    if has_data:
        score += 20

    # ── Research Keywords Boost (+20) ──
    research_kws = ["research", "research analyst", "quantitative research", "ai research", "research engineer"]
    if any(check_word_in_text(kw, role) for kw in research_kws):
        score += 20

    # ── Startup-Aware Boost (+15) ──
    source = item.get("source", "")
    is_startup_source = source in ["YC Jobs", "Wellfound"]
    has_startup_text = "founding" in role or "startup" in role or "labs" in role or "founding" in company or "startup" in company or "labs" in company or company.endswith(".ai") or company.endswith(" ai") or role.endswith(".ai") or role.endswith(" ai")
    if is_startup_source or has_startup_text:
        score += 15

    # ── Generic Suffix Soft Penalty (-10) ──
    warning_words = ["solutions", "technologies", "labs", "innovation", "innovations", "digital", "systems"]
    has_warning = any(w in company for w in warning_words)
    if has_warning and not company_domain_ok:
        score -= 10

    return max(0, min(100, score))


def get_legitimacy_bucket(score: int) -> str:
    """Categorizes the legitimacy score into 4 confidence classes."""
    if score >= 80:
        return "HIGH_CONFIDENCE"
    elif score >= 60:
        return "MEDIUM_CONFIDENCE"
    elif score >= 45:
        return "LOW_CONFIDENCE"
    else:
        return "REJECT"


# ── RELEVANCE & CATEGORY SCORING ──────────────────────────────────────────

def get_relevance_tier_and_category(title: str, skills: str, description: str, company_domain: str = None, source: str = None) -> tuple[int, str, str]:
    """Calculates unified relevance score, tier, and role category with exact skill matching."""
    if not title:
        return 0, "IRRELEVANT", "Other"

    title_lower = title.lower()
    skills_lower = (skills or "").lower()
    desc_lower = (description or "").lower()
    domain_lower = (company_domain or "").lower()
    source_lower = (source or "").lower()

    # Normalize title
    norm_title = re.sub(r'[-/_+:,()\[\]\s]+', ' ', title_lower)
    norm_title = ' '.join(norm_title.split())

    # 1. Hard Exclusions Check
    penalties = [
        "sales", "marketing", "hr", "telecalling", "customer support", "customer care",
        "equity dealer", "back office", "social media", "content writing", "telecaller",
        "human resources", "business development", "bde", "bda", "recruiter", "recruiting",
        "talent acquisition"
    ]
    for p in penalties:
        if check_word_in_text(p, norm_title):
            return 0, "IRRELEVANT", "Other"

    # 2. Determine Category
    data_ai_keywords = [
        "data science", "data scientist", "data analyst", "data analytics", "business analyst", 
        "business intelligence", "machine learning", "artificial intelligence", "deep learning", 
        "sql", "research analyst", "data engineer", "ml engineer", "ai engineer", "analytics", 
        "bi analyst", "bi developer", "mis analyst", "quantitative research", "research engineer",
        "nlp", "computer vision", "statistics", "data wrangler", "insights analyst", "analytics engineer"
    ]
    
    software_keywords = [
        "software engineer", "software engineering", "full stack", "fullstack", "backend", 
        "product engineer", "product engineering", "software developer", "frontend", "front end", 
        "web developer", "web development", "react", "node", "flutter", "java developer", 
        "android", "ios"
    ]

    is_data_ai = any(check_word_in_text(kw, norm_title) for kw in data_ai_keywords)
    is_software = any(check_word_in_text(kw, norm_title) for kw in software_keywords)

    category = "Other"
    if is_data_ai:
        category = "Data/AI"
    elif is_software:
        category = "Software"
    else:
        # Fallback to skills/description if title is ambiguous (using exact matching)
        has_data_skills = any(
            check_word_in_text(sk, skills_lower) or check_word_in_text(sk, desc_lower)
            for sk in ["python", "sql", "pandas", "tableau", "power bi", "machine learning", "data science"]
        )
        has_sw_skills = any(
            check_word_in_text(sk, skills_lower) or check_word_in_text(sk, desc_lower)
            for sk in ["javascript", "react", "node", "html", "css", "java", "c++", "flutter"]
        )
        if has_data_skills:
            category = "Data/AI"
        elif has_sw_skills:
            category = "Software"

    if category == "Other":
        return 20, "IRRELEVANT", "Other"

    # 3. Calculate Score
    score = 30  # Base score for matching category

    # Title Match (Max 55 points)
    if category == "Data/AI":
        boosted = [
            "data science", "data scientist", "data analyst", "data analytics", "business analyst", 
            "business intelligence", "machine learning", "artificial intelligence", "deep learning", 
            "sql", "research analyst", "data engineer", "ml engineer", "ai engineer"
        ]
        if any(check_word_in_text(b, norm_title) for b in boosted):
            score += 55
        else:
            score += 40
    elif category == "Software":
        sw_boosted = ["software engineer", "software engineering", "full stack", "fullstack", "backend", "product engineer", "product engineering"]
        if any(check_word_in_text(s, norm_title) for s in sw_boosted):
            score += 55
        else:
            score += 40

    # Skills Match (Max 20 points)
    if category == "Data/AI":
        core_skills = ["python", "sql", "excel", "power bi", "tableau", "pandas", "numpy", "machine learning", "data science", "statistics", "r", "spark", "databricks", "database", "etl", "bigquery", "analytics"]
    else:
        core_skills = ["javascript", "react", "node", "html", "css", "java", "c++", "flutter", "android", "ios", "git", "typescript"]

    # Tokenize input skills and run exact check
    input_skills = [normalize_skill(s) for s in skills_lower.split(",") if s.strip()]
    normalized_core_skills = [normalize_skill(cs) for cs in core_skills]
    
    matched_skills = set()
    for s in input_skills:
        if s in normalized_core_skills:
            matched_skills.add(s)
            
    score += min(20, len(matched_skills) * 5)

    # Description Match (Max 15 points)
    desc_score = 0
    if desc_lower:
        matched_desc = set()
        for cs in core_skills:
            if check_word_in_text(cs, desc_lower):
                matched_desc.add(cs)
        desc_score = min(15, len(matched_desc) * 3)
    score += desc_score

    # Company Domain Match (Max 5 points)
    if domain_lower:
        job_boards = ["internshala.com", "indeed.com", "indeed.co.in", "in.indeed.com", "wellfound.com", "workatastartup.com", "linkedin.com"]
        if not any(jb in domain_lower for jb in job_boards):
            score += 5

    # Source Match (Max 5 points)
    if source_lower:
        if "wellfound" in source_lower or "yc" in source_lower or "workatastartup" in source_lower:
            score += 5
        else:
            score += 2

    score = min(100, max(0, score))

    # Determine Tier
    if score >= 80:
        tier = "HIGHLY_RELEVANT"
    elif score >= 60:
        tier = "RELEVANT"
    elif score >= 40:
        tier = "MARGINALLY_RELEVANT"
    else:
        tier = "IRRELEVANT"

    return score, tier, category


def calculate_relevance_score(title: str, skills: str, description: str, company_domain: str = None, source: str = None) -> int:
    """Calculates role relevance score. Returns an integer from 0 to 100."""
    score, _, _ = get_relevance_tier_and_category(title, skills, description, company_domain, source)
    return score


# ── Helpers ───────────────────────────────────────────────────────────────

def _infer_company_domain(company_name: str) -> str:
    """Infers a domain name from a company name for DNS lookup."""
    clean = re.sub(
        r"\b(pvt|private|ltd|limited|inc|llc|corp|corporation|co|company)\b",
        "", company_name.lower()
    )
    clean = re.sub(r"[^a-z0-9\s]", "", clean).strip()
    parts = clean.split()
    if not parts:
        return ""
    return f"{parts[0]}.com"


@lru_cache(maxsize=1024)
def _quick_dns_check(domain: str) -> bool:
    """Returns True if the domain resolves via DNS (fast, 2s timeout)."""
    try:
        socket.setdefaulttimeout(2)
        socket.getaddrinfo(domain, None)
        return True
    except (socket.gaierror, socket.timeout, OSError):
        return False
