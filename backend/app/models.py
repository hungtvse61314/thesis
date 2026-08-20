from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from .database import Base


class CV(Base):
    __tablename__ = "cvs"

    id = Column(Integer, primary_key=True)
    candidate_id = Column(String(100), unique=True, index=True, nullable=False)
    file_name = Column(String(255))
    file_path = Column(String(1000))
    source_type = Column(String(50), default="real")
    role_title = Column(String(255))
    raw_text = Column(Text, nullable=False)
    clean_text = Column(Text, nullable=False)
    sections_json = Column(Text, default="{}")
    skills_json = Column(Text, default="[]")
    years_experience = Column(Float, default=0)
    seniority = Column(String(30), default="unknown")
    parse_status = Column(String(80), default="ok")
    created_at = Column(DateTime, server_default=func.now())


class JobDescription(Base):
    __tablename__ = "job_descriptions"

    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    requirements_json = Column(Text, default="[]")
    minimum_years = Column(Float, default=0)
    required_seniority = Column(String(30), default="unknown")
    created_at = Column(DateTime, server_default=func.now())


class ReviewerLabel(Base):
    __tablename__ = "reviewer_labels"

    id = Column(Integer, primary_key=True)
    jd_id = Column(Integer, ForeignKey("job_descriptions.id"), index=True)
    cv_id = Column(Integer, ForeignKey("cvs.id"), index=True)
    reviewer = Column(String(100), default="reviewer")
    label = Column(Integer, nullable=False)
    note = Column(Text, default="")
    created_at = Column(DateTime, server_default=func.now())
