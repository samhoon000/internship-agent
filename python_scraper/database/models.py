from datetime import datetime
from sqlalchemy import Column, String, Boolean, Integer, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Internship(Base):
    __tablename__ = 'internships'
    
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
    source = Column(String(100), nullable=False)
    legitimacy_score = Column(Integer, default=50, nullable=False)
    stipend_numeric = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

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
            "stipend_numeric": self.stipend_numeric,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None
        }
