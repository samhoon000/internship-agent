from datetime import datetime
from sqlalchemy import Column, String, Boolean, Integer, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Internship(Base):
    __tablename__ = 'internships'
    
    # Using apply_link as the primary key perfectly matches your requested schema 
    # columns without introducing an extra 'id' column.
    apply_link = Column(String, primary_key=True, nullable=False)
    
    company_name = Column(String, nullable=False)
    role = Column(String, nullable=False)
    stipend = Column(String, nullable=True)
    paid = Column(Boolean, default=False, nullable=False)
    location = Column(String, nullable=True)
    remote = Column(Boolean, default=False, nullable=False)
    duration = Column(String, nullable=True)
    skills = Column(String, nullable=True)  # Stored as comma-separated text
    source = Column(String, nullable=False)
    legitimacy_score = Column(Integer, default=50, nullable=False)
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
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None
        }
