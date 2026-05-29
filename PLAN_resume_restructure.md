# Resume System Restructure Plan

## Problem
Resume data is stored as a single `resume_text` blob in the `Profile` table. Every generation runs a fragile regex parser (`_parse_resume_text`) to un-serialize it, which causes:
- Words running together (spacing lost at line joins)
- Section headers misdetected (QUALIFICATIONS → name)
- Skills categories merging (compound names like "AI & Machine Learning" not matching)
- AI chat tool (`update_resume`) must rewrite the entire blob to change one bullet
- Constant bugs requiring regex fixes that break other things

## Solution
Structured database tables. One-time migration. Generator reads DB objects directly. No more parsing.

---

## New Database Models

### ResumeProfile (replaces resume_text on Profile)
```python
class ResumeProfile(Base):
    __tablename__ = 'resume_profile'
    id = Column(Integer, primary_key=True, default=1)
    full_name = Column(String(255), default='Michael Sounhein')
    email = Column(String(255), default='')
    phone = Column(String(50), default='')
    location = Column(String(255), default='Appleton, WI')
    linkedin_url = Column(String(500), default='')
    summary = Column(Text, default='')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### ResumeExperience
```python
class ResumeExperience(Base):
    __tablename__ = 'resume_experience'
    id = Column(Integer, primary_key=True, autoincrement=True)
    company = Column(String(255), nullable=False)
    title = Column(String(255), nullable=False)
    location = Column(String(255), default='')
    start_date = Column(String(50), default='')   # "2019" or "January 2019"
    end_date = Column(String(50), default='')     # "December 2024" or "Present"
    bullets = Column(Text, default='[]')           # JSON array of strings
    sort_order = Column(Integer, default=0)        # display order
    created_at = Column(DateTime, default=datetime.utcnow)
```

### ResumeEducation
```python
class ResumeEducation(Base):
    __tablename__ = 'resume_education'
    id = Column(Integer, primary_key=True, autoincrement=True)
    institution = Column(String(255), nullable=False)
    degree = Column(String(255), default='')
    field_of_study = Column(String(255), default='')
    gpa = Column(String(20), default='')
    dates = Column(String(100), default='')
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
```

### ResumeSkillCategory
```python
class ResumeSkillCategory(Base):
    __tablename__ = 'resume_skill_categories'
    id = Column(Integer, primary_key=True, autoincrement=True)
    category_name = Column(String(255), nullable=False)
    skills = Column(Text, default='')   # comma-separated skill names
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
```

---

## Migration Script

`scripts/migrate_resume_to_structured.py` — one-time run:

1. Read `Profile.resume_text` (the current blob)
2. Parse with the existing `_parse_resume_text()` regex (one last time)
3. Insert into new tables:
   - ResumeProfile: name, contact info, summary
   - ResumeExperience: each job with its bullets (JSON array)
   - ResumeEducation: each education entry
   - ResumeSkillCategory: each skill category with its skills
4. Print summary of what was migrated
5. **Do NOT delete** the old `resume_text` — keep as backup

---

## API Changes

### New endpoints (CRUD on structured resume):

```
GET  /api/resume/profile          → ResumeProfile fields
PUT  /api/resume/profile          → update name, summary, contact

GET  /api/resume/experience       → list of ResumeExperience
POST /api/resume/experience       → add experience entry
PUT  /api/resume/experience/:id   → update experience entry
DELETE /api/resume/experience/:id → delete experience entry
PUT  /api/resume/experience/reorder  → reorder experience entries

GET  /api/resume/education        → list of ResumeEducation
POST /api/resume/education        → add education entry
PUT  /api/resume/education/:id    → update education entry
DELETE /api/resume/education/:id  → delete education entry

