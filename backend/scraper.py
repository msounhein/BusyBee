import hashlib
import json
import gc
import subprocess
import sys
import tempfile
import os
import time
from datetime import datetime, date
from sqlalchemy import func
from database import SessionLocal
from models import Job, SearchTerm, BlockedCompany, Profile
from config import Config


import urllib.request
import xml.etree.ElementTree as ET
import email.utils
from concurrent.futures import ThreadPoolExecutor, as_completed

SITE_TIMEOUT_SECS = 90
DELAY_BETWEEN_SCRAPES = 10  # seconds — avoid API rate limits

# Inline worker script: accepts JSON args via stdin, writes results to stdout
_WORKER_SCRIPT = '''
import sys, json, numpy as np
from datetime import date, datetime
from jobspy import scrape_jobs

class Encoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, (date, datetime, np.datetime64)):
            return str(o)
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, (np.floating,)):
            return float(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
        return super().default(o)

args = json.loads(sys.stdin.read())
try:
    df = scrape_jobs(**args)
    if df is not None and not df.empty:
        # Convert date columns to string first
        for col in df.columns:
            df[col] = df[col].apply(lambda x: str(x) if hasattr(x, "isoformat") else x)
            df[col] = df[col].replace({np.nan: None})
        print(json.dumps(df.to_dict("records"), cls=Encoder))
    else:
        print(json.dumps([]))
except Exception as e:
    import traceback
    traceback.print_exc()
    print(json.dumps({"__error": str(e)}))
'''


def _scrape_with_timeout(site, search_term, location, results_wanted, hours_old,
                          remote=False, timeout=SITE_TIMEOUT_SECS):
    """Run scrape_jobs in a subprocess with a hard kill timeout. Returns (success, results)."""
    # Wrap term in quotes for exact phrase matching — prevents OR-style partial matches
    # e.g. "Systems Administrator" won't match "Senior DevOps Engineer"
    quoted_term = f'"{search_term}"'
    query = f'{quoted_term} remote' if remote else quoted_term
    kwargs = {
        "site_name": [site],
        "search_term": query,
        "results_wanted": results_wanted,
        "hours_old": hours_old,
        "country_indeed": "USA",
        "linkedin_fetch_description": True,
    }
    if location and not remote:
        kwargs["location"] = location
        kwargs["distance"] = 30  # miles radius around location

    label = f"{site} '{search_term}' {'remote' if remote else 'local'}"
    print(f"[scrape] Starting {label}...", flush=True)
    try:
        proc = subprocess.run(
            [sys.executable, "-c", _WORKER_SCRIPT],
            input=json.dumps(kwargs),
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=os.path.join(os.path.dirname(__file__), '..'),
        )
        if proc.returncode != 0:
            print(f"[scrape] Worker failed {label}: {proc.stderr[:300]}", flush=True)
            return False, []
        result = json.loads(proc.stdout.strip())
        if isinstance(result, dict) and "__error" in result:
            print(f"[scrape] Error {label}: {result['__error'][:200]}", flush=True)
            return False, []
        print(f"[scrape] {label}: {len(result)} results", flush=True)
        return True, result
    except subprocess.TimeoutExpired:
        print(f"[scrape] TIMEOUT ({timeout}s) {label} — skipping", flush=True)
        return False, []
    except Exception as e:
        print(f"[scrape] Exception {label}: {e}", flush=True)
        return False, []


def _scrape_with_retry(site, search_term, location, results_wanted, hours_old,
                       remote=False, timeout=SITE_TIMEOUT_SECS, max_retries=3):
    """Scrape with retry capability."""
    for attempt in range(1, max_retries + 1):
        success, results = _scrape_with_timeout(
            site=site,
            search_term=search_term,
            location=location,
            results_wanted=results_wanted,
            hours_old=hours_old,
            remote=remote,
            timeout=timeout
        )
        if success:
            return results
        if attempt < max_retries:
            backoff = attempt * 2
            print(f"[scrape] Attempt {attempt} failed for {site} '{search_term}'. Retrying in {backoff}s...", flush=True)
            time.sleep(backoff)
    print(f"[scrape] All {max_retries} attempts failed for {site} '{search_term}'", flush=True)
    return []


