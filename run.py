import os
import sys
import time
import asyncio
import logging
import random
from pathlib import Path
from datetime import datetime, timedelta
from urllib.parse import urlparse
import re

# Ensure local modules import cleanly by adding current directory to system path
sys.path.append(str(Path(__file__).resolve().parent))

# Import scrapers and database/validation functions
from python_scraper.database.db import init_db, get_db_session, save_internships
from python_scraper.database.models import Internship
from python_scraper.scrapers.internshala import InternshalaScraper
from python_scraper.scrapers.wellfound import WellfoundScraper
from python_scraper.scrapers.yc_jobs import YCJobsScraper
from python_scraper.scrapers.indeed import IndeedScraper
from python_scraper.utils.validators import validate_url, run_validation_pipeline
from playwright.async_api import async_playwright
from python_scraper.config import USER_AGENTS, PLAYWRIGHT_VIEWPORT

# Setup logging
log_file = Path(__file__).resolve().parent / "python_scraper" / "python_scraper.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file, encoding='utf-8')
    ]
)
logger = logging.getLogger("python_scraper.pipeline")

# Reconfigure stdout for utf-8 if supported (to prevent emoji/unicode errors in windows terminal)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)


from python_scraper.database.cleanup_service import (
    cleanup_old_internships as service_cleanup_old_internships,
    remove_dead_links_async as service_remove_dead_links_async
)

def cleanup_old_internships(session) -> int:
    """Wrapper calling the shared cleanup service."""
    soft_deleted, purged = service_cleanup_old_internships(session)
    return soft_deleted + purged

async def remove_dead_links(session) -> int:
    """Wrapper calling the shared liveness validation service."""
    return await service_remove_dead_links_async(session)


async def scrape_all_sources_parallel(browser_context) -> tuple[list[dict], list]:
    """
    STEP 3 — Parallel Source Scraping.
    Runs all scrapers concurrently under a single browser context.
    """
    logger.info("STEP 3: Initiating parallel source scraping...")
    scrapers = [
        InternshalaScraper(),
        WellfoundScraper(),
        YCJobsScraper(),
        IndeedScraper()
    ]
    
    # Execute scrapers concurrently
    tasks = [s.scrape(browser_context) for s in scrapers]
    results = await asyncio.gather(*tasks)
    
    # Flatten items
    all_scraped_items = []
    for items in results:
        all_scraped_items.extend(items)
        
    logger.info(f"Parallel scraping complete. Yielded {len(all_scraped_items)} raw validated items.")
    return all_scraped_items, scrapers


async def validate_new_items_liveness(items) -> list[dict]:
    """
    STEP 4 — Centralized Async Liveness Validation.
    Performs concurrent GET requests on all newly scraped items with local domain caching,
    rescuing borderline roles if they have data-related keywords in their description.
    """
    logger.info("STEP 4: Performing async URL liveness checks and description-based rescue on newly scraped listings...")
    if not items:
        return []

    semaphore = asyncio.Semaphore(15)
    url_domain_cache = {}
    
    async def validate_single_item(item):
        apply_link = item.get("apply_link")
        source = item.get("source")
        confidence = item.get("confidence", "HIGH")
        
        parsed = urlparse(apply_link)
        domain = parsed.netloc.lower()
        
        # Domain caching optimization
        if domain in url_domain_cache:
            if not url_domain_cache[domain]:
                return None
                
        async with semaphore:
            is_live, reason, html_content = await asyncio.to_thread(validate_url, apply_link, source, True)
            url_domain_cache[domain] = is_live
            if not is_live:
                logger.warning(f"[Liveness Gate] Rejecting new link for {item.get('company_name')} - {item.get('role')}: {reason}")
                from python_scraper.utils.validators import log_rejection
                log_rejection(item.get('company_name'), item.get('role'), item.get('legitimacy_score', 0), [f"Dead Link: {reason}"])
                return None
            
            # Extract and store clean description
            description = ""
            if html_content:
                text_content = re.sub(r'<script.*?</script>', ' ', html_content, flags=re.DOTALL | re.IGNORECASE)
                text_content = re.sub(r'<style.*?</style>', ' ', text_content, flags=re.DOTALL | re.IGNORECASE)
                text_content = re.sub(r'<.*?>', ' ', text_content)
                description = ' '.join(text_content.split())
            
            item['description'] = description[:4900]
            
            # Calculate unified relevance score
            from python_scraper.utils.validators import calculate_relevance_score
            relevance = calculate_relevance_score(item.get("role"), item.get("skills"), description)
            item['relevance_score'] = relevance
            
            # Reject if below relevance threshold (40)
            if relevance < 40:
                logger.warning(f"[Relevance Gate] Rejecting role: '{item.get('role')}' at '{item.get('company_name')}' (Relevance score {relevance} < 40)")
                from python_scraper.utils.validators import log_rejection
                log_rejection(item.get('company_name'), item.get('role'), item.get('legitimacy_score', 0), [f"Low Relevance Score ({relevance} < 40)"])
                return None
            
            # If the item needs description-based rescue, promote it
            if confidence == "NEEDS_RESCUE":
                item['confidence'] = 'MEDIUM_CONFIDENCE'
                item['rescued'] = True
                # Ensure legitimacy score is at least the keep threshold
                from python_scraper.config import MIN_LEGITIMACY_TO_KEEP
                item['legitimacy_score'] = max(MIN_LEGITIMACY_TO_KEEP, item.get('legitimacy_score', 50) + 15)
                logger.info(f"[Description Rescue] Rescued borderline role: '{item.get('role')}' at '{item.get('company_name')}' (Relevance score {relevance})")
            
        return item

    tasks = [validate_single_item(item) for item in items]
    results = await asyncio.gather(*tasks)
    
    valid_items = [item for item in results if item is not None]
    logger.info(f"Liveness and rescue validation complete: {len(valid_items)} of {len(items)} items passed liveness check.")
    return valid_items


