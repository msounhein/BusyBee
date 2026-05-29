import json
import time
import logging
import os
import subprocess
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from sqlalchemy.orm.exc import StaleDataError
from models import Job, SearchTerm, BlockedCompany
from config import Config
from llm_client import call_llm

log = logging.getLogger(__name__)

MAX_SCORE_ATTEMPTS = 3
SCORE_RETRY_DELAYS = [10, 30, 60]  # seconds — exponential-ish backoff between attempts
SCORE_TIMEOUT = 300  # per-job LLM call timeout
BATCH_SIZE = 10
MAX_TOTAL = 200
AUTO_REJECT_SCORE = -1


def is_fake_remote(job):
    """Detect jobs marked remote but actually require on-site presence.
    Only fires on EXPLICIT on-site requirement language — not on HQ addresses.
    """
    import re
    desc = (job.description or '').lower()

    # If jobspy flagged it as remote, trust it — location in desc is likely HQ address
    if job.remote or (job.job_type or '').lower() == 'remote':
        # Only override if there are EXPLICIT on-site requirement phrases
        hard_onsite = [
            r'on[- ]?site (?:only|required|mandatory)',
            r'in[- ]?office (?:only|required|mandatory)',
            r'must (?:be able to |)report to (?:our |the |)office',
            r'must (?:be |)on[- ]?site',
            r'100%\s*on[- ]?site',
            r'this (?:is |)(?:not|not a) remote (?:position|role|job|opportunity)',
            r'not a remote (?:position|role|job)',
            r'required to (?:be|work|report) (?:in[- ]?office|on[- ]?site)',
        ]
        return any(re.search(p, desc) for p in hard_onsite)

    # For jobs NOT flagged remote by jobspy, apply the same hard checks
    hard_onsite = [
        r'on[- ]?site (?:only|required|mandatory)',
        r'in[- ]?office (?:only|required|mandatory)',
        r'must (?:be able to |)report to (?:our |the |)office',
        r'must (?:be |)on[- ]?site',
        r'100%\s*on[- ]?site',
        r'this (?:is |)(?:not|not a) remote (?:position|role|job|opportunity)',
        r'required to (?:be|work|report) (?:in[- ]?office|on[- ]?site)',
    ]
    return any(re.search(p, desc) for p in hard_onsite)


def score_job_with_retry(job, resume_text, behavior_context=""):
    """Score a single job with retry logic. Returns (result_dict, attempts, last_error)."""
    last_error = None

    for attempt in range(1, MAX_SCORE_ATTEMPTS + 1):
        job.score_attempts = attempt
        try:
            result = _call_llm_for_score(job, resume_text, behavior_context)
            return result, attempt, None
        except Exception as e:
            last_error = str(e)
            log.warning(f"Score attempt {attempt}/{MAX_SCORE_ATTEMPTS} failed for job {job.id} ({job.title}): {e}")
            if attempt < MAX_SCORE_ATTEMPTS:
                delay = SCORE_RETRY_DELAYS[min(attempt - 1, len(SCORE_RETRY_DELAYS) - 1)]
                log.info(f"Retrying job {job.id} in {delay}s...")
                time.sleep(delay)

    return None, MAX_SCORE_ATTEMPTS, last_error


