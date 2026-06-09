from datetime import datetime
from sqlalchemy import Column, String, Boolean, Integer, DateTime, Index, text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Internship(Base):
    __tablename__ = 'internships'
    
    __table_args__ = (
        Index('ix_internships_active_category_posted', 'is_active', 'role_category', text('posted_at DESC')),
        Index('ix_internships_active_category_created', 'is_active', 'role_category', text('created_at DESC')),
        Index('ix_internships_active_category_stipend', 'is_active', 'role_category', text('stipend_numeric DESC')),
        Index('ix_internships_active_company', 'is_active', 'company_name'),
        Index('ix_internships_active_source', 'is_active', 'source'),
    )
    
    # MySQL requires explicit VARCHAR lengths on all String columns.
    # apply_link serves as the unique primary key matching the user's exact schema.
    apply_link = Column(String(500), primary_key=True, nullable=False)
    
    company_name = Column(String(255), nullable=False)
    role = Column(String(255), nullable=False)
    stipend = Column(String(100), nullable=True)
    paid = Column(Boolean, default=False, nullable=False)
    location = Column(String(255), nullable=True)
    remote = Column(Boolean, default=False, nullable=False)
    duration = Column(String(100), nullable=True)
    skills = Column(String(500), nullable=True)  # Stored as comma-separated text
    source = Column(String(100), nullable=False, index=True)
    legitimacy_score = Column(Integer, default=50, nullable=False, index=True)
    confidence_score = Column(Integer, default=50, nullable=False, index=True)
    stipend_numeric = Column(Integer, default=0, nullable=False, index=True)
    posted_at = Column(DateTime, nullable=True, index=True)
    freshness_score = Column(Integer, default=0, nullable=False, index=True)
    confidence = Column(String(50), default="HIGH", nullable=False)
    confidence_tier = Column(String(50), default="HIGH_CONFIDENCE", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    inactive_reason = Column(String(255), nullable=True)
    last_seen = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    deactivated_at = Column(DateTime, nullable=True, index=True)
    consecutive_failures = Column(Integer, default=0, nullable=False)
    description = Column(String(5000), nullable=True)  # Stored text description
    relevance_score = Column(Integer, default=0, nullable=False, index=True)
    relevance_tier = Column(String(50), default="IRRELEVANT", nullable=False)
    role_category = Column(String(50), default="Other", nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    def to_dict(self):
        """Helper to convert model instance to dictionary."""
        return {
            "company_name": self.company_name,
            "role": self.role,
            "stipend": self.stipend,
            "paid": self.paid,
            "location": self.location,
            "remote": self.remote,
            "duration": self.duration,
            "skills": self.skills,
            "apply_link": self.apply_link,
            "source": self.source,
            "legitimacy_score": self.legitimacy_score,
            "confidence_score": self.confidence_score,
            "stipend_numeric": self.stipend_numeric,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
            "posted_at": self.posted_at.strftime("%Y-%m-%d %H:%M:%S") if self.posted_at else None,
            "freshness_score": self.freshness_score,
            "confidence": self.confidence,
            "confidence_tier": self.confidence_tier,
            "description": self.description,
            "relevance_score": self.relevance_score,
            "relevance_tier": self.relevance_tier,
            "role_category": self.role_category,
            "is_active": self.is_active,
            "inactive_reason": self.inactive_reason,
            "last_seen": self.last_seen.strftime("%Y-%m-%d %H:%M:%S") if self.last_seen else None,
            "deactivated_at": self.deactivated_at.strftime("%Y-%m-%d %H:%M:%S") if self.deactivated_at else None,
            "consecutive_failures": self.consecutive_failures
        }


class InternshipRejection(Base):
    __tablename__ = 'internship_rejections'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    company_name = Column(String(255), nullable=False)
    role = Column(String(255), nullable=False)
    source = Column(String(100), nullable=False, index=True)
    reasons = Column(String(500), nullable=False)  # Stored as comma-separated reasons
    relevance_score = Column(Integer, default=0, nullable=False)
    legitimacy_score = Column(Integer, default=0, nullable=False)
    confidence_score = Column(Integer, default=0, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
            "company_name": self.company_name,
            "role": self.role,
            "source": self.source,
            "reasons": self.reasons,
            "relevance_score": self.relevance_score,
            "legitimacy_score": self.legitimacy_score,
            "confidence_score": self.confidence_score
        }


class SourceHealth(Base):
    __tablename__ = 'source_health'
    
    source = Column(String(100), primary_key=True, nullable=False)
    last_successful_scrape = Column(DateTime, nullable=True)
    last_failure = Column(DateTime, nullable=True)
    health_status = Column(String(50), default="UNKNOWN", nullable=False)
    last_jobs_found = Column(Integer, default=0, nullable=False)
    last_jobs_saved = Column(Integer, default=0, nullable=False)
    success_count = Column(Integer, default=0, nullable=False)
    failure_count = Column(Integer, default=0, nullable=False)

    def to_dict(self):
        return {
            "source": self.source,
            "last_successful_scrape": self.last_successful_scrape.strftime("%Y-%m-%d %H:%M:%S") if self.last_successful_scrape else None,
            "last_failure": self.last_failure.strftime("%Y-%m-%d %H:%M:%S") if self.last_failure else None,
            "health_status": self.health_status,
            "last_jobs_found": self.last_jobs_found,
            "last_jobs_saved": self.last_jobs_saved,
            "success_count": self.success_count,
            "failure_count": self.failure_count
        }
