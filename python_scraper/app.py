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

def run_agent_cycle():
    """Runs a single iteration of all scraper modules and logs consolidated metrics."""
    logger.info("=== Starting AI Internship Discovery Cycle ===")
    
    scrapers = [
        InternshalaScraper(),
        WellfoundScraper(),
        YCJobsScraper(),
        IndeedScraper()
    ]
    
    all_scraped_items = []
    
    for scraper in scrapers:
        try:
            logger.info(f"Triggering {scraper.source_name} scraping sequence...")
            data = scraper.scrape()
            all_scraped_items.extend(data)
            logger.info(f"{scraper.source_name} successfully yielded {len(data)} items.")
        except Exception as e:
            logger.error(f"Scraper failed: {scraper.source_name}. Reason: {e}", exc_info=True)
            
    # Calculate consolidated production metrics
    total_scraped = sum(s.scraped_count for s in scrapers)
    total_suspicious = sum(s.rejected_suspicious + s.score_below_threshold for s in scrapers)
    total_broken = sum(s.broken_urls for s in scrapers)
    blocked_sources = sum(1 for s in scrapers if s.blocked)
    
    logger.info("Saving results to SQL database and applying deduplication...")
    
    # Save to database
    stats = {}
    added, updated, skipped = save_internships(all_scraped_items, stats_dict=stats)
    
    # Extract and log detailed Internshala metrics
    internshala_scraper = next((s for s in scrapers if s.source_name == "Internshala"), None)
    if internshala_scraper:
        ishala_stats = stats.get("Internshala", {"added": 0, "updated": 0, "skipped": 0})
        ishala_report = f"""
========================================================
INTERNSHALA DETAILED REPORT
========================================================
Pages scraped: {getattr(internshala_scraper, 'pages_scraped', 0)}
Raw internships found: {internshala_scraper.scraped_count}
Rejected unpaid: {internshala_scraper.unpaid_or_cert}
Rejected suspicious companies: {internshala_scraper.rejected_suspicious + internshala_scraper.score_below_threshold}
Broken URLs: {internshala_scraper.broken_urls}
Inserted into SQL: {ishala_stats['added']}
========================================================
"""
        logger.info(ishala_report)
        print(ishala_report)

    # print and log production metrics exactly as requested
    metrics_report = f"""
========================================================
PRODUCTION METRICS REPORT
========================================================
Real internships scraped: {total_scraped}
Rejected suspicious internships: {total_suspicious}
Broken URLs rejected: {total_broken}
Blocked sources: {blocked_sources}
Duplicates skipped: {skipped}
Inserted into SQL: {added}
========================================================
"""
    logger.info(metrics_report)
    print(metrics_report)
    
    logger.info(f"=== Cycle Finished. Added: {added}, Updated: {updated}, Unchanged/Skipped: {skipped} ===")
    return added, updated, skipped


def start_scheduler():
    """Initializes and blocks on the background scheduler to run the agent daily."""
    logger.info("Scheduler starting...")
    scheduler = BlockingScheduler()
    
    # Schedule agent to run every 24 hours (once daily)
    scheduler.add_job(run_agent_cycle, 'interval', hours=24, next_run_time=None)
    
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
        added, updated, skipped = run_agent_cycle()
        print(f"\nExecution stats:\n- Added: {added}\n- Updated: {updated}\n- Skipped/Unchanged: {skipped}")
        
    elif args.scheduler:
        logger.info("Automatic scheduler mode triggered via --scheduler flag.")
        # Perform an initial run immediately so database has listings right away, then start scheduler
        logger.info("Running initial setup scraping cycle...")
        run_agent_cycle()
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