def parse_jobspy_row(row):
    location_str = ''
    if row.get('location') and str(row['location']) != 'nan':
        location_str = str(row['location']).strip()
    else:
        location_parts = []
        if row.get('city') and str(row['city']) != 'nan':
            location_parts.append(str(row['city']))
        if row.get('state') and str(row['state']) != 'nan':
            location_parts.append(str(row['state']))
        location_str = ', '.join(location_parts) if location_parts else ''

    is_remote = bool(row.get('is_remote', False))

    salary_min = None
    salary_max = None
    if row.get('min_amount') and str(row['min_amount']) != 'nan':
        try:
            salary_min = int(float(row['min_amount']))
        except (ValueError, TypeError):
            pass
    if row.get('max_amount') and str(row['max_amount']) != 'nan':
        try:
            salary_max = int(float(row['max_amount']))
        except (ValueError, TypeError):
            pass

    job_url = row.get('job_url', '') or ''
    source_id = hashlib.sha256(job_url.encode()).hexdigest()[:40] if job_url else ''

    source = str(row.get('site', 'unknown')).lower() if row.get('site') else 'unknown'

    description = row.get('description', '') or ''
    if str(description) == 'nan':
        description = ''

    posted_date = None
    date_val = row.get('date_posted')
    if date_val and str(date_val) != 'nan':
        if hasattr(date_val, 'date'):
            posted_date = date_val.date() if callable(getattr(date_val, 'date', None)) else date_val
        elif isinstance(date_val, date):
            posted_date = date_val

    return {
        'source': source,
        'source_id': source_id,
        'title': str(row.get('title', '')) or '',
        'company': str(row.get('company', '')) or '',
        'location': location_str,
        'job_type': 'remote' if is_remote else 'fulltime',
        'remote': is_remote,
        'distance_miles': None,
        'salary_min': salary_min,
        'salary_max': salary_max,
        'description': description,
        'url': job_url,
        'posted_date': posted_date,
    }


def is_blocked(company, blocked_companies):
    company_lower = company.lower().strip()
    for bc in blocked_companies:
        if bc.name.lower().strip() in company_lower:
            return True
    return False


def parse_rss_date(date_str):
    try:
        dt = email.utils.parsedate_to_datetime(date_str)
        return dt.date()
    except Exception:
        return None


def parse_iso_date(date_str):
    try:
        if not date_str:
            return None
        if date_str.endswith('Z'):
            date_str = date_str[:-1] + '+00:00'
        dt = datetime.fromisoformat(date_str)
        return dt.date()
    except Exception:
        return None


def fetch_and_parse_wwr(terms):
    """Fetch We Work Remotely RSS and return parsed jobs matching search terms."""
    url = "https://weworkremotely.com/remote-jobs.rss"
    print(f"[scrape] Fetching We Work Remotely RSS...", flush=True)
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            xml_data = r.read()
        root = ET.fromstring(xml_data)
        channel = root.find('channel')
        items = channel.findall('item') if channel is not None else []
        print(f"[scrape] WWR RSS: found {len(items)} raw jobs", flush=True)
        
        parsed_jobs = []
        for item in items:
            title_str = (item.find('title').text or '') if item.find('title') is not None else ''
            if ':' in title_str:
                parts = title_str.split(':', 1)
                company = parts[0].strip()
                title = parts[1].strip()
            else:
                company = "We Work Remotely"
                title = title_str

            url_val = (item.find('link').text or '') if item.find('link') is not None else ''
            guid_val = (item.find('guid').text or url_val) if item.find('guid') is not None else url_val
            source_id = hashlib.sha256(guid_val.encode()).hexdigest()[:40] if guid_val else ''

            pub_date_str = (item.find('pubDate').text) if item.find('pubDate') is not None else None
            posted_date = parse_rss_date(pub_date_str) if pub_date_str else None

            description = (item.find('description').text or '') if item.find('description') is not None else ''
            region = item.find('region')
            region_str = region.text if region is not None else 'Remote'
            
            job = {
                'source': 'wwr',
                'source_id': source_id,
                'title': title,
                'company': company,
                'location': region_str,
                'job_type': 'remote',
                'remote': True,
                'distance_miles': None,
                'salary_min': None,
                'salary_max': None,
                'description': description,
                'url': url_val,
                'posted_date': posted_date,
            }
            parsed_jobs.append(job)

        matched_jobs = []
        for job in parsed_jobs:
            title_lower = job['title'].lower()
            if any(t.lower() in title_lower for t in terms):
                matched_jobs.append(job)
        print(f"[scrape] WWR RSS: Matched {len(matched_jobs)} jobs matching active terms", flush=True)
        return matched_jobs
    except Exception as e:
        print(f"[scrape] Error fetching/parsing WWR RSS: {e}", flush=True)
        return []