def _call_llm_for_score_raw(title, company, location, remote, description, resume_text, behavior_context=""):
    """Single LLM call to score a job using raw primitive values. Raises on failure."""
    behavior_section = ""
    if behavior_context:
        behavior_section = f"""
BEHAVIORAL CONTEXT (learned from user's past decisions):
{behavior_context}

Use this context to adjust your score. Penalize jobs matching rejection patterns. Boost jobs matching preferences."""

    prompt = f"""You are an expert IT job matcher. First, you MUST strictly verify the job location and work arrangement constraints.

LOCATION AND WORK ARRANGEMENT CONSTRAINTS:
1. The job MUST be EITHER:
   - Local: Located within 30 miles of Appleton, WI. Surrounding Wisconsin cities in this search area are: Appleton, Neenah, Menasha, Oshkosh, Green Bay, De Pere, Kaukauna, Little Chute, Kimberly, Combined Locks, Sherwood, Greenville, Hortonville, New London, Black Creek, Freedom, Wrightstown, Shiocton, and Seymour.
   - Fully Remote: 100% remote / work from home from anywhere in the United States, or specifically remote for Wisconsin residents.
     * CRITICAL: If the job location or description indicates it is restricted to a specific non-Wisconsin geographic region (e.g., "Must reside in California", "California residents only", or "Location: California" with no mention of nationwide remote), it is NOT remote for the candidate and MUST be rejected with reasoning "location".
     * CRITICAL: If the job requires being close to or visiting an office outside Wisconsin, it is NOT fully remote and MUST be rejected with reasoning "location".

2. Absolutely NO Hybrid roles:
   * Reject the job if the description, requirements, or benefits section contains terms like "Hybrid", "hybrid working", "mix of working from home and in the office", "partial work from home", "2-3 days in office", "office presence", or any in-person/on-site requirements (even if the job header claims "Remote").
   * General company benefit listings describing hybrid models, office amenities, or flexible hybrid structures count as hybrid/on-site requirements unless the description explicitly and unconditionally overrides it to state that this specific position is 100% remote from anywhere in the US.
   * If there is ANY conflict, ambiguity, or doubt (e.g. the header says "remote" but the text mentions "hybrid", "in office", or "onsite"), you MUST err on the side of caution and reject the job.

If the location and work arrangement constraints are NOT met, you MUST reject the job immediately.
To reject the job, you must respond in this exact JSON format:
{{"score": -1, "reasoning": "location", "title_variant": null}}

If (and only if) the location and work arrangement constraints are fully met, score the job from 0-100 how well it matches the candidate's resume and preferences.

RESUME:
{resume_text}
{behavior_section}

JOB TITLE: {title}
COMPANY: {company}
LOCATION: {location}
REMOTE: {remote}
DESCRIPTION:
{description[:15000]}

Score from 0-100 how well this job matches. Consider:
- Skills alignment (PowerShell, MECM, endpoint management)
- Experience level match
- Job type preference (end-user computing > backend server)
- Remote preference
- Behavioral context if provided above

Respond in this exact JSON format only:
{{"score": <number 0-100 or -1>, "reasoning": "<explanation or 'location'>", "title_variant": "<suggested search term or null>"}}"""

    result = call_llm(
        [{'role': 'user', 'content': prompt}],
        temperature=0.3,
        max_tokens=8192,
        timeout=SCORE_TIMEOUT,
    )
    content = result['content']

    # Strip any non-JSON text before the first { or [
    content = content.strip()
    if '```json' in content:
        content = content.split('```json')[1].split('```')[0].strip()
    elif '```' in content:
        content = content.split('```')[1].split('```')[0].strip()

    # Find the first JSON object
    for start_char, end_char in [('{', '}'), ('[', ']')]:
        start_idx = content.find(start_char)
        if start_idx >= 0:
            # Find matching closing bracket
            depth = 0
            for i in range(start_idx, len(content)):
                if content[i] == start_char:
                    depth += 1
                elif content[i] == end_char:
                    depth -= 1
                    if depth == 0:
                        content = content[start_idx:i+1]
                        break
            break

    return json.loads(content.strip())


def _call_llm_for_score(job, resume_text, behavior_context=""):
    """Single LLM call to score a job. Raises on failure."""
    return _call_llm_for_score_raw(
        job.title,
        job.company,
        job.location,
        job.remote,
        job.description or "",
        resume_text,
        behavior_context
    )


# IT-relevant keywords for pre-filtering
IT_KEYWORDS = [
    'it ', 'it,', 'it/', ' it',
    'admin', 'administrator', 'engineer', 'analyst', 'architect', 'developer',
    'support', 'help desk', 'helpdesk', 'desktop', 'technician',
    'systems', 'system', 'network', 'security', 'cloud',
    'devops', 'sre', 'infra', 'infrastructure',
    'intune', 'mecm', 'sccm', 'configmgr', 'endpoint',
    'microsoft', 'azure', 'powershell', 'scripting',
    'm365', 'office 365', 'o365', 'sharepoint',
    'sysadmin', 'sys admin', 'linux', 'windows server',
    'virtualization', 'vmware', 'hyper-v',
    'automation', 'deployment', 'patching',
    'mobility', 'mdm', 'mam',
    'release manager', 'service now', 'servicenow',
    'cloud', 'aws', 'gcp',
]

