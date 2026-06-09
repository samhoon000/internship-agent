import logging
import difflib
import re
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from python_scraper.config import DATABASE_URL
from python_scraper.database.models import Base, Internship

logger = logging.getLogger("python_scraper.database")

def create_database_if_not_exists():
    """
    Connects to the local MySQL server and creates the database if it doesn't exist.
    """
    try:
        # Split URL to get server base connection and database name
        # "mysql+pymysql://root:@localhost/internship" -> "mysql+pymysql://root:@localhost" and "internship"
        base_url, db_name = DATABASE_URL.rsplit('/', 1)
        temp_engine = create_engine(base_url, pool_pre_ping=True)
        with temp_engine.connect() as conn:
            from sqlalchemy import text
            conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {db_name}"))
        temp_engine.dispose()
        logger.info(f"Database validation: Database '{db_name}' exists or was successfully verified/created.")
    except Exception as e:
        logger.warning(f"Database validation: Auto-creation check failed (continuing to connect): {e}")

# Validate database existence before creating main connection engine
create_database_if_not_exists()

# Setup SQLAlchemy engine and sessions with pool_pre_ping enabled
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)

class DBExistenceChecker:
    """
    On-demand existence checker for URL links. 
    Implements the '__contains__' magic method to act as a set, querying the DB 
    by Primary Key (apply_link) and caching results locally.
    Memory complexity is O(N) where N is the number of processed links, preventing full-table scans.
    """
    def __init__(self):
        self.cache = {}

    def __contains__(self, link: str) -> bool:
        if not link:
            return False
        link_str = link.strip()
        if link_str in self.cache:
            return self.cache[link_str]
        
        session = Session()
        try:
            # Performs an indexed check on the Primary Key
            exists = session.query(Internship.apply_link).filter(
                Internship.apply_link == link_str
            ).first() is not None
            self.cache[link_str] = exists
            return exists
        except Exception as e:
            logger.error(f"Error checking link existence: {e}")
            return False
        finally:
            session.close()

def test_connection() -> bool:
    """
    Tests the database connection to the local MySQL database 'internship'.
    Ensures the local MySQL installation is accessible.
    """
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Successfully connected to MySQL database: internship")
        return True
    except Exception as e:
        logger.error("Could not connect to MySQL at localhost:3306", exc_info=True)
        return False

def init_db():
    """
    Initializes the local MySQL database and tables automatically on startup.
    Handles errors for connection issues or table creation failures.
    Automatically migrates missing relevance columns and backfills existing data.
    """
    try:
        logger.info("Initiating database startup sequence...")
        if not test_connection():
            raise ConnectionError("Could not connect to MySQL at localhost:3306")
            
        Base.metadata.create_all(engine)
        logger.info("Tables created or verified via SQLAlchemy Metadata.")
                
        # Perform dynamic backfill of existing rows
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        try:
            from python_scraper.utils.validators import get_relevance_tier_and_category
            unclassified = session.query(Internship).filter(
                (Internship.role_category == 'Other') | (Internship.role_category == None) | (Internship.relevance_tier == 'IRRELEVANT') | (Internship.relevance_tier == None)
            ).all()
            if unclassified:
                logger.info(f"Backfilling relevance score, tier, and category for {len(unclassified)} existing internships...")
                for job in unclassified:
                    # Extract domain candidates
                    domain = ""
                    if job.apply_link:
                        try:
                            from urllib.parse import urlparse
                            domain = urlparse(job.apply_link).netloc.lower()
                        except:
                            pass
                    
                    score, tier, cat = get_relevance_tier_and_category(
                        job.role, job.skills or "", job.description or "", domain, job.source
                    )
                    job.relevance_score = score
                    job.relevance_tier = tier
                    job.role_category = cat
                session.commit()
                logger.info("Database backfill completed successfully.")
        except Exception as e:
            session.rollback()
            logger.error(f"Error executing database backfill: {e}")
        finally:
            session.close()

        logger.info("Database startup sequence: SUCCESSFUL. Table 'internships' verified and updated.")
    except Exception as e:
        logger.critical(f"Database startup sequence: FAILED. Error initializing tables: {e}", exc_info=True)
        raise e

def is_similar(str1, str2, threshold=0.85):
    """Calculates string similarity using difflib SequenceMatcher."""
    if not str1 or not str2:
        return False
    return difflib.SequenceMatcher(None, str1.strip().lower(), str2.strip().lower()).ratio() >= threshold

