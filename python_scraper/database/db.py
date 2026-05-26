import logging
import difflib
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

def save_internships(internship_dicts, stats_dict=None):
    """
    Saves a list of internship dictionaries to the database.
    Prevents duplicates by:
    1. Checking for unique apply_link.
    2. Fuzzy matching company_name + role against existing records.
    Updates existing records if changes are detected.
    Ensures SQL Insert Safety by rejecting low legitimacy or malformed rows.
    """
    session = get_db_session()
    saved_count = 0
    updated_count = 0
    skipped_count = 0
    rejected_low_confidence = 0
    rejected_malformed = 0

    from python_scraper.config import MIN_LEGITIMACY_TO_KEEP

    try:
        # Load all existing internships into memory to avoid repeated queries in fuzzy matching
        existing_records = session.query(Internship).all()

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

            # 1. Exact link check
            existing_by_link = next((r for r in existing_records if r.apply_link == apply_link), None)
            
            # 2. Fuzzy similarity check on company_name + role
            existing_by_similarity = None
            if not existing_by_link:
                for r in existing_records:
                    if is_similar(r.company_name, company_name) and is_similar(r.role, role):
                        existing_by_similarity = r
                        break

            target_record = existing_by_link or existing_by_similarity

            if target_record:
                # Update existing record if needed
                updated = False
                
                # Update fields if new data has value
                if item.get('stipend') and target_record.stipend != item.get('stipend'):
                    target_record.stipend = item.get('stipend')
                    updated = True
                
                if item.get('paid') is not None and target_record.paid != item.get('paid'):
                    target_record.paid = item.get('paid')
                    updated = True

                if item.get('location') and target_record.location != item.get('location'):
                    target_record.location = item.get('location')
                    updated = True

                if item.get('remote') is not None and target_record.remote != item.get('remote'):
                    target_record.remote = item.get('remote')
                    updated = True

                if item.get('duration') and target_record.duration != item.get('duration'):
                    target_record.duration = item.get('duration')
                    updated = True

                if item.get('skills') and target_record.skills != item.get('skills'):
                    target_record.skills = item.get('skills')
                    updated = True

                if item.get('legitimacy_score') is not None and target_record.legitimacy_score != item.get('legitimacy_score'):
                    # Retain the higher legitimacy score
                    new_score = item.get('legitimacy_score')
                    if new_score > target_record.legitimacy_score:
                        target_record.legitimacy_score = new_score
                        updated = True

                if updated:
                    target_record.created_at = datetime.utcnow()  # Update timestamp on modification
                    updated_count += 1
                    if stats_dict is not None:
                        stats_dict[source]['updated'] += 1
                else:
                    skipped_count += 1
                    if stats_dict is not None:
                        stats_dict[source]['skipped'] += 1
            else:
                # Create a new record
                new_internship = Internship(
                    apply_link=apply_link,
                    company_name=company_name,
                    role=role,
                    stipend=item.get('stipend'),
                    paid=item.get('paid', False),
                    location=item.get('location'),
                    remote=item.get('remote', False),
                    duration=item.get('duration'),
                    skills=item.get('skills'),
                    source=source,
                    legitimacy_score=score,
                    created_at=datetime.utcnow()
                )
                session.add(new_internship)
                existing_records.append(new_internship)  # Keep local cache updated
                saved_count += 1
                if stats_dict is not None:
                    stats_dict[source]['added'] += 1

        session.commit()
        logger.info(f"Database sync complete. Added: {saved_count}, Updated: {updated_count}, Duplicates skipped: {skipped_count}, Rejected low-confidence: {rejected_low_confidence}, Rejected malformed: {rejected_malformed}")
        return saved_count, updated_count, skipped_count

    except Exception as e:
        session.rollback()
        logger.error(f"Error executing database transaction: {e}", exc_info=True)
        return 0, 0, 0
    finally:
        session.close()
        Session.remove()

