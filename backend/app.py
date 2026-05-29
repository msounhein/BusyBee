import json
import os
import threading
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from database import init_db, SessionLocal
from models import Job, SearchTerm, Profile, RejectionPattern, BlockedCompany
from models_chat import ChatMessage
from config import Config

app = Flask(__name__)
CORS(app)

init_db()


# ─── Jobs API ────────────────────────────────────────────


@app.route('/api/jobs', methods=['GET'])
def get_jobs():
    db = SessionLocal()
    try:
        status = request.args.get('status')
        from models import ResearchPacket
        query = db.query(Job, ResearchPacket.id.isnot(None).label('has_packet'))
        query = query.outerjoin(ResearchPacket, Job.id == ResearchPacket.job_id)
        if status:
            query = query.filter(Job.status == status)
        jobs = query.order_by(Job.match_score.desc(), Job.found_date.desc()).all()
        return jsonify([{
            'id': j.id,
            'source': j.source,
            'title': j.title,
            'company': j.company,
            'location': j.location,
            'job_type': j.job_type,
            'remote': j.remote,
            'distance_miles': j.distance_miles,
            'salary_min': j.salary_min,
            'salary_max': j.salary_max,
            'url': j.url,
            'status': j.status,
            'match_score': j.match_score,
            'match_reasoning': j.match_reasoning,
            'rejection_reason': j.rejection_reason,
            'apply_note': j.apply_note,
            'posted_date': j.posted_date.isoformat() if j.posted_date else None,
            'found_date': j.found_date.isoformat() + 'Z' if j.found_date else None,
            'applied_date': j.applied_date.isoformat() + 'Z' if j.applied_date else None,
            'has_packet': bool(has_pkt),
        } for j, has_pkt in jobs])
    finally:
        db.close()


@app.route('/api/jobs/<int:job_id>', methods=['GET'])
def get_job(job_id):
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return jsonify({'error': 'Not found'}), 404
        return jsonify({
            'id': job.id,
            'source': job.source,
            'source_id': job.source_id,
            'title': job.title,
            'company': job.company,
            'location': job.location,
            'job_type': job.job_type,
            'remote': job.remote,
            'distance_miles': job.distance_miles,
            'salary_min': job.salary_min,
            'salary_max': job.salary_max,
            'description': job.description,
            'url': job.url,
            'status': job.status,
            'match_score': job.match_score,
            'match_reasoning': job.match_reasoning,
            'rejection_reason': job.rejection_reason,
            'apply_note': job.apply_note,
            'posted_date': job.posted_date.isoformat() if job.posted_date else None,
            'found_date': job.found_date.isoformat() + 'Z' if job.found_date else None,
            'applied_date': job.applied_date.isoformat() + 'Z' if job.applied_date else None,
        })
    finally:
        db.close()


@app.route('/api/jobs/<int:job_id>/status', methods=['PATCH'])
def update_job_status(job_id):
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return jsonify({'error': 'Not found'}), 404
        data = request.json
        new_status = data.get('status')
        if new_status not in ('new', 'will_apply', 'applied', 'interview', 'offer', 'rejected', 'closed'):
            return jsonify({'error': 'Invalid status'}), 400
        job.status = new_status
        if new_status == 'applied':
            job.applied_date = datetime.utcnow()
        if new_status == 'rejected':
            job.rejection_reason = data.get('reason', '')
        if new_status == 'will_apply':
            job.apply_note = data.get('note', '')
        if new_status != 'rejected':
            job.rejection_reason = None
        db.commit()
        return jsonify({'message': 'Status updated', 'status': new_status})
    finally:
        db.close()


# ─── Dashboard Stats ─────────────────────────────────────

@app.route('/api/stats', methods=['GET'])
def get_stats():
    db = SessionLocal()
    try:
        from models import ResearchPacket
        from datetime import datetime, timedelta
        
        total = db.query(Job).count()
        new = db.query(Job).filter(Job.status == 'new').count()
        will_apply = db.query(Job).filter(Job.status == 'will_apply').count()
        applied = db.query(Job).filter(Job.status == 'applied').count()
        interview = db.query(Job).filter(Job.status == 'interview').count()
        rejected = db.query(Job).filter(Job.status == 'rejected').count()
        top_score = db.query(Job).filter(Job.status == 'new').order_by(Job.match_score.desc()).first()
        
        day_ago = datetime.utcnow() - timedelta(days=1)
        week_ago = datetime.utcnow() - timedelta(days=7)
        
        applied_daily = db.query(Job).filter(Job.applied_date >= day_ago).count()
        applied_weekly = db.query(Job).filter(Job.applied_date >= week_ago).count()
        
        packet_stats = {
            'total': db.query(ResearchPacket).count(),
            'last_24h': db.query(ResearchPacket).filter(ResearchPacket.created_at >= day_ago).count(),
            'last_7d': db.query(ResearchPacket).filter(ResearchPacket.created_at >= week_ago).count(),
            'high_match': db.query(ResearchPacket).join(Job, Job.id == ResearchPacket.job_id).filter(Job.match_score >= 70).count(),
            'by_status': {
                'new': db.query(ResearchPacket).join(Job, Job.id == ResearchPacket.job_id).filter(Job.status == 'new').count(),
                'will_apply': db.query(ResearchPacket).join(Job, Job.id == ResearchPacket.job_id).filter(Job.status == 'will_apply').count(),
                'applied': db.query(ResearchPacket).join(Job, Job.id == ResearchPacket.job_id).filter(Job.status == 'applied').count(),
                'interview': db.query(ResearchPacket).join(Job, Job.id == ResearchPacket.job_id).filter(Job.status == 'interview').count(),
                'rejected': db.query(ResearchPacket).join(Job, Job.id == ResearchPacket.job_id).filter(Job.status == 'rejected').count(),
            }
        }
        
        return jsonify({
            'total': total,
            'new': new,
            'will_apply': will_apply,
            'applied': applied,
            'interview': interview,
            'rejected': rejected,
            'top_match_score': top_score.match_score if top_score else 0,
            'packet_stats': packet_stats,
            'applied_daily': applied_daily,
            'applied_weekly': applied_weekly,
        })
    finally:
        db.close()


# ─── Profile API ─────────────────────────────────────────

@app.route('/api/profile', methods=['GET'])
def get_profile():
    db = SessionLocal()
    try:
        profile = db.query(Profile).first()
        if not profile:
            return jsonify({'error': 'No profile'}), 404
        return jsonify({
            'id': profile.id,
            'resume_text': profile.resume_text,
            'location': profile.location,
            'max_distance': profile.max_distance,
            'preferred_titles': json.loads(profile.preferred_titles),
            'dealbreakers': json.loads(profile.dealbreakers),
            'preferences': json.loads(profile.preferences) if profile.preferences else {},
            'scrape_linkedin': getattr(profile, 'scrape_linkedin', True),
            'scrape_indeed': getattr(profile, 'scrape_indeed', True),
            'scrape_himalayas': getattr(profile, 'scrape_himalayas', True),
            'scrape_remotive': getattr(profile, 'scrape_remotive', True),
            'scrape_wwr': getattr(profile, 'scrape_wwr', True),
            'llm_provider': getattr(profile, 'llm_provider', 'zai'),
            'llm_api_key': getattr(profile, 'llm_api_key', ''),
            'llm_model': getattr(profile, 'llm_model', 'glm-5.1'),
            'llm_api_url': getattr(profile, 'llm_api_url', ''),
        })
    finally:
        db.close()