NON_IT_PATTERNS = [
    'accounting', 'accounts payable', 'accounts receivable',
    'marketing', 'sales rep', 'real estate', 'insurance agent',
    'truck driver', 'delivery driver', 'warehouse',
    'nurse', 'nursing', 'medical assistant', 'dental',
    'food service', 'cashier', 'retail',
    'scheduling coordinator', 'annotator',
    'business development', 'recruiter', 'human resources',
]


def is_likely_it_job(title):
    """Pre-filter: returns True if the job title looks like it could be IT-related."""
    title_lower = title.lower()
    for pattern in NON_IT_PATTERNS:
        if pattern in title_lower:
            return False
    for keyword in IT_KEYWORDS:
        if keyword in title_lower:
            return True
    return False


def get_resume_text(db):
    """Generate a clean plain-text representation of the structured resume for LLM scoring."""
    from models import ResumeProfile, ResumeExperience, ResumeEducation, ResumeSkillCategory
    import json

    profile = db.query(ResumeProfile).first()
    if not profile:
        return ""

    lines = []
    lines.append(f"NAME: {profile.full_name or ''}")
    lines.append(f"EMAIL: {profile.email or ''}")
    lines.append(f"PHONE: {profile.phone or ''}")
    lines.append(f"LOCATION: {profile.location or ''}")
    lines.append(f"LINKEDIN: {profile.linkedin_url or ''}")
    lines.append(f"GITHUB: {profile.github_url or ''}")
    lines.append("")
    lines.append("PROFESSIONAL SUMMARY:")
    lines.append(profile.summary or "")
    lines.append("")

    lines.append("EXPERIENCE:")
    exps = db.query(ResumeExperience).order_by(ResumeExperience.sort_order).all()
    for e in exps:
        lines.append(f"\n{e.title} at {e.company}")
        if e.start_date or e.end_date:
            dates = [p for p in (e.start_date, e.end_date) if p]
            lines.append(" - ".join(dates))
        if e.location:
            lines.append(f"Location: {e.location}")
        bullets = json.loads(e.bullets) if e.bullets else []
        for b in bullets:
            lines.append(f"  - {b}")

    lines.append("")
    lines.append("SKILLS:")
    skills = db.query(ResumeSkillCategory).order_by(ResumeSkillCategory.sort_order).all()
    for s in skills:
        lines.append(f"- {s.category_name}: {s.skills}")

    lines.append("")
    lines.append("EDUCATION:")
    edu = db.query(ResumeEducation).order_by(ResumeEducation.sort_order).all()
    for ed in edu:
        lines.append(f"- {ed.degree or ''} in {ed.field_of_study or ''} from {ed.institution or ''} ({ed.dates or ''})")

    return "\n".join(lines)


def is_job_local(job_location):
    """
    Check if the job location is within Appleton, WI, or surrounding towns/cities (within 25 miles).
    """
    if not job_location:
        return False
    loc_lower = job_location.lower().strip()
    
    local_keywords = [
        "appleton", "neenah", "menasha", "oshkosh", "green bay", 
        "de pere", "kaukauna", "little chute", "kimberly", 
        "combined locks", "sherwood", "greenville", "hortonville", 
        "new london", "black creek", "freedom", "wrightstown", 
        "shiocton", "seymour"
    ]
    
    has_local_city = any(city in loc_lower for city in local_keywords)
    if not has_local_city:
        return False
        
    # Also check if it's in Wisconsin. If it specifies another state (e.g. Appleton, MN), it's not local.
    import re
    state_match = re.search(r'\b([a-z]{2})\b', loc_lower)
    if state_match:
        state = state_match.group(1)
        if state != 'wi' and state != 'wisconsin':
            return False
            
    return True


def extract_linkedin_id(url):
    import re
    if not url:
        return None
    match = re.search(r'/view/(\d+)', url)
    if match:
        return match.group(1)
    match = re.search(r'currentJobId=(\d+)', url)
    if match:
        return match.group(1)
    return None