def fetch_and_parse_himalayas(terms):
    """Fetch Himalayas paginated browse feed (5 pages of 20) and return matching jobs."""
    parsed_jobs = []
    print(f"[scrape] Fetching Himalayas API (up to 5 pages)...", flush=True)
    for page in range(5):
        offset = page * 20
        url = f"https://himalayas.app/jobs/api?limit=20&offset={offset}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read().decode('utf-8'))
            raw_jobs = data.get('jobs', [])
            if not raw_jobs:
                break
            for item in raw_jobs:
                title = item.get('title') or ''
                company = item.get('companyName') or ''
                url_val = item.get('applicationLink') or item.get('guid') or ''
                source_id = hashlib.sha256(url_val.encode()).hexdigest()[:40] if url_val else ''
                
                pub_date_str = item.get('pubDate')
                posted_date = parse_iso_date(pub_date_str)
                description = item.get('description') or ''
                locs = item.get('locationRestrictions') or []
                location_str = ', '.join(locs) if locs else 'Remote'
                
                min_sal = item.get('minSalary')
                max_sal = item.get('maxSalary')
                
                job = {
                    'source': 'himalayas',
                    'source_id': source_id,
                    'title': title,
                    'company': company,
                    'location': location_str,
                    'job_type': 'remote',
                    'remote': True,
                    'distance_miles': None,
                    'salary_min': min_sal,
                    'salary_max': max_sal,
                    'description': description,
                    'url': url_val,
                    'posted_date': posted_date,
                }
                parsed_jobs.append(job)
            time.sleep(0.5)  # respect rate limits between page calls
        except Exception as e:
            print(f"[scrape] Error fetching Himalayas page {page}: {e}", flush=True)
            break
            
    matched_jobs = []
    for job in parsed_jobs:
        title_lower = job['title'].lower()
        if any(t.lower() in title_lower for t in terms):
            matched_jobs.append(job)
    print(f"[scrape] Himalayas: Matched {len(matched_jobs)} jobs matching active terms (out of {len(parsed_jobs)} fetched)", flush=True)
    return matched_jobs


def fetch_and_parse_remotive(terms):
    """Fetch Remotive API feed once and return matching jobs."""
    url = "https://remotive.com/api/remote-jobs"
    print(f"[scrape] Fetching Remotive API...", flush=True)
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode('utf-8'))
        raw_jobs = data.get('jobs', [])
        print(f"[scrape] Remotive API: found {len(raw_jobs)} raw jobs", flush=True)
        
        parsed_jobs = []
        for item in raw_jobs:
            title = item.get('title') or ''
            company = item.get('company_name') or ''
            url_val = item.get('url') or ''
            source_id = str(item.get('id', '')) or (hashlib.sha256(url_val.encode()).hexdigest()[:40] if url_val else '')
            
            pub_date_str = item.get('publication_date')
            posted_date = parse_iso_date(pub_date_str)
            description = item.get('description') or ''
            location_str = item.get('candidate_required_location') or 'Remote'
            
            job = {
                'source': 'remotive',
                'source_id': source_id,
                'title': title,
                'company': company,
                'location': location_str,
                'job_type': 'remote',
                'remote': True,
                'distance_miles': None,
                'salary_min': None,
                'salary_max': None,
                'description': description,
                'url': url_val,
                'posted_date': posted_date,
            }
            parsed_jobs.append(job)

        matched_jobs = []
        for job in parsed_jobs:
            title_lower = job['title'].lower()
            if any(t.lower() in title_lower for t in terms):
                matched_jobs.append(job)
        print(f"[scrape] Remotive: Matched {len(matched_jobs)} jobs matching active terms", flush=True)
        return matched_jobs
    except Exception as e:
        print(f"[scrape] Error fetching/parsing Remotive: {e}", flush=True)
        return []


