"""
Deduplication Helper Utility
============================
Handles normalization of company names and role titles, generates canonical keys,
and performs fuzzy matching using rapidfuzz token sort ratio.
"""

import re
from rapidfuzz import fuzz

def normalize_company_name(name: str) -> str:
    """
    Normalizes company names for deduplication:
    - Lowercase
    - Strip common suffixes (Inc, LLC, Ltd, Private Limited, Pvt Ltd, Corporation, Technologies, Solutions, etc.)
    - Strip non-alphanumeric characters
    - Remove extra spaces
    """
    if not name:
        return ""
    name_lower = name.lower()
    
    # Suffixes to remove, ordered longest to shortest
    suffixes = [
        "private limited", "pvt ltd", "pvt. ltd.", "pvt.ltd.",
        "corporation", "technologies", "solutions", "limited", "ltd.", "ltd", 
        "inc.", "inc", "llc", "corp.", "corp", "co.", "co", "company"
    ]
    for suffix in suffixes:
        name_lower = re.sub(rf"\b{re.escape(suffix)}\b", "", name_lower)
        
    name_lower = re.sub(r"[^a-z0-9\s]", "", name_lower)
    return " ".join(name_lower.split())


def normalize_role_title(role: str) -> str:
    """
    Normalizes role titles for deduplication:
    - Lowercase
    - Strip generic qualifiers (internship, intern, co-op, coop, part-time, full-time, etc.)
    - Strip non-alphanumeric characters
    - Remove extra spaces
    """
    if not role:
        return ""
    role_lower = role.lower()
    words_to_remove = ["internship", "intern", "co-op", "coop", "temporary", "part-time", "full-time"]
    for word in words_to_remove:
        role_lower = re.sub(rf"\b{re.escape(word)}\b", "", role_lower)
        
    role_lower = re.sub(r"[^a-z0-9\s]", "", role_lower)
    return " ".join(role_lower.split())


def get_canonical_key(comp: str, role_title: str) -> str:
    """
    Generates a canonical deduplication key from company name and role title.
    """
    c = normalize_company_name(comp)
    r = normalize_role_title(role_title)
    return f"{c}||{r}"


def is_duplicate_fuzzy(comp1: str, role1: str, comp2: str, role2: str, threshold: int = 90) -> bool:
    """
    Calculates fuzzy similarity between two company name + role pairs.
    Returns True if both company name and role title match at or above the threshold.
    """
    norm_comp1 = normalize_company_name(comp1)
    norm_comp2 = normalize_company_name(comp2)
    norm_role1 = normalize_role_title(role1)
    norm_role2 = normalize_role_title(role2)
    
    # Quick exact check after normalization
    if norm_comp1 == norm_comp2 and norm_role1 == norm_role2:
        return True
        
    # If one of them is empty, they are not duplicates
    if not norm_comp1 or not norm_comp2 or not norm_role1 or not norm_role2:
        return False
        
    # Fuzzy match using token sort ratio to handle word order variations
    comp_sim = fuzz.token_sort_ratio(norm_comp1, norm_comp2)
    role_sim = fuzz.token_sort_ratio(norm_role1, norm_role2)
    
    return comp_sim >= threshold and role_sim >= threshold
