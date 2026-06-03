"""
Production Data Validation Pipeline
====================================
Every scraped internship MUST pass all 5 validation stages before it can be
considered for SQL insertion. If any stage fails, the internship is rejected
and the reason is logged.

Stages:
  1. URL Validation    — apply_link must be live and match source domain
  2. Company Legitimacy — company name must not be suspicious / generated
  3. Role Quality       — only tech roles allowed
  4. Payment Check      — must be paid (reject unpaid / cert-only)
  5. Data Completeness  — all required fields present
"""

import re
import logging
import socket
import requests
import json
from pathlib import Path
from collections import Counter
from urllib.parse import urlparse
from rapidfuzz import fuzz

from python_scraper.config import (
    SOURCE_DOMAIN_MAP,
    SUSPICIOUS_COMPANY_PATTERNS,
    ROLE_WHITELIST_KEYWORDS,
    ROLE_CONTEXT_KEYWORDS,
    ROLE_HARD_EXCLUDE_KEYWORDS,
    ROLE_SOFT_EXCLUDE_KEYWORDS,
    REQUEST_TIMEOUT,
)

logger = logging.getLogger("python_scraper.validators")

REJECTION_REASONS_COUNTER = Counter()

def log_rejection(company: str, role: str, score: int, reasons: list[str]):
    """
    Logs a rejected internship in JSON format to a file and updates the rejection reasons counter.
    """
    simplified_reasons = []
    for r in reasons:
        r_lower = r.lower()
        if "completeness" in r_lower or "missing required fields" in r_lower:
            simplified_reasons.append("Missing Critical Fields")
        elif "role" in r_lower or "relevance" in r_lower:
            simplified_reasons.append("Low Relevance / Excluded Role")
        elif "company" in r_lower or "suspicious" in r_lower:
            simplified_reasons.append("Suspicious / Invalid Company")
        elif "payment" in r_lower or "unpaid" in r_lower or "commission" in r_lower:
            simplified_reasons.append("Unpaid / Certificate Only")
        elif "url" in r_lower or "liveness" in r_lower or "dead link" in r_lower:
            simplified_reasons.append("Invalid / Dead URL")
        elif "score" in r_lower or "threshold" in r_lower:
            simplified_reasons.append("Legitimacy Score Below Threshold")
        elif "duplicate" in r_lower:
            simplified_reasons.append("Duplicate")
        else:
            simplified_reasons.append("Other Rejection Reason")

    for sr in simplified_reasons:
        REJECTION_REASONS_COUNTER[sr] += 1

    log_entry = {
        "company": company or "Unknown Company",
        "role": role or "Unknown Role",
        "score": score,
        "accepted": False,
        "reasons": reasons
    }

    rejections_file = Path(__file__).resolve().parent.parent / "rejections.jsonl"
    try:
        # Create directories if they do not exist (defensive design)
        rejections_file.parent.mkdir(parents=True, exist_ok=True)
        with open(rejections_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        logger.error(f"Failed to write rejection log entry: {e}")

    logger.info(f"[REJECTION LOG] {json.dumps(log_entry)}")



# ─────────────────────────────────────────────────────────────────────
# STAGE 1 — URL VALIDATION
# ─────────────────────────────────────────────────────────────────────

def validate_url(apply_link: str, source: str, check_liveness: bool = True) -> tuple[bool, str, str]:
    """
    Validates that the apply_link:
      - starts with https://
      - belongs to the correct source domain
      - responds with HTTP 200 or a valid redirect (3xx → 200) [optional]
      - is not a dead link, redirect loop, or placeholder
    """
    if not apply_link or not apply_link.strip():
        return False, "apply_link is empty", ""

    link = apply_link.strip()

    # Must start with https://
    if not link.startswith("https://"):
        return False, f"apply_link does not start with https:// -> {link}", ""

    # Domain must match source
    allowed_domains = SOURCE_DOMAIN_MAP.get(source, [])
    if allowed_domains:
        parsed = urlparse(link)
        hostname = parsed.hostname or ""
        domain_match = any(domain in hostname for domain in allowed_domains)
        if not domain_match:
            return False, f"apply_link domain '{hostname}' does not match source '{source}' (expected: {allowed_domains})", ""

    # Reject obvious placeholder URLs
    placeholder_slugs = [
        "example.com", "placeholder", "test.com", "dummy",
        "localhost", "127.0.0.1", "fake", "sample",
    ]
    link_lower = link.lower()
    for slug in placeholder_slugs:
        if slug in link_lower:
            return False, f"apply_link contains placeholder slug: '{slug}'", ""

    if not check_liveness:
        return True, "URL structure is valid", ""

    # HTTP GET check for liveness & content retrieval
    try:
        resp = requests.get(
            link,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            },
        )
        html_content = resp.text if resp.status_code == 200 else ""
        if resp.status_code == 200:
            return True, "URL is live (200)", html_content
        elif 300 <= resp.status_code < 400:
            return True, f"URL redirects ({resp.status_code}) - accepted", html_content
        elif resp.status_code in [401, 403, 405, 406]:
            # Some sites block GET but page exists; accept with caution
            return True, f"URL returned {resp.status_code} (access-restricted but exists)", html_content
        elif resp.status_code == 404:
            return False, "URL returned 404 - dead link", ""
        else:
            return False, f"URL returned unexpected status {resp.status_code}", ""
    except requests.exceptions.TooManyRedirects:
        return False, "URL has a redirect loop", ""
    except requests.exceptions.ConnectionError:
        return False, "URL connection failed — host unreachable", ""
    except requests.exceptions.Timeout:
        return False, "URL timed out", ""
    except Exception as e:
        return False, f"URL check error: {e}", ""


