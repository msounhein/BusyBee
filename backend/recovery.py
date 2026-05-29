"""Recovery module for failed job scoring.

Handles escalation when jobs fail scoring after max retries:
1. Re-attempts failed jobs with a longer timeout
2. Jobs that still fail get flagged for human review
3. Generates an escalation report
"""
import json
import time
import logging
from datetime import datetime, timedelta

import requests
from models import Job
from scorer import (
    MAX_SCORE_ATTEMPTS,
    is_likely_it_job, is_fake_remote, _call_llm_for_score,
)
from learner import get_rejection_context
from database import SessionLocal

log = logging.getLogger(__name__)

RECOVERY_TIMEOUT = 180  # longer timeout for recovery attempts
RECOVERY_MAX_ATTEMPTS = 1  # one more try with longer timeout
ESCALATION_WINDOW_HOURS = 24  # only retry jobs that failed within this window


def recover_failed_jobs(db=None):
    """Find jobs that failed scoring and retry them with longer timeout.

    Returns dict with recovery stats and any jobs that need human escalation.
    """
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        cutoff = datetime.utcnow() - timedelta(hours=ESCALATION_WINDOW_HOURS)

        failed_jobs = db.query(Job).filter(
            Job.status == 'new',
            Job.score_failed_at.isnot(None),
            Job.score_failed_at >= cutoff,
        ).all()

        if not failed_jobs:
            print("No failed jobs to recover.")
            return {'retried': 0, 'recovered': 0, 'escalated': 0, 'escalation_report': ''}

        from scorer import get_resume_text
        resume_text = get_resume_text(db)
        if not resume_text:
            from models import Profile
            profile = db.query(Profile).first()
            resume_text = profile.resume_text if profile else ''

        if not resume_text:
            print("No resume text — cannot recover failed jobs")
            return {'retried': len(failed_jobs), 'recovered': 0, 'escalated': len(failed_jobs),
                    'escalation_report': 'No resume text available for recovery scoring.'}

        behavior_context = get_rejection_context(db)
        recovered = 0
        escalated = []
        escalation_report_lines = []

        for job in failed_jobs:
            log.info(f"Recovery attempt for job {job.id}: {job.title} @ {job.company}")

            try:
                result = _call_llm_for_score(job, resume_text, behavior_context)
                job.match_score = min(100, max(0, result.get('score', 50)))
                job.match_reasoning = result.get('reasoning', '')
                job.score_error = None
                job.score_failed_at = None

                if job.match_score < 70:
                    job.status = 'rejected'
                    job.rejection_reason = f'Auto-rejected: match score {job.match_score}% below 70% threshold'
                else:
                    job.status = 'new'  # keep as new for notification

                recovered += 1
                log.info(f"Recovered job {job.id} with score {job.match_score}%")

            except Exception as e:
                job.score_attempts += 1
                job.score_error = str(e)
                escalated.append({
                    'id': job.id,
                    'title': job.title,
                    'company': job.company,
                    'location': job.location,
                    'url': job.url,
                    'attempts': job.score_attempts,
                    'error': str(e),
                })
                escalation_report_lines.append(
                    f"• **{job.title}** @ {job.company} — {job.score_attempts} attempts, last error: {str(e)[:100]}"
                )

        db.commit()

        report_text = ""
        if escalated:
            report_text = (
                f"⚠️ **{len(escalated)} jobs could not be scored after recovery:**\n"
                + "\n".join(escalation_report_lines)
            )

        return {
            'retried': len(failed_jobs),
            'recovered': recovered,
            'escalated': len(escalated),
            'escalation_report': report_text,
            'escalated_jobs': escalated,
        }

    finally:
        if close_db:
            db.close()


def get_scoring_health(db=None):
    """Quick health check on the scoring pipeline. Returns a summary dict."""
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        total_new = db.query(Job).filter(Job.status == 'new').count()
        unscored = db.query(Job).filter(Job.status == 'new', Job.match_score == 0).count()
        scored_ok = db.query(Job).filter(Job.status == 'new', Job.match_score > 0).count()
        failed = db.query(Job).filter(
            Job.status == 'new', Job.score_failed_at.isnot(None)
        ).count()

        return {
            'total_new': total_new,
            'unscored': unscored,
            'scored': scored_ok,
            'failed': failed,
            'healthy': failed == 0 and unscored == 0,
        }
    finally:
        if close_db:
            db.close()
