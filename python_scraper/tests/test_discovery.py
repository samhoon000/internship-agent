import sys
from pathlib import Path
import pytest

# Add the project root to sys.path to enable correct imports
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from python_scraper.utils.deduplication import get_canonical_key, is_duplicate_fuzzy
from python_scraper.scoring.scoring_service import (
    check_word_in_text,
    get_relevance_tier_and_category,
    calculate_legitimacy_score,
    get_legitimacy_bucket
)

def test_duplicate_detection():
    # Canonical keys normalization check
    key1 = get_canonical_key("Google Inc", "Software Engineer")
    key2 = get_canonical_key("Google", "Software Engineer")
    assert key1 == key2

    key3 = get_canonical_key("Microsoft Technologies Pvt Ltd", "Data Scientist")
    key4 = get_canonical_key("Microsoft", "Data Scientist")
    assert key3 == key4

    # Fuzzy duplicate matching check
    # Google Inc vs Google, Software Engineer vs Software Engineering
    assert is_duplicate_fuzzy("Google Inc", "Software Engineer", "Google", "Software Engineering")
    # Completely different companies/roles should not be duplicates
    assert not is_duplicate_fuzzy("Google", "Software Engineer", "Microsoft", "Data Scientist")


def test_exact_skill_matching():
    # Test check_word_in_text to prevent substring matching issues
    # "Java" should NOT match "JavaScript"
    assert not check_word_in_text("Java", "I am a JavaScript developer")
    # "Java" should match exact "Java"
    assert check_word_in_text("Java", "Looking for a Java developer")
    
    # "SQL" should NOT match "NoSQL"
    assert not check_word_in_text("SQL", "Experience with NoSQL databases")
    # "SQL" should match exact "SQL"
    assert check_word_in_text("SQL", "Must know SQL databases")

    # Handles C++ or similar exact words with punctuation
    assert check_word_in_text("C++", "C++ Developer position")
    assert not check_word_in_text("C", "Looking for C++ developer")


def test_relevance_scoring():
    # Highly relevant Data/AI role
    score, tier, cat = get_relevance_tier_and_category(
        title="Data Scientist Intern",
        skills="Python, SQL, Machine Learning",
        description="We are hiring a Data Scientist intern to work on ML models.",
        company_domain="google.com",
        source="YC Jobs"
    )
    assert cat == "Data/AI"
    assert tier == "HIGHLY_RELEVANT"
    assert score >= 80

    # Software Engineering role
    score, tier, cat = get_relevance_tier_and_category(
        title="Full Stack Software Developer",
        skills="React, Node, JavaScript",
        description="Build awesome web apps.",
        company_domain="netflix.com",
        source="Wellfound"
    )
    assert cat == "Software"
    assert score >= 60

    # Hard exclusion check (HR, sales)
    score, tier, cat = get_relevance_tier_and_category(
        title="HR Manager Internship",
        skills="Communication, Recruiting",
        description="Manage human resources operations.",
        company_domain="test.com"
    )
    assert cat == "Other"
    assert tier == "IRRELEVANT"
    assert score == 0


def test_legitimacy_scoring():
    # High confidence paid role
    dummy_item = {
        "role": "Data Analyst Intern",
        "company_name": "Stripe",
        "stipend": "₹25,000 / Month",
        "paid": True,
        "location": "Bangalore",
        "remote": False,
        "duration": "3 Months",
        "skills": "SQL, Python, Excel",
        "apply_link": "https://stripe.com/jobs/apply/data-analyst",
        "source": "Wellfound"
    }
    
    score = calculate_legitimacy_score(dummy_item)
    bucket = get_legitimacy_bucket(score)
    assert score >= 60
    assert bucket in ["MEDIUM_CONFIDENCE", "HIGH_CONFIDENCE"]

    # Low confidence role with scam keywords and unpaid status
    scam_item = {
        "role": "Intern",
        "company_name": "Vague Systems",
        "stipend": "Unpaid training",
        "paid": False,
        "location": "Remote",
        "remote": True,
        "duration": "1 Month",
        "skills": "None",
        "apply_link": "http://short.url",
        "source": "Internshala"
    }
    
    score_scam = calculate_legitimacy_score(scam_item)
    bucket_scam = get_legitimacy_bucket(score_scam)
    assert score_scam < 45
    assert bucket_scam == "REJECT"