@app.route('/api/profile', methods=['PUT'])
def update_profile():
    db = SessionLocal()
    try:
        profile = db.query(Profile).first()
        if not profile:
            profile = Profile()
            db.add(profile)
        data = request.json
        if 'resume_text' in data:
            profile.resume_text = data['resume_text']
        if 'location' in data:
            profile.location = data['location']
        if 'max_distance' in data:
            profile.max_distance = data['max_distance']
        if 'preferred_titles' in data:
            profile.preferred_titles = json.dumps(data['preferred_titles'])
        if 'dealbreakers' in data:
            profile.dealbreakers = json.dumps(data['dealbreakers'])
        if 'preferences' in data:
            profile.preferences = json.dumps(data['preferences'])
        if 'scrape_linkedin' in data:
            profile.scrape_linkedin = bool(data['scrape_linkedin'])
        if 'scrape_indeed' in data:
            profile.scrape_indeed = bool(data['scrape_indeed'])
        if 'scrape_himalayas' in data:
            profile.scrape_himalayas = bool(data['scrape_himalayas'])
        if 'scrape_remotive' in data:
            profile.scrape_remotive = bool(data['scrape_remotive'])
        if 'scrape_wwr' in data:
            profile.scrape_wwr = bool(data['scrape_wwr'])
        if 'llm_provider' in data:
            profile.llm_provider = data['llm_provider']
        if 'llm_api_key' in data:
            profile.llm_api_key = data['llm_api_key']
        if 'llm_model' in data:
            profile.llm_model = data['llm_model']
        if 'llm_api_url' in data:
            profile.llm_api_url = data['llm_api_url']
        db.commit()
        return jsonify({'message': 'Profile updated'})
    finally:
        db.close()


# ─── Structured Resume API ───────────────────────────────

@app.route('/api/resume/profile', methods=['GET'])
def get_resume_profile():
    db = SessionLocal()
    try:
        from models import ResumeProfile
        profile = db.query(ResumeProfile).first()
        if not profile:
            return jsonify({'error': 'No resume profile'}), 404
        return jsonify({
            'id': profile.id,
            'full_name': profile.full_name,
            'email': profile.email,
            'phone': profile.phone,
            'location': profile.location,
            'linkedin_url': profile.linkedin_url,
            'github_url': profile.github_url,
            'summary': profile.summary,
        })
    finally:
        db.close()


@app.route('/api/resume/profile', methods=['PUT'])
def update_resume_profile():
    db = SessionLocal()
    try:
        from models import ResumeProfile
        profile = db.query(ResumeProfile).first()
        if not profile:
            profile = ResumeProfile()
            db.add(profile)
        data = request.json
        for field in ('full_name', 'email', 'phone', 'location', 'linkedin_url', 'github_url', 'summary'):
            if field in data:
                setattr(profile, field, data[field])
        db.commit()
        return jsonify({'message': 'Resume profile updated', 'id': profile.id})
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        db.close()


@app.route('/api/resume/experience', methods=['GET'])
def get_resume_experience():
    db = SessionLocal()
    try:
        from models import ResumeExperience
        items = db.query(ResumeExperience).order_by(ResumeExperience.sort_order).all()
        return jsonify([{
            'id': e.id,
            'company': e.company,
            'title': e.title,
            'location': e.location,
            'start_date': e.start_date,
            'end_date': e.end_date,
            'bullets': json.loads(e.bullets) if e.bullets else [],
            'sort_order': e.sort_order,
        } for e in items])
    finally:
        db.close()


@app.route('/api/resume/experience', methods=['POST'])
def create_resume_experience():
    db = SessionLocal()
    try:
        from models import ResumeExperience
        data = request.json
        # Get next sort_order
        max_order = db.query(ResumeExperience).count()
        bullets = data.get('bullets', [])
        exp = ResumeExperience(
            company=data['company'],
            title=data['title'],
            location=data.get('location', ''),
            start_date=data.get('start_date', ''),
            end_date=data.get('end_date', ''),
            bullets=json.dumps(bullets),
            sort_order=data.get('sort_order', max_order),
        )
        db.add(exp)
        db.commit()
        return jsonify({'message': 'Experience created', 'id': exp.id}), 201
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        db.close()


@app.route('/api/resume/experience/<int:exp_id>', methods=['PUT'])
def update_resume_experience(exp_id):
    db = SessionLocal()
    try:
        from models import ResumeExperience
        exp = db.query(ResumeExperience).filter(ResumeExperience.id == exp_id).first()
        if not exp:
            return jsonify({'error': 'Not found'}), 404
        data = request.json
        for field in ('company', 'title', 'location', 'start_date', 'end_date', 'sort_order'):
            if field in data:
                setattr(exp, field, data[field])
        if 'bullets' in data:
            exp.bullets = json.dumps(data['bullets'])
        db.commit()
        return jsonify({'message': 'Experience updated'})
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        db.close()


@app.route('/api/resume/experience/<int:exp_id>', methods=['DELETE'])
def delete_resume_experience(exp_id):
    db = SessionLocal()
    try:
        from models import ResumeExperience
        exp = db.query(ResumeExperience).filter(ResumeExperience.id == exp_id).first()
        if not exp:
            return jsonify({'error': 'Not found'}), 404
        db.delete(exp)
        db.commit()
        return jsonify({'message': 'Experience deleted'})
    finally:
        db.close()


@app.route('/api/resume/experience/reorder', methods=['PUT'])
def reorder_resume_experience():
    db = SessionLocal()
    try:
        from models import ResumeExperience
        data = request.json  # expects [{id, sort_order}, ...]
        for item in data:
            exp = db.query(ResumeExperience).filter(ResumeExperience.id == item['id']).first()
            if exp:
                exp.sort_order = item['sort_order']
        db.commit()
        return jsonify({'message': 'Experience reordered'})
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        db.close()


@app.route('/api/resume/education', methods=['GET'])
def get_resume_education():
    db = SessionLocal()
    try:
        from models import ResumeEducation
        items = db.query(ResumeEducation).order_by(ResumeEducation.sort_order).all()
        return jsonify([{
            'id': e.id,
            'institution': e.institution,
            'degree': e.degree,
            'field_of_study': e.field_of_study,
            'gpa': e.gpa,
            'dates': e.dates,
            'sort_order': e.sort_order,
        } for e in items])
    finally:
        db.close()


@app.route('/api/resume/education', methods=['POST'])
def create_resume_education():
    db = SessionLocal()
    try:
        from models import ResumeEducation
        data = request.json
        max_order = db.query(ResumeEducation).count()
        edu = ResumeEducation(
            institution=data['institution'],
            degree=data.get('degree', ''),
            field_of_study=data.get('field_of_study', ''),
            gpa=data.get('gpa', ''),
            dates=data.get('dates', ''),
            sort_order=data.get('sort_order', max_order),
        )
        db.add(edu)
        db.commit()
        return jsonify({'message': 'Education created', 'id': edu.id}), 201
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        db.close()