GET  /api/resume/skills           → list of ResumeSkillCategory
POST /api/resume/skills           → add skill category
PUT  /api/resume/skills/:id       → update skill category
DELETE /api/resume/skills/:id     → delete skill category
PUT  /api/resume/skills/reorder   → reorder skill categories
```

### Modified endpoints:

```
GET /api/profile                  → still works, resume_text kept for backup
```

### Resume generation:
`POST /api/jobs/:id/resumes/generate` — no longer needs summary_override etc.
reads structured data directly from new tables.

---

## Generator Rewrite

`resume_generator.py` changes:

**Delete:**
- `_parse_resume_text()` — no more text parsing
- `_classify_skills_regex()` — skills are already categorized in DB
- `_classify_skills_with_llm()` — same reason

**Rewrite:**
- `_build_html()` → reads ResumeProfile, ResumeExperience[], ResumeEducation[], ResumeSkillCategory[] directly
- `generate_resume()` → queries new tables instead of receiving a text blob
- `generate_docx()` → same, reads structured data

**Contact string:** built from ResumeProfile fields (name, email, phone, location, linkedin)

---

## Chat Tools Update

Current `update_resume` tool: replaces entire text blob.

New approach — add finer-grained tools:
- `update_resume_summary` — update just the summary text
- `update_resume_bullet` — add/edit/remove a bullet from an experience entry
- `update_resume_skills` — update a skill category
- Keep `update_resume` as a legacy fallback (generates text blob, runs migration on it)

Actually, simpler: keep the existing `add_resume_bullet`, `add_resume_skills`, `update_resume` tools but have them operate on the structured tables. The AI doesn't need to know about the underlying schema — it just says "add bullet" or "update summary."

**Specifically:**
- `add_resume_bullet` → inserts into ResumeExperience (find by company, append to bullets JSON)
- `add_resume_skills` → inserts into ResumeSkillCategory (find by category, append skills)
- `update_resume` → update summary on ResumeProfile (change from "replace all text" to "update summary field")
- New: `remove_resume_bullet` → remove a bullet from an experience entry

---

## Frontend Changes

Replace the single textarea editor in Profile page with:

1. **Contact & Summary section** — form fields for name, email, phone, location, linkedin, summary textarea
2. **Experience section** — list of cards, each with: company, title, location, dates, bullet list (add/remove/edit bullets)
3. **Education section** — list of cards, each with: institution, degree, field, gpa, dates
4. **Skills section** — list of category cards, each with: category name + skills textarea

All with inline editing and save-on-change. Much more maintainable than a text blob.

---

## Implementation Order

1. **Add new models** to `models.py` (ResumeProfile, ResumeExperience, ResumeEducation, ResumeSkillCategory)
2. **Write migration script** that parses existing resume_text and populates new tables
3. **Run migration** and verify data
4. **Add new API routes** in `app.py` for structured resume CRUD
5. **Rewrite `resume_generator.py`** to read from structured tables
6. **Update chat_tools.py** — modify tool implementations to work with structured tables
7. **Rebuild frontend** — Profile page form with structured editing
8. **Test generation** — generate a resume, verify PDF/DOCX output matches or improves on current
9. **Keep old `resume_text` column** as backup, but no longer read from it

---

## Open Questions

1. **Should `update_resume` (the catch-all AI tool) stay or be replaced?** It currently replaces the entire text blob. Options:
   - Replace with `update_resume_summary` (just the summary field)
   - Keep it but have it only update the summary (since bullets/skills now have dedicated tools)
   - **Recommended:** Replace with `update_resume_summary` and keep `add_resume_bullet`/`remove_resume_bullet`/`add_resume_skills` for fine-grained edits

2. **Contact info** — currently parsed from the text blob. Should we keep it on the Profile model or move to ResumeProfile?
   - **Recommended:** Move to ResumeProfile. Profile keeps job-search preferences (location, distance, preferred_titles, dealbreakers).

3. **Should we keep the text blob on Profile?**
   - **Recommended:** Keep `resume_text` column but stop reading from it. It serves as backup and audit trail. Can be removed later.

4. **Experience ordering** — the current `experience_order` param on resume generation reorders entries. With structured data, we just use `sort_order` on the model. The AI can call a reorder endpoint if needed.
