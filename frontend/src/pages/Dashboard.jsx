import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api/client';
import { Badge } from './NewJobs';

function StatCard({ label, value, color, link, icon }) {
  const [hovered, setHovered] = useState(false);
  const navigate = useNavigate();
  
  return (
    <div
      onClick={() => link && navigate(link)}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        background: 'var(--surface-elevated)',
        border: '1px solid var(--border)',
        borderLeft: `4px solid ${color}`,
        borderColor: hovered ? color : 'var(--border)',
        borderRadius: 8,
        padding: '16px 20px',
        cursor: link ? 'pointer' : 'default',
        transform: hovered ? 'translateY(-2px)' : 'translateY(0)',
        boxShadow: hovered ? 'var(--shadow-md)' : 'var(--shadow-sm)',
        transition: 'all 200ms cubic-bezier(0.4, 0, 0.2, 1)',
        backdropFilter: 'var(--glass-blur)',
        WebkitBackdropFilter: 'var(--glass-blur)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
      }}
    >
      <div>
        <div style={{ fontSize: 24, fontWeight: 700, color: color, letterSpacing: '-0.02em', lineHeight: 1 }}>{value}</div>
        <div style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--text-secondary)', marginTop: 8 }}>{label}</div>
      </div>
      <div style={{
        width: 28,
        height: 28,
        borderRadius: 6,
        background: `${color}12`,
        color: color,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexShrink: 0,
      }}>
        {icon}
      </div>
    </div>
  );
}

