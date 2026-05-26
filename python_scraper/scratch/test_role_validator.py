import os
import sys

# Ensure python_scraper is in Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from python_scraper.utils.validators import validate_role_quality

def run_tests():
    test_cases = [
        # (role_title, expected_pass)
        ("Operations & Data Analytics", True),
        ("Financial Data Analyst", True),
        ("Data Operations", True),
        ("SQL Developer", True),
        ("Databricks Data Engineer", True),
        ("AI Benchmark Engineer (Data Analysis)", True),
        ("Quant Analyst", True),
        ("Quantitative Analyst", True),
        ("Lead Management & Pre-Sales Analyst", False),
        ("Marketing Intern", False),
        ("Web Developer", False),
        ("Business Development Intern (non-tech)", False),
        ("Marketing Data Analyst", True),
        ("Business Development & Data Analyst", True),
    ]

    print("=" * 80)
    print("RUNNING ROLE QUALITY VALIDATOR TEST SUITE")
    print("=" * 80)

    failures = 0

    for role, expected_pass in test_cases:
        passed, reason = validate_role_quality(role)
        status = "PASS" if passed else "FAIL"
        expected_status = "PASS" if expected_pass else "FAIL"
        
        is_correct = (passed == expected_pass)
        result_symbol = "OK" if is_correct else "ERROR"
        if not is_correct:
            failures += 1

        print(f"[{result_symbol}] Role: '{role}'")
        print(f"    Expected: {expected_status} | Actual: {status}")
        print(f"    Details:\n{reason}")
        print("-" * 80)

    print("=" * 80)
    if failures == 0:
        print("ALL TESTS PASSED SUCCESSFULLY! (SUCCESS)")
        sys.exit(0)
    else:
        print(f"{failures} TEST(S) FAILED. (FAILED)")
        sys.exit(1)

if __name__ == "__main__":
    run_tests()