def run_scraper():
    """Main scraper logic. Returns stats dict."""
    from run_status import update_process_status
    from datetime import datetime

    update_process_status(
        'scraper',
        running=True,
        started_at=datetime.utcnow().isoformat() + 'Z',
        finished_at=None,
        result=None,
        error=None
    )

    db = SessionLocal()
    try:
        terms = db.query(SearchTerm).filter(SearchTerm.active == True).all()
        profile = db.query(Profile).first()
        blocked = db.query(BlockedCompany).all()

        if not profile:
            profile = Profile()

        location = profile.location or Config.LOCATION

        total_found = 0
        new_jobs = 0
        skipped_blocked = 0
        skipped_duplicate = 0
        scraped_list = []
        # In-memory set of (title_lower, company_lower) seen THIS run
        # Catches duplicates across batches/terms before they reach the DB
        seen_title_company = set()

        def _is_viable_location(parsed):
            """
            Returns False if the job is clearly non-remote AND non-local at scrape time.
            Checks the location field and description for embedded location indicators.
            This prevents obviously-wrong jobs from ever hitting the DB.
            """
            import re
            location = (parsed.get('location') or '').strip()
            is_remote_flag = parsed.get('remote', False)
            job_type = (parsed.get('job_type') or '').lower()

            LOCAL_WI_CITIES = [
                'appleton', 'neenah', 'menasha', 'oshkosh', 'green bay',
                'de pere', 'kaukauna', 'little chute', 'kimberly',
                'combined locks', 'sherwood', 'greenville', 'hortonville',
                'new london', 'black creek', 'freedom', 'wrightstown',
                'shiocton', 'seymour', 'wisconsin', ', wi',
            ]
            NON_SPECIFIC = ['remote', 'anywhere', 'united states', 'usa', 'us', '']

            loc_lower = location.lower()

            # If location is blank or generic, we can't rule it out at scrape time — keep it
            if loc_lower in NON_SPECIFIC:
                return True

            # If location contains a WI city — it's local, keep it
            if any(city in loc_lower for city in LOCAL_WI_CITIES):
                return True

            # Location has content (e.g. "Cedar Rapids, IA") — extract state
            state_m = re.search(r',\s*([A-Z]{2})\b', location)
            if state_m:
                state = state_m.group(1).upper()
                if state == 'WI':
                    return True
                # Non-WI state in location — only viable if remote
                if is_remote_flag or job_type == 'remote':
                    return True
                # Check description for genuine remote-work phrases
                desc_lower = (parsed.get('description') or '').lower()
                remote_phrases = [
                    r'\bwork(?:ing)?\s+(?:fully\s+)?remote\b',
                    r'\bfully\s+remote\b', r'\b100%\s+remote\b',
                    r'\bwork\s+from\s+home\b', r'\bwfh\b', r'\btelecommut',
                    r'\bremote[-\s](?:first|only|position|role|work|job|opportunity)\b',
                    r'\bthis\s+(?:is\s+a\s+)?remote\s+(?:position|role|job)\b',
                    r'\bposition\s+is\s+(?:fully\s+)?remote\b',
                ]
                if any(re.search(p, desc_lower) for p in remote_phrases):
                    return True
                # Non-WI location, not flagged remote, no remote language — reject
                print(f"[scrape] Dropping non-local non-remote: {parsed.get('title')} @ {parsed.get('company')} ({location})", flush=True)
                return False

            # Location has text but no clear state — keep it (can't be sure)
            return True

        def _process_parsed_jobs(parsed_jobs, db, blocked):
            nonlocal scraped_list
            fnd = len(parsed_jobs)
            nw = blk = dup = 0
            loc_filtered = 0
            for parsed in parsed_jobs:
                if not parsed.get('title') or not parsed.get('source_id'):
                    continue
                if is_blocked(parsed['company'], blocked):
                    blk += 1
                    continue
                # 0) Location/remote viability — drop obviously wrong jobs at scrape time
                if not _is_viable_location(parsed):
                    loc_filtered += 1
                    continue
                # 1) Source-level dedup (same site, same listing ID)
                existing = db.query(Job).filter(
                    Job.source == parsed['source'],
                    Job.source_id == parsed['source_id']
                ).first()
                if existing:
                    dup += 1
                    continue
                title_norm = parsed['title'].lower().strip()
                company_norm = (parsed.get('company') or '').lower().strip()
                key = (title_norm, company_norm)
                # 2) In-memory dedup — catches same job from different search terms
                if key in seen_title_company:
                    dup += 1
                    continue
                # 3) Cross-source DB dedup — catches same job already committed
                if title_norm and company_norm:
                    cross_dupe = db.query(Job).filter(
                        func.lower(Job.title) == title_norm,
                        func.lower(Job.company) == company_norm
                    ).first()
                    if cross_dupe:
                        dup += 1
                        continue
                seen_title_company.add(key)
                db.add(Job(**parsed))
                nw += 1
                scraped_list.append(parsed)
            if loc_filtered:
                print(f"[scrape] Location-filtered {loc_filtered} non-local/non-remote jobs", flush=True)
            return fnd, nw, blk, dup


        term_strings = [t.term for t in terms]

        # 1. Fetch from global remote APIs/RSS if enabled and terms are active
        # NOTE: WWR and Remotive disabled — tested and confirmed zero matches for
        # IT infrastructure roles (Systems Admin, Intune, SCCM, Endpoint, etc.)
        # Their feeds are dominated by Software Engineering, Marketing, and Sales.
        if term_strings:
            if getattr(profile, 'scrape_himalayas', True):
                himalayas_jobs = fetch_and_parse_himalayas(term_strings)
                f, n, b, d = _process_parsed_jobs(himalayas_jobs, db, blocked)
                total_found += f; new_jobs += n; skipped_blocked += b; skipped_duplicate += d
                db.commit()
                db.commit()

        # 2. Build active search-term scraper sites (LinkedIn, Indeed)
        active_sites = []
        if getattr(profile, 'scrape_linkedin', True):
            active_sites.append("linkedin")
        if getattr(profile, 'scrape_indeed', True):
            active_sites.append("indeed")

        # Scrape active search-term sites concurrently per term
        if active_sites and terms:
            with ThreadPoolExecutor(max_workers=4) as executor:
                for term in terms:
                    term_new = 0
                    futures = {}
                    for site in active_sites:
                        # Local search
                        fut_local = executor.submit(
                            _scrape_with_retry,
                            site, term.term, location, 25, 168, False
                        )
                        futures[fut_local] = (site, term, False)
                        
                        # Remote search
                        fut_remote = executor.submit(
                            _scrape_with_retry,
                            site, term.term, location, 25, 168, True
                        )
                        futures[fut_remote] = (site, term, True)
                    
                    for future in as_completed(futures):
                        site, t_obj, is_rem = futures[future]
                        try:
                            raw = future.result()
                            if raw:
                                parsed_list = [parse_jobspy_row(r) for r in raw]
                                f, n, b, d = _process_parsed_jobs(parsed_list, db, blocked)
                                total_found += f; new_jobs += n; skipped_blocked += b; skipped_duplicate += d
                                term_new += n
                        except Exception as exc:
                            print(f"[scrape] {site} scrape generated an exception for '{t_obj.term}': {exc}", flush=True)
                    
                    gc.collect()
                    db.commit()
                    db.expire_all()
                    
                    term.last_used = datetime.utcnow()
                    term.hit_count = (term.hit_count or 0) + term_new
                    print(f"Term '{term.term}': {term_new} new jobs saved", flush=True)
                    
                    time.sleep(DELAY_BETWEEN_SCRAPES)

        db.commit()

        if new_jobs > 0 and scraped_list:
            try:
                backup_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'scraped_jobs.json')
                class DateEncoder(json.JSONEncoder):
                    def default(self, obj):
                        if isinstance(obj, (date, datetime)):
                            return obj.isoformat()
                        return super().default(obj)
                
                with open(backup_file, 'w') as f:
                    json.dump(scraped_list, f, indent=2, cls=DateEncoder)
                print(f"Saved {len(scraped_list)} raw new jobs to {backup_file}", flush=True)
            except Exception as e:
                print(f"Error saving scraped jobs to file: {e}", flush=True)

        if new_jobs > 0:
            try:
                from learner import analyze_user_behavior
                analyze_user_behavior(db)
            except Exception as e:
                print(f"Error running learner: {e}", flush=True)

        if new_jobs > 0:
            try:
                from scorer import score_new_jobs
                score_new_jobs(db, profile)
            except Exception as e:
                print(f"Error scoring jobs: {e}", flush=True)

        result_dict = {
            'total': total_found,
            'new': new_jobs,
            'skipped_blocked': skipped_blocked,
            'skipped_duplicate': skipped_duplicate,
        }
        update_process_status(
            'scraper',
            running=False,
            finished_at=datetime.utcnow().isoformat() + 'Z',
            result=result_dict,
            error=None
        )
        return result_dict
    except Exception as e:
        update_process_status(
            'scraper',
            running=False,
            finished_at=datetime.utcnow().isoformat() + 'Z',
            result=None,
            error=str(e)
        )
        raise
    finally:
        db.close()
