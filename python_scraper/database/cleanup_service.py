import logging
import asyncio
import sys
from datetime import datetime, timedelta
from urllib.parse import urlparse

from python_scraper.database.models import Internship
from python_scraper.config import (
    ACTIVE_THRESHOLD_DAYS,
    INACTIVE_THRESHOLD_DAYS,
    ARCHIVED_THRESHOLD_DAYS,
    PURGE_OLD_RECORDS,
    CONSECUTIVE_FAILURES_LIMIT
)
from python_scraper.utils.validators import validate_url

logger = logging.getLogger("python_scraper.cleanup_service")

def cleanup_old_internships(session) -> tuple[int, int]:
    """
    Categorizes internships based on age:
    - Active: 0-21 days (appear normally)
    - Inactive: 21-30 days (is_active = False, inactive_reason = "Inactive (Stale)")
    - Archived: 30-90 days (is_active = False, inactive_reason = "Archived")
    - Purged: 90+ days (hard-deleted only if PURGE_OLD_RECORDS = True)
    """
    logger.info("Starting expiration and archival updates...")
    now = datetime.utcnow()
    
    cutoff_inactive = now - timedelta(days=ACTIVE_THRESHOLD_DAYS)
    cutoff_archived = now - timedelta(days=INACTIVE_THRESHOLD_DAYS)
    cutoff_purge = now - timedelta(days=ARCHIVED_THRESHOLD_DAYS)

    soft_deleted = 0
    archived = 0
    purged = 0
    
    try:
        # 1. Soft-delete Active listings that become Inactive (21-30 days old)
        inactive_listings = session.query(Internship).filter(
            Internship.is_active == True,
            (
                ((Internship.posted_at != None) & (Internship.posted_at < cutoff_inactive)) |
                ((Internship.posted_at == None) & (Internship.created_at < cutoff_inactive))
            )
        ).all()
        
        for job in inactive_listings:
            job.is_active = False
            job.inactive_reason = "Inactive (Stale)"
            job.deactivated_at = now
            soft_deleted += 1

        # 2. Archive Inactive listings that become Archived (30-90 days old)
        archived_listings = session.query(Internship).filter(
            Internship.is_active == False,
            Internship.inactive_reason == "Inactive (Stale)",
            (
                ((Internship.posted_at != None) & (Internship.posted_at < cutoff_archived)) |
                ((Internship.posted_at == None) & (Internship.created_at < cutoff_archived))
            )
        ).all()
        
        for job in archived_listings:
            job.inactive_reason = "Archived"
            archived += 1

        # 3. Purge listings older than 90 days (if configured)
        if PURGE_OLD_RECORDS:
            purged = session.query(Internship).filter(
                ((Internship.posted_at != None) & (Internship.posted_at < cutoff_purge)) |
                ((Internship.posted_at == None) & (Internship.created_at < cutoff_purge))
            ).delete(synchronize_session=False)
        else:
            # Mark them as Archived if not already
            unarchived_old = session.query(Internship).filter(
                Internship.inactive_reason != "Archived",
                (
                    ((Internship.posted_at != None) & (Internship.posted_at < cutoff_purge)) |
                    ((Internship.posted_at == None) & (Internship.created_at < cutoff_purge))
                )
            ).all()
            for job in unarchived_old:
                job.is_active = False
                job.inactive_reason = "Archived"
                if not job.deactivated_at:
                    job.deactivated_at = now
                archived += 1

        session.commit()
        logger.info(f"Cleanup complete. Soft-deleted: {soft_deleted}, Archived: {archived}, Purged: {purged}")
        return soft_deleted, purged
    except Exception as e:
        session.rollback()
        logger.error(f"Error during database cleanup and archival cycle: {e}", exc_info=True)
        return 0, 0

async def check_url_liveness_async(job, semaphore) -> tuple[str, bool, str, str]:
    """Asynchronously checks if a URL is still live."""
    async with semaphore:
        try:
            # Run validate_url in thread pool to avoid blocking async event loop
            is_live, reason, html = await asyncio.to_thread(validate_url, job.apply_link, job.source, True)
            return job.apply_link, is_live, reason, html
        except Exception as e:
            return job.apply_link, False, f"[ERROR] Unexpected: {e}", ""

async def remove_dead_links_async(session) -> int:
    """
    Validates active links concurrently.
    - If 404 is received 3 consecutive checks -> deactivate (soft-delete)
    - If 500, 502, 503, 504, timeout, or DNS error -> do NOT deactivate
    """
    logger.info("Starting safe dead-link validation cycle...")
    try:
        active_jobs = session.query(Internship).filter(Internship.is_active == True).all()
        if not active_jobs:
            logger.info("No active links in database to validate.")
            return 0

        logger.info(f"Validating liveness for {len(active_jobs)} active listings...")
        
        # Concurrency limit of 15 requests
        semaphore = asyncio.Semaphore(15)
        tasks = [check_url_liveness_async(job, semaphore) for job in active_jobs]
        results = await asyncio.gather(*tasks)
        
        # Map results by link
        results_map = {link: (is_live, reason) for link, is_live, reason, _ in results}
        
        deactivated_count = 0
        now = datetime.utcnow()
        
        for job in active_jobs:
            link = job.apply_link
            if link not in results_map:
                continue
                
            is_live, reason = results_map[link]
            
            if is_live:
                # Reset failure count on success
                if job.consecutive_failures > 0:
                    job.consecutive_failures = 0
            else:
                # Analyze failure reason
                if "[404]" in reason:
                    # Increment failure count for explicit 404
                    job.consecutive_failures += 1
                    logger.warning(f"[Liveness Check] Link returned 404 ({job.company_name} - {job.role}). Failures: {job.consecutive_failures}/3")
                    
                    if job.consecutive_failures >= CONSECUTIVE_FAILURES_LIMIT:
                        job.is_active = False
                        job.inactive_reason = "Dead Link (404)"
                        job.deactivated_at = now
                        deactivated_count += 1
                        logger.error(f"[Liveness Deactivation] Deactivating dead link: {job.company_name} - {job.role}")
                else:
                    # Ignore transient timeouts, DNS, or 5XX errors - do NOT increment failure count, do NOT deactivate
                    logger.info(f"[Liveness Ignored] Transient liveness issue ignored: {job.company_name} - {job.role}. Reason: {reason}")
        
        session.commit()
        logger.info(f"Liveness check complete. Deactivated: {deactivated_count} listings.")
        return deactivated_count
    except Exception as e:
        session.rollback()
        logger.error(f"Error during dead-link validation cycle: {e}", exc_info=True)
        return 0

def remove_dead_links(session) -> int:
    """Synchronous wrapper for async remove_dead_links."""
    return asyncio.run(remove_dead_links_async(session))
