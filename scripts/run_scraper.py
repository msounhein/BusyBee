#!/usr/bin/env python3
"""Cron entry point for job scraper — enterprise-grade reliability."""
import sys
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from scraper import run_scraper
from recovery import recover_failed_jobs, get_scoring_health
from notifier import send_daily_summary
from database import SessionLocal
from models import Job

if __name__ == '__main__':
    print(f"[{__import__('datetime').datetime.now()}] Starting job scraper...")

    # Phase 1: Recover any previously failed jobs
    print("[Recovery] Checking for failed jobs to retry...")
    recovery = recover_failed_jobs()
    print(f"[Recovery] {recovery['retried']} retried, {recovery['recovered']} recovered, {recovery['escalated']} escalated")

    # Phase 2: Run fresh scrape + scoring
    results = run_scraper()
    print(f"Scrape complete: {results}")

    # Phase 3: Build combined notification
    db = SessionLocal()
    try:
        health = get_scoring_health(db)
        print(f"[Health] {health}")

        # Build escalation message if there are stuck jobs
        escalation_msg = None
        if recovery['escalated'] > 0 and recovery['escalation_report']:
            escalation_msg = recovery['escalation_report']
        elif health['failed'] > 0 or health['unscored'] > 5:
            # Generic warning if pipeline is unhealthy but no specific escalation
            escalation_msg = (
                f"⚠️ **Pipeline health:** {health['unscored']} unscored, {health['failed']} failed jobs remain. "
                "Will retry on next run."
            )

        if results['new'] > 0:
            new_jobs = db.query(Job).filter(
                Job.status == 'new', Job.match_score > 0
            ).order_by(Job.match_score.desc()).limit(20).all()
            send_daily_summary(new_jobs, results, escalation_report=escalation_msg)
        elif escalation_msg:
            # No new jobs but something needs attention
            reports_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
            os.makedirs(reports_dir, exist_ok=True)
            with open(os.path.join(reports_dir, 'last_job_summary.txt'), 'w') as f:
                f.write(escalation_msg)

    finally:
        db.close()
