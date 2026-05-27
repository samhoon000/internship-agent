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
from urllib.parse import urlparse

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


# ─────────────────────────────────────────────────────────────────────
# STAGE 1 — URL VALIDATION
# ─────────────────────────────────────────────────────────────────────

def validate_url(apply_link: str, source: str, check_liveness: bool = True) -> tuple[bool, str]:
    """
    Validates that the apply_link:
      - starts with https://
      - belongs to the correct source domain
      - responds with HTTP 200 or a valid redirect (3xx → 200) [optional]
      - is not a dead link, redirect loop, or placeholder
    """
    if not apply_link or not apply_link.strip():
        return False, "apply_link is empty"

    link = apply_link.strip()

    # Must start with https://
    if not link.startswith("https://"):
        return False, f"apply_link does not start with https:// -> {link}"

    # Domain must match source
    allowed_domains = SOURCE_DOMAIN_MAP.get(source, [])
    if allowed_domains:
        parsed = urlparse(link)
        hostname = parsed.hostname or ""
        domain_match = any(domain in hostname for domain in allowed_domains)
        if not domain_match:
            return False, f"apply_link domain '{hostname}' does not match source '{source}' (expected: {allowed_domains})"

    # Reject obvious placeholder URLs
    placeholder_slugs = [
        "example.com", "placeholder", "test.com", "dummy",
        "localhost", "127.0.0.1", "fake", "sample",
    ]
    link_lower = link.lower()
    for slug in placeholder_slugs:
        if slug in link_lower:
            return False, f"apply_link contains placeholder slug: '{slug}'"

    if not check_liveness:
        return True, "URL structure is valid"

    # HTTP HEAD check for liveness
    try:
        resp = requests.head(
            link,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
        )
        if resp.status_code == 200:
            return True, "URL is live (200)"
        elif 300 <= resp.status_code < 400:
            return True, f"URL redirects ({resp.status_code}) - accepted"
        elif resp.status_code == 403:
            # Some sites block HEAD but page exists; accept with caution
            return True, "URL returned 403 (may be access-restricted but exists)"
        elif resp.status_code == 404:
            return False, "URL returned 404 - dead link"
        else:
            return False, f"URL returned unexpected status {resp.status_code}"
    except requests.exceptions.TooManyRedirects:
        return False, "URL has a redirect loop"
    except requests.exceptions.ConnectionError:
        return False, "URL connection failed — host unreachable"
    except requests.exceptions.Timeout:
        return False, "URL timed out"
    except Exception as e:
        return False, f"URL check error: {e}"


# ─────────────────────────────────────────────────────────────────────
# STAGE 2 — COMPANY LEGITIMACY
# ─────────────────────────────────────────────────────────────────────

def validate_company(company_name: str) -> tuple[bool, str]:
    """
    Heuristic-based company legitimacy check:
      - Rejects known suspicious / generated company name patterns
      - Checks for extremely short or generic names
      - Optionally checks if the company domain resolves via DNS
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

    # Check for generic naming patterns (e.g., "XYZ Technologies", "ABC Solutions")
    generic_suffixes = [
        r"\b(?:pvt|private)\s*(?:ltd|limited)\b",  # common but not inherently suspicious
    ]
    # These alone aren't suspicious, but combined with very generic prefixes they are
    generic_prefixes_re = r"^(?:the\s+)?(?:[a-z]{1,4}\s+)?(?:tech|digital|global|smart|next|future|cyber|virtual|cloud)\s+"
    if re.search(generic_prefixes_re, name_lower) and len(name.split()) <= 3:
        return False, f"company_name looks generically generated: '{name}'"

    # DNS check — try to resolve a plausible domain
    # This is a lightweight heuristic, not a definitive check.
    domain_candidate = _infer_domain(name)
    if domain_candidate:
        domain_resolves = _check_dns(domain_candidate)
        if domain_resolves:
            return True, f"company '{name}' — domain '{domain_candidate}' resolves"

    # If we can't verify via DNS, accept with a note (don't reject just because DNS fails)
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

def validate_role_quality(role: str) -> tuple[bool, str]:
    """
    Ensures the role is a legitimate tech/data internship using weighted scoring.
    """
    if not role or not role.strip():
        return False, "role is empty"

    role_lower = role.strip().lower()
    score = 0
    matched_whitelist = []
    matched_context = []
    matched_hard_exclude = []
    matched_soft_exclude = []

    def matches_keyword(keyword: str, text: str) -> bool:
        if len(keyword) <= 3 and keyword.isalnum():
            pattern = rf"\b{re.escape(keyword)}\b"
            return bool(re.search(pattern, text))
        return keyword in text

    # 1. Whitelist matches (sorted by length descending to prevent double-counting)
    sorted_whitelist = sorted(ROLE_WHITELIST_KEYWORDS, key=len, reverse=True)
    for kw in sorted_whitelist:
        if matches_keyword(kw, role_lower):
            if not any(kw in matched for matched in matched_whitelist):
                matched_whitelist.append(kw)

    # 2. Context matches (only if not a substring of a matched whitelist term)
    for kw in ROLE_CONTEXT_KEYWORDS:
        if matches_keyword(kw, role_lower):
            if not any(kw in matched for matched in matched_whitelist):
                matched_context.append(kw)

    # Context presence flag (if any whitelist or context keyword matched)
    context_present = len(matched_whitelist) > 0 or len(matched_context) > 0

    # 3. Exclusions
    for kw in ROLE_HARD_EXCLUDE_KEYWORDS:
        if matches_keyword(kw, role_lower):
            matched_hard_exclude.append(kw)

    for kw in ROLE_SOFT_EXCLUDE_KEYWORDS:
        if matches_keyword(kw, role_lower):
            matched_soft_exclude.append(kw)

    # 4. Calculate score
    whitelist_score = len(matched_whitelist) * 30
    context_score = len(matched_context) * 15

    hard_exclude_penalty = 0
    for kw in matched_hard_exclude:
        penalty = 10 if context_present else 25
        hard_exclude_penalty += penalty

    soft_exclude_penalty = 0
    for kw in matched_soft_exclude:
        penalty = 5 if context_present else 15
        soft_exclude_penalty += penalty

    score = whitelist_score + context_score - hard_exclude_penalty - soft_exclude_penalty

    threshold = 10
    passed = score >= threshold
    decision = "PASSED" if passed else "FAILED"

    reason = (
        f"Role quality check {decision} with score {score} (threshold: {threshold}).\n"
        f"  - Whitelist Matches (+30/ea): {matched_whitelist} -> +{whitelist_score}\n"
        f"  - Context Matches (+15/ea): {matched_context} -> +{context_score}\n"
        f"  - Hard Exclusions (-25 or -10/ea): {matched_hard_exclude} -> -{hard_exclude_penalty} (context present: {context_present})\n"
        f"  - Soft Exclusions (-15 or -5/ea): {matched_soft_exclude} -> -{soft_exclude_penalty} (context present: {context_present})"
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
    ok, reason = validate_role_quality(item.get("role", ""))
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
    ok, reason = validate_url(item.get("apply_link", ""), item.get("source", ""), check_liveness=check_liveness)
    if not ok:
        failures.append(f"[URL] {reason}")
    else:
        notes.append(f"[URL] {reason}")

    if failures:
        return False, failures
    return True, notes