def get_db_session():
    """Returns a new database session."""
    return Session()

def parse_stipend_to_numeric(stipend_str: str) -> int:
    if not stipend_str:
        return 0
    # Remove commas and currency signs
    clean = re.sub(r'[,₹$]', '', stipend_str)
    # Find all sequences of numbers
    matches = re.findall(r'\d+', clean)
    if not matches:
        return 0
    nums = [int(m) for m in matches]
    if len(nums) >= 2:
        return int((nums[0] + nums[1]) / 2)
    return nums[0]

def save_internships(internship_dicts, stats_dict=None):
    """
    Saves a list of internship dictionaries to the database.
    Prevents duplicates by checking against memory sets of existing records (apply_link and company_name + role + location hash).
    Supports updating existing records if new fields are better or changed.
    Uses SQLAlchemy bulk_insert_mappings for high performance database writes.
    """
    session = get_db_session()
    saved_count = 0
    updated_count = 0
    skipped_count = 0
    rejected_low_confidence = 0
    rejected_malformed = 0

    from python_scraper.utils.deduplication import get_canonical_key, is_duplicate_fuzzy

    def normalize_url(url_str: str) -> str:
        if not url_str:
            return ""
        from urllib.parse import urlparse
        try:
            parsed = urlparse(url_str)
            normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            return normalized.lower().strip()
        except Exception:
            return url_str.lower().strip()

    from python_scraper.config import MIN_LEGITIMACY_TO_KEEP

    try:
        # Optimization: Query candidate duplicates from database selectively
        # Complexity improvement: O(log M) B-tree lookup on PK & indexed company_name
        # replacing O(M) full table scan. Prevents OOM memory growth.
        batch_links = [item.get('apply_link') for item in internship_dicts if item.get('apply_link')]
        batch_companies = {item.get('company_name', '').strip() for item in internship_dicts if item.get('company_name')}
        
        from sqlalchemy import or_, and_
        company_conditions = []
        for comp in batch_companies:
            if not comp:
                continue
            company_conditions.append(Internship.company_name == comp)
            first_word = comp.split()[0] if comp.strip() else ""
            if len(first_word) > 2:
                company_conditions.append(Internship.company_name.like(f"{first_word}%"))
        
        query_filter = Internship.apply_link.in_(batch_links)
        if company_conditions:
            query_filter = or_(
                query_filter,
                and_(
                    Internship.is_active == True,
                    or_(*company_conditions)
                )
            )

        existing_jobs_list = session.query(Internship).filter(query_filter).all()
        existing_jobs = {job.apply_link: job for job in existing_jobs_list}
        
        # Map canonical keys and normalized URLs to existing apply_links
        existing_combos_map = {}
        for link, job in existing_jobs.items():
            ckey = get_canonical_key(job.company_name, job.role)
            existing_combos_map[ckey] = link
            
            norm_link = normalize_url(link)
            if norm_link:
                existing_combos_map[norm_link] = link

        to_insert = []
        
        from python_scraper.utils.validators import log_rejection
        from python_scraper.scoring.scoring_service import get_legitimacy_bucket

        for item in internship_dicts:
            apply_link = item.get('apply_link')
            company_name = item.get('company_name', '').strip()
            role = item.get('role', '').strip()
            score = item.get('legitimacy_score', 0)
            source = item.get('source', 'Unknown')

            # Initialize stats for this source if stats_dict is provided
            if stats_dict is not None and source not in stats_dict:
                stats_dict[source] = {'added': 0, 'updated': 0, 'skipped': 0}

            # Check critical fields (safety gate)
            if not apply_link or not company_name or not role:
                logger.warning(f"[SQL Insert Safety] Rejected malformed internship: {item}")
                rejected_malformed += 1
                reasons = []
                if not apply_link: reasons.append("Missing Critical Fields (apply_link)")
                if not company_name: reasons.append("Missing Critical Fields (company_name)")
                if not role: reasons.append("Missing Critical Fields (role)")
                log_rejection(company_name or "Unknown Company", role or "Unknown Role", 0, reasons, source=source, relevance_score=relevance_score)
                continue

            # Fallback calculation if relevance properties are missing from item
            role_category = item.get('role_category')
            relevance_tier = item.get('relevance_tier')
            relevance_score = item.get('relevance_score')
            
            if not role_category or not relevance_tier or relevance_score is None:
                from python_scraper.scoring.scoring_service import get_relevance_tier_and_category
                domain = ""
                if apply_link:
                    try:
                        from urllib.parse import urlparse
                        domain = urlparse(apply_link).netloc.lower()
                    except:
                        pass
                
                score_calc, tier_calc, cat_calc = get_relevance_tier_and_category(
                    role, item.get('skills', '') or "", item.get('description', '') or "", domain, source
                )
                if relevance_score is None:
                    relevance_score = score_calc
                    item['relevance_score'] = score_calc
                if not relevance_tier:
                    relevance_tier = tier_calc
                    item['relevance_tier'] = tier_calc
                if not role_category:
                    role_category = cat_calc
                    item['role_category'] = cat_calc

            # Check legitimacy score (safety gate)
            if score < MIN_LEGITIMACY_TO_KEEP:
                logger.warning(f"[SQL Insert Safety] Rejected low confidence internship ({company_name} - {role}): score {score} < {MIN_LEGITIMACY_TO_KEEP}")
                rejected_low_confidence += 1
                log_rejection(company_name, role, score, [f"Legitimacy Score Below Threshold ({score} < {MIN_LEGITIMACY_TO_KEEP})"], source=source, relevance_score=relevance_score)
                continue

            # Map the confidence to 4-tier class
            confidence_tier = item.get('confidence')
            if not confidence_tier or confidence_tier in ['HIGH', 'MEDIUM', 'LOW', 'REJECT', 'NEEDS_RESCUE']:
                confidence_tier = get_legitimacy_bucket(score)

            normalized_input_link = normalize_url(apply_link)
            ckey = get_canonical_key(company_name, role)

            # Check if this job exists in the DB (via direct link, normalized link, or canonical key)
            matched_link = None
            if apply_link in existing_jobs:
                matched_link = apply_link
            elif normalized_input_link in existing_combos_map:
                matched_link = existing_combos_map[normalized_input_link]
            elif ckey in existing_combos_map:
                matched_link = existing_combos_map[ckey]
            else:
                # Perform fuzzy matching on existing keys in memory
                for ext_key, link in existing_combos_map.items():
                    if '||' in ext_key:
                        ext_comp, ext_role = ext_key.split('||', 1)
                        if is_duplicate_fuzzy(company_name, role, ext_comp, ext_role):
                            matched_link = link
                            break

            # Prepare fields
            stipend_numeric = parse_stipend_to_numeric(item.get('stipend'))
            posted_at = item.get('posted_at')
            if isinstance(posted_at, str):
                try:
                    posted_at = datetime.strptime(posted_at, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    posted_at = datetime.utcnow()
            elif not posted_at:
                posted_at = datetime.utcnow()

            # Calculate freshness score
            age_hours = (datetime.utcnow() - posted_at).total_seconds() / 3600.0
            if age_hours <= 24:
                freshness = 100
            elif age_hours <= 48:
                freshness = 80
            elif age_hours <= 96:
                freshness = 50
            else:
                freshness = 0

            if matched_link:
                if matched_link not in existing_jobs:
                    # Duplicate within the same scraper batch (already queued for insertion)
                    skipped_count += 1
                    if stats_dict is not None:
                        stats_dict[source]['skipped'] += 1
                    continue

                # Update existing record
                existing_record = existing_jobs[matched_link]
                changed = False

                # Soft delete reactivation!
                if not getattr(existing_record, 'is_active', True):
                    existing_record.is_active = True
                    existing_record.deactivated_at = None
                    existing_record.inactive_reason = None
                    existing_record.consecutive_failures = 0
                    changed = True

                existing_record.last_seen = datetime.utcnow()

                if item.get('stipend') and existing_record.stipend != item.get('stipend'):
                    existing_record.stipend = item.get('stipend')
                    existing_record.stipend_numeric = stipend_numeric
                    changed = True
                if item.get('location') and existing_record.location != item.get('location'):
                    existing_record.location = item.get('location')
                    changed = True
                if item.get('skills') and existing_record.skills != item.get('skills'):
                    existing_record.skills = item.get('skills')
                    changed = True
                if score > existing_record.legitimacy_score:
                    existing_record.legitimacy_score = score
                    existing_record.confidence_score = score
                    changed = True
                if confidence_tier and existing_record.confidence != confidence_tier:
                    existing_record.confidence = confidence_tier
                    existing_record.confidence_tier = confidence_tier
                    changed = True
                if item.get('description') and existing_record.description != item.get('description'):
                    existing_record.description = item.get('description')
                    changed = True
                if item.get('relevance_score', 0) > existing_record.relevance_score:
                    existing_record.relevance_score = item.get('relevance_score', 0)
                    changed = True
                if item.get('relevance_tier') and existing_record.relevance_tier != item.get('relevance_tier'):
                    existing_record.relevance_tier = item.get('relevance_tier')
                    changed = True
                if item.get('role_category') and existing_record.role_category != item.get('role_category'):
                    existing_record.role_category = item.get('role_category')
                    changed = True

                existing_record.freshness_score = freshness

                # Even if no fields changed, we updated last_seen, so we mark session dirty
                if changed:
                    updated_count += 1
                    if stats_dict is not None:
                        stats_dict[source]['updated'] += 1
                else:
                    # Increment skipped_count but session still updates last_seen
                    skipped_count += 1
                    if stats_dict is not None:
                        stats_dict[source]['skipped'] += 1
                continue

            # Prepare for insertion
            new_record = {
                "apply_link": apply_link,
                "company_name": company_name,
                "role": role,
                "stipend": item.get('stipend'),
                "stipend_numeric": stipend_numeric,
                "paid": item.get('paid', False),
                "location": item.get('location'),
                "remote": item.get('remote', False),
                "duration": item.get('duration'),
                "skills": item.get('skills'),
                "source": source,
                "legitimacy_score": score,
                "confidence_score": score,
                "freshness_score": freshness,
                "confidence": confidence_tier or 'HIGH_CONFIDENCE',
                "confidence_tier": confidence_tier or 'HIGH_CONFIDENCE',
                "description": item.get('description'),
                "relevance_score": item.get('relevance_score', 0),
                "relevance_tier": item.get('relevance_tier', 'IRRELEVANT'),
                "role_category": item.get('role_category', 'Other'),
                "posted_at": posted_at,
                "created_at": datetime.utcnow(),
                "is_active": True,
                "inactive_reason": None,
                "last_seen": datetime.utcnow(),
                "deactivated_at": None,
                "consecutive_failures": 0
            }
            to_insert.append(new_record)
            
            # Keep memory mapping updated to prevent internal batch duplicates
            existing_combos_map[normalized_input_link] = apply_link
            existing_combos_map[ckey] = apply_link
            
            saved_count += 1
            if stats_dict is not None:
                stats_dict[source]['added'] += 1

        if to_insert:
            session.bulk_insert_mappings(Internship, to_insert)
        
        session.commit()
        logger.info(f"Database sync complete. Bulk inserted: {saved_count}, Updated: {updated_count}, Skipped/Duplicates: {skipped_count}, Rejected low-confidence: {rejected_low_confidence}, Rejected malformed: {rejected_malformed}")
        return saved_count, updated_count, skipped_count

    except Exception as e:
        session.rollback()
        logger.error(f"Error executing database transaction: {e}", exc_info=True)
        return 0, 0, 0
    finally:
        session.close()
        Session.remove()


def update_source_health(source_name: str, success: bool, jobs_found: int = 0, jobs_saved: int = 0):
    """
    Updates the health record for a given scraper source in the source_health table,
    including execution metrics (found, saved, success/failure counts).
    """
    from python_scraper.database.models import SourceHealth
    session = get_db_session()
    try:
        health = session.query(SourceHealth).filter(SourceHealth.source == source_name).first()
        if not health:
            health = SourceHealth(
                source=source_name,
                success_count=0,
                failure_count=0,
                last_jobs_found=0,
                last_jobs_saved=0
            )
            session.add(health)
            
        health.last_jobs_found = jobs_found
        health.last_jobs_saved = jobs_saved
        
        if success:
            health.last_successful_scrape = datetime.utcnow()
            health.health_status = "HEALTHY"
            health.success_count += 1
        else:
            health.last_failure = datetime.utcnow()
            health.health_status = "UNHEALTHY"
            health.failure_count += 1
            
        session.commit()
        logger.info(f"[Source Health] Updated {source_name} health: {health.health_status} (found={jobs_found}, saved={jobs_saved}, success_count={health.success_count}, failure_count={health.failure_count})")
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to update source health for {source_name}: {e}")
    finally:
        session.close()
        Session.remove()

