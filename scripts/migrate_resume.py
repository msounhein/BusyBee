#!/usr/bin/env python3
"""One-time migration: parse existing resume_text blob into structured tables."""

import sys
import os
import re
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from database import init_db, SessionLocal, engine, Base
from models import (
    Profile, ResumeProfile, ResumeExperience,
    ResumeEducation, ResumeSkillCategory,
)


def parse_resume_text(text):
    """Parse the existing resume text blob into structured data."""
    if not text or not text.strip():
        return None, [], [], []

    lines = text.strip().split('\n')
    current_section = 'header'
    current_job = None

    name = ''
    contact_parts = []
    summary = ''
    experience = []
    education = []
    skills_text = ''

    _SECTION_KEYWORDS = {
        'qualifications', 'professional summary', 'summary', 'objective', 'profile',
        'experience', 'work experience', 'employment', 'professional experience',
        'education', 'academic background', 'skills', 'technical skills',
        'core competencies', 'technologies', 'certifications',
    }

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        lower = stripped.lower()

        # Name detection
        if current_section == 'header' and not name:
            if lower.startswith('name:'):
                name = stripped[5:].strip()
                continue
            if (lower not in _SECTION_KEYWORDS
                    and '@' not in stripped
                    and '|' not in stripped
                    and not stripped.startswith('(')
                    and not stripped.endswith(':')):
                name = stripped
                continue

        # Contact info
        if any(kw in lower for kw in ['email', 'phone', 'linkedin', 'address', 'location']):
            if '@' in stripped or any(c.isdigit() for c in stripped):
                contact_parts.append(stripped)
                current_section = 'header'
                continue

        # Section headers
        if lower in ('summary', 'professional summary', 'objective', 'profile', 'qualifications'):
            current_section = 'summary'
            continue
        if lower in ('experience', 'work experience', 'employment', 'professional experience'):
            current_section = 'experience'
            continue
        if lower in ('education', 'academic background'):
            current_section = 'education'
            continue
        if lower.startswith(('skills', 'technical skills', 'core competencies', 'technologies')):
            current_section = 'skills'
            after_colon = stripped[stripped.index(':') + 1:].strip() if ':' in stripped else ''
            if after_colon:
                skills_text += ('\n' if skills_text else '') + after_colon
            continue

        # Content by section
        if current_section == 'summary':
            summary += (' ' if summary else '') + stripped
        elif current_section == 'experience':
            # Job header line: contains a date or has pipe separators
            if re.search(r'\d{4}', stripped) or (stripped and '|' in stripped):
                if current_job:
                    experience.append(current_job)
                current_job = {'title_company': stripped, 'bullets': []}
            elif stripped.startswith('-') or stripped.startswith('•'):
                bullet = stripped.lstrip('-•').strip()
                if current_job:
                    current_job['bullets'].append(bullet)
            elif current_job:
                current_job['bullets'].append(stripped)
        elif current_section == 'education':
            education.append(stripped)
        elif current_section == 'skills':
            skills_text += ('\n' if skills_text else '') + stripped

    if current_job:
        experience.append(current_job)

    return name, contact_parts, summary, experience, education, skills_text


def parse_title_company(tc_str):
    """Split 'Title | Company, Location | Dates' into components."""
    parts = [p.strip() for p in tc_str.split('|')]
    if len(parts) >= 3:
        return parts[0], parts[1].rsplit(',', 1)[0].strip(), parts[1], parts[2]
    elif len(parts) == 2:
        return parts[0], '', '', parts[1]
    else:
        return tc_str, '', '', ''


def parse_dates(date_str):
    """Parse '2019 - December 2024' into (start_date, end_date)."""
    date_str = date_str.strip()
    if ' - ' in date_str:
        start, end = date_str.split(' - ', 1)
        return start.strip(), end.strip()
    elif '-' in date_str:
        parts = date_str.split('-', 1)
        return parts[0].strip(), parts[1].strip()
    return date_str, ''


def parse_skills_text(skills_text):
    """Parse newline-separated skill categories into (name, skills) tuples."""
    categories = []
    for line in skills_text.split('\n'):
        line = line.strip()
        if not line:
            continue
        m = re.match(r'([A-Za-z][A-Za-z0-9/&\s]+?):\s*(.*)', line)
        if m:
            cat = m.group(1).strip()
            skills = m.group(2).strip().rstrip(',').strip()
            if cat and skills:
                categories.append((cat, skills))
    return categories


