import os


def send_daily_summary(new_jobs, stats, escalation_report=None):
    """Send a Telegram summary to the job search topic."""
    high_match = [j for j in new_jobs if j.match_score and j.match_score >= 70]
    medium_match = [j for j in new_jobs if j.match_score and 40 <= j.match_score < 70]
    low_match = [j for j in new_jobs if j.match_score and j.match_score < 40]

    lines = [
        f"🔍 **Job Search Update**",
        f"",
        f"📊 {stats['new']} new jobs found ({len(high_match)} high match, {len(medium_match)} medium, {len(low_match)} low)",
        f"🚫 {stats['skipped_blocked']} blocked, {stats['skipped_duplicate']} duplicates skipped",
        f"",
    ]

    if high_match:
        lines.append("🔥 **High Match Jobs:**")
        for job in high_match[:5]:
            remote_tag = " 🌐" if job.remote else ""
            lines.append(f"  • **{job.title}** at {job.company} ({job.match_score}%{remote_tag})")
            lines.append(f"    {job.location}")
        lines.append("")

    if medium_match:
        lines.append(f"📋 {len(medium_match)} medium-match jobs — check the dashboard")

    # Append escalation report if provided
    if escalation_report:
        lines.append("")
        lines.append(escalation_report)

    message = '\n'.join(lines)

    # Save to file for pickup
    reports_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    os.makedirs(reports_dir, exist_ok=True)
    with open(os.path.join(reports_dir, 'last_job_summary.txt'), 'w') as f:
        f.write(message)

    print(f"Job summary saved. {stats['new']} new jobs, {len(high_match)} high match.")
    return message