const getCompanyLogo = (companyName) => {
  const initial = companyName ? companyName.charAt(0).toUpperCase() : '?';
  
  let hash = 0;
  const nameStr = companyName || '';
  for (let i = 0; i < nameStr.length; i++) {
    hash = nameStr.charCodeAt(i) + ((hash << 5) - hash);
  }
  const hue = Math.abs(hash % 360);
  const bg = `hsl(${hue}, 40%, 50%, 0.12)`;
  const fg = `hsl(${hue}, 40%, 50%)`;

  return (
    <div style={{
      width: 32,
      height: 32,
      borderRadius: '50%',
      background: bg,
      color: fg,
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

const getScoreBadge = (score) => {
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

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [recentJobs, setRecentJobs] = useState([]);
  const [packets, setPackets] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    Promise.all([
      api.getStats(),
      api.getJobs(),
      api.listPackets().catch(() => []),
    ]).then(([s, jobs, pkts]) => {
      setStats(s);
      setRecentJobs(jobs.slice(0, 8));
      setPackets(pkts);
    }).finally(() => setLoading(false));
  }, []);

  if (loading) return <div style={{ color: 'var(--text-tertiary)', textAlign: 'center', padding: 48 }}>Loading...</div>;

  const cards = [
    {
      label: 'New',
      value: stats?.new || 0,
      color: 'var(--accent)',
      link: '/new',
      icon: (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 5v14M5 12h14" />
        </svg>
      )
    },
    {
      label: 'Will Apply',
      value: stats?.will_apply || 0,
      color: 'var(--warning)',
      link: '/will-apply',
      icon: (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" />
        </svg>
      )
    },
    {
      label: 'Applied',
      value: stats?.applied || 0,
      color: 'var(--success)',
      link: '/applied',
      icon: (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M22 2L11 13M22 2l-7 20-4-9-9-4Z" />
        </svg>
      )
    },
    {
      label: 'Interviews',
      value: stats?.interview || 0,
      color: '#A855F7',
      link: '/applied',
      icon: (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        </svg>
      )
    },
    {
      label: 'Rejected',
      value: stats?.rejected || 0,
      color: 'var(--error)',
      link: '/all',
      icon: (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="10" />
          <line x1="4.93" y1="4.93" x2="19.07" y2="19.07" />
        </svg>
      )
    },
    {
      label: 'Packets',
      value: stats?.packet_stats?.total || packets.length,
      color: 'var(--text-primary)',
      link: null,
      icon: (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
        </svg>
      )
    },
  ];

  return (
    <div>
      <h1 style={{ fontSize: 20, fontWeight: 600, letterSpacing: '-0.02em', marginBottom: 24 }}>Dashboard</h1>

      {/* Stat Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: 12, marginBottom: 32 }}>
        {cards.map((card) => (
          <StatCard key={card.label} {...card} />
        ))}
      </div>

      {/* Two columns: Left (Stats + Recent Jobs) vs Right (Research Packets) */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
        {/* Left Column: Stats + Recent Jobs */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
          {/* Application Stats */}
          <ApplicationStats stats={stats} />

          {/* Process Monitor */}
          <ProcessMonitor />

          {/* Recent Jobs */}
          <div>
            <h2 style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 12, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Recent Jobs
            </h2>
            <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, overflow: 'hidden' }}>
              {recentJobs.length === 0 ? (
                <div style={{ padding: 24, color: 'var(--text-tertiary)', fontSize: 13, textAlign: 'center' }}>
                  No jobs yet. Run a scan to get started.
                </div>
              ) : recentJobs.map((job, i) => (
                <div
                  key={job.id}
                  onClick={() => navigate(`/job/${job.id}`)}
                  style={{
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                    padding: '10px 16px',
                    borderBottom: i < recentJobs.length - 1 ? '1px solid var(--border-subtle)' : 'none',
                    cursor: 'pointer',
                    transition: 'all 200ms cubic-bezier(0.4, 0, 0.2, 1)',
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
                    {getCompanyLogo(job.company, i)}
                    <div style={{ minWidth: 0 }}>
                      <div style={{ fontSize: 13, fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', color: 'var(--text-primary)' }}>
                        {job.title}
                      </div>
                      <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 2 }}>
                        {job.company}
                      </div>
                    </div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginLeft: 12, flexShrink: 0 }}>
                    <Badge status={job.status} />
                    {getScoreBadge(job.match_score)}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Recent Packets / Research Packets */}
        <div>
          <h2 style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 12, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            Research Packets
          </h2>

          {/* Packet Stats Sub-grid */}
          {stats?.packet_stats && (
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(3, 1fr)',
              gap: 8,
              marginBottom: 12
            }}>
              <div style={{
                background: 'var(--surface-elevated)', border: '1px solid var(--border)',
                borderRadius: 8, padding: '10px 12px', textAlign: 'center'
              }}>
                <div style={{ fontSize: 18, fontWeight: 600, color: 'var(--text-primary)' }}>
                  {stats.packet_stats.total}
                </div>
                <div style={{ fontSize: 9, color: 'var(--text-secondary)', textTransform: 'uppercase', marginTop: 2, fontWeight: 500, letterSpacing: '0.02em' }}>
                  Total Packets
                </div>
              </div>
              <div style={{
                background: 'var(--surface-elevated)', border: '1px solid var(--border)',
                borderRadius: 8, padding: '10px 12px', textAlign: 'center'
              }}>
                <div style={{ fontSize: 18, fontWeight: 600, color: 'var(--success)' }}>
                  {stats.packet_stats.high_match}
                </div>
                <div style={{ fontSize: 9, color: 'var(--text-secondary)', textTransform: 'uppercase', marginTop: 2, fontWeight: 500, letterSpacing: '0.02em' }}>
                  High Match (≥70%)
                </div>
              </div>
              <div style={{
                background: 'var(--surface-elevated)', border: '1px solid var(--border)',
                borderRadius: 8, padding: '10px 12px', textAlign: 'center'
              }}>
                <div style={{ fontSize: 18, fontWeight: 600, color: 'var(--accent)' }}>
                  +{stats.packet_stats.last_24h}
                </div>
                <div style={{ fontSize: 9, color: 'var(--text-secondary)', textTransform: 'uppercase', marginTop: 2, fontWeight: 500, letterSpacing: '0.02em' }}>
                  Last 24 Hours
                </div>
              </div>
            </div>
          )}

          {/* Status Breakdown Bar */}
          {stats?.packet_stats?.by_status && (
            <div style={{
              background: 'var(--surface)', border: '1px solid var(--border)',
              borderRadius: 8, padding: '8px 12px', marginBottom: 12,
              display: 'flex', justifyContent: 'space-around', alignItems: 'center', fontSize: 11,
              flexWrap: 'wrap', gap: '4px 8px'
            }}>
              <span style={{ color: 'var(--text-secondary)', fontWeight: 500 }}>Breakdown:</span>
              <span>
                <span style={{ fontWeight: 600, color: 'var(--accent)' }}>{stats.packet_stats.by_status.new}</span> New
              </span>
              <span style={{ color: 'var(--border-subtle)' }}>|</span>
              <span>
                <span style={{ fontWeight: 600, color: 'var(--warning)' }}>{stats.packet_stats.by_status.will_apply || 0}</span> Will Apply
              </span>
              <span style={{ color: 'var(--border-subtle)' }}>|</span>
              <span>
                <span style={{ fontWeight: 600, color: 'var(--success)' }}>{stats.packet_stats.by_status.applied}</span> Applied
              </span>
              <span style={{ color: 'var(--border-subtle)' }}>|</span>
              <span>
                <span style={{ fontWeight: 600, color: '#A855F7' }}>{stats.packet_stats.by_status.interview}</span> Interview
              </span>
              <span style={{ color: 'var(--border-subtle)' }}>|</span>
              <span>
                <span style={{ fontWeight: 600, color: 'var(--error)' }}>{stats.packet_stats.by_status.rejected}</span> Rejected
              </span>
            </div>
          )}
          <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, overflow: 'hidden' }}>
            {packets.length === 0 ? (
              <div style={{ padding: 24, color: 'var(--text-tertiary)', fontSize: 13, textAlign: 'center' }}>
                No packets generated yet. They're built daily at 12:30 PM.
              </div>
            ) : packets.slice(0, 8).map((pkt, i) => (
              <div
                key={pkt.id}
                onClick={() => navigate(`/job/${pkt.job_id}`)}
                style={{
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  padding: '10px 16px',
                  borderBottom: i < Math.min(packets.length, 8) - 1 ? '1px solid var(--border-subtle)' : 'none',
                  cursor: 'pointer',
                  transition: 'all 200ms cubic-bezier(0.4, 0, 0.2, 1)',
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
                  {getCompanyLogo(pkt.company, i)}
                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontSize: 13, fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', color: 'var(--text-primary)' }}>
                      {pkt.title}
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 2 }}>
                      {pkt.company}
                    </div>
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginLeft: 12, flexShrink: 0 }}>
                  <span style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>
                    {pkt.updated_at ? new Date(pkt.updated_at).toLocaleDateString() : ''}
                  </span>
                  {getScoreBadge(pkt.match_score)}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}function MonitorCard({ status, name, icon }) {
  const [hovered, setHovered] = useState(false);
  if (!status) return null;
  
  const isRunning = status.running;
  const error = status.error;
  const result = status.result;
  
  let badgeColor = 'var(--text-tertiary)';
  let statusText = 'Idle';
  if (isRunning) {
    badgeColor = 'var(--accent)';
    statusText = 'Running';
  } else if (error) {
    badgeColor = 'var(--error)';
    statusText = 'Error';
  } else if (result) {
    badgeColor = 'var(--success)';
    statusText = 'Completed';
  }

  const formatTime = (isoString) => {
    if (!isoString) return '';
    return new Date(isoString).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        background: 'var(--surface-elevated)',
        border: '1px solid var(--border)',
        borderColor: hovered ? 'var(--accent)' : 'var(--border)',
        borderRadius: 8,
        padding: '12px 16px',
        display: 'flex',
        flexDirection: 'column',
        gap: 6,
        flex: 1,
        minWidth: '240px',
        boxShadow: hovered ? 'var(--shadow-md)' : 'var(--shadow-sm)',
        transform: hovered ? 'translateY(-2px)' : 'translateY(0)',
        transition: 'all 200ms cubic-bezier(0.4, 0, 0.2, 1)',
        cursor: 'default',
        backdropFilter: 'var(--glass-blur)',
        WebkitBackdropFilter: 'var(--glass-blur)',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontWeight: 600 }}>
          <div style={{ color: hovered ? 'var(--accent)' : 'var(--text-secondary)', display: 'flex', alignItems: 'center', transition: 'color 150ms ease' }}>
            {icon}
          </div>
          <span>{name}</span>
        </div>
        <div style={{
          fontSize: 10,
          fontWeight: 600,
          padding: '2px 8px',
          borderRadius: 12,
          background: `${badgeColor}15`,
          color: badgeColor,
          border: `1px solid ${badgeColor}30`,
          display: 'flex',
          alignItems: 'center',
          gap: 4
        }}>
          {isRunning && <span className="pulse-dot" style={{
            width: 6, height: 6, borderRadius: '50%', background: 'var(--accent)',
            display: 'inline-block', animation: 'pulse-anim 1.5s infinite'
          }} />}
          {statusText}
        </div>
      </div>
      <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
        {isRunning ? (
          <span>Started at {formatTime(status.started_at)}</span>
        ) : error ? (
          <span style={{ color: 'var(--error)', wordBreak: 'break-word' }}>{error}</span>
        ) : result ? (
          <span>
            {name === 'Scraper' ? (
              `Found ${result.total ?? 0} jobs (${result.new ?? 0} new) at ${formatTime(status.finished_at)}`
            ) : name === 'Scorer' ? (
              `Scored ${result.scored} jobs (${result.skipped} skipped, ${result.failed} failed)`
            ) : (
              `Generated ${result.packets_built || 0} packets at ${formatTime(status.finished_at)}`
            )}
          </span>
        ) : (
          <span>No recent activity</span>
        )}
      </div>
    </div>
  );
}