@app.route('/api/resume/education/<int:edu_id>', methods=['PUT'])
def update_resume_education(edu_id):
    db = SessionLocal()
    try:
        from models import ResumeEducation
        edu = db.query(ResumeEducation).filter(ResumeEducation.id == edu_id).first()
        if not edu:
            return jsonify({'error': 'Not found'}), 404
        data = request.json
        for field in ('institution', 'degree', 'field_of_study', 'gpa', 'dates', 'sort_order'):
            if field in data:
                setattr(edu, field, data[field])
        db.commit()
        return jsonify({'message': 'Education updated'})
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        db.close()


@app.route('/api/resume/education/<int:edu_id>', methods=['DELETE'])
def delete_resume_education(edu_id):
    db = SessionLocal()
    try:
        from models import ResumeEducation
        edu = db.query(ResumeEducation).filter(ResumeEducation.id == edu_id).first()
        if not edu:
            return jsonify({'error': 'Not found'}), 404
        db.delete(edu)
        db.commit()
        return jsonify({'message': 'Education deleted'})
    finally:
        db.close()


@app.route('/api/resume/skills', methods=['GET'])
def get_resume_skills():
    db = SessionLocal()
    try:
        from models import ResumeSkillCategory
        items = db.query(ResumeSkillCategory).order_by(ResumeSkillCategory.sort_order).all()
        return jsonify([{
            'id': s.id,
            'category_name': s.category_name,
            'skills': s.skills,
            'sort_order': s.sort_order,
        } for s in items])
    finally:
        db.close()


@app.route('/api/resume/skills', methods=['POST'])
def create_resume_skill():
    db = SessionLocal()
    try:
        from models import ResumeSkillCategory
        data = request.json
        max_order = db.query(ResumeSkillCategory).count()
        cat = ResumeSkillCategory(
            category_name=data['category_name'],
            skills=data.get('skills', ''),
            sort_order=data.get('sort_order', max_order),
        )
        db.add(cat)
        db.commit()
        return jsonify({'message': 'Skill category created', 'id': cat.id}), 201
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        db.close()


@app.route('/api/resume/skills/<int:skill_id>', methods=['PUT'])
def update_resume_skill(skill_id):
    db = SessionLocal()
    try:
        from models import ResumeSkillCategory
        cat = db.query(ResumeSkillCategory).filter(ResumeSkillCategory.id == skill_id).first()
        if not cat:
            return jsonify({'error': 'Not found'}), 404
        data = request.json
        for field in ('category_name', 'skills', 'sort_order'):
            if field in data:
                setattr(cat, field, data[field])
        db.commit()
        return jsonify({'message': 'Skill category updated'})
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        db.close()


@app.route('/api/resume/skills/<int:skill_id>', methods=['DELETE'])
def delete_resume_skill(skill_id):
    db = SessionLocal()
    try:
        from models import ResumeSkillCategory
        cat = db.query(ResumeSkillCategory).filter(ResumeSkillCategory.id == skill_id).first()
        if not cat:
            return jsonify({'error': 'Not found'}), 404
        db.delete(cat)
        db.commit()
        return jsonify({'message': 'Skill category deleted'})
    finally:
        db.close()


@app.route('/api/resume/skills/reorder', methods=['PUT'])
def reorder_resume_skills():
    db = SessionLocal()
    try:
        from models import ResumeSkillCategory
        data = request.json  # expects [{id, sort_order}, ...]
        for item in data:
            cat = db.query(ResumeSkillCategory).filter(ResumeSkillCategory.id == item['id']).first()
            if cat:
                cat.sort_order = item['sort_order']
        db.commit()
        return jsonify({'message': 'Skills reordered'})
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        db.close()


@app.route('/api/resume/all', methods=['GET'])
def get_resume_all():
    db = SessionLocal()
    try:
        from models import ResumeProfile, ResumeExperience, ResumeEducation, ResumeSkillCategory

        profile = db.query(ResumeProfile).first()
        profile_data = {
            'id': profile.id,
            'full_name': profile.full_name,
            'email': profile.email,
            'phone': profile.phone,
            'location': profile.location,
            'linkedin_url': profile.linkedin_url,
            'github_url': profile.github_url,
            'summary': profile.summary,
        } if profile else {}

        experience = db.query(ResumeExperience).order_by(ResumeExperience.sort_order).all()
        experience_data = [{
            'id': e.id,
            'company': e.company,
            'title': e.title,
            'location': e.location,
            'start_date': e.start_date,
            'end_date': e.end_date,
            'bullets': json.loads(e.bullets) if e.bullets else [],
            'sort_order': e.sort_order,
        } for e in experience]

        education = db.query(ResumeEducation).order_by(ResumeEducation.sort_order).all()
        education_data = [{
            'id': e.id,
            'institution': e.institution,
            'degree': e.degree,
            'field_of_study': e.field_of_study,
            'gpa': e.gpa,
            'dates': e.dates,
            'sort_order': e.sort_order,
        } for e in education]

        skills = db.query(ResumeSkillCategory).order_by(ResumeSkillCategory.sort_order).all()
        skills_data = [{
            'id': s.id,
            'category_name': s.category_name,
            'skills': s.skills,
            'sort_order': s.sort_order,
        } for s in skills]

        return jsonify({
            'profile': profile_data,
            'experience': experience_data,
            'education': education_data,
            'skills': skills_data,
        })
    finally:
        db.close()


# ─── Search Terms API ────────────────────────────────────

@app.route('/api/search-terms', methods=['GET'])
def get_search_terms():
    db = SessionLocal()
    try:
        terms = db.query(SearchTerm).all()
        return jsonify([{
            'id': t.id,
            'term': t.term,
            'source': t.source,
            'active': t.active,
            'last_used': t.last_used.isoformat() + 'Z' if t.last_used else None,
            'hit_count': t.hit_count,
        } for t in terms])
    finally:
        db.close()


@app.route('/api/search-terms', methods=['POST'])
def add_search_term():
    db = SessionLocal()
    try:
        data = request.json
        term = SearchTerm(term=data['term'], source=data.get('source', 'user'))
        db.add(term)
        db.commit()
        return jsonify({'message': 'Search term added', 'id': term.id}), 201
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        db.close()


@app.route('/api/search-terms/<int:term_id>', methods=['PATCH'])
def toggle_search_term(term_id):
    db = SessionLocal()
    try:
        term = db.query(SearchTerm).filter(SearchTerm.id == term_id).first()
        if not term:
            return jsonify({'error': 'Not found'}), 404
        term.active = not term.active
        db.commit()
        return jsonify({'message': 'Toggled', 'active': term.active})
    finally:
        db.close()


# ─── Blocked Companies API ───────────────────────────────

@app.route('/api/blocked-companies', methods=['GET'])
def get_blocked_companies():
    db = SessionLocal()
    try:
        companies = db.query(BlockedCompany).all()
        return jsonify([{
            'id': c.id,
            'name': c.name,
            'reason': c.reason,
        } for c in companies])
    finally:
        db.close()


