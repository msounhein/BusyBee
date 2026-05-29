#!/bin/bash
# Job Tracker Cron Scraper
# Runs scraper + scorer outside of OpenClaw exec system
# Logs to projects/job-tracker/logs/

set -euo pipefail

PROJECT_DIR="/home/msounhein/projects/job-tracker"
LOG_DIR="$PROJECT_DIR/logs"
mkdir -p "$LOG_DIR"

LOG_FILE="$LOG_DIR/scraper-$(date +%Y%m%d-%H%M%S).log"

cd "$PROJECT_DIR"

{
    echo "=== Job Scraper Cron — $(date) ==="
    echo "Memory: $(free -h | head -2 | tail -1)"
    echo ""

    export PYTHONPATH="$PROJECT_DIR/backend"
    export PATH="/home/msounhein/projects/job-tracker/.venv/bin:$PATH"

    echo "--- Phase 1: Scraping ---"
    python3 -u -c "
from scraper import run_scraper
result = run_scraper()
print(f'Result: {result}')
" 2>&1

    echo ""
    echo "--- Phase 2: Scoring ---"
    python3 -u -c "
from database import SessionLocal
from models import Job, Profile
from scorer import score_new_jobs

db = SessionLocal()
profile = db.query(Profile).first()
unscored = db.query(Job).filter(Job.match_score == 0).count()
print(f'Unscored jobs to process: {unscored}')
if unscored > 0:
    score_new_jobs(db, profile)
    print('Scoring complete.')
remaining = db.query(Job).filter(Job.match_score == 0).count()
scored = db.query(Job).filter(Job.match_score > 0).count()
rejected = db.query(Job).filter(Job.match_score == -1).count()
print(f'Final: {scored} scored, {rejected} rejected, {remaining} remaining unscored')
db.close()
" 2>&1

    echo ""
    echo "--- Phase 3: Research Packets ---"
    python3 -u scripts/build_packets.py --top 5 2>&1

    echo ""
    echo "=== Done — $(date) ==="
} | tee "$LOG_FILE"

# Keep only last 30 days of logs
find "$LOG_DIR" -name "scraper-*.log" -mtime +30 -delete