def fetch_linkedin_guest_details_raw(url):
    """
    Fetches the LinkedIn Guest API page for the job, extracts title, company,
    location, and description, and returns a dictionary of parsed details.
    """
    import requests
    from bs4 import BeautifulSoup
    
    job_id = extract_linkedin_id(url)
    if not job_id:
        return False, "Could not extract LinkedIn Job ID", {}
        
    guest_url = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        resp = requests.get(guest_url, headers=headers, timeout=15)
        if resp.status_code != 200:
            return False, f"HTTP status {resp.status_code}", {}
            
        soup = BeautifulSoup(resp.text, 'html.parser')
        data = {}
        
        # 1. Parse Location
        location_el = soup.find('span', class_='topcard__flavor--bullet')
        if location_el:
            location_text = location_el.get_text(strip=True)
            if location_text:
                data['location'] = location_text
                
        # 2. Parse Title (if missing or raw)
        title_el = (
            soup.find('h1') or 
            soup.find('h2', class_='topcard__title') or 
            soup.find('h2', class_='top-card-layout__title') or 
            soup.find('h3', class_='sub-nav-title')
        )
        if title_el:
            title_text = title_el.get_text(strip=True)
            if title_text and len(title_text) < 150:
                data['title'] = title_text
                
        # 3. Parse Company
        company_el = soup.find('a', class_='topcard__org-name-link') or soup.find('span', class_='topcard__flavor')
        if company_el:
            company_text = company_el.get_text(strip=True)
            if company_text:
                data['company'] = company_text
                
        # 4. Parse Description
        desc_el = soup.find(class_='description') or soup.find(class_='description__text')
        if desc_el:
            desc_text = desc_el.get_text("\n", strip=True)
            if desc_text:
                data['description'] = desc_text
                
        return True, "Successfully updated details from LinkedIn Guest API", data
    except Exception as e:
        return False, str(e), {}


def score_single_job_worker(job_data, resume_text, behavior_context=""):
    """Scoring worker function that runs in a background thread without accessing SQLAlchemy session objects."""
    url = job_data['url']
    title = job_data['title']
    company = job_data['company']
    location = job_data['location']
    remote = job_data['remote']
    description = job_data['description'] or ""
    source = job_data['source']
    
    updated_fields = {}
    
    # 1. Fetch details if LinkedIn
    if source == 'linkedin':
        success, msg, data = fetch_linkedin_guest_details_raw(url)
        if success:
            if 'location' in data:
                location = data['location']
                updated_fields['location'] = location
            if 'title' in data:
                title = data['title']
                updated_fields['title'] = title
            if 'company' in data:
                company = data['company']
                updated_fields['company'] = company
            if 'description' in data:
                description = data['description']
                updated_fields['description'] = description
                
    # 2. Score job with retry
    last_error = None
    result = None
    attempts = 0
    for attempt in range(1, MAX_SCORE_ATTEMPTS + 1):
        attempts = attempt
        try:
            result = _call_llm_for_score_raw(
                title, company, location, remote, description, resume_text, behavior_context
            )
            break
        except Exception as e:
            last_error = str(e)
            if attempt < MAX_SCORE_ATTEMPTS:
                time.sleep(1) # short pause
                
    return {
        'job_id': job_data['id'],
        'success': result is not None,
        'result': result,
        'attempts': attempts,
        'error': last_error,
        'updated_fields': updated_fields
    }


def fetch_linkedin_guest_details(job):
    """
    Fetches the LinkedIn Guest API page for the job, extracts title, company,
    location, and description, and updates the job DB record in-place.
    """
    success, msg, data = fetch_linkedin_guest_details_raw(job.url)
    if success:
        if 'location' in data:
            job.location = data['location']
        if 'title' in data:
            job.title = data['title']
        if 'company' in data:
            job.company = data['company']
        if 'description' in data:
            job.description = data['description']
    return success, msg


def _old_fetch_linkedin_guest_details_deprecated(job):
    """
    Fetches the LinkedIn Guest API page for the job, extracts title, company,
    location, and description, and updates the job DB record in-place.
    """
    import requests
    from bs4 import BeautifulSoup
    
    job_id = extract_linkedin_id(job.url)
    if not job_id:
        log.warning(f"Could not extract LinkedIn ID from url: {job.url}")
        return False, "Could not extract LinkedIn Job ID"
        
    guest_url = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        resp = requests.get(guest_url, headers=headers, timeout=15)
        if resp.status_code != 200:
            return False, f"HTTP status {resp.status_code}"
            
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # 1. Parse Location
        location_el = soup.find('span', class_='topcard__flavor--bullet')
        if location_el:
            location_text = location_el.get_text(strip=True)
            if location_text:
                job.location = location_text
                
        # 2. Parse Title (if missing or raw)
        title_el = (
            soup.find('h1') or 
            soup.find('h2', class_='topcard__title') or 
            soup.find('h2', class_='top-card-layout__title') or 
            soup.find('h3', class_='sub-nav-title')
        )
        if title_el:
            title_text = title_el.get_text(strip=True)
            if title_text and len(title_text) < 150:
                job.title = title_text
                
        # 3. Parse Company
        company_el = soup.find('a', class_='topcard__org-name-link') or soup.find('span', class_='topcard__flavor')
        if company_el:
            company_text = company_el.get_text(strip=True)
            if company_text:
                job.company = company_text
                
        # 4. Parse Description
        desc_el = soup.find(class_='description') or soup.find(class_='description__text')
        if desc_el:
            desc_text = desc_el.get_text("\n", strip=True)
            if desc_text:
                job.description = desc_text
                
        return True, "Successfully updated details from LinkedIn Guest API"
    except Exception as e:
        log.warning(f"Failed fetching details for job {job.id}: {e}")
        return False, str(e)
    pass


