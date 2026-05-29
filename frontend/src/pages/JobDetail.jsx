import { useEffect, useState, useRef } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import api from '../api/client';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ArrowLeft, Target, X, Check, Mic, Home, Download, Trash2, Send, MapPin, Sparkles, Loader, ExternalLink } from 'lucide-react';
import ResearchPacket from '../components/ResearchPacket';
import { getCompanyLogo, getScoreBadge, getCompanyHslColor } from './NewJobs';

const btnStyle = (bg, color, border) => ({
  height: 32, padding: '0 14px', borderRadius: 6, fontSize: 13, fontWeight: 500,
  background: bg, color, border: border || 'none', cursor: 'pointer',
  display: 'inline-flex', alignItems: 'center', gap: 6, transition: 'opacity 150ms ease',
});

export default function JobDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [job, setJob] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [loading, setLoading] = useState(true);
  const chatContainerRef = useRef(null);
  const [rejecting, setRejecting] = useState(false);
  const [rejectReason, setRejectReason] = useState('');
  const [chatExpanded, setChatExpanded] = useState(false);
  const [activeTab, setActiveTab] = useState('description');
  const [resumes, setResumes] = useState([]);
  const [tailoring, setTailoring] = useState(false);
  const [hoveredResumeId, setHoveredResumeId] = useState(null);

  const handleAutoTailor = async () => {
    if (tailoring) return;
    setTailoring(true);
    try {
      const result = await api.autoTailorResume(id);
      setResumes(prev => [result, ...prev]);
    } catch (err) {
      alert(`⚠️ Tailoring failed: ${err.response?.data?.error || err.message}`);
    } finally {
      setTailoring(false);
    }
  };

  useEffect(() => {
    Promise.all([api.getJob(id), api.getChatHistory(id), api.getResumes(id)])
      .then(([j, msgs, res]) => {
        setJob(j);
        setResumes(res);
        if (msgs.length === 0 && j.match_reasoning) {
          setMessages([{
            role: 'assistant',
            content: `**Match: ${j.match_score}%**\n\n${j.match_reasoning}`,
            _auto: true,
          }]);
        } else {
          setMessages(msgs);
        }
      })
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [messages]);

  const pollPacketDone = (jobId) => {
    // Show a toast while generating
    let toast = document.getElementById('packet-toast');
    if (!toast) {
      toast = document.createElement('div');
      toast.id = 'packet-toast';
      toast.style.cssText = `
        position: fixed; bottom: 24px; right: 24px; z-index: 9999;
        padding: 12px 20px; border-radius: 8px; font-size: 13px; font-weight: 500;
        color: #fff; background: #5E6AD2; box-shadow: 0 4px 16px rgba(0,0,0,0.25);
        display: flex; align-items: center; gap: 8px;
      `;
      document.body.appendChild(toast);
    }
    toast.innerHTML = `
      <svg style="animation: spin 1s linear infinite; width: 14px; height: 14px; border: 2px solid rgba(255,255,255,0.2); border-top-color: #fff; border-radius: 50%; display: inline-block; vertical-align: middle; margin-right: 8px;" viewBox="0 0 24 24"></svg>
      <span>Generating research packet…</span>
    `;

    const iv = setInterval(async () => {
      try {
        const data = await api.getPacket(jobId);
        if (!data.generating) {
          clearInterval(iv);
          // Success toast
          toast.style.background = '#4DAF73';
          toast.innerHTML = `
            <svg style="width: 14px; height: 14px; display: inline-block; vertical-align: middle; margin-right: 8px;" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"></polyline></svg>
            <span>Research packet ready!</span>
          `;
          setTimeout(() => { toast.style.opacity = '0'; setTimeout(() => toast.remove(), 300); }, 3500);
        }
      } catch {
        clearInterval(iv);
        toast.style.background = '#E5534B';
        toast.innerHTML = `
          <svg style="width: 14px; height: 14px; display: inline-block; vertical-align: middle; margin-right: 8px;" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>
          <span>Packet generation failed</span>
        `;
        setTimeout(() => { toast.style.opacity = '0'; setTimeout(() => toast.remove(), 300); }, 3500);
      }
    }, 3000);
  };

  const sendMessage = async () => {
    if (!input.trim() || sending) return;
    const userMsg = { role: 'user', content: input };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setSending(true);
    try {
      const aiMsg = await api.sendChatMessage(id, input);
      setMessages(prev => [...prev, aiMsg]);
      // Refresh resumes in case AI generated one
      api.getResumes(id).then(setResumes);
      // If chat triggered async packet generation, start polling for toast
      if (aiMsg._packet_generating) {
        pollPacketDone(id);
      }
    } catch (e) {
      setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${e.message}` }]);
    }
    setSending(false);
  };

  const updateStatus = async (status, extra = '') => {
    await api.updateJobStatus(id, status, extra);
    setJob(prev => ({ ...prev, status }));
    setRejecting(false);
    setRejectReason('');
  };

  const confirmReject = () => {
    if (!rejecting) { setRejecting(true); return; }
    updateStatus('rejected', rejectReason);
  };

  const getActions = () => {
    switch (job.status) {
      case 'new':
        return (
          <>
            <button onClick={() => updateStatus('will_apply')} style={btnStyle('transparent', 'var(--warning)', '1px solid var(--warning)')}>
              <Target size={14} /> Will Apply
            </button>
            <button onClick={confirmReject} style={btnStyle('transparent', 'var(--error)', '1px solid var(--error)')}>
              <X size={14} /> Reject
            </button>
          </>
        );
      case 'will_apply':
        return (
          <>
            <button onClick={() => updateStatus('applied')} style={btnStyle('var(--success)', '#fff')}>
              <Check size={14} /> Applied
            </button>
            <button onClick={confirmReject} style={btnStyle('transparent', 'var(--error)', '1px solid var(--error)')}>
              <X size={14} /> Not For Me
            </button>
          </>
        );
      case 'applied':
        return (
          <>
            <button onClick={() => updateStatus('interview')} style={btnStyle('var(--interview)', '#fff')}>
              <Mic size={14} /> Interview
            </button>
            <button onClick={confirmReject} style={btnStyle('transparent', 'var(--error)', '1px solid var(--error)')}>
              <X size={14} /> Ghosted/Rejected
            </button>
          </>
        );
      case 'interview':
        return (
          <>
            <button onClick={() => updateStatus('offer')} style={btnStyle('var(--success)', '#fff')}>
              <Home size={14} /> Offer
            </button>
            <button onClick={confirmReject} style={btnStyle('transparent', 'var(--error)', '1px solid var(--error)')}>
              <X size={14} /> Rejected
            </button>
          </>
        );
      default:
        return <span style={{ color: 'var(--text-tertiary)', fontSize: 12 }}>Status: {job.status}</span>;
    }
  };

  if (loading) return <div style={{ color: 'var(--text-tertiary)', textAlign: 'center', padding: 48 }}>Loading...</div>;
  if (!job) return <div style={{ color: 'var(--error)', textAlign: 'center', padding: 48 }}>Job not found</div>;

  const statusColors = {
    new: 'var(--accent)', will_apply: 'var(--warning)', applied: 'var(--success)',
    interview: 'var(--interview)', offer: 'var(--success)', rejected: 'var(--error)', closed: 'var(--text-tertiary)',
  };

  const renderDownloadLink = (content) => {
    if (!content) return null;
    const match = content.match(/\/api\/resumes\/(\d+)\/download/);
    if (match) {
      return (
        <a
          href={api.downloadResume(match[1])}
          style={{
            display: 'inline-flex', alignItems: 'center', gap: 6,
            marginTop: 10, padding: '8px 16px', borderRadius: 6,
            fontSize: 13, fontWeight: 500, background: 'var(--accent)',
            color: '#fff', textDecoration: 'none',
          }}
        >⬇ Download Resume (PDF + DOCX)</a>
      );
    }
    return null;
  };

  return (
    <div className="job-detail-container">
      {/* Header */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        borderBottom: '1px solid var(--border)', padding: '12px 0', marginBottom: 0,
        flexShrink: 0,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <button onClick={() => navigate(-1)} style={{
            background: 'none', border: 'none', color: 'var(--text-secondary)',
            cursor: 'pointer', fontSize: 13, padding: 0, display: 'inline-flex', alignItems: 'center', gap: 4,
            flexShrink: 0
          }}>
            <ArrowLeft size={13} /> Back
          </button>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            {getCompanyLogo(job.company)}
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                <span style={{ fontWeight: 600, fontSize: 15, color: 'var(--text-primary)' }}>{job.title}</span>
                <span style={{ color: 'var(--text-secondary)', fontSize: 14 }}>— {job.company}</span>
                {getScoreBadge(job.match_score)}
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 4 }}>
                {job.remote && <span style={{ fontSize: 11, fontWeight: 500, background: 'rgba(42,157,118,0.12)', color: 'var(--success)', padding: '2px 8px', borderRadius: 999 }}>REMOTE</span>}
                <span style={{ fontSize: 11, fontWeight: 500, background: `${statusColors[job.status] || '#555'}22`, color: statusColors[job.status] || '#555', padding: '2px 8px', borderRadius: 999 }}>
                  {job.status.toUpperCase().replace('_', ' ')}
                </span>
              </div>
            </div>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          {getActions()}
          {rejecting && (
            <>
              <input
                value={rejectReason}
                onChange={e => setRejectReason(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && confirmReject()}
                placeholder="Reason for rejecting..."
                autoFocus
                style={{
                  height: 30, padding: '0 10px', borderRadius: 6, fontSize: 12,
                  background: 'var(--bg)', border: '1px solid var(--error)', color: 'var(--text-primary)',
                  outline: 'none', width: 200,
                }}
              />
              <button onClick={confirmReject} style={btnStyle('var(--error)', '#fff')}>Confirm</button>
              <button onClick={() => { setRejecting(false); setRejectReason(''); }} style={btnStyle('transparent', 'var(--text-tertiary)', '1px solid var(--border)')}>Cancel</button>
            </>
          )}
        </div>
      </div>

      {/* Split view */}
      <div className="job-detail-split">
        {/* Left: Job Details + Research Packet + Resumes */}
        <div style={{
          flex: 1,
          borderRight: '1px solid var(--border)',
          borderLeft: '4px solid ' + getCompanyHslColor(job.company),
          display: 'flex',
          flexDirection: 'column',
          minWidth: 0
        }}>
          {/* Tabs */}
          <div style={{ display: 'flex', borderBottom: '1px solid var(--border)', flexShrink: 0 }}>
            {[
              { key: 'description', label: 'Description' },
              { key: 'packet', label: 'Research Packet' },
              { key: 'resumes', label: `Resumes (${resumes.length})` },
            ].map(tab => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                style={{
                  padding: '10px 20px', fontSize: 13, fontWeight: 500,
                  background: 'none', border: 'none', cursor: 'pointer',
                  borderBottom: activeTab === tab.key ? '2px solid var(--accent)' : '2px solid transparent',
                  color: activeTab === tab.key ? 'var(--text-primary)' : 'var(--text-secondary)',
                  transition: 'color 150ms ease, border-color 150ms ease',
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Tab content */}
          <div style={{ flex: 1, overflow: 'auto' }}>
            {activeTab === 'description' ? (
              <div style={{ padding: 24 }}>
                {job.url && (
                  <a href={job.url} target="_blank" rel="noopener noreferrer" style={{
                    display: 'inline-flex', alignItems: 'center', gap: 8,
                    padding: '10px 20px', borderRadius: 8, fontSize: 14, fontWeight: 500,
                    background: 'var(--accent)', color: '#fff', textDecoration: 'none', marginBottom: 20,
                  }}><ExternalLink size={14} /> Open Job Listing (new tab)</a>
                )}
                {job.location && (
                  <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6, color: 'var(--text-secondary)', fontSize: 13, marginBottom: 8 }}>
                    <MapPin size={13} style={{ color: 'var(--text-tertiary)' }} />
                    <span>{job.location}</span>
                  </div>
                )}
                <div style={{ color: 'var(--text-primary)', fontSize: 13, whiteSpace: 'pre-line', lineHeight: 1.6 }}>
                  {job.description || 'No description available.'}
                </div>
              </div>
            ) : activeTab === 'resumes' ? (
              <div style={{ padding: 24 }}>
                <h3 style={{ margin: '0 0 16px', fontSize: 14, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em' }}>Tailored Resumes</h3>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20, gap: 16, flexWrap: 'wrap' }}>
                  <p style={{ color: 'var(--text-secondary)', fontSize: 13, margin: 0, maxWIdth: '60%' }}>
                    Create a customized, non-hallucinated version of your resume aligned perfectly with this job.
                  </p>
                  <button
                    onClick={handleAutoTailor}
                    disabled={tailoring}
                    style={{
                      display: 'inline-flex', alignItems: 'center', gap: 8,
                      padding: '10px 20px', borderRadius: 8, fontSize: 13, fontWeight: 600,
                      background: 'var(--accent)', color: '#fff', border: 'none', cursor: 'pointer',
                      opacity: tailoring ? 0.7 : 1, pointerEvents: tailoring ? 'none' : 'auto',
                      boxShadow: '0 2px 8px rgba(94, 106, 210, 0.25)', transition: 'all 150ms ease'
                    }}
                  >
                    {tailoring ? (
                      <>
                        <Loader size={14} style={{ animation: 'spin 1s linear infinite' }} />
                        <span>Tailoring Resume...</span>
                      </>
                    ) : (
                      <>
                        <Sparkles size={14} />
                        <span>Auto-Tailor Resume</span>
                      </>
                    )}
                  </button>
                </div>
                {resumes.length === 0 ? (
                  <div style={{ color: 'var(--text-tertiary)', fontSize: 13, textAlign: 'center', padding: 32 }}>
                    No tailored resumes yet. Start a conversation in the chat to create one.
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {resumes.map(r => (
                      <div
                        key={r.id}
                        onMouseEnter={() => setHoveredResumeId(r.id)}
                        onMouseLeave={() => setHoveredResumeId(null)}
                        style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          padding: '14px 18px',
                          borderRadius: 8,
                          border: '1px solid var(--border)',
                          background: 'var(--surface-elevated)',
                          transform: hoveredResumeId === r.id ? 'translateY(-2px)' : 'none',
                          boxShadow: hoveredResumeId === r.id 
                            ? '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -4px rgba(0, 0, 0, 0.1)'
                            : '0 1px 3px rgba(0, 0, 0, 0.05)',
                          transition: 'all 200ms cubic-bezier(0.4, 0, 0.2, 1)',
                        }}
                      >
                        <div>
                          <div style={{ fontSize: 13, fontWeight: 500 }}>
                            Resume #{r.id}
                            {r.notes && <span style={{ color: 'var(--text-secondary)', marginLeft: 8 }}>— {r.notes}</span>}
                          </div>
                          <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 2 }}>
                            {new Date(r.created_at).toLocaleString()}
                          </div>
                        </div>
                        <div style={{ display: 'flex', gap: 6 }}>
                          <a href={api.downloadResume(r.id)} style={{ ...btnStyle('var(--accent)', '#fff'), textDecoration: 'none' }}>
                            <Download size={13} /> Download
                          </a>
                          <button onClick={async () => {
                            if (confirm('Delete this resume?')) {
                              await api.deleteResume(r.id);
                              setResumes(prev => prev.filter(x => x.id !== r.id));
                            }
                          }} style={btnStyle('transparent', 'var(--error)', '1px solid var(--error)')}>
                            <Trash2 size={13} />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <ResearchPacket jobId={id} />
            )}
          </div>
        </div>

        {/* Right: AI Chat */}
        <div className="job-detail-chat-panel" style={{
          width: chatExpanded ? '60%' : 400, minWidth: chatExpanded ? 500 : 400,
          maxWidth: chatExpanded ? '70%' : 400, display: 'flex', flexDirection: 'column',
          background: 'var(--surface)', borderLeft: '1px solid var(--border)',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 16px', borderBottom: '1px solid var(--border)', flexShrink: 0 }}>
            <span style={{ fontSize: 14, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--text-secondary)' }}>AI Assistant</span>
            <button onClick={() => setChatExpanded(!chatExpanded)} style={{ background: 'none', border: '1px solid var(--border)', borderRadius: 4, color: 'var(--text-secondary)', cursor: 'pointer', fontSize: 11, padding: '2px 8px' }}>
              {chatExpanded ? '⬅ Collapse' : '➡ Expand'}
            </button>
          </div>

          <div ref={chatContainerRef} style={{ flex: 1, overflowY: 'auto', padding: 16 }}>
            {messages.length === 0 && (
              <div style={{ color: 'var(--text-tertiary)', fontSize: 12, textAlign: 'center', marginTop: 24 }}>
                Ask me anything about this job.
              </div>
            )}
            {messages.map((msg, i) => (
              <div key={i} style={{ marginBottom: 16, display: 'flex', justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start' }}>
                <div style={{
                  maxWidth: '85%',
                  padding: '12px 16px',
                  borderRadius: msg.role === 'user' ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
                  fontSize: 13,
                  lineHeight: 1.5,
                  background: msg.role === 'user' 
                    ? 'linear-gradient(135deg, var(--accent) 0%, var(--accent-hover, #4F46E5) 100%)' 
                    : 'linear-gradient(135deg, var(--surface-elevated) 0%, var(--surface) 100%)',
                  color: msg.role === 'user' ? '#fff' : 'var(--text-primary)',
                  border: msg.role === 'user' ? 'none' : '1px solid var(--border)',
                  boxShadow: msg.role === 'user' 
                    ? '0 4px 14px rgba(99, 102, 241, 0.2)' 
                    : '0 4px 12px rgba(0, 0, 0, 0.04)',
                }}>
                  {msg.role === 'user' ? msg.content : msg._auto ? (
                    <div style={{ whiteSpace: 'pre-line' }}>
                      {msg.content.split('**').map((part, i) => i % 2 === 1 ? <strong key={i}>{part}</strong> : part)}
                      <div style={{ marginTop: 12, paddingTop: 12, borderTop: '1px solid var(--border)' }}>
                        <span style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>Ask me to analyze skills, tailor your resume, or anything about this job.</span>
                      </div>
                    </div>
                  ) : (
                    <div className="chat-markdown">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                      {renderDownloadLink(msg.content)}
                    </div>
                  )}
                </div>
              </div>
            ))}
            {sending && (
              <div style={{ display: 'flex', justifyContent: 'flex-start', marginBottom: 16 }}>
                <div style={{
                  padding: '12px 16px',
                  borderRadius: '18px 18px 18px 4px',
                  fontSize: 13,
                  background: 'linear-gradient(135deg, var(--surface-elevated) 0%, var(--surface) 100%)',
                  border: '1px solid var(--border)',
                  color: 'var(--text-tertiary)',
                  boxShadow: '0 4px 12px rgba(0, 0, 0, 0.04)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8
                }}>
                  <Loader size={13} style={{ animation: 'spin 1s linear infinite' }} />
                  <span>Thinking...</span>
                </div>
              </div>
            )}
          </div>

          <div style={{ padding: 12, borderTop: '1px solid var(--border)', flexShrink: 0 }}>
            <div style={{ display: 'flex', gap: 8 }}>
              <textarea value={input} onChange={e => setInput(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); } }}
                placeholder="Ask about this job..." disabled={sending}
                rows={1}
                style={{ flex: 1, minHeight: 63, maxHeight: 200, height: 'auto', resize: 'none', background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 6, padding: '8px 12px', fontSize: 13, color: 'var(--text-primary)', outline: 'none', opacity: sending ? 0.6 : 1, fontFamily: 'inherit', lineHeight: 1.5 }}
              />
              <button onClick={sendMessage} disabled={sending || !input.trim()}
                style={{ height: 36, padding: '0 14px', borderRadius: 6, fontSize: 13, fontWeight: 500, background: 'var(--accent)', color: '#fff', border: 'none', cursor: 'pointer', opacity: sending || !input.trim() ? 0.5 : 1, display: 'inline-flex', alignItems: 'center', gap: 6 }}
              >
                <Send size={13} /> Send
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