@app.route('/api/blocked-companies', methods=['POST'])
def add_blocked_company():
    db = SessionLocal()
    try:
        data = request.json
        company = BlockedCompany(name=data['name'], reason=data.get('reason'))
        db.add(company)
        db.commit()
        return jsonify({'message': 'Company blocked', 'id': company.id}), 201
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        db.close()


@app.route('/api/blocked-companies/<int:company_id>', methods=['DELETE'])
def remove_blocked_company(company_id):
    db = SessionLocal()
    try:
        company = db.query(BlockedCompany).filter(BlockedCompany.id == company_id).first()
        if not company:
            return jsonify({'error': 'Not found'}), 404
        db.delete(company)
        db.commit()
        return jsonify({'message': 'Company removed from blocklist'})
    finally:
        db.close()


# ─── Scraper Trigger ─────────────────────────────────────

_scrape_status = {
    'running': False,
    'started_at': None,
    'finished_at': None,
    'result': None,
    'error': None,
}
_scrape_lock = threading.Lock()
_scrape_thread_active = False

def _run_scrape_background():
    """Run scraper in background thread."""
    global _scrape_thread_active
    _scrape_thread_active = True
    from scraper import run_scraper
    try:
        run_scraper()
    except Exception as e:
        print(f"Scraper thread exception: {e}", flush=True)
    finally:
        _scrape_thread_active = False

@app.route('/api/scrape', methods=['POST'])
def trigger_scrape():
    """Manual trigger for scraping — returns immediately, runs in background."""
    from run_status import load_status, save_status, is_external_process_running
    status_data = load_status()
    scrape_info = status_data.get('scraper', {})
    
    # Self-heal if needed
    if scrape_info.get('running'):
        if not (_scrape_thread_active or is_external_process_running('scraper')):
            scrape_info['running'] = False
            scrape_info['error'] = 'Process terminated unexpectedly'
            scrape_info['finished_at'] = datetime.utcnow().isoformat() + 'Z'
            status_data['scraper'] = scrape_info
            save_status(status_data)

    is_running = scrape_info.get('running') or _scrape_thread_active or is_external_process_running('scraper')
    if is_running:
        return jsonify({'status': 'already_running'}), 409

    t = threading.Thread(target=_run_scrape_background, daemon=True)
    t.start()
    return jsonify({'status': 'started'}), 202

@app.route('/api/scrape/status', methods=['GET'])
def scrape_status():
    """Check if a scrape is running and get results when done."""
    from run_status import load_status, save_status, is_external_process_running
    status_data = load_status()
    scrape_info = status_data.get('scraper', {
        'running': False, 'started_at': None, 'finished_at': None, 'result': None, 'error': None
    })
    
    # Cross-validate if it says it is running
    if scrape_info.get('running'):
        is_active = _scrape_thread_active or is_external_process_running('scraper')
        if not is_active:
            # Self-heal crashed process
            scrape_info['running'] = False
            scrape_info['error'] = 'Process terminated unexpectedly'
            scrape_info['finished_at'] = datetime.utcnow().isoformat() + 'Z'
            status_data['scraper'] = scrape_info
            save_status(status_data)
    else:
        # Check if external process is running
        if is_external_process_running('scraper'):
            scrape_info['running'] = True
            scrape_info['error'] = None
            if not scrape_info.get('started_at'):
                scrape_info['started_at'] = datetime.utcnow().isoformat() + 'Z'
    
    return jsonify(scrape_info)


# ─── Scorer Trigger ──────────────────────────────────────

_score_status = {
    'running': False,
    'started_at': None,
    'finished_at': None,
    'result': None,
    'error': None,
}
_score_lock = threading.Lock()
_score_thread_active = False

def _run_score_background():
    """Run scorer in background thread."""
    global _score_thread_active
    _score_thread_active = True
    try:
        db = SessionLocal()
        try:
            profile = db.query(Profile).first()
            if not profile:
                return

            # Reset score_attempts on previously failed jobs so they get retried
            from models import Job as JobModel
            stuck = db.query(JobModel).filter(
                JobModel.status == 'new',
                JobModel.match_score == 0,
                JobModel.score_attempts >= 3,
            ).all()
            for j in stuck:
                j.score_attempts = 0
                j.score_error = None
            if stuck:
                db.commit()

            from scorer import score_new_jobs
            score_new_jobs(db, profile)
        finally:
            db.close()
    except Exception as e:
        print(f"Scorer thread exception: {e}", flush=True)
    finally:
        _score_thread_active = False

@app.route('/api/score', methods=['POST'])
def trigger_score():
    """Manual trigger for scoring — returns immediately, runs in background."""
    from run_status import load_status, save_status, is_external_process_running
    status_data = load_status()
    score_info = status_data.get('scorer', {})
    
    # Self-heal if needed
    if score_info.get('running'):
        if not (_score_thread_active or is_external_process_running('scorer')):
            score_info['running'] = False
            score_info['error'] = 'Process terminated unexpectedly'
            score_info['finished_at'] = datetime.utcnow().isoformat() + 'Z'
            status_data['scorer'] = score_info
            save_status(status_data)

    is_running = score_info.get('running') or _score_thread_active or is_external_process_running('scorer')
    if is_running:
        return jsonify({'status': 'already_running'}), 409

    t = threading.Thread(target=_run_score_background, daemon=True)
    t.start()
    return jsonify({'status': 'started'}), 202

@app.route('/api/score/status', methods=['GET'])
def score_status():
    """Check if scoring is running and get results when done."""
    from run_status import load_status, save_status, is_external_process_running
    status_data = load_status()
    score_info = status_data.get('scorer', {
        'running': False, 'started_at': None, 'finished_at': None, 'result': None, 'error': None
    })
    
    # Cross-validate if it says it is running
    if score_info.get('running'):
        is_active = _score_thread_active or is_external_process_running('scorer')
        if not is_active:
            # Self-heal crashed process
            score_info['running'] = False
            score_info['error'] = 'Process terminated unexpectedly'
            score_info['finished_at'] = datetime.utcnow().isoformat() + 'Z'
            status_data['scorer'] = score_info
            save_status(status_data)
    else:
        # Check if external process is running
        if is_external_process_running('scorer'):
            score_info['running'] = True
            score_info['error'] = None
            if not score_info.get('started_at'):
                score_info['started_at'] = datetime.utcnow().isoformat() + 'Z'
                
    return jsonify(score_info)


@app.route('/api/research/status', methods=['GET'])
def research_status():
    """Check if researcher is running and get results when done."""
    from run_status import load_status, save_status, is_external_process_running
    status_data = load_status()
    researcher_info = status_data.get('researcher', {
        'running': False, 'started_at': None, 'finished_at': None, 'result': None, 'error': None
    })
    
    # Cross-validate if it says it is running
    is_active = len(_generating_packets) > 0 or is_external_process_running('researcher')
    if researcher_info.get('running'):
        if not is_active:
            # Self-heal crashed process
            researcher_info['running'] = False
            researcher_info['error'] = 'Process terminated unexpectedly'
            researcher_info['finished_at'] = datetime.utcnow().isoformat() + 'Z'
            status_data['researcher'] = researcher_info
            save_status(status_data)
    else:
        # Check if process is active
        if is_active:
            researcher_info['running'] = True
            researcher_info['error'] = None
            if not researcher_info.get('started_at'):
                researcher_info['started_at'] = datetime.utcnow().isoformat() + 'Z'
                
    return jsonify(researcher_info)


