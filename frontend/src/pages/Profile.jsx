import { useEffect, useState, useCallback } from 'react';
import api from '../api/client';
import { Plus, X, Check } from 'lucide-react';

const inputStyle = {
  width: '100%', height: 32, background: 'var(--surface)', border: '1px solid var(--border)',
  borderRadius: 6, padding: '0 10px', fontSize: 13, color: 'var(--text-primary)', outline: 'none',
};
const textareaStyle = {
  ...inputStyle, height: 'auto', padding: 10, resize: 'vertical',
  fontFamily: '"JetBrains Mono", "SF Mono", monospace', fontSize: 12,
};
const labelStyle = {
  display: 'block', fontSize: 11, fontWeight: 500, color: 'var(--text-secondary)',
  textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 6,
};
const cardStyle = {
  background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, padding: 16, marginBottom: 12,
};
const btnSmall = {
  height: 28, padding: '0 12px', borderRadius: 6, fontSize: 12, fontWeight: 500,
  background: 'var(--surface)', color: 'var(--text-primary)', border: '1px solid var(--border)',
  cursor: 'pointer',
  display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 4,
};
const btnDanger = { ...btnSmall, color: '#e74c3c', borderColor: '#e74c3c', padding: '0 8px' };
const btnAccent = { ...btnSmall, background: 'var(--accent)', color: '#fff', border: 'none' };

function Section({ title, children }) {
  return (
    <div style={{ marginBottom: 24 }}>
      <h2 style={{ fontSize: 14, fontWeight: 600, letterSpacing: '0.04em', textTransform: 'uppercase', marginBottom: 12, color: 'var(--text-secondary)' }}>{title}</h2>
      {children}
    </div>
  );
}