# ─────────────────────────────────────────────────────────────────────
# STAGE 2 — COMPANY LEGITIMACY
# ─────────────────────────────────────────────────────────────────────

def validate_company(company_name: str) -> tuple[bool, str]:
    """
    Heuristic-based company legitimacy check:
      - Rejects known suspicious / generated company name patterns
      - Checks for extremely short or generic names
      - Uses DNS resolution as a verification signal for warning-flagged generic names
    """
    if not company_name or not company_name.strip():
        return False, "company_name is empty"

    name = company_name.strip()
    name_lower = name.lower()

    # Reject very short names (likely garbage data)
    if len(name) < 3:
        return False, f"company_name too short: '{name}'"

    # Check against suspicious patterns
    for pattern in SUSPICIOUS_COMPANY_PATTERNS:
        if pattern in name_lower:
            return False, f"company_name matches suspicious pattern: '{pattern}' in '{name}'"

    # Infer domain and verify DNS resolution
    domain_candidate = _infer_domain(name)
    domain_resolves = False
    if domain_candidate:
        domain_resolves = _check_dns(domain_candidate)

    # Check for warning keywords (solutions, technologies, labs, innovation, innovations, digital, systems)
    warning_words = ["solutions", "technologies", "labs", "innovation", "innovations", "digital", "systems"]
    has_warning = any(w in name_lower for w in warning_words)

    if has_warning:
        return True, f"company '{name}' contains warning keyword (accepted, bypassing strict checks)"

    # Check for generic naming patterns (e.g., "XYZ Technologies", "ABC Solutions")
    generic_prefixes_re = r"^(?:the\s+)?(?:[a-z]{1,4}\s+)?(?:tech|digital|global|smart|next|future|cyber|virtual|cloud)\s+"
    is_generic_pattern = bool(re.search(generic_prefixes_re, name_lower) and len(name.split()) <= 3)

    if is_generic_pattern:
        if domain_resolves:
            return True, f"company '{name}' contains generic pattern but verified via DNS resolving: '{domain_candidate}'"
        else:
            return False, f"company_name looks generically generated and failed DNS validation: '{name}'"

    if domain_resolves:
        return True, f"company '{name}' — domain '{domain_candidate}' resolves"

    # If we can't verify via DNS but it's not a generic pattern or strict placeholder, accept it
    return True, f"company '{name}' — accepted (no DNS verification available)"


def _infer_domain(company_name: str) -> str:
    """Infers a plausible domain name from a company name for DNS resolution check."""
    # Remove common suffixes
    clean = re.sub(r"\b(pvt|private|ltd|limited|inc|llc|corp|corporation|co|company)\b", "", company_name.lower())
    clean = re.sub(r"[^a-z0-9\s]", "", clean).strip()
    parts = clean.split()
    if not parts:
        return ""
    # Try the simplest domain: firstword.com
    return f"{parts[0]}.com"


from functools import lru_cache

@lru_cache(maxsize=1024)
def _check_dns(domain: str) -> bool:
    """Returns True if the domain resolves via DNS."""
    try:
        socket.setdefaulttimeout(3)
        socket.getaddrinfo(domain, None)
        return True
    except (socket.gaierror, socket.timeout, OSError):
        return False