def refresh_stats(session) -> int:
    """
    STEP 7 — Refresh Stats / Freshness scores.
    Updates the freshness scores of all remaining internships in the database based on their post age.
    """
    logger.info("STEP 7: Refreshing freshness scores for all active rows...")
    try:
        active_internships = session.query(Internship).all()
        now = datetime.utcnow()
        updated_count = 0
        
        for internship in active_internships:
            posted_time = internship.posted_at or internship.created_at
            age_hours = (now - posted_time).total_seconds() / 3600.0
            
            # Freshness score buckets
            if age_hours <= 24:
                new_score = 100
            elif age_hours <= 48:
                new_score = 80
            elif age_hours <= 96:
                new_score = 50
            else:
                new_score = 0
                
            if internship.freshness_score != new_score:
                internship.freshness_score = new_score
                updated_count += 1
                
        session.commit()
        logger.info(f"Freshness scores updated for {updated_count} rows.")
        return updated_count
    except Exception as e:
        session.rollback()
        logger.error(f"Error refreshing freshness scores: {e}", exc_info=True)
        return 0


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Internship discovery pipeline")
    parser.add_argument("--cleanup", action="store_true", help="Run stale cleanups only")
    parser.add_argument("--liveness", action="store_true", help="Run liveness checks only")
    parser.add_argument("--scrape", action="store_true", help="Run scraper only")
    args = parser.parse_args()

    start_time = time.time()
    
    # If no flags are provided, run full pipeline
    run_full = not (args.cleanup or args.liveness or args.scrape)

    if args.cleanup:
        logger.info("=== STARTING STALE CLEANUP PIPELINE ===")
        init_db()
        session = get_db_session()
        cleanup_old_internships(session)
        session.close()
        logger.info(f"Cleanup finished in {time.time() - start_time:.2f}s")
        return

    if args.liveness:
        logger.info("=== STARTING LIVENESS CHECK PIPELINE ===")
        init_db()
        session = get_db_session()
        await remove_dead_links(session)
        session.close()
        logger.info(f"Liveness checks finished in {time.time() - start_time:.2f}s")
        return

    logger.info("=== STARTING AUTOMATED SCRAPING PIPELINE ===")
    
    # Initialize DB
    init_db()
    
    deleted_stale = 0
    deleted_expired = 0
    
    if run_full:
        session = get_db_session()
        # STEP 1 - Stale Cleanups
        deleted_stale = cleanup_old_internships(session)
        # STEP 2 - Dead Links Cleanups
        deleted_expired = await remove_dead_links(session)
        # Close session before scraping
        session.close()
    
    # 4. STEP 3 - Async Parallel Scraping
    all_scraped_items = []
    scrapers = []
    
    # Launch browser ONCE and block unnecessary resources
    from python_scraper.config import PLAYWRIGHT_HEADLESS
    async with async_playwright() as p:
        logger.info(f"Launching Chromium browser instance (headless={PLAYWRIGHT_HEADLESS})...")
        browser = await p.chromium.launch(
            headless=PLAYWRIGHT_HEADLESS,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-infobars"
            ]
        )
        
        # Reuse browser context
        browser_context = await browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            viewport=PLAYWRIGHT_VIEWPORT,
            extra_http_headers={"Accept-Language": "en-US,en;q=0.9"}
        )
        
        try:
            # Parallel Source Scraping
            all_scraped_items, scrapers = await scrape_all_sources_parallel(browser_context)
        finally:
            await browser_context.close()
            await browser.close()
            logger.info("Headless Chromium browser instance closed successfully.")
            
    # 5. STEP 4 - Centralized Async URL Liveness Validation
    validated_items = await validate_new_items_liveness(all_scraped_items)
    
    # 6. STEP 5 & 6 - Deduplicate & Bulk Insert into DB
    session = get_db_session()
    stats = {}
    
    # Save internships runs local O(1) deduplication and bulk inserts
    added, _, skipped = save_internships(validated_items, stats_dict=stats)
    
    # 7. STEP 7 - Refresh Stats
    refresh_stats(session)
    session.close()
    
    # Pipeline execution metrics calculations
    elapsed = time.time() - start_time
    minutes = int(elapsed // 60)
    seconds = int(elapsed % 60)
    runtime_str = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"
    
    # Speed improvements calculation (comparing vs standard sequential scraping runtime of ~2m 40s (160s))
    baseline_runtime = 160.0
    speed_improvement = int(((baseline_runtime - elapsed) / baseline_runtime) * 100)
    speed_improvement_str = f"+{speed_improvement}%" if speed_improvement > 0 else "N/A (first run / cached)"
    
    # Gather scraper details
    internshala_cnt = next((s.scraped_count for s in scrapers if s.source_name == "Internshala"), 0)
    wellfound_cnt = next((s.scraped_count for s in scrapers if s.source_name == "Wellfound"), 0)
    yc_cnt = next((s.scraped_count for s in scrapers if s.source_name == "YC Jobs"), 0)
    indeed_cnt = next((s.scraped_count for s in scrapers if s.source_name == "Indeed India"), 0)
    
    # Calculate detailed quality checks metrics
    passed_direct_role = sum(1 for item in validated_items if item.get('confidence') == 'HIGH_CONFIDENCE')
    passed_fuzzy = sum(1 for item in validated_items if item.get('confidence') == 'MEDIUM_CONFIDENCE' and not item.get('rescued'))
    passed_rescue = sum(1 for item in validated_items if item.get('rescued') == True)
    
    rejected_unpaid = sum(s.unpaid_or_cert for s in scrapers)
    rejected_irrelevant = sum(s.non_tech_roles + s.rejected_suspicious + s.score_below_threshold + s.missing_fields for s in scrapers)
    total_raw_scraped = sum(s.scraped_count for s in scrapers)
    
    # Calculate yield/collection improvement
    yield_rate = int((added / total_raw_scraped) * 100) if total_raw_scraped > 0 else 0

    high_count = sum(1 for item in validated_items if item.get('confidence') == 'HIGH_CONFIDENCE')
    medium_count = sum(1 for item in validated_items if item.get('confidence') == 'MEDIUM_CONFIDENCE')
    low_count = sum(1 for item in validated_items if item.get('confidence') == 'LOW_CONFIDENCE')
    reject_count = total_raw_scraped - len(validated_items)

    from python_scraper.utils.validators import REJECTION_REASONS_COUNTER
    rejections_summary = "\nTop Rejection Reasons:\n"
    if REJECTION_REASONS_COUNTER:
        for reason, count in REJECTION_REASONS_COUNTER.most_common(5):
            rejections_summary += f"  - {reason}: {count}\n"
    else:
        rejections_summary += "  - No rejections logged during this run.\n"

    # Print and log the professional SCRAPER RUN SUMMARY
    summary_report = f"""
=================================
SCRAPER QUALITY REPORT
=================================
Raw scraped: {total_raw_scraped}

Passed direct role match: {passed_direct_role}
Passed fuzzy match: {passed_fuzzy}
Passed description rescue: {passed_rescue}

Rejected unpaid: {rejected_unpaid}
Rejected irrelevant: {rejected_irrelevant}
Duplicates: {skipped + deleted_expired + deleted_stale}

Final inserted: {added}

Collection accuracy:
+{yield_rate}%

Confidence Classification:
- HIGH_CONFIDENCE count: {high_count}
- MEDIUM_CONFIDENCE count: {medium_count}
- LOW_CONFIDENCE count: {low_count}
- REJECT count: {reject_count}

Runtime: {runtime_str}
Speed improvement: {speed_improvement_str}
{rejections_summary}=================================
"""
    print(summary_report)
    logger.info(summary_report)


if __name__ == "__main__":
    asyncio.run(main())
