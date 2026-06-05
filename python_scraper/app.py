import sys
import argparse
import logging
from pathlib import Path
from apscheduler.schedulers.blocking import BlockingScheduler

# Append base path to Python systems search to ensure local modules import cleanly
sys.path.append(str(Path(__file__).resolve().parent.parent))

from python_scraper.database.db import init_db, save_internships
from python_scraper.scrapers.internshala import InternshalaScraper
from python_scraper.scrapers.wellfound import WellfoundScraper
from python_scraper.scrapers.yc_jobs import YCJobsScraper
from python_scraper.scrapers.indeed import IndeedScraper

# Configure robust production logging (stdout + file)
log_file = Path(__file__).resolve().parent / "python_scraper.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file, encoding='utf-8')
    ]
)
logger = logging.getLogger("python_scraper.app")

async def run_agent_cycle():
    """Runs a single iteration of all scraper modules and logs consolidated metrics."""
    import time
    start_time = time.time()
    logger.info("=== Starting AI Internship Discovery Cycle ===")
    
    # Run database cleanup and liveness validation before scraping starts
    from python_scraper.database.db import get_db_session
    from python_scraper.database.cleanup_service import cleanup_old_internships, remove_dead_links_async
    
    logger.info("Executing pre-cycle database expiration and archival cleanup...")
    session = get_db_session()
    try:
        cleanup_old_internships(session)
        await remove_dead_links_async(session)
    except Exception as cleanup_err:
        logger.error(f"Failed to execute database cleanup cycle: {cleanup_err}", exc_info=True)
    finally:
        session.close()
        
    from playwright.async_api import async_playwright
    from python_scraper.config import USER_AGENTS, PLAYWRIGHT_VIEWPORT
    import random
    import asyncio
    
    scrapers = [
        InternshalaScraper(),
        WellfoundScraper(),
        YCJobsScraper(),
        IndeedScraper()
    ]
    
    all_scraped_items = []
    
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
        browser_context = await browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            viewport=PLAYWRIGHT_VIEWPORT,
            extra_http_headers={"Accept-Language": "en-US,en;q=0.9"}
        )
        
        async def run_single_scraper(scraper):
            try:
                data = await scraper.scrape(browser_context)
                logger.info(f"{scraper.source_name} successfully yielded {len(data)} items.")
                return data
            except Exception as e:
                logger.error(f"Scraper failed: {scraper.source_name}. Reason: {e}", exc_info=True)
                return []

        # Log triggering in order
        for scraper in scrapers:
            logger.info(f"Triggering {scraper.source_name} scraping sequence...")
            
        # Run all scrapers concurrently
        results = await asyncio.gather(*(run_single_scraper(s) for s in scrapers))
        for data in results:
            all_scraped_items.extend(data)
            
        await browser_context.close()
        await browser.close()
        logger.info("Headless Chromium browser instance closed successfully.")
            
    logger.info("Performing centralized async URL liveness validation and description rescue...")
    from run import validate_new_items_liveness
    validated_items = await validate_new_items_liveness(all_scraped_items)

    logger.info("Saving results to SQL database and applying deduplication...")
    
    # Save to database
    stats = {}
    added, updated, skipped = save_internships(validated_items, stats_dict=stats)
    
    # Refresh freshness scores for active listings
    from run import refresh_stats
    session = get_db_session()
    try:
        refresh_stats(session)
    except Exception as stats_err:
        logger.error(f"Failed to refresh freshness scores: {stats_err}")
    finally:
        session.close()
    
    # Calculate detailed metrics per scraper
    ishala_scraper = next((s for s in scrapers if s.source_name == "Internshala"), None)
    wellfound_scraper = next((s for s in scrapers if s.source_name == "Wellfound"), None)
    indeed_scraper = next((s for s in scrapers if s.source_name == "Indeed India"), None)
    yc_scraper = next((s for s in scrapers if s.source_name == "YC Jobs"), None)
    
    ishala_stats = stats.get("Internshala", {"added": 0, "updated": 0, "skipped": 0})
    wellfound_stats = stats.get("Wellfound", {"added": 0, "updated": 0, "skipped": 0})
    indeed_stats = stats.get("Indeed India", {"added": 0, "updated": 0, "skipped": 0})
    yc_stats = stats.get("YC Jobs", {"added": 0, "updated": 0, "skipped": 0})
    
    ishala_raw = ishala_scraper.scraped_count if ishala_scraper else 0
    ishala_role = ishala_scraper.non_tech_roles if ishala_scraper else 0
    ishala_unpaid = ishala_scraper.unpaid_or_cert if ishala_scraper else 0
    ishala_dup = ishala_stats.get('skipped', 0)
    ishala_company = ishala_scraper.rejected_suspicious if ishala_scraper else 0
    ishala_accepted = sum(1 for item in validated_items if item.get('source') == "Internshala")
    
    wellfound_raw = wellfound_scraper.scraped_count if wellfound_scraper else 0
    wellfound_accepted = sum(1 for item in validated_items if item.get('source') == "Wellfound")
    
    indeed_raw = indeed_scraper.scraped_count if indeed_scraper else 0
    indeed_accepted = sum(1 for item in validated_items if item.get('source') == "Indeed India")
    
    yc_raw = yc_scraper.scraped_count if yc_scraper else 0
    yc_accepted = sum(1 for item in validated_items if item.get('source') == "YC Jobs")

    elapsed = time.time() - start_time
    minutes = int(elapsed // 60)
    seconds = int(elapsed % 60)
    runtime_str = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"

    total_scraped = ishala_raw + wellfound_raw + indeed_raw + yc_raw
    total_accepted = ishala_accepted + wellfound_accepted + indeed_accepted + yc_accepted

    high_count = sum(1 for item in validated_items if item.get('confidence') == 'HIGH_CONFIDENCE')
    medium_count = sum(1 for item in validated_items if item.get('confidence') == 'MEDIUM_CONFIDENCE')
    low_count = sum(1 for item in validated_items if item.get('confidence') == 'LOW_CONFIDENCE')
    reject_count = total_scraped - total_accepted

    from python_scraper.utils.validators import REJECTION_REASONS_COUNTER
    rejections_summary = "\nTop Rejection Reasons:\n"
    if REJECTION_REASONS_COUNTER:
        for reason, count in REJECTION_REASONS_COUNTER.most_common(5):
            rejections_summary += f"  - {reason}: {count}\n"
    else:
        rejections_summary += "  - No rejections logged during this run.\n"

    summary_report = f"""
Internshala Summary
Raw Scraped: {ishala_raw}
Rejected Role: {ishala_role}
Rejected Unpaid: {ishala_unpaid}
Rejected Duplicate: {ishala_dup}
Rejected Company: {ishala_company}
Accepted: {ishala_accepted}

Wellfound Summary
Raw Scraped: {wellfound_raw}
Accepted: {wellfound_accepted}

Indeed Summary
Raw Scraped: {indeed_raw}
Accepted: {indeed_accepted}

YC Jobs Summary
Raw Scraped: {yc_raw}
Accepted: {yc_accepted}

Overall Summary
Total Scraped: {total_scraped}
Total Accepted: {total_accepted}
Total Inserted: {added}
Runtime: {runtime_str}

Confidence Classification:
- HIGH_CONFIDENCE count: {high_count}
- MEDIUM_CONFIDENCE count: {medium_count}
- LOW_CONFIDENCE count: {low_count}
- REJECT count: {reject_count}
{rejections_summary}"""
    logger.info(summary_report)
    print(summary_report)
    
    logger.info(f"=== Cycle Finished. Added: {added}, Updated: {updated}, Unchanged/Skipped: {skipped} ===")
    return added, updated, skipped


def run_agent_cycle_sync():
    """Synchronous wrapper around the async run_agent_cycle for scheduler and CLI execution."""
    import asyncio
    return asyncio.run(run_agent_cycle())


def start_scheduler():
    """Initializes and blocks on the background scheduler to run the agent daily."""
    logger.info("Scheduler starting...")
    scheduler = BlockingScheduler()
    
    # Schedule agent to run every 24 hours (once daily)
    scheduler.add_job(run_agent_cycle_sync, 'interval', hours=24, next_run_time=None)
    
    logger.info("Scheduler initialized. Scraper agent scheduled to run automatically once daily (every 24 hours).")
    logger.info("Press Ctrl+C to terminate.")
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped manually.")

def main():
    parser = argparse.ArgumentParser(
        description="🤖 AI Internship Scraper Agent Command Line Utility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands to execute details:
  1. Trigger all scrapers right now:
     python app.py --run-now
     
  2. Start the daily automatic scheduler in foreground:
     python app.py --scheduler
     
  3. Start the dashboard interface:
     streamlit run dashboard/streamlit_app.py
        """
    )
    
    parser.add_argument(
        "--run-now", 
        action="store_true", 
        help="Execute all scrapers immediately, commit to SQL, and exit."
    )
    parser.add_argument(
        "--scheduler", 
        action="store_true", 
        help="Launch the daily automated scheduler to scrape internships every 24 hours."
    )
    
    args = parser.parse_args()
 
    # Initializing database tables automatically on any script execute
    init_db()
 
    if args.run_now:
        logger.info("Manual execution triggered via --run-now flag.")
        added, updated, skipped = run_agent_cycle_sync()
        print(f"\nExecution stats:\n- Added: {added}\n- Updated: {updated}\n- Skipped/Unchanged: {skipped}")
        
    elif args.scheduler:
        logger.info("Automatic scheduler mode triggered via --scheduler flag.")
        # Perform an initial run immediately so database has listings right away, then start scheduler
        logger.info("Running initial setup scraping cycle...")
        run_agent_cycle_sync()
        start_scheduler()
        
    else:
        # Standard welcome menu
        banner = f"""========================================================================
🤖 AI INTERNSHIP SCRAPER AGENT RUNNER Menu
========================================================================
Database: internship
Table   : internships
Host    : localhost
Log file: {log_file}

Please choose a command line option to proceed:

- Run scraper cycle once:
    python app.py --run-now

- Launch daily scheduler:
    python app.py --scheduler

- Launch web dashboard:
    streamlit run dashboard/streamlit_app.py
========================================================================\n"""
        try:
            print(banner)
        except UnicodeEncodeError:
            print(banner.replace("🤖", "[AI]"))

if __name__ == "__main__":
    main()
