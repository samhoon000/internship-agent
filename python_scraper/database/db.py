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
    Prevents duplicates by checking against memory sets of existing records (apply_link and company_name + role).
    Uses SQLAlchemy bulk_insert_mappings for high performance database writes.
    """
    session = get_db_session()
    saved_count = 0
    skipped_count = 0
    rejected_low_confidence = 0
    rejected_malformed = 0

    from python_scraper.config import MIN_LEGITIMACY_TO_KEEP

    try:
        # Load all existing links and combos into memory sets
        existing_links = {r[0] for r in session.query(Internship.apply_link).all()}
        existing_combos = {f"{r[0].lower().strip()}||{r[1].lower().strip()}" 
                           for r in session.query(Internship.company_name, Internship.role).all() if r[0] and r[1]}

        to_insert = []
        
        # Sort incoming data to process newest first (so if duplicates exist in incoming, we keep the newest)
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
                continue

            # Check legitimacy score (safety gate)
            if score < MIN_LEGITIMACY_TO_KEEP:
                logger.warning(f"[SQL Insert Safety] Rejected low confidence internship ({company_name} - {role}): score {score} < {MIN_LEGITIMACY_TO_KEEP}")
                rejected_low_confidence += 1
                continue

            combo = f"{company_name.lower()}||{role.lower()}"

            # Dedup check
            if apply_link in existing_links or combo in existing_combos:
                skipped_count += 1
                if stats_dict is not None:
                    stats_dict[source]['skipped'] += 1
                continue

            # Prepare for insertion
            stipend_numeric = parse_stipend_to_numeric(item.get('stipend'))
            
            # Parse or set posted_at
            posted_at = item.get('posted_at')
            if isinstance(posted_at, str):
                try:
                    posted_at = datetime.strptime(posted_at, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    posted_at = datetime.utcnow()
            elif not posted_at:
                posted_at = datetime.utcnow()

            # Calculate initial freshness score
            age_hours = (datetime.utcnow() - posted_at).total_seconds() / 3600.0
            if age_hours <= 24:
                freshness = 100
            elif age_hours <= 48:
                freshness = 80
            elif age_hours <= 96:
                freshness = 50
            else:
                freshness = 0

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
                "freshness_score": freshness,
                "posted_at": posted_at,
                "created_at": datetime.utcnow()
            }
            to_insert.append(new_record)
            
            # Keep memory sets updated in case duplicates exist within the batch itself
            existing_links.add(apply_link)
            existing_combos.add(combo)
            
            saved_count += 1
            if stats_dict is not None:
                stats_dict[source]['added'] += 1

        if to_insert:
            session.bulk_insert_mappings(Internship, to_insert)
            session.commit()
            
        logger.info(f"Database sync complete. Bulk inserted: {saved_count}, Skipped/Duplicates: {skipped_count}, Rejected low-confidence: {rejected_low_confidence}, Rejected malformed: {rejected_malformed}")
        return saved_count, 0, skipped_count

    except Exception as e:
        session.rollback()
        logger.error(f"Error executing database transaction: {e}", exc_info=True)
        return 0, 0, 0
    finally:
        session.close()
        Session.remove()