function ExperienceCard({ exp, onSave, onDelete }) {
  const [editing, setEditing] = useState(false);
  const [data, setData] = useState({ ...exp, bullets: exp.bullets || [] });
  const [newBullet, setNewBullet] = useState('');

  const addBullet = () => {
    if (!newBullet.trim()) return;
    setData({ ...data, bullets: [...data.bullets, newBullet.trim()] });
    setNewBullet('');
  };

  const removeBullet = (i) => {
    setData({ ...data, bullets: data.bullets.filter((_, idx) => idx !== i) });
  };

  const save = () => { onSave(data); setEditing(false); };

  return (
    <div style={cardStyle} className="profile-card profile-card-experience">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <div>
          <strong style={{ fontSize: 13, color: 'var(--accent)' }}>{exp.title}</strong>
          <span style={{ color: 'var(--text-secondary)', fontSize: 13 }}> @ {exp.company}</span>
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          <button onClick={() => setEditing(!editing)} style={btnSmall}>{editing ? 'Cancel' : 'Edit'}</button>
          {editing && <button onClick={save} style={btnAccent}>Save</button>}
          <button onClick={() => onDelete(exp.id)} style={btnDanger}><X size={14} /></button>
        </div>
      </div>
      {!editing ? (
        <div>
          {exp.bullets?.map((b, i) => (
            <div key={i} style={{ fontSize: 12, color: 'var(--text-secondary)', padding: '2px 0 2px 12px', borderLeft: '2px solid var(--border)' }}>• {b}</div>
          ))}
          <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 4 }}>{exp.start_date} — {exp.end_date} | {exp.location}</div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
            <div>
              <label style={labelStyle}>Title</label>
              <input value={data.title} onChange={e => setData({ ...data, title: e.target.value })} style={inputStyle} />
            </div>
            <div>
              <label style={labelStyle}>Company</label>
              <input value={data.company} onChange={e => setData({ ...data, company: e.target.value })} style={inputStyle} />
            </div>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
            <div>
              <label style={labelStyle}>Location</label>
              <input value={data.location || ''} onChange={e => setData({ ...data, location: e.target.value })} style={inputStyle} />
            </div>
            <div>
              <label style={labelStyle}>Start Date</label>
              <input value={data.start_date || ''} onChange={e => setData({ ...data, start_date: e.target.value })} style={inputStyle} />
            </div>
            <div>
              <label style={labelStyle}>End Date</label>
              <input value={data.end_date || ''} onChange={e => setData({ ...data, end_date: e.target.value })} style={inputStyle} />
            </div>
          </div>
          <div>
            <label style={labelStyle}>Bullets</label>
            {data.bullets.map((b, i) => (
              <div key={i} style={{ display: 'flex', gap: 6, marginBottom: 4 }}>
                <input value={b} onChange={e => {
                  const newBullets = [...data.bullets];
                  newBullets[i] = e.target.value;
                  setData({ ...data, bullets: newBullets });
                }} style={{ ...inputStyle, flex: 1 }} />
                <button onClick={() => removeBullet(i)} style={btnDanger}><X size={14} /></button>
              </div>
            ))}
            <div style={{ display: 'flex', gap: 6 }}>
              <input value={newBullet} onChange={e => setNewBullet(e.target.value)} onKeyDown={e => e.key === 'Enter' && addBullet()} placeholder="Add bullet..." style={{ ...inputStyle, flex: 1 }} />
              <button onClick={addBullet} style={btnSmall}><Plus size={13} /> Add</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function EducationCard({ edu, onSave, onDelete }) {
  const [editing, setEditing] = useState(false);
  const [data, setData] = useState(edu);

  const save = () => { onSave(data); setEditing(false); };

  return (
    <div style={cardStyle} className="profile-card profile-card-education">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <div>
          <strong style={{ fontSize: 13, color: 'var(--accent)' }}>{edu.degree}</strong>
          {edu.field_of_study && <span style={{ color: 'var(--text-secondary)', fontSize: 13 }}> — {edu.field_of_study}</span>}
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          <button onClick={() => setEditing(!editing)} style={btnSmall}>{editing ? 'Cancel' : 'Edit'}</button>
          {editing && <button onClick={save} style={btnAccent}>Save</button>}
          <button onClick={() => onDelete(edu.id)} style={btnDanger}><X size={14} /></button>
        </div>
      </div>
      {!editing ? (
        <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
          {edu.institution} {edu.gpa && `(GPA: ${edu.gpa})`} {edu.dates && `| ${edu.dates}`}
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginTop: 8 }}>
          <div>
            <label style={labelStyle}>Institution</label>
            <input value={data.institution} onChange={e => setData({ ...data, institution: e.target.value })} style={inputStyle} />
          </div>
          <div>
            <label style={labelStyle}>Degree</label>
            <input value={data.degree} onChange={e => setData({ ...data, degree: e.target.value })} style={inputStyle} />
          </div>
          <div>
            <label style={labelStyle}>GPA</label>
            <input value={data.gpa || ''} onChange={e => setData({ ...data, gpa: e.target.value })} style={inputStyle} />
          </div>
          <div>
            <label style={labelStyle}>Dates</label>
            <input value={data.dates || ''} onChange={e => setData({ ...data, dates: e.target.value })} style={inputStyle} />
          </div>
        </div>
      )}
    </div>
  );
}

function SkillCategoryCard({ cat, onSave, onDelete }) {
  const [editing, setEditing] = useState(false);
  const [data, setData] = useState(cat);

  const save = () => { onSave(data); setEditing(false); };

  return (
    <div style={cardStyle} className="profile-card profile-card-skill">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
        <strong style={{ fontSize: 13, color: 'var(--accent)' }}>{cat.category_name}</strong>
        <div style={{ display: 'flex', gap: 6 }}>
          <button onClick={() => setEditing(!editing)} style={btnSmall}>{editing ? 'Cancel' : 'Edit'}</button>
          {editing && <button onClick={save} style={btnAccent}>Save</button>}
          <button onClick={() => onDelete(cat.id)} style={btnDanger}><X size={14} /></button>
        </div>
      </div>
      {!editing ? (
        <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.5 }}>{cat.skills}</div>
      ) : (
        <div style={{ marginTop: 8 }}>
          <label style={labelStyle}>Category Name</label>
          <input value={data.category_name} onChange={e => setData({ ...data, category_name: e.target.value })} style={inputStyle} />
          <label style={{ ...labelStyle, marginTop: 8 }}>Skills (comma-separated)</label>
          <textarea value={data.skills} onChange={e => setData({ ...data, skills: e.target.value })} rows={3} style={textareaStyle} />
        </div>
      )}
    </div>
  );
}

