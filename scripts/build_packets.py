#!/usr/bin/env python3
"""Build interview research packets for top-scoring jobs.

Pulls jobs from the database, generates comprehensive research packets
using web research, and saves them to projects/interview-packet/.

Usage:
    python3 build_packets.py                  # Build packets for all will_apply jobs
    python3 build_packets.py --top 5          # Build for top 5 by match score
    python3 build_packets.py --job-id 1234    # Build for specific job
    python3 build_packets.py --force          # Rebuild even if packet exists
"""
import sys
import os
import json
import sqlite3
import subprocess
import re
from datetime import datetime
from pathlib import Path

# Paths
PROJECT_DIR = Path(__file__).parent.parent
DB_PATH = PROJECT_DIR / "data" / "jobs.db"
PACKETS_DIR = Path.home() / "projects/interview-packet"
MEMORY_DIR = Path.home() / ".hermes/memory"


def get_db():
    """Get SQLAlchemy session for packet storage."""
    import sys
    sys.path.insert(0, str(PROJECT_DIR / 'backend'))
    from database import SessionLocal
    return SessionLocal()


def get_jobs(db, job_id=None, top=None):
    """Get jobs to build packets for."""
    from models import Job
    query = db.query(Job).filter(Job.status == 'will_apply', Job.match_score > 0)
    
    if job_id:
        query = query.filter(Job.id == job_id)
    
    query = query.order_by(Job.match_score.desc())
    
    if top:
        query = query.limit(top)
    
    rows = query.all()
    return [{c.name: getattr(row, c.name) for c in row.__table__.columns} for row in rows]


def get_michael_context():
    """Load Michael's resume/experience context for packet generation."""
    context_path = PROJECT_DIR / "data" / "profile.json"
    if context_path.exists():
        with open(context_path) as f:
            return json.load(f)
    
    # Fallback: try to get from database
    db = get_db()
    try:
        from models import Profile
        profile = db.query(Profile).first()
        if profile:
            return {
                'resume_text': profile.resume_text or '',
                'location': profile.location or '',
                'preferred_titles': profile.preferred_titles or '',
                'preferences': profile.preferences or '',
            }
    finally:
        db.close()
    return {}


def generate_packet(job, profile):
    """Generate a research packet markdown for a job."""
    company = job.get('company', 'Unknown')
    title = job.get('title', 'Unknown')
    match_score = job.get('match_score', 0)
    description = job.get('description', '')
    url = job.get('url', '')
    location = job.get('location', 'Not specified')
    salary_min = job.get('salary_min')
    salary_max = job.get('salary_max')
    source = job.get('source', 'unknown')
    date_posted = job.get('date_posted', '')
    
    # Clean description
    if description:
        description = re.sub(r'\\n', '\n', description)
        description = re.sub(r'\\-', '-', description)
        description = re.sub(r'\*\\*\\*\\*\\*\\*\\*\\*\\*', '', description)
    
    salary_str = "Not listed"
    if salary_min and salary_max:
        salary_str = f"${salary_min:,.0f} – ${salary_max:,.0f}"
    elif salary_min:
        salary_str = f"${salary_min:,.0f}+"
    
    # Generate packet
    packet = f"""# Interview Research Packet — {company}
**Role:** {title}  
**Location:** {location}  
**Match Score:** {match_score}/100  
**Salary Range:** {salary_str}  
**Source:** {source}  
**Posted:** {date_posted}  
**Link:** {url}  
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}  

---

## Company Overview

**{company}** — Research needed. This section should be populated with:
- Company founding year, size, industry
- Headquarters and office locations  
- Key products/services
- Recent news, acquisitions, or layoffs
- Company culture and values
- Parent company (if applicable)

---

## Job Description

{description}

---

## Role Breakdown

### Key Technologies
*(Extract from job description)*

### Responsibilities
*(Summarize from job description)*

### What Makes This Role Interesting
*(Analysis of the opportunity)*

---

## Michael's Fit Analysis

### Direct Matches ✅
*(Map job requirements to Michael's experience)*

### Strong Partial Matches 🟡
*(Skills that partially match)*

### Gaps to Address ⚠️
*(Areas that may need attention)*

---

## Likely Interview Questions & Suggested Answers

### Technical Questions
*(Role-specific technical questions with answer frameworks)*

### Behavioral Questions
*(Common behavioral questions with suggested responses)*

---

## Questions to Ask Them

*(Strategic questions for the interview)*

---

## Networking Opportunities

*(People to find, approach strategies)*

---

## Risk Assessment

| Risk | Level | Notes |
|---|---|---|
| *(Risk factors)* | | |

---

## Bottom Line

*(Summary recommendation)*
"""
    
    return packet


