import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api/client';
import { Badge, getCompanyLogo, getScoreBadge, getCompanyHslColor } from './NewJobs';
import { Lightbulb } from 'lucide-react';

export default function AllJobs() {
  const navigate = useNavigate();
  const [jobs, setJobs] = useState([]);
  const [filter, setFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [hoveredId, setHoveredId] = useState(null);

  useEffect(() => { api.getJobs().then(setJobs).finally(() => setLoading(false)); }, []);
  const filtered = filter ? jobs.filter(j => j.status === filter) : jobs;

  if (loading) return <div style={{ color: 'var(--text-tertiary)', textAlign: 'center', padding: 48 }}>Loading...</div>;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <h1 style={{ fontSize: 20, fontWeight: 600, letterSpacing: '-0.02em' }}>
          All Jobs <span style={{ color: 'var(--text-tertiary)', fontWeight: 400 }}>({filtered.length})</span>
        </h1>
        <select value={filter} onChange={e => setFilter(e.target.value)} style={{
          height: 32, background: 'var(--surface)', border: '1px solid var(--border)',
          borderRadius: 6, padding: '0 10px', fontSize: 13, color: 'var(--text-primary)', outline: 'none',
        }}>
          <option value="">All Statuses</option>
          <option value="new">New</option>
          <option value="will_apply">Will Apply</option>
          <option value="applied">Applied</option>
          <option value="interview">Interview</option>
          <option value="rejected">Rejected</option>
          <option value="closed">Closed</option>
        </select>
      </div>
      <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, overflow: 'hidden' }}>
        {filtered.map((job, i) => (
          <div
            key={job.id}
            onClick={() => navigate(`/job/${job.id}`)}
            onMouseEnter={() => setHoveredId(job.id)}
            onMouseLeave={() => setHoveredId(null)}
            style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              borderBottom: i < filtered.length - 1 ? '1px solid var(--border-subtle)' : 'none',
              borderLeft: '4px solid ' + getCompanyHslColor(job.company, i),
              padding: '10px 16px',
              paddingLeft: hoveredId === job.id ? 20 : 16,
              cursor: 'pointer',
              transition: 'all 200ms cubic-bezier(0.4, 0, 0.2, 1)',
              background: hoveredId === job.id ? 'var(--surface-elevated)' : 'transparent',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', minWidth: 0, flex: 1 }}>
              {getCompanyLogo(job.company, i)}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ fontWeight: 500, fontSize: 13 }}>{job.title}</span>
                  <Badge status={job.status} />
                </div>
                <div style={{ color: 'var(--text-secondary)', fontSize: 12, marginTop: 2 }}>
                  {job.company} — {job.location || 'Location not specified'}
                </div>
                {job.match_reasoning && (
                  <div style={{
                    fontSize: 11, color: 'var(--text-tertiary)', marginTop: 4,
                    lineHeight: 1.4, fontStyle: 'italic',
                    maxWidth: '100%',
                    overflow: 'hidden', textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                    display: 'flex', alignItems: 'center', gap: 4
                  }}>
                    <Lightbulb size={11} style={{ color: 'var(--warning)', flexShrink: 0 }} />
                    <span>{job.match_reasoning}</span>
                  </div>
                )}
              </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginLeft: 16, flexShrink: 0 }}>
              {job.remote && (
                <span style={{ fontSize: 11, fontWeight: 500, background: 'rgba(42,157,118,0.12)', color: 'var(--success)', padding: '2px 8px', borderRadius: 999 }}>REMOTE</span>
              )}
              {getScoreBadge(job.match_score)}
            </div>
          </div>
        ))}
        {filtered.length === 0 && (
          <div style={{ color: 'var(--text-tertiary)', textAlign: 'center', padding: 48, fontSize: 13 }}>
            No jobs found.
          </div>
        )}
      </div>
    </div>
  );
}
