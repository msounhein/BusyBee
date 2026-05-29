import json
from models import Job, SearchTerm, RejectionPattern
from database import SessionLocal
from config import Config
from llm_client import call_llm


def analyze_user_behavior(db):
    """
    Analyze recent rejection reasons and will_apply notes to learn patterns.
    Returns a context string that gets injected into job scoring prompts.
    """
    # Gather recent rejections (last 100)
    rejected = db.query(Job).filter(
        Job.status == 'rejected',
        Job.rejection_reason.isnot(None),
        Job.rejection_reason != ''
    ).order_by(Job.found_date.desc()).limit(100).all()

    # Gather will_apply notes (last 50)
    will_apply = db.query(Job).filter(
        Job.status.in_(['will_apply', 'applied']),
        Job.apply_note.isnot(None),
        Job.apply_note != ''
    ).order_by(Job.found_date.desc()).limit(50).all()

    if not rejected and not will_apply:
        return ""

    # Build summary for GLM
    rejection_summary = []
    for j in rejected:
        rejection_summary.append(
            '- "%s" at %s: rejected because "%s" (score was %s%%)' % (
                j.title, j.company, j.rejection_reason, j.match_score
            )
        )

    apply_summary = []
    for j in will_apply:
        apply_summary.append(
            '- "%s" at %s: applying because "%s" (score was %s%%)' % (
                j.title, j.company, j.apply_note, j.match_score
            )
        )

    prompt = (
        "Analyze this job search behavior and extract patterns.\n\n"
        "REJECTED JOBS (user passed on these):\n"
        + "\n".join(rejection_summary[:30]) + "\n\n"
        "JOBS USER WANTS TO APPLY TO:\n"
        + "\n".join(apply_summary[:20]) + "\n\n"
        "Based on this behavior, provide:\n"
        "1. A list of 3-5 rejection patterns (what the user consistently does not want)\n"
        "2. A list of 3-5 preference patterns (what the user consistently likes)\n"
        "3. Any suggested adjustments to search keywords\n\n"
        'Respond in this exact JSON format:\n'
        '{\n'
        '  "rejection_patterns": ["pattern1", "pattern2"],\n'
        '  "preference_patterns": ["pattern1", "pattern2"],\n'
        '  "search_adjustments": {"add": ["term1"], "remove": ["term1"]},\n'
        '  "scoring_hints": "Brief guidance for scoring future jobs based on these patterns"\n'
        '}'
    )

    try:
        result = call_llm(
            [{'role': 'user', 'content': prompt}],
            temperature=0.3,
            max_tokens=131072,
            timeout=300,
        )
        content = result['content']

        if '```json' in content:
            content = content.split('```json')[1].split('```')[0]
        elif '```' in content:
            content = content.split('```')[1].split('```')[0]

        result = json.loads(content.strip())

        # Store rejection patterns in DB
        new_patterns = result.get('rejection_patterns', [])
        for pattern_text in new_patterns:
            existing = db.query(RejectionPattern).filter(RejectionPattern.pattern == pattern_text).first()
            if not existing:
                db.add(RejectionPattern(pattern=pattern_text, source='ai', active=True))

        # Add suggested search terms (validate they look like job titles)
        adjustments = result.get('search_adjustments', {})
        for term in adjustments.get('add', [])[:3]:
            # Only add if it looks like a job title (2-5 words, no special chars)
            if (len(term.split()) >= 2 and len(term.split()) <= 5 and
                not any(c in term for c in ['"', '-', 'NOT', 'only', 'remote']) and
                term.lower() not in ['fully remote', '100% remote', 'work from home',
                    'work from anywhere', 'fully distributed', 'remote only',
                    'posted last 7 days', 'remote eligible']):
                existing = db.query(SearchTerm).filter(SearchTerm.term == term).first()
                if not existing:
                    db.add(SearchTerm(term=term, source='ai', active=True))

        # Disable terms suggested for removal
        for term in adjustments.get('remove', []):
            existing = db.query(SearchTerm).filter(SearchTerm.term == term).first()
            if existing and existing.source == 'ai':
                existing.active = False

        db.commit()

        # Build context string for scoring
        context_parts = []
        if result.get('rejection_patterns'):
            context_parts.append("USER CONSISTENTLY REJECTS: " + "; ".join(result['rejection_patterns']))
        if result.get('preference_patterns'):
            context_parts.append("USER CONSISTENTLY LIKES: " + "; ".join(result['preference_patterns']))
        if result.get('scoring_hints'):
            context_parts.append("SCORING GUIDANCE: " + result['scoring_hints'])

        return " | ".join(context_parts)

    except Exception as e:
        print(f"Error analyzing behavior: {e}")
        if rejected:
            reasons = list(set(j.rejection_reason for j in rejected[:20] if j.rejection_reason))
            return "USER REJECTION REASONS: " + "; ".join(reasons)
        return ""


def get_rejection_context(db):
    """Quick context from stored patterns for scoring (no API call)."""
    patterns = db.query(RejectionPattern).filter(RejectionPattern.active == True).all()
    if patterns:
        # Cap at 1500 chars to avoid bloating system prompts
        text = "KNOWN REJECTION PATTERNS: " + "; ".join(p.pattern for p in patterns)
        return text[:1500] if len(text) > 1500 else text
    return ""