def save_packet(job, packet_text, db):
    """Save packet to file and database."""
    company = job.get('company', 'unknown').lower().replace("'", "").replace(' ', '-')
    date_str = datetime.now().strftime('%Y-%m-%d')
    filename = f"{company}-{date_str}.md"
    
    PACKETS_DIR.mkdir(parents=True, exist_ok=True)
    filepath = PACKETS_DIR / filename
    
    with open(filepath, 'w') as f:
        f.write(packet_text)
    
    # Save to database
    try:
        sys.path.insert(0, str(PROJECT_DIR / 'backend'))
        from models import ResearchPacket
        job_id = job.get('id')
        existing = db.query(ResearchPacket).filter(ResearchPacket.job_id == job_id).first()
        if existing:
            existing.content = packet_text
            existing.updated_at = datetime.now()
        else:
            pkt = ResearchPacket(job_id=job_id, content=packet_text)
            db.add(pkt)
        db.commit()
    except Exception as e:
        print(f"  ⚠️  DB save failed: {e}")
        db.rollback()
    
    return str(filepath)


def packet_exists(job):
    """Check if a packet already exists for this job."""
    company = job.get('company', 'unknown').lower().replace("'", "").replace(' ', '-')
    date_str = datetime.now().strftime('%Y-%m-%d')
    filename = f"{company}-{date_str}.md"
    return (PACKETS_DIR / filename).exists()


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Build interview research packets')
    parser.add_argument('--top', type=int, help='Build for top N jobs by match score')
    parser.add_argument('--job-id', type=int, help='Build for specific job ID')
    parser.add_argument('--force', action='store_true', help='Rebuild even if packet exists')
    args = parser.parse_args()
    
    # Path setup & import run_status
    import sys
    sys.path.insert(0, str(PROJECT_DIR / 'backend'))
    from run_status import update_process_status
    
    update_process_status('researcher', running=True, started_at=datetime.utcnow().isoformat() + 'Z')
    
    try:
        db = get_db()
        profile = get_michael_context()
        jobs = get_jobs(db, job_id=args.job_id, top=args.top)
        
        if not jobs:
            print("No jobs found matching criteria.")
            update_process_status('researcher', running=False, finished_at=datetime.utcnow().isoformat() + 'Z', result={'packets_built': 0})
            return []
        
        print(f"Building research packets for {len(jobs)} job(s)...")
        
        results = []
        for job in jobs:
            company = job.get('company', 'Unknown')
            title = job.get('title', 'Unknown')
            score = job.get('match_score', 0)
            job_id = job.get('id')
            
            # Check if database already has a packet
            from models import ResearchPacket
            existing_pkt = db.query(ResearchPacket).filter(ResearchPacket.job_id == job_id).first()
            
            if not args.force:
                if existing_pkt and "Research needed" not in (existing_pkt.content or ""):
                    if not packet_exists(job):
                        print(f"  💾 {company} — {title} (researched packet exists in DB, writing to disk file)")
                        filepath = save_packet(job, existing_pkt.content, db)
                        results.append({
                            'company': company,
                            'title': title,
                            'score': score,
                            'path': filepath
                        })
                    else:
                        print(f"  ⏭️  {company} — {title} (researched packet already exists in DB and disk, skipping)")
                    continue
                
                if packet_exists(job):
                    print(f"  ⏭️  {company} — {title} (skeleton packet exists on disk, skipping)")
                    continue
            
            print(f"  📝 {company} — {title} (score: {score})")
            packet = generate_packet(job, profile)
            filepath = save_packet(job, packet, db)
            results.append({
                'company': company,
                'title': title,
                'score': score,
                'path': filepath
            })
            print(f"     → {filepath}")
        
        print(f"\n✅ Built {len(results)} research packet(s)")
        
        # Write manifest for agent consumption
        manifest_path = PACKETS_DIR / "latest-manifest.json"
        with open(manifest_path, 'w') as f:
            json.dump({
                'generated_at': datetime.now().isoformat(),
                'packets': results
            }, f, indent=2)
        
        update_process_status('researcher', running=False, finished_at=datetime.utcnow().isoformat() + 'Z', result={'packets_built': len(results)})
        return results
    except Exception as e:
        update_process_status('researcher', running=False, finished_at=datetime.utcnow().isoformat() + 'Z', error=str(e))
        raise e


if __name__ == '__main__':
    main()