# ─── Chat API ────────────────────────────────────────────

@app.route('/api/jobs/<int:job_id>/chat', methods=['GET'])
def get_chat_history(job_id):
    db = SessionLocal()
    try:
        messages = db.query(ChatMessage).filter(ChatMessage.job_id == job_id).order_by(ChatMessage.created_at).all()
        return jsonify([{
            'id': m.id,
            'role': m.role,
            'content': m.content,
            'created_at': m.created_at.isoformat() + 'Z' if m.created_at else None,
        } for m in messages])
    finally:
        db.close()


@app.route('/api/jobs/<int:job_id>/chat', methods=['POST'])
def send_chat_message(job_id):
    """Send a message and get AI response with job + resume context."""
    import requests as http_requests
    db = SessionLocal()
    try:
        data = request.json
        user_message = data.get('message', '')
        if not user_message.strip():
            return jsonify({'error': 'Empty message'}), 400

        # Save user message
        db.add(ChatMessage(job_id=job_id, role='user', content=user_message))
        db.commit()

        # Get job + profile context
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return jsonify({'error': 'Job not found'}), 404
        profile = db.query(Profile).first()

        # Get chat history (last 20 messages)
        history = db.query(ChatMessage).filter(
            ChatMessage.job_id == job_id
        ).order_by(ChatMessage.created_at.desc()).limit(20).all()
        history.reverse()

        # Fix consecutive same-role messages (MiniMax rejects these)
        cleaned_history = []
        for msg in history:
            if cleaned_history and cleaned_history[-1].role == msg.role:
                # Insert a placeholder assistant message between consecutive same-role
                cleaned_history.append(type('obj', (object,), {'role': 'assistant', 'content': 'Understood.'})())
            cleaned_history.append(msg)
        history = cleaned_history

        # Get behavioral context
        from learner import get_rejection_context
        behavior = get_rejection_context(db)

        # Build resume index for bullet_overrides
        from models import ResumeExperience
        import json as _json
        resume_index_lines = []
        resume_exps = db.query(ResumeExperience).order_by(ResumeExperience.sort_order).all()
        for _e in resume_exps:
            _bullets = _json.loads(_e.bullets) if _e.bullets else []
            resume_index_lines.append(f'Experience ID {_e.id}: {_e.title} @ {_e.company} ({len(_bullets)} bullets)')
            for _bi, _b in enumerate(_bullets):
                resume_index_lines.append(f'  [{_bi}] {_b[:100]}')
        resume_index = chr(10).join(resume_index_lines)

        # Build system context
        system_msg = f"""You are Michael's job search assistant. Direct, concise, no filler.

RESUME:
{profile.resume_text or ''}

RESUME STRUCTURE (use IDs for bullet_overrides in generate_tailored_resume):
{resume_index}

JOB:
{job.title} at {job.company}
Location: {job.location} | Remote: {job.remote}
Score: {job.match_score}% — {job.match_reasoning or 'N/A'}

DESCRIPTION:
{(job.description or '')[:3000]}

{behavior}

FIRST MESSAGE ON A NEW JOB: Give a quick skills analysis — what matches, what's missing, what he forgot, and whether to apply. Keep it tight.

RESUME — TWO MODES, USE THE RIGHT ONE:

MODE 1: PERMANENT EDITS (user wants to fix/improve the master resume)
- add_resume_bullet: Add a bullet to an experience entry.
- remove_resume_bullet: Remove a bullet from experience.
- add_resume_skills: Add skills to a category.
- update_resume_summary: Replace the professional summary.
Use these when Michael says things like "remove that printer bullet", "add X to my skills", "change my summary".

MODE 2: JOB-SPECIFIC TAILORING (user wants a tailored resume for THIS job)
- generate_tailored_resume: Creates a COPY tailored for this job. NEVER modifies the master.
  Args: summary, experience_order, skills_emphasis, bullet_overrides, notes.
  **bullet_overrides** is a dict mapping experience ID -> list of bullet indices to KEEP.
  Example: {{"1": [0, 2, 5]}} means "for experience #1, include only bullets 0, 2, and 5."
  Use this when Michael says "generate a resume for this job", "tailor it", "create a version".
  **CRITICAL: You MUST output the actual <<ACTION>> block or native tool call. Do NOT write "✅ Resume ID X" without calling the tool. If you don't call the tool, no resume is generated.**

OTHER TOOLS:
- update_job_status: Change status (will_apply, applied, interview, offer, rejected).
- add_search_term: Add search keywords for the scraper.
- block_company: Block a company from results.
- add_rejection_pattern: Penalize similar future jobs.
- update_profile: Update search preferences.
- generate_research_packet: Start research for this job.
- save_research_packet: Save completed research data.

TOOL FORMAT — output an ACTION block:
<<ACTION>>
{{"tool": "tool_name", "args": {{"key": "value"}}}}
<</ACTION>>

RULES:
- When Michael asks to edit the resume, DO IT. Don't ask for permission or say you can't.
- Multiple ACTION blocks are fine in one response.
- If the job is clearly bad (wrong location/role), reject it proactively.
- "reject"/"skip"/"nope"/"hard pass" → immediately output update_job_status with status='rejected'.
- Never narrate about tools. Just use them.
- TAILORING ≠ EDITING: When generating a tailored resume, use generate_tailored_resume with bullet_overrides to SELECT which bullets to include. Do NOT use remove_resume_bullet or add_resume_bullet for tailoring — those permanently change the master resume."""

        # Build messages for MiniMax — must include reasoning_content for thinking mode
        api_messages = [{'role': 'system', 'content': system_msg}]
        for msg in history:
            m = {'role': msg.role, 'content': msg.content}
            if msg.role == 'assistant' and getattr(msg, 'reasoning_content', None):
                m['reasoning_content'] = msg.reasoning_content
            api_messages.append(m)
        api_messages.append({'role': 'user', 'content': user_message})

        # Cap total context: system + last N messages + user. MiniMax rejects >128k tokens.
        MAX_CONTEXT_MESSAGES = 30
        if len(api_messages) > MAX_CONTEXT_MESSAGES + 2:  # +2 for system + user
            api_messages = [api_messages[0]] + api_messages[-(MAX_CONTEXT_MESSAGES + 1):]

        # Pre-check: handle research packet generation directly
        from chat_tools import TOOLS_SCHEMA, execute_tool
        lower_msg = user_message.lower()
        is_packet_request = any(phrase in lower_msg for phrase in [
            'research packet', 'generate packet', 'packet for this',
            'create packet', 'build packet', 'reasearch packet',
            'resarch packet', 'reseach packet', 'packet', 'company research',
        ])
        if is_packet_request:
                # Fire async generation — don't block the chat request
                if job_id not in _generating_packets:
                    _start_packet_generation(job_id)
                    return jsonify({'role': 'assistant', 'content': '🔍 Research packet generation started — this takes a minute. Check the Research Packet tab, I\'ll notify you when it\'s ready.', '_packet_generating': True})
                else:
                    return jsonify({'role': 'assistant', 'content': '⏳ Already generating a research packet for this job. Check the Research Packet tab.', '_packet_generating': True})

        # Call LLM with tools via unified client
        from llm_client import call_llm
        from llm_helpers import strip_thinking_tags

        # Loop to handle tool calls
        max_iterations = 5
        for iteration in range(max_iterations):
            llm_result = call_llm(
                api_messages,
                tools=TOOLS_SCHEMA,
                tool_choice='auto',
                temperature=0.4,
                max_tokens=8192,
                timeout=300,
                thinking_budget=16384,  # MiniMax requires thinking enabled for reasoning_content passback on multi-turn
            )
            message = llm_result['raw_message']
            finish_reason = llm_result['finish_reason']
            app.logger.info(f'[Chat job={job_id}] finish_reason={finish_reason}, has_tool_calls={bool(message.get("tool_calls"))}, content_len={len(message.get("content", "") or "")}')

            native_calls = llm_result['tool_calls']
            parsed_tools = llm_result['parsed_tool_calls']
            raw_content = llm_result['content']

            # No tool calls at all → we're done
            if not native_calls and not parsed_tools:
                ai_content = raw_content
                break

            # Process parsed ACTION block tools (MiniMax text fallback)
            auto_results = []
            for action in parsed_tools:
                try:
                    tool_name = action.get('tool')
                    tool_args = action.get('args', {})
                    exec_result = execute_tool(db, tool_name, tool_args, job_id)
                    auto_results.append(f"✅ {exec_result['message']}")
                    app.logger.info(f'[Chat job={job_id}] Parsed tool: {tool_name}({tool_args}) -> {exec_result}')
                except Exception as e:
                    auto_results.append(f"⚠️ Action failed: {e}")
                    app.logger.warning(f'[Chat job={job_id}] Parsed tool error: {e}')

            # Process native tool calls — must follow OpenAI protocol:
            # assistant(with tool_calls) → tool(result1) → tool(result2) → ...
            if native_calls:
                # Step 1: Append the assistant message WITH its tool_calls to the context
                # MiniMax requires seeing the assistant message that triggered the tool calls
                assistant_msg = {
                    'role': 'assistant',
                    'content': raw_content or '',
                    'tool_calls': native_calls,
                }
                # Pass through reasoning_content if present (MiniMax thinking mode)
                if llm_result.get('reasoning_content'):
                    assistant_msg['reasoning_content'] = llm_result['reasoning_content']
                api_messages.append(assistant_msg)

                # Step 2: Execute each tool and append tool result messages
                for tool_call in native_calls:
                    try:
                        func_info = tool_call.get('function', {})
                        func_name = func_info.get('name')
                        if not func_name:
                            app.logger.warning(f'[Chat job={job_id}] Tool call missing function name: {tool_call}')
                            continue
                        import json as json_mod
                        func_args_raw = func_info.get('arguments', '{}')
                        func_args = json_mod.loads(func_args_raw) if isinstance(func_args_raw, str) else func_args_raw
                        tool_result = execute_tool(db, func_name, func_args, job_id)
                        auto_results.append(f"✅ {tool_result['message']}")
                        app.logger.info(f'[Chat job={job_id}] Native tool: {func_name}({func_args}) -> {tool_result}')
                    except Exception as te:
                        app.logger.error(f'[Chat job={job_id}] Tool call error: {te}')
                        tool_result = {'message': f'Tool error: {te}'}
                        auto_results.append(f"⚠️ Tool error: {te}")

                    api_messages.append({
                        'role': 'tool',
                        'tool_call_id': tool_call.get('id', ''),
                        'content': json.dumps(tool_result),
                    })

                # Native tool calls → loop back so LLM can respond to results
                continue

            # Parsed tools only (ACTION blocks) — don't need LLM follow-up
            # Just compose the final response from content + results
            if parsed_tools:
                ai_content = raw_content + '\n\n' + '\n'.join(auto_results) if auto_results else raw_content
                break
        else:
            ai_content = strip_thinking_tags(message.get('content', 'I processed your request but hit the iteration limit.'))

        # Save AI response (skip empty ones)
        # Capture reasoning_content from LLM result for MiniMax thinking mode multi-turn
        rc = llm_result.get('reasoning_content') if llm_result else None
        if ai_content and ai_content.strip():
            ai_msg = ChatMessage(job_id=job_id, role='assistant', content=ai_content, reasoning_content=rc or None)
            db.add(ai_msg)
            db.commit()
        else:
            ai_content = "I processed that but had nothing to say. Try rephrasing."
            ai_msg = ChatMessage(job_id=job_id, role='assistant', content=ai_content, reasoning_content=rc or None)
            db.add(ai_msg)
            db.commit()

        return jsonify({
            'id': ai_msg.id,
            'role': 'assistant',
            'content': ai_content,
            'created_at': ai_msg.created_at.isoformat() + 'Z' if ai_msg.created_at else None,
        })
    except Exception as e:
        db.rollback()
        import logging
        logging.error(f"[Chat job={job_id}] {type(e).__name__}: {e}")
        # Log full response body for HTTP errors so we can diagnose
        if hasattr(e, 'response') and e.response is not None:
            logging.error(f"[Chat job={job_id}] Response body: {e.response.text[:500]}")
        if "400" in str(e) or "429" in str(e) or "500" in str(e):
            return jsonify({
                'id': None,
                'role': 'assistant',
                'content': 'AI service is temporarily unavailable. Try again in a moment.',
                'created_at': None,
            })
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()