def parse_education(edu_str):
    """Parse education string into (institution, degree, field, gpa, dates)."""
    edu_str = edu_str.strip()
    gpa = ''
    dates = ''

    # Extract GPA if present
    gpa_match = re.search(r'GPA:\s*([0-9.]+)', edu_str)
    if gpa_match:
        gpa = gpa_match.group(1)

    # Extract dates if in parentheses at the end
    date_match = re.search(r'\((\d{4})\s*\)', edu_str)
    if date_match:
        dates = date_match.group(1)

    # Split on dash to get degree/institution
    if ' - ' in edu_str:
        degree_part, institution = edu_str.rsplit(' - ', 1)
        # Clean up institution (remove GPA/dates)
        institution = re.sub(r'\s*\(GPA:.*?\)', '', institution).strip()
    elif ' -' in edu_str:
        degree_part, institution = edu_str.rsplit('-', 1)
        institution = institution.strip()
    else:
        degree_part = edu_str
        institution = ''

    # Split degree into degree and field
    degree = degree_part.strip()
    field = ''

    return institution, degree, field, gpa, dates


def migrate():
    init_db()
    db = SessionLocal()

    # Check if already migrated
    existing = db.query(ResumeProfile).first()
    if existing:
        print("ResumeProfile already exists. Skipping migration.")
        print("  To re-migrate, delete existing structured data first.")
        db.close()
        return

    profile = db.query(Profile).first()
    if not profile or not profile.resume_text:
        print("No Profile with resume_text found. Nothing to migrate.")
        db.close()
        return

    text = profile.resume_text
    print(f"Migrating resume_text ({len(text)} chars)...")

    name, contact_parts, summary, experience_raw, education_raw, skills_text = parse_resume_text(text)

    # Extract email, phone from contact_parts
    email = ''
    phone = ''
    location = profile.location or 'Appleton, WI'
    for cp in contact_parts:
        cp_lower = cp.lower()
        if '@' in cp:
            email = cp
        elif any(c.isdigit() for c in cp) and not '@' in cp:
            phone = cp
        if 'location' in cp_lower or 'address' in cp_lower:
            location = cp.split(':', 1)[-1].strip() if ':' in cp else cp

    # Create ResumeProfile
    rp = ResumeProfile(
        full_name=name or 'Michael Sounhein',
        email=email,
        phone=phone,
        location=location,
        linkedin_url='',
        summary=summary,
    )
    db.add(rp)
    print(f"  ResumeProfile: name={rp.full_name}, summary={len(rp.summary)} chars")

    # Create ResumeExperience entries
    for i, exp_raw in enumerate(experience_raw):
        tc = exp_raw['title_company']
        title, company_stub, full_company, dates = parse_title_company(tc)
        start_date, end_date = parse_dates(dates) if dates else ('', '')

        # Extract location from company field if present
        exp_location = ''
        if ',' in full_company:
            company_stub_clean = full_company.rsplit(',', 1)[0].strip()
            exp_location = full_company
            company_stub = company_stub_clean
        else:
            company_stub = full_company or company_stub

        re_entry = ResumeExperience(
            company=company_stub,
            title=title,
            location=exp_location,
            start_date=start_date,
            end_date=end_date,
            bullets=json.dumps(exp_raw['bullets']),
            sort_order=i,
        )
        db.add(re_entry)
        print(f"  Experience: {title} @ {company_stub} ({len(exp_raw['bullets'])} bullets)")

    # Create ResumeEducation entries
    for i, edu_raw in enumerate(education_raw):
        institution, degree, field, gpa, dates = parse_education(edu_raw)
        re_edu = ResumeEducation(
            institution=institution,
            degree=degree,
            field_of_study=field,
            gpa=gpa,
            dates=dates,
            sort_order=i,
        )
        db.add(re_edu)
        print(f"  Education: {degree} @ {institution}")

    # Create ResumeSkillCategory entries
    skill_cats = parse_skills_text(skills_text)
    for i, (cat_name, skills) in enumerate(skill_cats):
        rsc = ResumeSkillCategory(
            category_name=cat_name,
            skills=skills,
            sort_order=i,
        )
        db.add(rsc)
        print(f"  Skills: {cat_name} ({len(skills)} chars)")

    db.commit()
    print(f"\nMigration complete!")
    print(f"  {len(experience_raw)} experience entries")
    print(f"  {len(education_raw)} education entries")
    print(f"  {len(skill_cats)} skill categories")
    print(f"  Resume text blob preserved on Profile for backup.")

    db.close()


if __name__ == '__main__':
    migrate()
