"""
Legitimacy Scoring Engine
=========================
Calculates a 0–100 score representing how trustworthy an internship listing is.
The score must vary realistically — NOT every listing should score 100.

Score buckets:
  90–100  →  Excellent
  75–89   →  High Confidence
  60–74   →  Good
  40–59   →  Risky          (auto-rejected before SQL insert)
  0–39    →  Reject         (auto-rejected before SQL insert)

AUTO-REJECT threshold: score < 60
"""

import re
import logging
import socket

from internship_agent.config import SUSPICIOUS_COMPANY_PATTERNS, TECH_KEYWORDS

logger = logging.getLogger("internship_agent.scoring.legitimacy")


def calculate_legitimacy_score(item: dict) -> int:
    """
    Calculates a legitimacy score from 0 to 100 based on weighted positive
    and negative signals. Starts from 0 and adds/subtracts points.

    POSITIVE SIGNALS (max ~100):
      +20  paid internship
      +15  company domain resolves (DNS check)
      +15  LinkedIn presence heuristic
      +10  clear skills listed
      +10  skills match tech keywords
      +10  realistic stipend amount
      +10  valid apply URL (starts with https, has source domain)
      +5   internship duration specified
      +5   remote flexibility

    NEGATIVE SIGNALS:
      -20  suspicious / generated company name
      -15  vague / generic role title
      -20  unpaid / certificate-only
      -15  no online footprint indicators
      -25  broken or placeholder URL
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

    # ── 1. PAID INTERNSHIP (+20 / -20) ────────────────────────────
    if paid and stipend not in ["unpaid", "none", "unspecified", ""]:
        score += 20
    elif paid:
        score += 10  # paid flag set but no explicit stipend value
    else:
        score -= 20

    # ── 2. COMPANY DNS RESOLUTION (+15) ───────────────────────────
    company_domain_ok = False
    if company and company != "unknown company" and len(company) > 2:
        domain = _infer_company_domain(company)
        if domain and _quick_dns_check(domain):
            score += 15
            company_domain_ok = True
        else:
            score += 5  # company name exists but domain didn't resolve
    else:
        score -= 15  # no company name at all

    # ── 3. LINKEDIN / ONLINE PRESENCE HEURISTIC (+15) ─────────────
    # We can't call the LinkedIn API, but we use signals as proxy:
    # known companies, long-established naming, real-sounding structure
    if company_domain_ok:
        score += 10  # if domain resolves, likely has LinkedIn too
    if len(company.split()) >= 2 and len(company) >= 5:
        score += 5   # multi-word company names tend to be real
    else:
        score -= 5

    # ── 4. SKILLS LISTED (+10) ────────────────────────────────────
    if skills and skills != "not specified" and len(skills) > 5:
        score += 10
    else:
        score -= 5

    # ── 5. TECH SKILLS MATCH (+10) ────────────────────────────────
    tech_match = False
    for kw in TECH_KEYWORDS:
        if kw in skills or kw in role:
            tech_match = True
            break
    if tech_match:
        score += 10
    else:
        score -= 5

    # ── 6. REALISTIC STIPEND (+10) ────────────────────────────────
    # Check for numeric stipend amounts (₹5000, 10000, etc.)
    has_real_amount = bool(re.search(r"\d{3,}", stipend))  # at least 3 digits
    if has_real_amount:
        score += 10

    # ── 7. VALID APPLY URL (+10 / -25) ────────────────────────────
    if apply_link.startswith("https://") and len(apply_link) > 20:
        score += 10
    elif apply_link:
        score -= 10  # has a link but it's suspicious
    else:
        score -= 25  # no link at all

    # ── 8. DURATION SPECIFIED (+5) ────────────────────────────────
    if duration and duration != "not specified" and any(c.isdigit() for c in duration):
        score += 5

    # ── 9. REMOTE FLEXIBILITY (+5) ────────────────────────────────
    if remote or "remote" in location or "wfh" in location:
        score += 5

    # ── NEGATIVE: SUSPICIOUS COMPANY NAME (-20) ──────────────────
    for pattern in SUSPICIOUS_COMPANY_PATTERNS:
        if pattern in company:
            score -= 20
            break

    # ── NEGATIVE: VAGUE / GENERIC ROLE (-15) ──────────────────────
    generic_roles = ["intern", "trainee", "candidate", "associate"]
    role_words = role.split()
    if role_words and all(w in generic_roles for w in role_words):
        score -= 15  # role is ONLY generic words like "Intern" or "Trainee"
    elif len(role) < 5:
        score -= 10  # very short role title

    # ── NEGATIVE: CERTIFICATE-ONLY / SCAM WORDING (-20) ──────────
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

    # ── BOUNDS ENFORCEMENT (0–100) ────────────────────────────────
    score = max(0, min(100, score))
    return score


def get_legitimacy_bucket(score: int) -> str:
    """
    Categorizes the legitimacy score into 5 tiers:
      90–100  →  Excellent
      75–89   →  High Confidence
      60–74   →  Good
      40–59   →  Risky
      0–39    →  Reject
    """
    if score >= 90:
        return "Excellent"
    elif score >= 75:
        return "High Confidence"
    elif score >= 60:
        return "Good"
    elif score >= 40:
        return "Risky"
    else:
        return "Reject"


# ── Internal Helpers ──────────────────────────────────────────────

def _infer_company_domain(company_name: str) -> str:
    """Infers a plausible domain from a company name for DNS lookup."""
    clean = re.sub(
        r"\b(pvt|private|ltd|limited|inc|llc|corp|corporation|co|company)\b",
        "", company_name.lower()
    )
    clean = re.sub(r"[^a-z0-9\s]", "", clean).strip()
    parts = clean.split()
    if not parts:
        return ""
    return f"{parts[0]}.com"


def _quick_dns_check(domain: str) -> bool:
    """Returns True if the domain resolves via DNS (fast, 2s timeout)."""
    try:
        socket.setdefaulttimeout(2)
        socket.getaddrinfo(domain, None)
        return True
    except (socket.gaierror, socket.timeout, OSError):
        return False
