import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api/client';
import { Target, X, FileText } from 'lucide-react';

const statusStyles = {
  new: { bg: 'rgba(88,94,199,0.12)', color: 'var(--accent)' },
  will_apply: { bg: 'rgba(212,138,34,0.12)', color: 'var(--warning)' },
  applied: { bg: 'rgba(42,157,118,0.12)', color: 'var(--success)' },
  interview: { bg: 'rgba(123,84,206,0.12)', color: 'var(--interview)' },
  rejected: { bg: 'rgba(202,74,74,0.12)', color: 'var(--error)' },
  closed: { bg: 'rgba(107,114,128,0.12)', color: 'var(--text-tertiary)' },
};

function Badge({ status }) {
  const s = statusStyles[status] || statusStyles.closed;
  return (
    <span style={{
      fontSize: 11, fontWeight: 500, letterSpacing: '0.02em',
      padding: '3px 8px', borderRadius: 999,
      background: s.bg, color: s.color,
    }}>
      {status === 'will_apply' ? 'WILL APPLY' : status.toUpperCase()}
    </span>
  );
}

function MatchScore({ score }) {
  const color = score >= 70 ? 'var(--success)' : score >= 40 ? 'var(--warning)' : 'var(--error)';
  return <span style={{ fontSize: 24, fontWeight: 600, color, letterSpacing: '-0.02em' }}>{score}%</span>;
}

export { Badge, MatchScore, statusStyles };

export const getCompanyHslColor = (companyName, index = 0) => {
  return index % 2 === 0 ? 'var(--accent)' : 'var(--text-secondary)';
};

export const getCompanyLogo = (companyName, index = 0) => {
  const initial = companyName ? companyName.charAt(0).toUpperCase() : '?';
  const color = getCompanyHslColor(companyName, index);
  const bg = index % 2 === 0 ? 'rgba(88, 94, 199, 0.08)' : 'var(--surface-hover)';

  return (
    <div style={{
      width: 32,
      height: 32,
      borderRadius: '50%',
      background: bg,
      color: color,
      fontWeight: 700,
      fontSize: 13,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      marginRight: 12,
      flexShrink: 0,
    }}>
      {initial}
    </div>
  );
};

export const getScoreBadge = (score) => {
  let bg = 'rgba(202, 74, 74, 0.08)';
  let color = 'var(--error)';
  let border = 'rgba(202, 74, 74, 0.15)';
  
  if (score >= 70) {
    bg = 'rgba(42, 157, 118, 0.08)';
    color = 'var(--success)';
    border = 'rgba(42, 157, 118, 0.15)';
  } else if (score >= 40) {
    bg = 'rgba(212, 138, 34, 0.08)';
    color = 'var(--warning)';
    border = 'rgba(212, 138, 34, 0.15)';
  }
  
  return (
    <div style={{
      fontSize: 11,
      fontWeight: 600,
      padding: '2px 8px',
      borderRadius: 6,
      background: bg,
      color: color,
      border: `1px solid ${border}`,
      display: 'inline-flex',
      alignItems: 'center',
      whiteSpace: 'nowrap'
    }}>
      {score}% Match
    </div>
  );
};


const btnStyle = (bg, color, border) => ({
  height: 28, padding: '0 8px', borderRadius: 4, fontSize: 12, fontWeight: 500,
  background: bg, color, border: border || 'none', cursor: 'pointer',
  display: 'inline-flex', alignItems: 'center',
});

export default function NewJobs() {
  const [jobs, setJobs] = useState([]);
  const [selected, setSelected] = useState(null);
  const [rejectId, setRejectId] = useState(null);
  const [rejectReason, setRejectReason] = useState('');
  const [applyNoteId, setApplyNoteId] = useState(null);
  const [applyNote, setApplyNote] = useState('');
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);

  useEffect(() => { api.getJobs('new').then(setJobs).finally(() => setLoading(false)); }, []);

  const handleStatus = async (id, status, extra = '') => {
    if (status === 'rejected') await api.updateJobStatus(id, status, extra);
    else if (status === 'will_apply') await api.updateJobStatus(id, status, '', extra);
    else await api.updateJobStatus(id, status);
    setJobs(jobs.filter(j => j.id !== id));
    setSelected(null); setRejectId(null); setRejectReason('');
    setApplyNoteId(null); setApplyNote('');
  };

  if (loading) return <div style={{ color: 'var(--text-tertiary)', textAlign: 'center', padding: 48 }}>Loading...</div>;

  return (
    <div>
      <h1 style={{ fontSize: 20, fontWeight: 600, letterSpacing: '-0.02em', marginBottom: 24 }}>
        New Jobs <span style={{ color: 'var(--text-tertiary)', fontWeight: 400 }}>({jobs.length})</span>
      </h1>
      <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, overflow: 'hidden' }}>
        {jobs.map((job, idx) => (
          <div key={job.id} onClick={() => navigate(`/job/${job.id}`)} style={{
            borderBottom: idx < jobs.length - 1 ? '1px solid var(--border-subtle)' : 'none',
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
                <div style={{ fontWeight: 500, fontSize: 13 }}>{job.title}</div>
                <div style={{ color: 'var(--text-secondary)', fontSize: 13, marginTop: 2 }}>{job.company} — {job.location}</div>
                <div style={{ display: 'flex', gap: 8, marginTop: 4, alignItems: 'center' }}>
                  {job.remote && (
                    <span style={{ fontSize: 11, fontWeight: 500, background: 'rgba(42,157,118,0.12)', color: 'var(--success)', padding: '2px 8px', borderRadius: 999 }}>REMOTE</span>
                  )}
                  {job.has_packet && (
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 11, fontWeight: 500, background: 'rgba(88,94,199,0.12)', color: 'var(--accent)', padding: '2px 8px', borderRadius: 999 }}>
                      <FileText size={11} /> PACKET
                    </span>
                  )}
                  {job.salary_min && (
                    <span style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>${(job.salary_min/1000).toFixed(0)}k – ${(job.salary_max/1000).toFixed(0)}k</span>
                  )}
                </div>
              </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginLeft: 16 }}>
              {getScoreBadge(job.match_score)}
              <button onClick={e => { e.stopPropagation(); handleStatus(job.id, 'will_apply'); }} style={btnStyle('transparent', 'var(--warning)', '1px solid var(--warning)')} title="Will Apply">
                <Target size={13} />
              </button>
              <button onClick={e => { e.stopPropagation(); handleStatus(job.id, 'rejected'); }} style={btnStyle('transparent', 'var(--error)', '1px solid var(--error)')} title="Reject">
                <X size={13} />
              </button>
            </div>
          </div>
        ))}
        {jobs.length === 0 && (
          <p style={{ color: 'var(--text-tertiary)', textAlign: 'center', padding: 48 }}>
            No new jobs. Run a scan or wait for the next scheduled scrape.
          </p>
        )}
      </div>
    </div>
  );
}