function ProcessMonitor() {
  const [scrapeStatus, setScrapeStatus] = useState(null);
  const [scoreStatus, setScoreStatus] = useState(null);
  const [researchStatus, setResearchStatus] = useState(null);
 
  const fetchStatus = () => {
    Promise.all([
      api.getScrapeStatus().catch(() => null),
      api.getScoreStatus().catch(() => null),
      api.getResearchStatus().catch(() => null)
    ]).then(([scrape, score, research]) => {
      setScrapeStatus(scrape);
      setScoreStatus(score);
      setResearchStatus(research);
    });
  };
 
  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, []);
 
  if (!scrapeStatus && !scoreStatus && !researchStatus) return null;
 
  return (
    <div style={{ marginBottom: 24 }}>
      <h2 style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 12, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
        Process Monitor
      </h2>
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
        <MonitorCard
          status={scrapeStatus}
          name="Scraper"
          icon={
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20M2 12h20" />
            </svg>
          }
        />
        <MonitorCard
          status={scoreStatus}
          name="Scorer"
          icon={
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <circle cx="12" cy="12" r="6" />
              <circle cx="12" cy="12" r="2" />
            </svg>
          }
        />
        <MonitorCard
          status={researchStatus}
          name="Researcher"
          icon={
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20M4 4.5A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1-2.5-2.5v-15z" />
            </svg>
          }
        />
      </div>
      <style>{`
        @keyframes pulse-anim {
          0% { transform: scale(0.95); opacity: 0.5; }
          50% { transform: scale(1.1); opacity: 1; }
          100% { transform: scale(0.95); opacity: 0.5; }
        }
      `}</style>
    </div>
  );
}