def score_new_jobs(db, profile=None):
    """Score all unscored new jobs concurrently, with pre-filtering and per-job retry.

    Returns a ScoringReport dict with stats for the caller.
    """
    from run_status import update_process_status
    from datetime import datetime
    import time

    update_process_status(
        'scorer',
        running=True,
        started_at=datetime.utcnow().isoformat() + 'Z',
        finished_at=None,
        result=None,
        error=None
    )

    try:
        resume_text = get_resume_text(db)
        if not resume_text:
            # Fallback to legacy profile if structured resume is empty
            resume_text = profile.resume_text if profile else ''

        if not resume_text:
            print("No resume text found — skipping scoring")
            report = {'scored': 0, 'skipped': 0, 'failed': 0, 'escalated': 0}
            update_process_status(
                'scorer',
                running=False,
                finished_at=datetime.utcnow().isoformat() + 'Z',
                result=report,
                error=None
            )
            return report

        from learner import get_rejection_context
        behavior_context = get_rejection_context(db)

        new_terms_to_add = []
        total_scored = 0
        total_skipped = 0
        total_failed = 0
        failed_jobs = []

        try:
            while total_scored < MAX_TOTAL:
                # Fetch next batch of unscored jobs (score == 0 and not already failed)
                batch = db.query(Job).filter(
                    Job.status == 'new',
                    Job.match_score == 0,
                    Job.score_attempts < MAX_SCORE_ATTEMPTS,
                ).limit(BATCH_SIZE).all()

                if not batch:
                    break

                print(f"\n--- Scoring batch of {len(batch)} jobs (concurrently) ---")
                
                # Check for rate limit cooldown
                time.sleep(2.0)

                jobs_to_score = []
                blocked_jobs = []
                blocked_companies = db.query(BlockedCompany).all()

                for job in batch:
                    # Pre-filter blocked companies
                    company_lower = (job.company or "").lower().strip()
                    is_company_blocked = any(bc.name.lower().strip() in company_lower for bc in blocked_companies)
                    if is_company_blocked:
                        blocked_jobs.append(job)
                    else:
                        jobs_to_score.append({
                            'id': job.id,
                            'url': job.url,
                            'title': job.title,
                            'company': job.company,
                            'location': job.location,
                            'remote': job.remote,
                            'description': job.description,
                            'source': job.source
                        })

                # Handle blocked companies sequentially
                for job in blocked_jobs:
                    print(f"Auto-rejecting blocked company: {job.company}")
                    job.status = 'rejected'
                    job.match_score = -1
                    job.rejection_reason = f"Company '{job.company}' is in the blocklist."
                    total_skipped += 1

                if not jobs_to_score:
                    # All jobs in batch were blocked, commit and continue
                    try:
                        db.commit()
                        db.expire_all()
                    except StaleDataError:
                        db.rollback()
                        db.expire_all()
                    total_scored += len(batch)
                    continue

                # Run unblocked jobs scoring in parallel
                results = []
                with ThreadPoolExecutor(max_workers=len(jobs_to_score)) as executor:
                    futures = {
                        executor.submit(
                            score_single_job_worker, job_data, resume_text, behavior_context
                        ): job_data for job_data in jobs_to_score
                    }
                    for future in as_completed(futures):
                        try:
                            res = future.result()
                            results.append(res)
                        except Exception as e:
                            job_data = futures[future]
                            results.append({
                                'job_id': job_data['id'],
                                'success': False,
                                'result': None,
                                'attempts': 1,
                                'error': f"ThreadError: {str(e)}",
                                'updated_fields': {}
                            })

                # Apply scoring results sequentially in main thread
                for res in results:
                    job = db.query(Job).filter(Job.id == res['job_id']).first()
                    if not job:
                        continue

                    # Apply guest API updates
                    for field, val in res['updated_fields'].items():
                        setattr(job, field, val)

                    job.score_attempts = res['attempts']

                    if not res['success']:
                        job.score_error = res['error']
                        job.score_failed_at = datetime.utcnow()
                        total_failed += 1
                        failed_jobs.append(job.id)
                        print(f"Error scoring job {job.id}: {res['error']}")
                        
                        if job.score_attempts >= MAX_SCORE_ATTEMPTS:
                            job.status = 'rejected'
                            job.rejection_reason = f"Failed to score after {MAX_SCORE_ATTEMPTS} attempts. Last error: {job.score_error}"
                            print(f"Escalating: job {job.id} marked as rejected due to scoring failures.")
                        continue

                    # Scoring succeeded
                    score_result = res['result']
                    score = score_result.get('score', 50)
                    reasoning = score_result.get('reasoning', '')

                    if score == -1 or reasoning.lower() == 'location':
                        print(f"  ❌ Auto-rejecting: location/work arrangement criteria failed")
                        job.status = 'rejected'
                        job.match_score = -1
                        job.rejection_reason = 'location'
                        total_skipped += 1
                        continue

                    job.match_score = min(100, max(0, score))
                    job.match_reasoning = reasoning

                    if job.match_score < 70:
                        job.status = 'rejected'
                        job.rejection_reason = f"Auto-rejected: match score {job.match_score}% below 70% threshold"
                        total_skipped += 1
                    elif job.match_score >= 85:
                        # Auto-queue to Will Apply and generate packet in background
                        job.status = 'will_apply'
                        job.apply_note = f"Auto-queued: match score {job.match_score}% >= 85%"
                        print(f"  🎯 Auto-queued job {job.id} ({job.title} at {job.company}): score {job.match_score}% >= 85%. Triggering background research packet build...")
                        try:
                            script_path = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'build_packets.py')
                            python_path = os.path.join(os.path.dirname(__file__), '..', '.venv', 'bin', 'python')
                            subprocess.Popen(
                                [python_path, script_path, '--job-id', str(job.id)],
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL
                            )
                        except Exception as pe:
                            print(f"  ⚠️ Failed to trigger build_packets.py background process for job {job.id}: {pe}")
                    else:
                        job.status = 'new'

                    job.score_error = None
                    job.score_failed_at = None

                    variant = score_result.get('title_variant')
                    if (variant and len(variant.split()) >= 2 and len(variant.split()) <= 5 and
                        not any(c in variant for c in ['"', '-', 'NOT', 'only']) and
                        variant.lower() not in [t.term.lower() for t in db.query(SearchTerm).all()]):
                        new_terms_to_add.append(variant)

                try:
                    db.commit()
                    db.expire_all()
                except StaleDataError:
                    db.rollback()
                    db.expire_all()
                    print("[scorer] StaleDataError: one or more jobs in this batch no longer exist — skipping batch.", flush=True)

                total_scored += len(batch)
                print(f"Scored batch: {len(batch)} jobs (total: {total_scored}, skipped: {total_skipped}, failed: {total_failed})")
        finally:
            pass

        # Add new search terms (limit to 3 new per run)
        for term_text in new_terms_to_add[:3]:
            existing = db.query(SearchTerm).filter(SearchTerm.term == term_text).first()
            if not existing:
                db.add(SearchTerm(term=term_text, source='ai', active=True))
        db.commit()

        report = {
            'scored': total_scored,
            'skipped': total_skipped,
            'failed': total_failed,
            'escalated': len(failed_jobs),
            'failed_jobs': failed_jobs,
        }
        print(f"Scoring complete: {total_scored} processed, {total_skipped} auto-rejected, {total_failed} failed → escalated")
        update_process_status(
            'scorer',
            running=False,
            finished_at=datetime.utcnow().isoformat() + 'Z',
            result=report,
            error=None
        )
        return report
    except Exception as e:
        update_process_status(
            'scorer',
            running=False,
            finished_at=datetime.utcnow().isoformat() + 'Z',
            result=None,
            error=str(e)
        )
        raise
