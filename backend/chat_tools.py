"""Tools the AI chat agent can call to modify the database directly."""

import os
from config import Config
from llm_client import call_llm

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "generate_tailored_resume",
            "description": "Generate a tailored resume for the current job. NEVER modifies the master resume — works on a copy. Use bullet_overrides to select which bullets to include per experience. Produces PDF and DOCX in a zip file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {
                        "type": "string",
                        "description": "Custom professional summary for this job"
                    },
                    "experience_order": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Company names in desired display order (most relevant first)"
                    },
                    "skills_emphasis": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Skills to highlight/emphasize for this role"
                    },
                    "bullet_overrides": {
                        "type": "object",
                        "description": "Dict mapping experience ID (int) -> list of bullet indices (int) to INCLUDE. Example: {1: [0, 2, 5]} keeps only bullets 0, 2, 5 from experience 1. If omitted for an experience, all bullets are kept."
                    },
                    "notes": {
                        "type": "string",
                        "description": "Notes about this tailored version"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_research_packet",
            "description": "Generate a research packet for the current job. Creates a template with job details and saves it. The agent can then fill in research details later.",
            "parameters": {
                "type": "object",
                "properties": {
                    "force": {
                        "type": "boolean",
                        "description": "Regenerate even if a packet already exists"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "save_research_packet",
            "description": "Save a completed research packet for the current job. Use after doing web research to fill in the packet sections.",
            "parameters": {
                "type": "object",
                "properties": {
                    "company_overview": {
                        "type": "string",
                        "description": "Company background, size, industry, culture, recent news"
                    },
                    "role_analysis": {
                        "type": "string",
                        "description": "Key technologies, responsibilities, what makes this role interesting"
                    },
                    "fit_analysis": {
                        "type": "string",
                        "description": "Michael's direct matches, partial matches, and gaps for this role"
                    },
                    "interview_prep": {
                        "type": "string",
                        "description": "Likely interview questions with suggested answers"
                    },
                    "questions_to_ask": {
                        "type": "string",
                        "description": "Strategic questions for the interviewer"
                    },
                    "risk_assessment": {
                        "type": "string",
                        "description": "Risk factors and concerns about this role"
                    },
                    "bottom_line": {
                        "type": "string",
                        "description": "Summary recommendation"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_resume_skills",
            "description": "Add skills to the resume. Use when you identify skills the user has but forgot to list.",
            "parameters": {
                "type": "object",
                "properties": {
                    "skills": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Skills to add (e.g. ['Microsoft Intune', 'Okta SSO'])"
                    },
                    "category": {
                        "type": "string",
                        "description": "Skill category (e.g. 'Endpoint Management', 'Scripting & Automation'). Defaults to 'Other'."
                    }
                },
                "required": ["skills"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "remove_resume_bullet",
            "description": "Remove a bullet point from work experience. Use when the user wants to delete a specific bullet.",
            "parameters": {
                "type": "object",
                "properties": {
                    "company": {
                        "type": "string",
                        "description": "Company name (partial match is fine)"
                    },
                    "text_contains": {
                        "type": "string",
                        "description": "Text that appears in the bullet to remove (partial match, case-insensitive)"
                    }
                },
                "required": ["company", "text_contains"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_resume_summary",
            "description": "Replace the professional summary on the resume.",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {
                        "type": "string",
                        "description": "The new professional summary text"
                    }
                },
                "required": ["summary"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_resume_bullet",
            "description": "Add a bullet point to work experience. Use when you want to add a specific achievement or responsibility.",
            "parameters": {
                "type": "object",
                "properties": {
                    "section": {
                        "type": "string",
                        "enum": ["experience", "summary"],
                        "description": "Which section to add to"
                    },
                    "company": {
                        "type": "string",
                        "description": "Company name if adding to experience"
                    },
                    "text": {
                        "type": "string",
                        "description": "The bullet point text"
                    }
                },
                "required": ["section", "text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_search_term",
            "description": "Add a new search term for job scraping. Use when you discover a job title or keyword that matches the user's skills.",
            "parameters": {
                "type": "object",
                "properties": {
                    "term": {
                        "type": "string",
                        "description": "The search term to add (e.g., 'Client Systems Administrator')"
                    }
                },
                "required": ["term"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "block_company",
            "description": "Add a company to the blocklist. Use when the user says they don't want to see jobs from a specific company.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Company name to block"
                    },
                    "reason": {
                        "type": "string",
                        "description": "Why it's blocked"
                    }
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_rejection_pattern",
            "description": "Add a rejection pattern. Use when the user consistently rejects a type of job and you want to filter future matches.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Description of the pattern (e.g., 'contract-only roles', 'jobs requiring relocation')"
                    }
                },
                "required": ["pattern"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_job_status",
            "description": "Change the status of the current job being discussed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["new", "will_apply", "applied", "interview", "offer", "rejected"],
                        "description": "The new status"
                    },
                    "note": {
                        "type": "string",
                        "description": "Optional note (apply note or rejection reason)"
                    }
                },
                "required": ["status"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_profile",
            "description": "Update job search preferences like location, distance, or focus areas.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "Search location (e.g., 'Appleton, WI')"
                    },
                    "max_distance": {
                        "type": "integer",
                        "description": "Max distance in miles"
                    },
                    "preferences": {
                        "type": "object",
                        "description": "Key-value pairs of preferences (e.g., {\"focus\": \"endpoint management\"})"
                    }
                }
            }
        }
    }
]


def execute_tool(db, tool_name, arguments, job_id=None):
    """Execute a tool call and return the result."""
    from models import Job, SearchTerm, Profile, RejectionPattern, BlockedCompany

    try:
        if tool_name == "generate_tailored_resume":
            if not job_id:
                return {"success": False, "message": "No job context."}
            from models import TailoredResume
            from resume_generator import generate_resume
            import json as _json

            output_dir = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                'data', 'resumes', str(job_id)
            )

            # Convert bullet_overrides keys to ints (JSON sends string keys)
            bullet_overrides = arguments.get('bullet_overrides')
            if bullet_overrides:
                bullet_overrides = {int(k): v for k, v in bullet_overrides.items()}

            result = generate_resume(
                job_id=job_id,
                output_dir=output_dir,
                summary_override=arguments.get('summary', ''),
                experience_order=arguments.get('experience_order'),
                skills_emphasis=arguments.get('skills_emphasis'),
                bullet_overrides=bullet_overrides,
            )

            tailored = TailoredResume(
                job_id=job_id,
                resume_html=result['html'],
                resume_pdf_path=result['pdf_path'],
                resume_docx_path=result['docx_path'],
                notes=arguments.get('notes', ''),
            )
            db.add(tailored)
            db.commit()

            return {
                "success": True,
                "message": f"Resume generated! PDF and DOCX saved. Download: /api/resumes/{tailored.id}/download",
                "resume_id": tailored.id,
                "download_url": f"/api/resumes/{tailored.id}/download",
            }

        elif tool_name == "generate_research_packet":
            if not job_id:
                return {"success": False, "message": "No job context."}
            from models import Job, ResearchPacket, Profile
            import requests as http_requests

            job = db.query(Job).filter(Job.id == job_id).first()
            if not job:
                return {"success": False, "message": "Job not found."}

            # Check if packet already exists
            existing = db.query(ResearchPacket).filter(ResearchPacket.job_id == job_id).first()
            if existing and not arguments.get('force', False):
                return {"success": True, "message": f"Research packet already exists for {job.company}. Use force=true to regenerate."}

            # Step 1: Web research via Brave Search
            BRAVE_API_KEY = 'BSAZD8sqsawgEDkrLGdnsbnhyzMaz3c'
            search_results = []
            queries = [
                f'{job.company} company overview employees revenue industry',
                f'{job.company} Glassdoor reviews culture rating',
                f'{job.title} salary range {job.location or "US"} compensation',
                f'{job.company} layoffs OR lawsuits OR controversy OR scandal',
                f'{job.company} benefits 401k healthcare remote work policy',
                f'{job.company} recent news 2025 2026',
                f'{job.company} interview questions {job.title}',
                f'{job.company} LinkedIn employees growth',
            ]
            for q in queries:
                try:
                    resp = http_requests.get(
                        'https://api.search.brave.com/res/v1/web/search',
                        headers={'X-Subscription-Token': BRAVE_API_KEY, 'Accept': 'application/json'},
                        params={'q': q, 'count': 3},
                        timeout=10,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        for r in data.get('web', {}).get('results', []):
                            search_results.append(f"Title: {r.get('title')}\nURL: {r.get('url')}\nSnippet: {r.get('description', '')[:500]}")
                except Exception:
                    pass

            # Step 2: Get Michael's resume context
            from scorer import get_resume_text
            resume_ctx = get_resume_text(db)
            if not resume_ctx:
                profile = db.query(Profile).first()
                resume_ctx = profile.resume_text if profile else ''

            # Step 3: Call LLM to synthesize research packet
            system_prompt = (
                "You are a job research analyst. Given search results about a company and a job description, "
                "write a comprehensive research packet. Be specific with real data from the search results. "
                "If search results are thin, use your knowledge. Format as markdown with these sections:\n"
                "## Company Overview\n## Role Breakdown\n## Michael's Fit Analysis\n"
                "## Likely Interview Questions & Suggested Answers\n## Questions to Ask Them\n"
                "## Risk Assessment\n## Bottom Line"
            )
            user_prompt = (
                f"Company: {job.company}\nRole: {job.title}\nLocation: {job.location}\n"
                f"Match Score: {job.match_score}/100\n"
                f"Job Description: {(job.description or '')[:2000]}\n\n"
                f"Michael's Resume: {resume_ctx}\n\n"
                f"Search Results:\n" + '\n---\n'.join(search_results[:15]) + '\n\n'
                f"Write the full research packet now."
            )

            last_err = None
            for attempt in range(3):
                try:
                    llm_result = call_llm(
                        [
                            {'role': 'system', 'content': system_prompt},
                            {'role': 'user', 'content': user_prompt},
                        ],
                        temperature=0.3,
                        max_tokens=8192,
                        timeout=120,
                    )
                    content = llm_result['content']
                    break
                except Exception as e:
                    last_err = e
                    print(f"[packet-llm] Attempt {attempt+1}/3 failed: {e}")
                    if attempt < 2:
                        import time; time.sleep(5)
            else:
                return {"success": False, "message": f"LLM synthesis failed after 3 attempts: {str(last_err)}"}

            # Step 4: Save to database
            if existing:
                existing.content = content
            else:
                db.add(ResearchPacket(job_id=job_id, content=content))
            db.commit()

            return {
                "success": True,
                "message": f"Research packet generated for {job.company} with {len(search_results)} search results. Check the Research Packet tab.",
            }

        elif tool_name == "save_research_packet":
            if not job_id:
                return {"success": False, "message": "No job context."}
            from models import Job, ResearchPacket
            import json as _json

            job = db.query(Job).filter(Job.id == job_id).first()
            if not job:
                return {"success": False, "message": "Job not found."}

            # Build the full packet content
            sections = []
            for key, label in [
                ('company_overview', 'Company Overview'),
                ('role_analysis', 'Role Breakdown'),
                ('fit_analysis', "Michael's Fit Analysis"),
                ('interview_prep', 'Interview Prep'),
                ('questions_to_ask', 'Questions to Ask'),
                ('risk_assessment', 'Risk Assessment'),
                ('bottom_line', 'Bottom Line'),
            ]:
                val = arguments.get(key, '')
                if val:
                    sections.append(f'## {label}\n\n{val}')

            content = f'# Research Packet — {job.company}\n**Role:** {job.title}\n**Score:** {job.match_score}/100\n\n---\n\n' + '\n\n---\n\n'.join(sections)

            # Save to database
            existing = db.query(ResearchPacket).filter(ResearchPacket.job_id == job_id).first()
            if existing:
                existing.content = content
            else:
                db.add(ResearchPacket(job_id=job_id, content=content))
            db.commit()

            filled = [k for k, v in arguments.items() if v]
            return {
                "success": True,
                "message": f"Research packet saved for {job.company}. Filled sections: {', '.join(filled)}. Check the Research Packet tab.",
            }

        elif tool_name == "add_resume_skills":
            from models import ResumeSkillCategory
            skills = arguments.get("skills", [])
            category = arguments.get("category", "Other")
            # Find existing category or create one
            cat = db.query(ResumeSkillCategory).filter(
                ResumeSkillCategory.category_name == category
            ).first()
            if cat:
                existing_skills = [s.strip() for s in cat.skills.split(',') if s.strip()]
                new_skills = [s for s in skills if s not in existing_skills]
                if not new_skills:
                    return {"success": True, "message": "Skills already on resume."}
                cat.skills = cat.skills.rstrip(', ').strip() + ', ' + ', '.join(new_skills)
            else:
                max_order = db.query(ResumeSkillCategory).count()
                cat = ResumeSkillCategory(
                    category_name=category,
                    skills=', '.join(skills),
                    sort_order=max_order,
                )
                db.add(cat)
            db.commit()
            return {"success": True, "message": f"Added {len(skills)} skills to '{category}'."}

        elif tool_name == "add_resume_bullet":
            from models import ResumeExperience, ResumeProfile
            import json as _json
            section = arguments.get("section", "experience")
            company = arguments.get("company", "")
            text = arguments.get("text", "")
            if section == "summary":
                rp = db.query(ResumeProfile).first()
                if rp:
                    rp.summary = (rp.summary + ' ' + text).strip() if rp.summary else text
                    db.commit()
                    return {"success": True, "message": "Added to summary."}
                return {"success": False, "message": "No resume profile found."}
            elif section == "experience" and company:
                # Find experience entry by company name (partial match)
                exp = db.query(ResumeExperience).filter(
                    ResumeExperience.company.ilike(f'%{company}%')
                ).first()
                if exp:
                    bullets = _json.loads(exp.bullets) if exp.bullets else []
                    bullets.append(text)
                    exp.bullets = _json.dumps(bullets)
                    db.commit()
                    return {"success": True, "message": f"Added bullet to {exp.company}."}
                else:
                    return {"success": False, "message": f"No experience found matching '{company}'."}
            return {"success": False, "message": "Provide company name for experience bullets."}

        elif tool_name == "remove_resume_bullet":
            from models import ResumeExperience, ResumeProfile
            import json as _json
            company = arguments.get("company", "")
            text_contains = arguments.get("text_contains", "")
            if not company or not text_contains:
                return {"success": False, "message": "Provide company and text_contains to find the bullet."}
            exp = db.query(ResumeExperience).filter(
                ResumeExperience.company.ilike(f'%{company}%')
            ).first()
            if not exp:
                return {"success": False, "message": f"No experience found matching '{company}'."}
            bullets = _json.loads(exp.bullets) if exp.bullets else []
            original_count = len(bullets)
            bullets = [b for b in bullets if text_contains.lower() not in b.lower()]
            if len(bullets) == original_count:
                return {"success": False, "message": "No matching bullet found."}
            exp.bullets = _json.dumps(bullets)
            db.commit()
            return {"success": True, "message": f"Removed {original_count - len(bullets)} bullet(s) from {exp.company}."}

        elif tool_name == "update_resume_summary":
            from models import ResumeProfile
            summary = arguments.get("summary", "")
            rp = db.query(ResumeProfile).first()
            if not rp:
                return {"success": False, "message": "No resume profile found."}
            rp.summary = summary
            db.commit()
            return {"success": True, "message": "Resume summary updated."}

        elif tool_name == "update_resume":
            # Legacy: now just updates the summary
            from models import ResumeProfile
            rp = db.query(ResumeProfile).first()
            if not rp:
                return {"success": False, "message": "No resume profile found."}
            if "resume_text" in arguments:
                rp.summary = arguments["resume_text"]
            elif "summary" in arguments:
                rp.summary = arguments["summary"]
            db.commit()
            return {"success": True, "message": "Resume updated."}

        elif tool_name == "add_search_term":
            term = arguments["term"]
            existing = db.query(SearchTerm).filter(SearchTerm.term == term).first()
            if existing:
                if not existing.active:
                    existing.active = True
                    db.commit()
                    return {"success": True, "message": f"Re-enabled search term '{term}'."}
                return {"success": True, "message": f"Search term '{term}' already exists."}
            db.add(SearchTerm(term=term, source='ai', active=True))
            db.commit()
            return {"success": True, "message": f"Added search term '{term}'."}

        elif tool_name == "block_company":
            name = arguments["name"]
            reason = arguments.get("reason", "")
            existing = db.query(BlockedCompany).filter(BlockedCompany.name == name).first()
            if existing:
                return {"success": True, "message": f"'{name}' is already blocked."}
            db.add(BlockedCompany(name=name, reason=reason))
            db.commit()
            return {"success": True, "message": f"Blocked '{name}'."}

        elif tool_name == "add_rejection_pattern":
            pattern = arguments["pattern"]
            existing = db.query(RejectionPattern).filter(RejectionPattern.pattern == pattern).first()
            if existing:
                return {"success": True, "message": "Pattern already exists."}
            db.add(RejectionPattern(pattern=pattern, source='ai', active=True))
            db.commit()
            return {"success": True, "message": f"Added rejection pattern: '{pattern}'."}

        elif tool_name == "update_job_status":
            if not job_id:
                return {"success": False, "message": "No job context."}
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job:
                return {"success": False, "message": "Job not found."}
            new_status = arguments["status"]
            note = arguments.get("note", "")
            if new_status == "rejected":
                job.rejection_reason = note
            elif new_status == "will_apply":
                job.apply_note = note
            if new_status == "applied":
                from datetime import datetime
                job.applied_date = datetime.utcnow()
            job.status = new_status
            db.commit()
            return {"success": True, "message": f"Job status updated to '{new_status}'."}

        elif tool_name == "update_profile":
            profile = db.query(Profile).first()
            if not profile:
                return {"success": False, "message": "No profile found."}
            if "location" in arguments:
                profile.location = arguments["location"]
            if "max_distance" in arguments:
                profile.max_distance = arguments["max_distance"]
            if "preferences" in arguments:
                import json
                current = json.loads(profile.preferences or '{}')
                current.update(arguments["preferences"])
                profile.preferences = json.dumps(current)
            db.commit()
            return {"success": True, "message": "Profile updated."}

        else:
            return {"success": False, "message": f"Unknown tool: {tool_name}"}

    except Exception as e:
        db.rollback()
        return {"success": False, "message": str(e)}