# ─── Tailored Resumes API ────────────────────────────────

@app.route('/api/jobs/<int:job_id>/resumes', methods=['GET'])
def get_tailored_resumes(job_id):
    db = SessionLocal()
    try:
        from models import TailoredResume
        resumes = db.query(TailoredResume).filter(
            TailoredResume.job_id == job_id
        ).order_by(TailoredResume.created_at.desc()).all()
        return jsonify([{
            'id': r.id,
            'job_id': r.job_id,
            'notes': r.notes,
            'created_at': r.created_at.isoformat() + 'Z' if r.created_at else None,
            'has_pdf': bool(r.resume_pdf_path),
            'has_docx': bool(r.resume_docx_path),
        } for r in resumes])
    finally:
        db.close()


@app.route('/api/jobs/<int:job_id>/resumes/generate', methods=['POST'])
def generate_tailored_resume(job_id):
    db = SessionLocal()
    try:
        from models import TailoredResume, Profile, Job
        import json
        from resume_generator import generate_resume

        data = request.json or {}
        chat_history = data.get('chat_history', '')
        summary_override = data.get('summary', '')
        experience_order = data.get('experience_order')
        skills_emphasis = data.get('skills_emphasis')
        notes = data.get('notes', '')

        # Get base resume from profile
        profile = db.query(Profile).first()
        if not profile or not profile.resume_text:
            return jsonify({'error': 'No resume found in profile'}), 400

        # Get job info for contact customization
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return jsonify({'error': 'Job not found'}), 404

        output_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'data', 'resumes', str(job_id)
        )

        result = generate_resume(
            job_id=job_id,
            output_dir=output_dir,
            summary_override=summary_override,
            experience_order=experience_order,
            skills_emphasis=skills_emphasis,
        )

        # Save to database
        tailored = TailoredResume(
            job_id=job_id,
            chat_history=json.dumps(chat_history) if chat_history else None,
            resume_html=result['html'],
            resume_pdf_path=result['pdf_path'],
            resume_docx_path=result['docx_path'],
            notes=notes,
        )
        db.add(tailored)
        db.commit()

        return jsonify({
            'id': tailored.id,
            'pdf_path': result['pdf_path'],
            'docx_path': result['docx_path'],
            'zip_path': result['zip_path'],
            'created_at': tailored.created_at.isoformat() + 'Z',
        })
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()