# ─────────────────────────────────────────────────────────────────────
# STAGE 3 — ROLE QUALITY
# ─────────────────────────────────────────────────────────────────────

def validate_role_quality(role: str, item: dict = None) -> tuple[bool, str]:
    """
    Ensures the role is a legitimate tech/data internship using fuzzy keyword matching and weighted confidence tiers.
    """
    if not role or not role.strip():
        if item is not None:
            item['confidence'] = 'REJECT'
        return False, "role is empty"

    role_lower = role.strip().lower()
    # Normalize separators (replace hyphens, slashes, brackets, etc. with space) for fuzzy matching
    role_norm = re.sub(r'[-/_+:,()\[\]\s]+', ' ', role_lower)
    role_norm = ' '.join(role_norm.split())

    matched_whitelist = []
    matched_context = []
    matched_hard_exclude = []
    matched_soft_exclude = []

    def matches_keyword(keyword: str, text: str) -> bool:
        if len(keyword) <= 3 and keyword.isalnum():
            pattern = rf"\b{re.escape(keyword)}\b"
            return bool(re.search(pattern, text))
        
        # Exact substring match
        if keyword in text:
            return True
            
        # Fuzzy match using partial ratio (helps match data-analysis to data analysis, etc.)
        if fuzz.partial_ratio(keyword, text) >= 90:
            return True
            
        return False

    # 1. Whitelist matches (sorted by length descending to prevent double-counting)
    sorted_whitelist = sorted(ROLE_WHITELIST_KEYWORDS, key=len, reverse=True)
    for kw in sorted_whitelist:
        if matches_keyword(kw, role_lower) or matches_keyword(kw, role_norm):
            if not any(kw in matched for matched in matched_whitelist):
                matched_whitelist.append(kw)

    # Override keywords checking
    override_keywords = [
        "mis analyst", "data analyst", "ai engineer", "ml engineer", "machine learning",
        "business intelligence", "data science", "data scientist", "data engineering",
        "data engineer", "artificial intelligence", "ai research", "quantitative research",
        "research analyst"
    ]
    has_override = False
    for kw in override_keywords:
        if matches_keyword(kw, role_lower) or matches_keyword(kw, role_norm):
            has_override = True
            if kw not in matched_whitelist:
                matched_whitelist.append(kw)

    # 2. Context matches
    for kw in ROLE_CONTEXT_KEYWORDS:
        if matches_keyword(kw, role_lower) or matches_keyword(kw, role_norm):
            if not any(kw in matched for matched in matched_whitelist):
                matched_context.append(kw)

    # 3. Exclusions (skipped if overridden by a strong whitelist keyword)
    if not has_override:
        for kw in ROLE_HARD_EXCLUDE_KEYWORDS:
            if matches_keyword(kw, role_lower) or matches_keyword(kw, role_norm):
                # Check if this exclusion is balanced by a strong whitelisted keyword
                # E.g., "Marketing Analytics Intern" contains hard exclude "marketing" and whitelist "analytics"
                is_balanced = False
                for wl in matched_whitelist:
                    if "analytics" in wl or "data" in wl or "science" in wl:
                        is_balanced = True
                if not is_balanced:
                    matched_hard_exclude.append(kw)

        for kw in ROLE_SOFT_EXCLUDE_KEYWORDS:
            if matches_keyword(kw, role_lower) or matches_keyword(kw, role_norm):
                is_balanced = False
                for wl in matched_whitelist:
                    if "analytics" in wl or "data" in wl or "science" in wl:
                        is_balanced = True
                if not is_balanced:
                    matched_soft_exclude.append(kw)

    # 4. Classify confidence tier
    has_whitelist = len(matched_whitelist) > 0
    has_hard_exclude = len(matched_hard_exclude) > 0
    has_soft_exclude = len(matched_soft_exclude) > 0

    if has_hard_exclude:
        # If there's a hard exclusion that isn't overridden/balanced, reject it
        confidence = "REJECT"
    elif has_whitelist and not has_soft_exclude:
        # Direct whitelist match with no soft exclusions -> HIGH confidence
        confidence = "HIGH"
    elif has_whitelist:
        # Whitelisted but has some soft exclusions -> MEDIUM confidence
        confidence = "MEDIUM"
    else:
        # Vague role title without hard exclusions -> NEEDS_RESCUE (which triggers description check)
        confidence = "NEEDS_RESCUE"

    if item is not None:
        item['confidence'] = confidence

    # Validation succeeds if confidence is HIGH, MEDIUM, or NEEDS_RESCUE
    passed = confidence in ["HIGH", "MEDIUM", "NEEDS_RESCUE"]
    decision = "PASSED" if passed else "FAILED"
    
    reason = (
        f"Role quality check {decision} with confidence tier {confidence}.\n"
        f"  - Whitelist Matches: {matched_whitelist}\n"
        f"  - Context Matches: {matched_context}\n"
        f"  - Hard Exclusions: {matched_hard_exclude}\n"
        f"  - Soft Exclusions: {matched_soft_exclude}"
    )

    return passed, reason


