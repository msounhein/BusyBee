import { useEffect, useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api/client';
import { getCompanyLogo, getScoreBadge, getCompanyHslColor } from './NewJobs';
import { ArrowUpDown, ArrowUp, ArrowDown, Target, Building2, Briefcase, Calendar, CheckCircle2, FileText } from 'lucide-react';

const SORT_OPTIONS = [
  { key: 'match_score', label: 'Match Score', icon: Target },
  { key: 'company', label: 'Company', icon: Building2 },
  { key: 'title', label: 'Job Title', icon: Briefcase },
  { key: 'date', label: 'Date Found', icon: Calendar },
];

export default function AppliedJobs({ filter = 'applied' }) {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [sortBy, setSortBy] = useState(() => localStorage.getItem(`job_tracker_sort_${filter}_by`) || 'match_score');
  const [sortDir, setSortDir] = useState(() => localStorage.getItem(`job_tracker_sort_${filter}_dir`) || 'desc');
  const navigate = useNavigate();

  useEffect(() => { api.getJobs(filter).then(setJobs).finally(() => setLoading(false)); }, [filter]);

  useEffect(() => {
    const savedBy = localStorage.getItem(`job_tracker_sort_${filter}_by`);
    const savedDir = localStorage.getItem(`job_tracker_sort_${filter}_dir`);
    setSortBy(savedBy || 'match_score');
    setSortDir(savedDir || 'desc');
  }, [filter]);

  useEffect(() => {
    localStorage.setItem(`job_tracker_sort_${filter}_by`, sortBy);
  }, [sortBy, filter]);

  useEffect(() => {
    localStorage.setItem(`job_tracker_sort_${filter}_dir`, sortDir);
  }, [sortDir, filter]);

  const toggleSort = (key) => {
    if (sortBy === key) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(key);
      setSortDir(key === 'match_score' || key === 'date' ? 'desc' : 'asc');
    }
  };

  const sortedJobs = useMemo(() => {
    const copy = [...jobs];
    copy.sort((a, b) => {
      let cmp = 0;
      switch (sortBy) {
        case 'match_score':
          cmp = (a.match_score ?? 0) - (b.match_score ?? 0);
          break;
        case 'company':
          cmp = (a.company || '').localeCompare(b.company || '');
          break;
        case 'title':
          cmp = (a.title || '').localeCompare(b.title || '');
          break;
        case 'date': {
          const da = a.found_date ? new Date(a.found_date).getTime() : 0;
          const db = b.found_date ? new Date(b.found_date).getTime() : 0;
          cmp = da - db;
          break;
        }
        default: cmp = 0;
      }
      return sortDir === 'asc' ? cmp : -cmp;
    });
    return copy;
  }, [jobs, sortBy, sortDir]);

  const SortButton = ({ option }) => {
    const active = sortBy === option.key;
    const Icon = option.icon;
    return (
      <button
        onClick={() => toggleSort(option.key)}
        style={{
          display: 'inline-flex', alignItems: 'center', gap: 6,
          padding: '4px 10px', borderRadius: 6, fontSize: 12, fontWeight: active ? 600 : 400,
          background: active ? 'var(--accent-muted)' : 'var(--surface)',
          color: active ? 'var(--accent)' : 'var(--text-secondary)',
          border: active ? '1px solid var(--accent)' : '1px solid var(--border)',
          cursor: 'pointer', transition: 'all 150ms ease',
        }}
      >
        <Icon size={12} />
        {option.label}
        {active && (
          sortDir === 'asc' ? <ArrowUp size={12} /> : <ArrowDown size={12} />
        )}
      </button>
    );
  };

  const handleMarkApplied = async (id) => {
    await api.updateJobStatus(id, 'applied');
    setJobs(jobs.filter(j => j.id !== id));
  };

  const title = filter === 'will_apply' ? 'Will Apply' : 'Applied';

  if (loading) return <div style={{ color: 'var(--text-tertiary)', textAlign: 'center', padding: 48 }}>Loading...</div>;

  return (
    <div>
      <h1 style={{ fontSize: 20, fontWeight: 600, letterSpacing: '-0.02em', marginBottom: 24, display: 'flex', alignItems: 'center', gap: 8 }}>
        {filter === 'will_apply' ? <Target size={18} style={{ color: 'var(--warning)' }} /> : <CheckCircle2 size={18} style={{ color: 'var(--success)' }} />}
        <span>{title}</span>
        <span style={{ color: 'var(--text-tertiary)', fontWeight: 400 }}>({jobs.length})</span>
      </h1>
      {/* Sort Controls */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16,
        flexWrap: 'wrap',
      }}>
        <span style={{ fontSize: 12, color: 'var(--text-tertiary)', display: 'inline-flex', alignItems: 'center', gap: 4, marginRight: 4 }}>
          <ArrowUpDown size={13} /> Sort by:
        </span>
        {SORT_OPTIONS.map(opt => (
          <SortButton key={opt.key} option={opt} />
        ))}
      </div>

      <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, overflow: 'hidden' }}>
        {sortedJobs.map((job, idx) => (
          <div key={job.id} onClick={() => navigate(`/job/${job.id}`)} style={{
            borderBottom: idx < sortedJobs.length - 1 ? '1px solid var(--border-subtle)' : 'none',
            borderLeft: '4px solid ' + getCompanyHslColor(job.company, idx),
            padding: '12px 16px',
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            cursor: 'pointer', transition: 'all 200ms cubic-bezier(0.4, 0, 0.2, 1)',
          }}
          onMouseEnter={e => {
            e.currentTarget.style.background = 'var(--surface-elevated)';
            e.currentTarget.style.paddingLeft = '20px';
          }}
          onMouseLeave={e => {
            e.currentTarget.style.background = 'transparent';
            e.currentTarget.style.paddingLeft = '16px';
          }}
          >
            <div style={{ display: 'flex', alignItems: 'center', minWidth: 0, flex: 1 }}>
              {getCompanyLogo(job.company, idx)}
              <div style={{ minWidth: 0 }}>
                <div style={{ fontWeight: 500 }}>{job.title}</div>
                <div style={{ color: 'var(--text-secondary)', marginTop: 2 }}>{job.company} — {job.location}</div>
                <div style={{ display: 'flex', gap: 8, marginTop: 4, alignItems: 'center', flexWrap: 'wrap' }}>
                  {job.remote && (
                    <span style={{ fontSize: 11, fontWeight: 500, background: 'rgba(42,157,118,0.12)', color: 'var(--success)', padding: '2px 8px', borderRadius: 999 }}>
                      REMOTE
                    </span>
                  )}
                  {job.has_packet && (
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 11, fontWeight: 500, background: 'rgba(94,106,210,0.15)', color: '#5E6AD2', padding: '2px 8px', borderRadius: 999 }}>
                      <FileText size={11} /> PACKET
                    </span>
                  )}
                  <span style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>
                    {job.applied_date ? `Applied ${new Date(job.applied_date).toLocaleDateString()}` : `Found ${job.found_date ? new Date(job.found_date).toLocaleDateString() : ''}`}
                  </span>
                </div>
                {job.apply_note && (
                  <p style={{ fontSize: 12, color: 'var(--warning)', marginTop: 8, fontStyle: 'italic', display: 'flex', alignItems: 'center', gap: 4 }}>
                    <FileText size={12} />
                    <span>{job.apply_note}</span>
                  </p>
                )}
              </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginLeft: 16 }}>
              {getScoreBadge(job.match_score)}
              {filter === 'will_apply' && (
                <button onClick={() => handleMarkApplied(job.id)} style={{
                  display: 'inline-flex', alignItems: 'center', gap: 4,
                  height: 28, padding: '0 10px', borderRadius: 4, fontSize: 12, fontWeight: 500,
                  background: 'var(--success)', color: '#fff', border: 'none', cursor: 'pointer',
                }}>
                  <CheckCircle2 size={13} /> Applied
                </button>
              )}
              <button onClick={(e) => { e.stopPropagation(); navigate(`/job/${job.id}`); }} style={{ fontSize: 12, color: 'var(--accent)', background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}>View →</button>
            </div>
          </div>
        ))}
        {sortedJobs.length === 0 && (
          <p style={{ color: 'var(--text-tertiary)', textAlign: 'center', padding: 48 }}>
            {filter === 'will_apply' ? 'No jobs queued. Mark jobs as "Will Apply" from New Jobs.' : 'No applications yet.'}
          </p>
        )}
      </div>
    </div>
  );
}