function ApplicationStats({ stats }) {
  const [hovered, setHovered] = useState(false);

  const dailyValue = stats?.applied_daily || 0;
  const weeklyValue = stats?.applied_weekly || 0;
  const dailyTarget = 2;
  const weeklyTarget = 10;

  const dailyPercent = dailyTarget ? (dailyValue / dailyTarget) * 100 : 0;
  const weeklyPercent = weeklyTarget ? (weeklyValue / weeklyTarget) * 100 : 0;

  return (
    <div>
      <h2 style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 12, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
        Application Stats
      </h2>
      <div
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
        style={{
          background: 'var(--surface-elevated)',
          border: '1px solid var(--border)',
          borderLeft: '4px solid var(--success)',
          borderColor: hovered ? 'var(--success)' : 'var(--border)',
          borderRadius: 8,
          padding: '16px 20px',
          display: 'flex',
          flexDirection: 'column',
          gap: 16,
          boxShadow: hovered ? 'var(--shadow-md)' : 'var(--shadow-sm)',
          transform: hovered ? 'translateY(-2px)' : 'translateY(0)',
          transition: 'all 200ms cubic-bezier(0.4, 0, 0.2, 1)',
          cursor: 'default',
          backdropFilter: 'var(--glass-blur)',
          WebkitBackdropFilter: 'var(--glass-blur)',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h3 style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>
            Application Activity
          </h3>
          <span style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>Goal Progress</span>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {/* Daily Stats */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <div style={{
                  width: 24, height: 24, borderRadius: 4, background: 'rgba(16, 185, 129, 0.1)',
                  color: 'var(--success)', display: 'flex', alignItems: 'center', justifyContent: 'center'
                }}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="10" />
                    <polyline points="12 6 12 12 16 14" />
                  </svg>
                </div>
                <span style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-secondary)' }}>Daily Applications</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 2 }}>
                <span style={{ fontSize: 14, fontWeight: 700, color: 'var(--success)' }}>{dailyValue}</span>
                <span style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>/ {dailyTarget}</span>
                <span style={{ fontSize: 11, fontWeight: 500, color: 'var(--text-tertiary)', marginLeft: 4 }}>({Math.round(dailyPercent)}%)</span>
              </div>
            </div>
            <div style={{ height: 6, background: 'rgba(16, 185, 129, 0.05)', borderRadius: 3, overflow: 'hidden', border: '1px solid rgba(16, 185, 129, 0.1)' }}>
              <div style={{
                height: '100%',
                width: `${Math.min(dailyPercent, 100)}%`,
                background: 'linear-gradient(90deg, #10B981, #34D399)',
                borderRadius: 3,
                transition: 'width 600ms cubic-bezier(0.4, 0, 0.2, 1)',
              }} />
            </div>
          </div>

          {/* Weekly Stats */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <div style={{
                  width: 24, height: 24, borderRadius: 4, background: 'rgba(99, 102, 241, 0.1)',
                  color: 'var(--accent)', display: 'flex', alignItems: 'center', justifyContent: 'center'
                }}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
                    <line x1="16" y1="2" x2="16" y2="6" />
                    <line x1="8" y1="2" x2="8" y2="6" />
                    <line x1="3" y1="10" x2="21" y2="10" />
                  </svg>
                </div>
                <span style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-secondary)' }}>Weekly Applications</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 2 }}>
                <span style={{ fontSize: 14, fontWeight: 700, color: 'var(--accent)' }}>{weeklyValue}</span>
                <span style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>/ {weeklyTarget}</span>
                <span style={{ fontSize: 11, fontWeight: 500, color: 'var(--text-tertiary)', marginLeft: 4 }}>({Math.round(weeklyPercent)}%)</span>
              </div>
            </div>
            <div style={{ height: 6, background: 'rgba(99, 102, 241, 0.05)', borderRadius: 3, overflow: 'hidden', border: '1px solid rgba(99, 102, 241, 0.1)' }}>
              <div style={{
                height: '100%',
                width: `${Math.min(weeklyPercent, 100)}%`,
                background: 'linear-gradient(90deg, #6366F1, #818CF8)',
                borderRadius: 3,
                transition: 'width 600ms cubic-bezier(0.4, 0, 0.2, 1)',
              }} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