# ─────────────────────────────────────────────────────────────────────
# STAGE 4 — PAYMENT CHECK
# ─────────────────────────────────────────────────────────────────────

def validate_payment(paid: bool, stipend: str) -> tuple[bool, str]:
    """
    Rejects:
      - Unpaid internships
      - Certificate-only internships
      - Commission-based internships
    Accepts if stipend has real monetary value or paid flag is True.
    """
    stipend_lower = (stipend or "").lower().strip()

    # Explicit rejection patterns
    reject_patterns = [
        "unpaid", "certificate only", "certificate-only", "cert only",
        "commission", "commission based", "commission-based",
        "volunteer", "free", "no stipend", "nil", "training fee",
        "pay for training", "registration fee", "security deposit",
    ]
    for pat in reject_patterns:
        if pat in stipend_lower:
            return False, f"stipend indicates non-paid opportunity: '{stipend}'"

    # If explicitly paid with a real stipend
    if paid and stipend_lower not in ["unspecified", "none", "", "unpaid"]:
        return True, f"paid=True, stipend='{stipend}'"

    # If paid flag is true even without explicit stipend text
    if paid:
        return True, "paid=True (stipend unspecified but marked as paid)"

    # If stipend has numeric value (non-zero)
    has_non_zero_digits = any(c.isdigit() and c != '0' for c in stipend_lower)
    if has_non_zero_digits:
        return True, f"stipend has monetary value: '{stipend}'"

    # If stipend contains explicit paid indicators (after excluding reject patterns)
    paid_indicators = ["stipend", "salary", "competitive", "negotiable", "best in", "industry standard", "market standard", "paid", "allowance", "reimbursement", "incentive"]
    if any(ind in stipend_lower for ind in paid_indicators):
        return True, f"stipend contains paid indicator: '{stipend}'"

    # Unpaid / unknown
    return False, f"internship appears unpaid (paid={paid}, stipend='{stipend}')"


# ─────────────────────────────────────────────────────────────────────
# STAGE 5 — DATA COMPLETENESS
# ─────────────────────────────────────────────────────────────────────

def validate_data_completeness(item: dict) -> tuple[bool, str]:
    """
    Rejects internships missing critical fields:
      - company_name
      - role
      - apply_link
      - source
    """
    missing = []
    for field in ["company_name", "role", "apply_link", "source"]:
        val = item.get(field, "")
        if not val or not str(val).strip():
            missing.append(field)

    if missing:
        return False, f"missing required fields: {', '.join(missing)}"

    return True, "all required fields present"


# ─────────────────────────────────────────────────────────────────────
# MASTER VALIDATION PIPELINE
# ─────────────────────────────────────────────────────────────────────

def run_validation_pipeline(item: dict, check_liveness: bool = True) -> tuple[bool, list[str]]:
    """
    Runs all 5 validation stages on a single internship dict.

    Returns:
        (passed: bool, reasons: list[str])
        - If passed is True, all validations succeeded. reasons contains success notes.
        - If passed is False, at least one validation failed. reasons contains failure details.
    """
    failures = []
    notes = []

    # Stage 1: Data completeness (run first — no point checking other things if data is missing)
    ok, reason = validate_data_completeness(item)
    if not ok:
        failures.append(f"[COMPLETENESS] {reason}")
    else:
        notes.append(f"[COMPLETENESS] {reason}")

    # Stage 2: Role quality
    ok, reason = validate_role_quality(item.get("role", ""), item)
    if not ok:
        failures.append(f"[ROLE] {reason}")
    else:
        notes.append(f"[ROLE] {reason}")

    # Stage 3: Company legitimacy
    ok, reason = validate_company(item.get("company_name", ""))
    if not ok:
        failures.append(f"[COMPANY] {reason}")
    else:
        notes.append(f"[COMPANY] {reason}")

    # Stage 4: Payment check
    ok, reason = validate_payment(item.get("paid", False), item.get("stipend", ""))
    if not ok:
        failures.append(f"[PAYMENT] {reason}")
    else:
        notes.append(f"[PAYMENT] {reason}")

    # Stage 5: URL validation (most expensive — run last)
    ok, reason, html = validate_url(item.get("apply_link", ""), item.get("source", ""), check_liveness=check_liveness)
    if not ok:
        failures.append(f"[URL] {reason}")
    else:
        notes.append(f"[URL] {reason}")

    if failures:
        return False, failures
    return True, notes