export default function Profile() {
  const [resume, setResume] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  // Profile search preferences
  const [profile, setProfile] = useState(null);

  // Tabs and settings data
  const [activeTab, setActiveTab] = useState('resume'); // 'resume' or 'settings'
  const [terms, setTerms] = useState([]);
  const [blocked, setBlocked] = useState([]);
  const [newTerm, setNewTerm] = useState('');
  const [newBlock, setNewBlock] = useState('');

  const load = useCallback(async () => {
    try {
      const [resumeData, profileData, termsData, blockedData] = await Promise.all([
        api.getResumeAll(),
        api.getProfile(),
        api.getSearchTerms(),
        api.getBlockedCompanies(),
      ]);
      setResume(resumeData);
      setProfile(profileData);
      setTerms(termsData);
      setBlocked(blockedData);
    } catch (err) {
      console.error('Failed to load profile:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const saveProfile = async () => {
    setSaving(true); setSaved(false);
    await api.updateProfile(profile);
    await api.updateResumeProfile(resume.profile);
    setSaving(false); setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const saveExperience = async (exp) => {
    await api.updateResumeExperience(exp.id, exp);
    const updated = { ...resume, experience: resume.experience.map(e => e.id === exp.id ? exp : e) };
    setResume(updated);
  };

  const deleteExperience = async (id) => {
    await api.deleteResumeExperience(id);
    setResume({ ...resume, experience: resume.experience.filter(e => e.id !== id) });
  };

  const addExperience = async () => {
    await api.createResumeExperience({
      company: 'New Company', title: 'Job Title', location: '',
      start_date: '', end_date: '', bullets: [],
    });
    await load();
  };

  const saveEducation = async (edu) => {
    await api.updateResumeEducation(edu.id, edu);
    setResume({ ...resume, education: resume.education.map(e => e.id === edu.id ? edu : e) });
  };

  const deleteEducation = async (id) => {
    await api.deleteResumeEducation(id);
    setResume({ ...resume, education: resume.education.filter(e => e.id !== id) });
  };

  const addEducation = async () => {
    await api.createResumeEducation({ institution: 'Institution', degree: 'Degree', gpa: '', dates: '' });
    await load();
  };

  const saveSkillCategory = async (cat) => {
    await api.updateResumeSkill(cat.id, cat);
    setResume({ ...resume, skills: resume.skills.map(s => s.id === cat.id ? cat : s) });
  };

  const deleteSkillCategory = async (id) => {
    await api.deleteResumeSkill(id);
    setResume({ ...resume, skills: resume.skills.filter(s => s.id !== id) });
  };

  const addSkillCategory = async () => {
    await api.createResumeSkill({ category_name: 'New Category', skills: '' });
    await load();
  };

  const updateSummary = (text) => {
    setResume({ ...resume, profile: { ...resume.profile, summary: text } });
  };

  const addTerm = async () => {
    if (!newTerm.trim()) return;
    await api.addSearchTerm(newTerm.trim());
    setNewTerm('');
    const termsData = await api.getSearchTerms();
    setTerms(termsData);
  };

  const toggleTerm = async (id) => {
    await api.toggleSearchTerm(id);
    const termsData = await api.getSearchTerms();
    setTerms(termsData);
  };

  const addBlocked = async () => {
    if (!newBlock.trim()) return;
    await api.addBlockedCompany(newBlock.trim());
    setNewBlock('');
    const blockedData = await api.getBlockedCompanies();
    setBlocked(blockedData);
  };

  const removeBlocked = async (id) => {
    await api.removeBlockedCompany(id);
    const blockedData = await api.getBlockedCompanies();
    setBlocked(blockedData);
  };

  const toggleSource = async (key) => {
    if (!profile) return;
    const val = !profile[key];
    const updated = { ...profile, [key]: val };
    setProfile(updated);
    try {
      await api.updateProfile({ [key]: val });
    } catch (e) {
      console.error("Failed to update scraper source config:", e);
      setProfile(profile);
    }
  };

  const renderSourceToggle = (label, key) => {
    if (!profile) return null;
    const active = profile[key] !== false;
    return (
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        padding: '8px 12px', borderRadius: 6, background: 'var(--bg)', border: '1px solid var(--border)'
      }}>
        <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary)' }}>{label}</span>
        <button onClick={() => toggleSource(key)} style={{
          width: 32, height: 16, borderRadius: 999, border: 'none', cursor: 'pointer',
          background: active ? 'var(--success)' : 'var(--text-disabled)', position: 'relative',
          transition: 'background 150ms ease',
        }}>
          <div style={{
            width: 12, height: 12, borderRadius: 999, background: '#fff',
            position: 'absolute', top: 2,
            left: active ? 18 : 2,
            transition: 'left 150ms ease',
          }} />
        </button>
      </div>
    );
  };

  if (loading) return <div style={{ color: 'var(--text-tertiary)', textAlign: 'center', padding: 48 }}>Loading...</div>;
  if (!resume) return <div style={{ color: 'var(--text-tertiary)', textAlign: 'center', padding: 48 }}>Failed to load profile.</div>;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <h1 style={{ fontSize: 20, fontWeight: 600, letterSpacing: '-0.02em' }}>Profile & Settings</h1>
        <button onClick={saveProfile} disabled={saving} style={{
          height: 32, padding: '0 16px', borderRadius: 6, fontSize: 13, fontWeight: 500,
          background: 'var(--accent)', color: '#fff', border: 'none', cursor: saving ? 'wait' : 'pointer',
          opacity: saving ? 0.7 : 1,
          display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 6,
        }}>
          {saving ? 'Saving...' : saved ? <><Check size={14} /> Saved!</> : 'Save All'}
        </button>
      </div>

      {/* Tabs Switcher */}
      <div style={{
        display: 'flex',
        gap: 16,
        borderBottom: '1px solid var(--border)',
        marginBottom: 24,
      }}>
        <button
          onClick={() => setActiveTab('resume')}
          style={{
            background: 'none',
            border: 'none',
            borderBottom: activeTab === 'resume' ? '2px solid var(--accent)' : '2px solid transparent',
            color: activeTab === 'resume' ? 'var(--text-primary)' : 'var(--text-tertiary)',
            padding: '8px 4px',
            fontSize: 14,
            fontWeight: 500,
            cursor: 'pointer',
            transition: 'all 150ms ease',
          }}
        >
          Resume & Profile
        </button>
        <button
          onClick={() => setActiveTab('settings')}
          style={{
            background: 'none',
            border: 'none',
            borderBottom: activeTab === 'settings' ? '2px solid var(--accent)' : '2px solid transparent',
            color: activeTab === 'settings' ? 'var(--text-primary)' : 'var(--text-tertiary)',
            padding: '8px 4px',
            fontSize: 14,
            fontWeight: 500,
            cursor: 'pointer',
            transition: 'all 150ms ease',
          }}
        >
          Job Search Settings
        </button>
      </div>

      {activeTab === 'resume' ? (
        <>
          {/* Contact Info */}
          <Section title="Contact Info">
            <div style={cardStyle} className="profile-card profile-card-contact">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                <strong style={{ fontSize: 13, color: 'var(--accent)' }}>Contact Details</strong>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div>
                  <label style={labelStyle}>Full Name</label>
                  <input value={resume.profile?.full_name || ''} onChange={e => setResume({ ...resume, profile: { ...resume.profile, full_name: e.target.value } })} style={inputStyle} />
                </div>
                <div>
                  <label style={labelStyle}>Email</label>
                  <input value={resume.profile?.email || ''} onChange={e => setResume({ ...resume, profile: { ...resume.profile, email: e.target.value } })} style={inputStyle} />
                </div>
                <div>
                  <label style={labelStyle}>Phone</label>
                  <input value={resume.profile?.phone || ''} onChange={e => setResume({ ...resume, profile: { ...resume.profile, phone: e.target.value } })} style={inputStyle} />
                </div>
                <div>
                  <label style={labelStyle}>Location</label>
                  <input value={resume.profile?.location || ''} onChange={e => setResume({ ...resume, profile: { ...resume.profile, location: e.target.value } })} style={inputStyle} />
                </div>
                <div>
                  <label style={labelStyle}>LinkedIn URL</label>
                  <input value={resume.profile?.linkedin_url || ''} onChange={e => setResume({ ...resume, profile: { ...resume.profile, linkedin_url: e.target.value } })} style={inputStyle} />
                </div>
                <div>
                  <label style={labelStyle}>GitHub URL</label>
                  <input value={resume.profile?.github_url || ''} onChange={e => setResume({ ...resume, profile: { ...resume.profile, github_url: e.target.value } })} style={inputStyle} />
                </div>
              </div>
            </div>
          </Section>

          {/* Summary */}
          <Section title="Professional Summary">
            <div style={cardStyle} className="profile-card profile-card-summary">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                <strong style={{ fontSize: 13, color: 'var(--accent)' }}>Overview</strong>
              </div>
              <textarea
                value={resume.profile?.summary || ''}
                onChange={e => updateSummary(e.target.value)}
                rows={4}
                style={textareaStyle}
              />
            </div>
          </Section>

          {/* Experience */}
          <Section title={`Experience (${resume.experience.length})`}>
            {resume.experience.map(exp => (
              <ExperienceCard key={exp.id} exp={exp} onSave={saveExperience} onDelete={deleteExperience} />
            ))}
            <button onClick={addExperience} style={{ ...btnSmall, background: 'var(--accent)', color: '#fff', border: 'none' }}><Plus size={13} /> Add Experience</button>
          </Section>

          {/* Skills */}
          <Section title={`Skills (${resume.skills.length} categories)`}>
            {resume.skills.map(cat => (
              <SkillCategoryCard key={cat.id} cat={cat} onSave={saveSkillCategory} onDelete={deleteSkillCategory} />
            ))}
            <button onClick={addSkillCategory} style={{ ...btnSmall, background: 'var(--accent)', color: '#fff', border: 'none' }}><Plus size={13} /> Add Category</button>
          </Section>

          {/* Education */}
          <Section title={`Education (${resume.education.length})`}>
            {resume.education.map(edu => (
              <EducationCard key={edu.id} edu={edu} onSave={saveEducation} onDelete={deleteEducation} />
            ))}
            <button onClick={addEducation} style={{ ...btnSmall, background: 'var(--accent)', color: '#fff', border: 'none' }}><Plus size={13} /> Add Education</button>
          </Section>
        </>
      ) : (
        <>
          {/* Search Preferences */}
          <Section title="Search Preferences">
            <div style={cardStyle} className="profile-card profile-card-preferences">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                <strong style={{ fontSize: 13, color: 'var(--accent)' }}>Job Match Settings</strong>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div>
                  <label style={labelStyle}>Location</label>
                  <input value={profile?.location || ''} onChange={e => setProfile({ ...profile, location: e.target.value })} style={inputStyle} />
                </div>
                <div>
                  <label style={labelStyle}>Max Distance (miles)</label>
                  <input type="number" value={profile?.max_distance || 25} onChange={e => setProfile({ ...profile, max_distance: parseInt(e.target.value) })} style={inputStyle} />
                </div>
              </div>
            </div>
          </Section>

          {/* Scraper Sources */}
          <Section title="Scraper Sources">
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 12, marginBottom: 24 }}>
              {renderSourceToggle("LinkedIn Scraper", "scrape_linkedin")}
              {renderSourceToggle("Indeed Scraper", "scrape_indeed")}
              {renderSourceToggle("Himalayas Remote API", "scrape_himalayas")}
              {renderSourceToggle("Remotive API", "scrape_remotive")}
              {renderSourceToggle("We Work Remotely RSS", "scrape_wwr")}
            </div>
          </Section>

          {/* Search Terms (Skills Scrapes) */}
          <Section title="Search Terms (Skills Scrapes)">
            <div style={cardStyle}>
              <div style={{ marginBottom: 12 }}>
                {terms.map(t => (
                  <div key={t.id} style={{
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                    padding: '6px 8px', borderRadius: 6, background: 'var(--bg)', marginBottom: 4,
                  }}>
                    <span style={{ fontSize: 13, color: t.active ? 'var(--text-primary)' : 'var(--text-disabled)', textDecoration: t.active ? 'none' : 'line-through' }}>
                      {t.term}
                    </span>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{
                        fontSize: 11, fontWeight: 500, padding: '2px 6px', borderRadius: 4,
                        background: t.source === 'ai' ? 'rgba(168,85,247,0.15)' : 'rgba(94,106,210,0.15)',
                        color: t.source === 'ai' ? '#A855F7' : '#5E6AD2',
                      }}>{t.source}</span>
                      <span style={{ fontSize: 11, color: 'var(--text-tertiary)', marginRight: 4 }}>{t.hit_count} hits</span>
                      <button onClick={() => toggleTerm(t.id)} style={{
                        width: 32, height: 16, borderRadius: 999, border: 'none', cursor: 'pointer',
                        background: t.active ? 'var(--success)' : 'var(--text-disabled)', position: 'relative',
                        transition: 'background 150ms ease',
                      }}>
                        <div style={{
                          width: 12, height: 12, borderRadius: 999, background: '#fff',
                          position: 'absolute', top: 2,
                          left: t.active ? 18 : 2,
                          transition: 'left 150ms ease',
                        }} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <input value={newTerm} onChange={e => setNewTerm(e.target.value)} onKeyDown={e => e.key === 'Enter' && addTerm()} placeholder="Add search term..." style={{ ...inputStyle, flex: 1, width: 'auto' }} />
                <button onClick={addTerm} style={{ display: 'inline-flex', alignItems: 'center', gap: 4, height: 32, padding: '0 12px', borderRadius: 6, fontSize: 13, fontWeight: 500, background: 'var(--accent)', color: '#fff', border: 'none', cursor: 'pointer' }}><Plus size={14} /> Add</button>
              </div>
            </div>
          </Section>

          {/* Blocked Companies */}
          <Section title="Blocked Companies">
            <div style={cardStyle} className="profile-card profile-card-blocked">
              <div style={{ marginBottom: 12 }}>
                {blocked.map(c => (
                  <div key={c.id} style={{
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                    padding: '6px 8px', borderRadius: 6, background: 'var(--bg)', marginBottom: 4,
                  }}>
                    <span style={{ fontSize: 13 }}>{c.name}</span>
                    <button onClick={() => removeBlocked(c.id)} style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: 24, height: 24, borderRadius: 4, background: 'transparent', border: 'none', color: 'var(--text-tertiary)', cursor: 'pointer', transition: 'all 150ms ease' }} onMouseEnter={e => e.currentTarget.style.color = 'var(--error)'} onMouseLeave={e => e.currentTarget.style.color = 'var(--text-tertiary)'}><X size={14} /></button>
                  </div>
                ))}
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <input value={newBlock} onChange={e => setNewBlock(e.target.value)} onKeyDown={e => e.key === 'Enter' && addBlocked()} placeholder="Block company..." style={{ ...inputStyle, flex: 1, width: 'auto' }} />
                <button onClick={addBlocked} style={{ display: 'inline-flex', alignItems: 'center', gap: 4, height: 32, padding: '0 12px', borderRadius: 6, fontSize: 13, fontWeight: 500, background: 'var(--error)', color: '#fff', border: 'none', cursor: 'pointer' }}><X size={14} /> Block</button>
              </div>
            </div>
          </Section>
        </>
      )}
    </div>
  );
}
