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
    """
    try:
        logger.info("Initiating database startup sequence...")
        if not test_connection():
            raise ConnectionError("Could not connect to MySQL at localhost:3306")
            
        Base.metadata.create_all(engine)
        logger.info("Database startup sequence: SUCCESSFUL. Table 'internships' created or verified successfully.")

        # Verify and add posted_at and freshness_score columns dynamically if they do not exist
        try:
            with engine.connect() as conn:
                from sqlalchemy import text
                columns_query = conn.execute(text("SHOW COLUMNS FROM internships"))
                existing_cols = [row[0] for row in columns_query.fetchall()]
                
                if "posted_at" not in existing_cols:
                    logger.info("[Migration] Adding 'posted_at' column to 'internships' table...")
                    conn.execute(text("ALTER TABLE internships ADD COLUMN posted_at DATETIME DEFAULT NULL"))
                    logger.info("[Migration] Column 'posted_at' added successfully.")
                
                if "freshness_score" not in existing_cols:
                    logger.info("[Migration] Adding 'freshness_score' column to 'internships' table...")
                    conn.execute(text("ALTER TABLE internships ADD COLUMN freshness_score INT DEFAULT 0"))
                    logger.info("[Migration] Column 'freshness_score' added successfully.")
                
                if "confidence" not in existing_cols:
                    logger.info("[Migration] Adding 'confidence' column to 'internships' table...")
                    conn.execute(text("ALTER TABLE internships ADD COLUMN confidence VARCHAR(50) DEFAULT 'HIGH' NOT NULL"))
                    logger.info("[Migration] Column 'confidence' added successfully.")
                
                if "confidence_score" not in existing_cols:
                    logger.info("[Migration] Adding 'confidence_score' column to 'internships' table...")
                    conn.execute(text("ALTER TABLE internships ADD COLUMN confidence_score INT DEFAULT 0 NOT NULL"))
                    conn.execute(text("UPDATE internships SET confidence_score = legitimacy_score"))
                    logger.info("[Migration] Column 'confidence_score' added successfully.")
                
                if "confidence_tier" not in existing_cols:
                    logger.info("[Migration] Adding 'confidence_tier' column to 'internships' table...")
                    conn.execute(text("ALTER TABLE internships ADD COLUMN confidence_tier VARCHAR(50) DEFAULT 'HIGH_CONFIDENCE' NOT NULL"))
                    conn.execute(text("UPDATE internships SET confidence_tier = confidence"))
                    logger.info("[Migration] Column 'confidence_tier' added successfully.")

                if "description" not in existing_cols:
                    logger.info("[Migration] Adding 'description' column to 'internships' table...")
                    conn.execute(text("ALTER TABLE internships ADD COLUMN description TEXT DEFAULT NULL"))
                    logger.info("[Migration] Column 'description' added successfully.")

                if "relevance_score" not in existing_cols:
                    logger.info("[Migration] Adding 'relevance_score' column to 'internships' table...")
                    conn.execute(text("ALTER TABLE internships ADD COLUMN relevance_score INT DEFAULT 0 NOT NULL"))
                    logger.info("[Migration] Column 'relevance_score' added successfully.")
                
                conn.commit()
        except Exception as migration_error:
            logger.warning(f"Database startup sequence: Auto-migration of columns failed: {migration_error}")
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

    def get_canonical_key(comp: str, role_title: str) -> str:
        # Normalize company name (remove common suffixes and non-alphanumeric)
        c = (comp or "").lower()
        c = re.sub(r"\b(pvt|private|ltd|limited|inc|llc|corp|corporation|co|company)\b", "", c)
        c = re.sub(r"[^a-z0-9]", "", c).strip()
        
        # Normalize role title (remove words like 'internship', 'intern', 'co-op', and extra whitespace)
        r = (role_title or "").lower()
        r = re.sub(r"\b(internship|intern|co-op|coop|temporary|part-time|full-time)\b", "", r)
        r = re.sub(r"[^a-z0-9]", "", r).strip()
        
        return f"{c}||{r}"

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
        # Load all existing records from DB
        existing_jobs = {job.apply_link: job for job in session.query(Internship).all()}
        
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
        from python_scraper.scoring.legitimacy import get_legitimacy_bucket

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
                log_rejection(company_name or "Unknown Company", role or "Unknown Role", 0, reasons)
                continue

            # Check legitimacy score (safety gate)
            if score < MIN_LEGITIMACY_TO_KEEP:
                logger.warning(f"[SQL Insert Safety] Rejected low confidence internship ({company_name} - {role}): score {score} < {MIN_LEGITIMACY_TO_KEEP}")
                rejected_low_confidence += 1
                log_rejection(company_name, role, score, [f"Legitimacy Score Below Threshold ({score} < {MIN_LEGITIMACY_TO_KEEP})"])
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

                existing_record.freshness_score = freshness

                if changed:
                    updated_count += 1
                    if stats_dict is not None:
                        stats_dict[source]['updated'] += 1
                else:
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
                "posted_at": posted_at,
                "created_at": datetime.utcnow()
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