def calculate_relevance_score(title: str, skills: str, description: str) -> int:
    """
    Calculates role relevance score based on title, skills, and description.
    Returns an integer from 0 to 100.
    """
    if not title:
        return 0
        
    title_lower = title.lower()
    skills_lower = (skills or "").lower()
    desc_lower = (description or "").lower()
    
    # Check override keywords first to bypass hard exclusions
    override_keywords = [
        "mis analyst", "data analyst", "ai engineer", "ml engineer", "machine learning",
        "business intelligence", "data science", "data scientist", "data engineering",
        "data engineer", "artificial intelligence", "ai research", "quantitative research",
        "research analyst"
    ]
    has_override = False
    norm_title = re.sub(r'[-/_+:,()\[\]\s]+', ' ', title_lower)
    norm_title = ' '.join(norm_title.split())
    for kw in override_keywords:
        if len(kw) <= 3 and kw.isalnum():
            pattern = rf"\b{re.escape(kw)}\b"
            if re.search(pattern, title_lower) or re.search(pattern, norm_title):
                has_override = True
                break
        else:
            if kw in title_lower or kw in norm_title:
                has_override = True
                break
            if fuzz.partial_ratio(kw, title_lower) >= 90 or fuzz.partial_ratio(kw, norm_title) >= 90:
                has_override = True
                break

    # 1. Hard Excludes Check (Title-based)
    # If title contains any of the hard exclusions, relevance is 0
    if not has_override:
        from python_scraper.config import ROLE_HARD_EXCLUDE_KEYWORDS
        for kw in ROLE_HARD_EXCLUDE_KEYWORDS:
            # Use word boundary matching
            pattern = rf"\b{re.escape(kw)}\b"
            if re.search(pattern, title_lower):
                return 0
            
    # 2. Positive Keyword Matching
    # Title Score (Max 60)
    title_score = 10
    
    # Analyst / BI / Reporting / Business Analyst
    analyst_keywords = ["data analyst", "business analyst", "analytics", "bi analyst", "reporting analyst", "business intelligence", "mis analyst", "mis executive"]
    science_keywords = ["data science", "data scientist", "machine learning", "ai", "predictive modeling"]
    engineer_keywords = ["data engineer", "etl", "sql developer", "database"]
    core_tools = ["data", "analyst", "python", "sql", "excel", "tableau", "power bi"]
    
    if any(kw in title_lower for kw in analyst_keywords):
        title_score = 60
    elif any(kw in title_lower for kw in science_keywords):
        title_score = 60
    elif any(kw in title_lower for kw in engineer_keywords):
        title_score = 50
    elif any(kw in title_lower for kw in core_tools):
        title_score = 40
        
    # Skills Score (Max 30)
    # Score 10 points per matching core skill, up to 30
    skills_score = 0
    core_skills = ["python", "sql", "excel", "power bi", "tableau", "pandas", "numpy", "sklearn", "machine learning", "data science", "database", "bi", "analytics", "reporting"]
    
    # Split skills by comma
    skills_list = [s.strip() for s in skills_lower.split(",") if s.strip()]
    matched_skills = set()
    for s in skills_list:
        for cs in core_skills:
            if cs in s:
                matched_skills.add(cs)
                
    skills_score = min(30, len(matched_skills) * 10)
    
    # Description Score (Max 20)
    # Score 5 points per matching core tool/keyword in description, up to 20
    desc_score = 0
    if desc_lower:
        matched_desc = set()
        for kw in core_skills + analyst_keywords + science_keywords:
            if kw in desc_lower:
                matched_desc.add(kw)
        desc_score = min(20, len(matched_desc) * 5)
        
    return title_score + skills_score + desc_score

