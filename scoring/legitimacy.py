import logging

logger = logging.getLogger("internship_agent.scoring.legitimacy")

def calculate_legitimacy_score(item: dict) -> int:
    """
    Calculates a legitimacy score from 0 to 100 based on positive and negative signals.
    
    POSITIVE SIGNALS:
    + Stipend exists / Paid is True (+20)
    + Company website / Profile exists / Known source (+10)
    + Technical skills/tech stack mentioned (+15)
    + Remote flexibility (+10)
    + Clear internship duration (+15)
    + Descriptive role title (+10)
    
    NEGATIVE SIGNALS:
    - Unpaid (-30)
    - Certificate-only or training-fees warning (-30)
    - Vague role title (e.g., "Intern" or "Assistant" without tech context) (-20)
    - Missing crucial details (e.g., no skills and unspecified duration) (-10)
    """
    score = 50  # Base starting score
    
    role = item.get('role', '').lower()
    company = item.get('company_name', '').lower()
    stipend = item.get('stipend', '').lower()
    paid = item.get('paid', False)
    location = item.get('location', '').lower()
    remote = item.get('remote', False)
    duration = item.get('duration', '').lower()
    skills = item.get('skills', '').lower()
    apply_link = item.get('apply_link', '')

    # --- 1. PAID VS UNPAID SIGNALS ---
    if paid and stipend not in ["unpaid", "none", "unspecified"]:
        score += 20
    else:
        score -= 30  # Strong negative signal for unpaid/certificate-only

    # --- 2. COMPANY PROFILE VALIDATION ---
    # Real companies usually have standard names and profiles
    if company and company != "unknown company" and len(company) > 2:
        score += 10
    else:
        score -= 10

    # --- 3. TECH STACK AND SKILLS ---
    if skills and skills != "not specified" and len(skills) > 5:
        score += 15
    else:
        score -= 10

    # --- 4. REMOTE FLEXIBILITY ---
    if remote or "remote" in location or "wfh" in location:
        score += 10

    # --- 5. INTERNSHIP DURATION ---
    if duration and duration != "not specified" and any(char.isdigit() for char in duration):
        score += 15
    else:
        score -= 5

    # --- 6. ROLE DESCRIPTIVENESS & SPECIFICITY ---
    # If the role is highly specific (e.g., "Backend Engineer Intern" vs "Intern")
    generic_words = ["intern", "trainee", "associate", "candidate"]
    is_generic = all(word in role for word in role.split()) if role else True
    
    if any(tech_kw in role for tech_kw in ["python", "machine learning", "ai", "data", "software", "backend", "frontend", "full stack"]):
        score += 10
    elif is_generic or len(role) < 8:
        score -= 20

    # --- 7. SUSPICIOUS WORDING / CERTIFICATE-ONLY WARNINGS ---
    suspicious_patterns = [
        "certificate only", "pay for training", "course bundle", "paid training", 
        "security deposit", "registration fee", "buy certificate", "unpaid training"
    ]
    
    for pattern in suspicious_patterns:
        if pattern in role or pattern in skills or pattern in stipend:
            score -= 30

    # --- 8. BOUNDS ENFORCEMENT (0-100) ---
    score = max(0, min(100, score))
    return score

def get_legitimacy_bucket(score: int) -> str:
    """
    Categorizes the legitimacy score into the requested buckets:
    80–100 = Highly Legit
    60–79 = Good
    40–59 = Risky
    0–39 = Avoid
    """
    if score >= 80:
        return "Highly Legit"
    elif score >= 60:
        return "Good"
    elif score >= 40:
        return "Risky"
    else:
        return "Avoid"
