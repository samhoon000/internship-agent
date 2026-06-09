import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from python_scraper.database.db import DBExistenceChecker, save_internships
from python_scraper.database.models import Internship

def test_db_existence_checker_caching_and_indexed_lookup():
    """
    Verifies that DBExistenceChecker performs an indexed lookup by Primary Key (apply_link)
    and caches the result to avoid redundant database calls.
    """
    checker = DBExistenceChecker()
    mock_session = MagicMock()
    mock_query = mock_session.query.return_value
    mock_filter = mock_query.filter.return_value
    
    # First call: link exists in DB
    mock_filter.first.return_value = ("https://example.com/apply/1",)
    
    with patch("python_scraper.database.db.Session", return_value=mock_session):
        # Trigger DB lookup
        assert "https://example.com/apply/1" in checker
        # Trigger cache lookup (no database call should be made)
        assert "https://example.com/apply/1" in checker

    # Verify query was executed exactly once for this URL
    assert mock_session.query.call_count == 1
    mock_session.query.assert_called_with(Internship.apply_link)


def test_save_internships_targeted_query():
    """
    Verifies that save_internships executes a selective B-tree range query 
    using the batch's apply_links and company name prefixes, rather than 
    loading all records via session.query(Internship).all().
    """
    mock_session = MagicMock()
    mock_query = mock_session.query.return_value
    mock_filter = mock_query.filter.return_value
    
    # Return empty list from candidate lookup (no duplicates exist)
    mock_filter.all.return_value = []
    
    test_batch = [
        {"apply_link": "https://example.com/apply/1", "company_name": "Google", "role": "Data Analyst Intern", "legitimacy_score": 80},
        {"apply_link": "https://example.com/apply/2", "company_name": "Stripe Inc", "role": "Software Intern", "legitimacy_score": 75}
    ]

    with patch("python_scraper.database.db.get_db_session", return_value=mock_session), \
         patch("python_scraper.database.db.Session", return_value=mock_session):
        
        save_internships(test_batch)

    # Verify query was called
    assert mock_session.query.call_count == 1
    # Verify filter was applied instead of retrieving all records
    assert mock_query.filter.call_count == 1
    
    # Verify the query was made on the Internship model
    mock_session.query.assert_called_with(Internship)