@app.route('/api/jobs/<int:job_id>/resumes/auto-tailor', methods=['POST'])
def auto_tailor_resume(job_id):
    db = SessionLocal()
    try:
        from models import TailoredResume, ResumeProfile, ResumeExperience, ResumeSkillCategory, Job
        import json
        from resume_generator import generate_resume
        from llm_client import call_llm
        from llm_helpers import _extract_json_object

        # Load job info
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return jsonify({'error': 'Job not found'}), 404

        # Load master profile data
        profile = db.query(ResumeProfile).first()
        if not profile:
            return jsonify({'error': 'Master resume profile not found'}), 400

        # Build index of experiences and bullets
        exps = db.query(ResumeExperience).order_by(ResumeExperience.sort_order).all()
        experience_data = []
        for e in exps:
            bullets = json.loads(e.bullets) if e.bullets else []
            experience_data.append({
                'id': e.id,
                'company': e.company,
                'title': e.title,
                'bullets': bullets
            })

        # Build index of skill categories
        skills = db.query(ResumeSkillCategory).order_by(ResumeSkillCategory.sort_order).all()
        skills_data = []
        for s in skills:
            skills_data.append({
                'category_name': s.category_name,
                'skills': s.skills
            })

        # Format prompt for the LLM
        prompt = f"""You are an expert resume writer tailoring Michael's resume for a specific job.
Your task is to select the most relevant experiences and skills, and write a professional summary.
NEVER invent or hallucinate any facts, dates, certifications, tools, or past roles. Only use what is provided in the master resume.

JOB INFO:
Title: {job.title}
Company: {job.company}
Location: {job.location} | Remote: {job.remote}
Description:
{(job.description or '')[:3000]}

MASTER RESUME DATA:
Summary: {profile.summary or ''}

EXPERIENCES & BULLETS:
"""
        for exp in experience_data:
            prompt += f"\nExperience ID {exp['id']}: {exp['title']} @ {exp['company']}\n"
            for idx, b in enumerate(exp['bullets']):
                prompt += f"  [{idx}] {b}\n"

        prompt += "\nSKILL CATEGORIES:\n"
        for cat in skills_data:
            prompt += f"- {cat['category_name']}: {cat['skills']}\n"

        prompt += """
Your goal is to decide:
1. **summary**: A professional summary (around 4-5 sentences, max 100 words) tailored to the job description, highlight his actual matching skills, with NO hallucinations.
2. **bullet_overrides**: A dictionary mapping Experience ID (as string) to a list of bullet indices (as integers) to KEEP. You must filter out irrelevant or redundant bullets. KEEP the most impactful, relevant ones. For example, if the job has NO AI/LLM components, exclude the AI-powered automation bullets! If the job is an endpoint management role, keep MECM, Intune, Autopilot, AD, and scripting bullets. Keep between 6 and 12 bullet points for the main WSI experience, and 2-3 for other experiences.
3. **skills_emphasis**: An array of Category Names to highlight/emphasize, placed first in order.
4. **experience_order**: An array of experience IDs (ints) in desired order.
5. **notes**: A brief string describing what you tailored and why (e.g. "Focused on Intune and SCCM, suppressed AI/LLM work").

You MUST return ONLY a clean JSON object of this structure:
{
  "summary": "...",
  "bullet_overrides": {
    "1": [0, 2, 5],
    "2": [0, 1]
  },
  "skills_emphasis": ["Endpoint Management", "Scripting & Automation"],
  "experience_order": [1, 3, 2],
  "notes": "..."
}

Ensure the output is valid JSON."""

        # Call LLM — thinking disabled so all tokens go to the JSON output
        llm_res = call_llm(
            messages=[{'role': 'user', 'content': prompt}],
            temperature=0.2,
            max_tokens=4096,
            thinking_budget=0,
        )
        content = llm_res['content']

        if not content or not content.strip():
            raise Exception("LLM returned an empty response (possible timeout or API error)")

        # Strip markdown code fences if present
        import re
        fence_match = re.search(r'```(?:json)?\s*([\s\S]+?)```', content)
        if fence_match:
            content = fence_match.group(1).strip()

        # Extract JSON
        json_str, _ = _extract_json_object(content)
        if not json_str:
            # Fallback: greedy search for outermost JSON object
            m = re.search(r'\{[\s\S]*\}', content)
            if m:
                json_str = m.group(0)

        if not json_str:
            raise Exception("Could not extract JSON from LLM response: " + content[:500])

        # Attempt JSON repair: strip trailing commas before } or ] which cause parse errors
        # when the model truncates mid-object
        def _repair_json(s):
            # Remove trailing commas before closing brackets/braces
            s = re.sub(r',\s*([}\]])', r'\1', s)
            return s

        try:
            tailoring_params = json.loads(json_str)
        except json.JSONDecodeError:
            repaired = _repair_json(json_str)
            try:
                tailoring_params = json.loads(repaired)
            except json.JSONDecodeError as e:
                raise Exception(f"JSON parse failed even after repair: {e}. Raw: {json_str[:400]}")

        summary_override = tailoring_params.get('summary', '')
        bullet_overrides_raw = tailoring_params.get('bullet_overrides', {})
        skills_emphasis = tailoring_params.get('skills_emphasis', [])
        experience_order = tailoring_params.get('experience_order', [])
        notes = tailoring_params.get('notes', 'Auto-tailored by AI')

        # Convert bullet overrides keys to integers
        bullet_overrides = {}
        for k, v in bullet_overrides_raw.items():
            try:
                bullet_overrides[int(k)] = [int(x) for x in v]
            except Exception:
                pass

        output_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'data', 'resumes', str(job_id)
        )

        result = generate_resume(
            job_id=job_id,
            output_dir=output_dir,
            summary_override=summary_override,
            experience_order=experience_order,
            skills_emphasis=skills_emphasis,
            bullet_overrides=bullet_overrides,
        )

        # Save to database
        tailored = TailoredResume(
            job_id=job_id,
            resume_html=result['html'],
            resume_pdf_path=result['pdf_path'],
            resume_docx_path=result['docx_path'],
            notes=notes,
        )
        db.add(tailored)
        db.commit()

        return jsonify({
            'id': tailored.id,
            'pdf_path': result['pdf_path'],
            'docx_path': result['docx_path'],
            'zip_path': result['zip_path'],
            'notes': notes,
            'created_at': tailored.created_at.isoformat() + 'Z',
        })
    except Exception as e:
        db.rollback()
        import logging
        logging.error(f"Error in auto_tailor_resume: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()


@app.route('/api/resumes/<int:resume_id>/download', methods=['GET'])
def download_tailored_resume(resume_id):
    db = SessionLocal()
    try:
        from models import TailoredResume
        resume = db.query(TailoredResume).filter(TailoredResume.id == resume_id).first()
        if not resume:
            return jsonify({'error': 'Not found'}), 404

        import zipfile
        from flask import send_file
        from io import BytesIO

        buf = BytesIO()
        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
            if resume.resume_pdf_path and os.path.exists(resume.resume_pdf_path):
                zf.write(resume.resume_pdf_path, os.path.basename(resume.resume_pdf_path))
            if resume.resume_docx_path and os.path.exists(resume.resume_docx_path):
                zf.write(resume.resume_docx_path, os.path.basename(resume.resume_docx_path))
        buf.seek(0)

        return send_file(
            buf,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'resume_job_{resume.job_id}_{resume.id}.zip',
        )
    finally:
        db.close()


@app.route('/api/resumes/<int:resume_id>', methods=['DELETE'])
def delete_tailored_resume(resume_id):
    db = SessionLocal()
    try:
        from models import TailoredResume
        resume = db.query(TailoredResume).filter(TailoredResume.id == resume_id).first()
        if not resume:
            return jsonify({'error': 'Not found'}), 404

        # Delete files
        for path in [resume.resume_pdf_path, resume.resume_docx_path]:
            if path and os.path.exists(path):
                os.remove(path)

        db.delete(resume)
        db.commit()
        return jsonify({'success': True})
    finally:
        db.close()


# ─── Research Packets API ────────────────────────────────

# In-memory tracker for background packet generation
_generating_packets = set()
_generating_lock = threading.Lock()


def _start_packet_generation(job_id):
    """Fire async packet generation. Safe to call from chat or REST endpoint."""
    with _generating_lock:
        if job_id in _generating_packets:
            return False
        _generating_packets.add(job_id)

    def _run():
        import logging
        logger = logging.getLogger('packet-gen')
        try:
            from chat_tools import execute_tool
            db = SessionLocal()
            try:
                logger.info(f'[job={job_id}] Starting packet generation')
                result = execute_tool(db, 'generate_research_packet', {'force': True}, job_id)
                logger.info(f'[job={job_id}] Done: success={result.get("success")} msg={result.get("message","")[:100]}')
            finally:
                db.close()
        except Exception as e:
            logger.error(f'[job={job_id}] FAILED: {type(e).__name__}: {e}')
        finally:
            with _generating_lock:
                _generating_packets.discard(job_id)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    return True


@app.route('/api/jobs/<int:job_id>/packet/generate', methods=['POST'])
def generate_packet_async(job_id):
    """Start research packet generation in background. Returns immediately."""
    if not _start_packet_generation(job_id):
        return jsonify({'status': 'already_generating'}), 409
    return jsonify({'status': 'started'}), 202


@app.route('/api/jobs/<int:job_id>/packet', methods=['GET'])
def get_research_packet(job_id):
    db = SessionLocal()
    try:
        from models import ResearchPacket, PacketFeedback
        packet = db.query(ResearchPacket).filter(ResearchPacket.job_id == job_id).first()
        feedback = db.query(PacketFeedback).filter(PacketFeedback.job_id == job_id).order_by(PacketFeedback.created_at.desc()).all()
        if not packet:
            return jsonify({'packet': None, 'feedback': [], 'generating': job_id in _generating_packets})
        return jsonify({
            'packet': {
                'id': packet.id,
                'job_id': packet.job_id,
                'content': packet.content,
                'company_research': packet.company_research,
                'role_analysis': packet.role_analysis,
                'fit_analysis': packet.fit_analysis,
                'interview_prep': packet.interview_prep,
                'questions_to_ask': packet.questions_to_ask,
                'risk_assessment': packet.risk_assessment,
                'bottom_line': packet.bottom_line,
                'created_at': packet.created_at.isoformat() + 'Z' if packet.created_at else None,
                'updated_at': packet.updated_at.isoformat() + 'Z' if packet.updated_at else None,
            },
            'feedback': [{
                'id': f.id,
                'section': f.section,
                'feedback_text': f.feedback_text,
                'created_at': f.created_at.isoformat() + 'Z' if f.created_at else None,
            } for f in feedback],
            'generating': job_id in _generating_packets,
        })
    finally:
        db.close()


@app.route('/api/jobs/<int:job_id>/packet', methods=['PUT'])
def update_research_packet(job_id):
    db = SessionLocal()
    try:
        from models import ResearchPacket
        data = request.get_json()
        packet = db.query(ResearchPacket).filter(ResearchPacket.job_id == job_id).first()
        if not packet:
            packet = ResearchPacket(job_id=job_id)
            db.add(packet)
        for field in ['content', 'company_research', 'role_analysis', 'fit_analysis',
                      'interview_prep', 'questions_to_ask', 'risk_assessment', 'bottom_line']:
            if field in data:
                setattr(packet, field, data[field])
        from datetime import datetime
        packet.updated_at = datetime.utcnow()
        db.commit()
        return jsonify({'ok': True, 'id': packet.id})
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()


@app.route('/api/jobs/<int:job_id>/packet/feedback', methods=['POST'])
def add_packet_feedback(job_id):
    db = SessionLocal()
    try:
        from models import PacketFeedback
        data = request.get_json()
        fb = PacketFeedback(
            job_id=job_id,
            section=data.get('section', 'general'),
            feedback_text=data.get('feedback_text', ''),
        )
        db.add(fb)
        db.commit()
        return jsonify({'ok': True, 'id': fb.id})
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()


@app.route('/api/packets', methods=['GET'])
def list_packets():
    """List all research packets with job info."""
    db = SessionLocal()
    try:
        from models import ResearchPacket, Job
        packets = db.query(ResearchPacket).order_by(ResearchPacket.updated_at.desc()).all()
        result = []
        for p in packets:
            job = db.query(Job).filter(Job.id == p.job_id).first()
            result.append({
                'id': p.id,
                'job_id': p.job_id,
                'company': job.company if job else 'Unknown',
                'title': job.title if job else 'Unknown',
                'match_score': job.match_score if job else 0,
                'updated_at': p.updated_at.isoformat() + 'Z' if p.updated_at else None,
            })
        return jsonify(result)
    finally:
        db.close()


# ─── Serve Frontend (production) ─────────────────────────

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_frontend(path):
    import os
    from flask import send_from_directory
    frontend_dist = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'dist')
    if path and os.path.exists(os.path.join(frontend_dist, path)):
        return send_from_directory(frontend_dist, path)
    return send_from_directory(frontend_dist, 'index.html')


if __name__ == '__main__':
    from config import Config
    app.run(host=Config.FLASK_HOST, port=Config.FLASK_PORT, debug=True)
