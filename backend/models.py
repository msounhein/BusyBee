from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Date
from database import Base
from datetime import datetime


class Job(Base):
    __tablename__ = 'jobs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(50), nullable=False)
    source_id = Column(String(255), nullable=False)
    title = Column(String(255), nullable=False)
    company = Column(String(255), nullable=False)
    location = Column(String(255))
    job_type = Column(String(50))
    remote = Column(Boolean, default=False)
    distance_miles = Column(Integer, nullable=True)
    salary_min = Column(Integer, nullable=True)
    salary_max = Column(Integer, nullable=True)
    description = Column(Text)
    url = Column(Text, nullable=False)
    status = Column(String(50), default='new')
    apply_note = Column(Text, nullable=True)
    match_score = Column(Integer, default=0)
    match_reasoning = Column(Text)
    rejection_reason = Column(Text, nullable=True)
    score_attempts = Column(Integer, default=0)
    score_error = Column(Text, nullable=True)
    score_failed_at = Column(DateTime, nullable=True)
    posted_date = Column(Date, nullable=True)
    found_date = Column(DateTime, default=datetime.utcnow)
    applied_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        {'sqlite_autoincrement': True},
    )


class SearchTerm(Base):
    __tablename__ = 'search_terms'

    id = Column(Integer, primary_key=True, autoincrement=True)
    term = Column(String(255), nullable=False, unique=True)
    source = Column(String(50), default='user')
    active = Column(Boolean, default=True)
    last_used = Column(DateTime, nullable=True)
    hit_count = Column(Integer, default=0)


class Profile(Base):
    __tablename__ = 'profile'

    id = Column(Integer, primary_key=True, default=1)
    resume_text = Column(Text, default='')
    location = Column(String(255), default='Appleton, WI')
    max_distance = Column(Integer, default=25)
    preferred_titles = Column(Text, default='["IT Systems Administrator", "Endpoint Engineer", "Desktop Support Engineer"]')
    dealbreakers = Column(Text, default='["WSI", "Marion Body Works"]')
    preferences = Column(Text, default='{"focus": "end-user computing, MECM/PDQ, PowerShell"}')
    scrape_linkedin = Column(Boolean, default=True)
    scrape_indeed = Column(Boolean, default=True)
    scrape_himalayas = Column(Boolean, default=True)
    scrape_remotive = Column(Boolean, default=True)
    scrape_wwr = Column(Boolean, default=True)
    llm_provider = Column(String(50), default='zai')
    llm_api_key = Column(String(255), default='')
    llm_model = Column(String(255), default='glm-5.1')
    llm_api_url = Column(String(500), default='')


class RejectionPattern(Base):
    __tablename__ = 'rejection_patterns'

    id = Column(Integer, primary_key=True, autoincrement=True)
    pattern = Column(Text, nullable=False)
    source = Column(String(50), default='ai')
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class BlockedCompany(Base):
    __tablename__ = 'blocked_companies'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class TailoredResume(Base):
    __tablename__ = 'tailored_resumes'

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, nullable=False)
    chat_history = Column(Text, nullable=True)  # JSON of the conversation
    resume_html = Column(Text, nullable=True)   # HTML content for PDF generation
    resume_docx_path = Column(Text, nullable=True)  # Path to DOCX file
    resume_pdf_path = Column(Text, nullable=True)   # Path to PDF file
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        {'sqlite_autoincrement': True},
    )


class ResearchPacket(Base):
    __tablename__ = 'research_packets'

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, nullable=False, unique=True)
    content = Column(Text, default='')  # Full markdown content
    company_research = Column(Text, default='')
    role_analysis = Column(Text, default='')
    fit_analysis = Column(Text, default='')
    interview_prep = Column(Text, default='')
    questions_to_ask = Column(Text, default='')
    risk_assessment = Column(Text, default='')
    bottom_line = Column(Text, default='')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PacketFeedback(Base):
    __tablename__ = 'packet_feedback'

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, nullable=False)
    section = Column(String(100), nullable=False)  # e.g. 'fit_analysis', 'interview_prep'
    feedback_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# ─── Structured Resume Models ──────────────────────────────

class ResumeProfile(Base):
    __tablename__ = 'resume_profile'

    id = Column(Integer, primary_key=True, default=1)
    full_name = Column(String(255), default='Michael Sounhein')
    email = Column(String(255), default='')
    phone = Column(String(50), default='')
    location = Column(String(255), default='Appleton, WI')
    linkedin_url = Column(String(500), default='')
    github_url = Column(String(500), default='')
    summary = Column(Text, default='')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ResumeExperience(Base):
    __tablename__ = 'resume_experience'

    id = Column(Integer, primary_key=True, autoincrement=True)
    company = Column(String(255), nullable=False)
    title = Column(String(255), nullable=False)
    location = Column(String(255), default='')
    start_date = Column(String(50), default='')
    end_date = Column(String(50), default='')
    bullets = Column(Text, default='[]')  # JSON array of strings
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class ResumeEducation(Base):
    __tablename__ = 'resume_education'

    id = Column(Integer, primary_key=True, autoincrement=True)
    institution = Column(String(255), nullable=False)
    degree = Column(String(255), default='')
    field_of_study = Column(String(255), default='')
    gpa = Column(String(20), default='')
    dates = Column(String(100), default='')
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class ResumeSkillCategory(Base):
    __tablename__ = 'resume_skill_categories'

    id = Column(Integer, primary_key=True, autoincrement=True)
    category_name = Column(String(255), nullable=False)
    skills = Column(Text, default='')  # comma-separated skill names
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
