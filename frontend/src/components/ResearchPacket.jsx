import { useState, useEffect, useRef, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import api from '../api/client';
import { Building2, FileText, CheckCircle2, Mic, HelpCircle, AlertTriangle, Pin, RefreshCw, Loader, MessageSquare, ChevronDown, ChevronRight } from 'lucide-react';

const sectionLabels = {
  company_research: 'Company Research',
  role_analysis: 'Role Analysis',
  fit_analysis: 'Fit Analysis',
  interview_prep: 'Interview Prep',
  questions_to_ask: 'Questions to Ask',
  risk_assessment: 'Risk Assessment',
  bottom_line: 'Bottom Line',
};

const sectionIcons = {
  company_research: Building2,
  role_analysis: FileText,
  fit_analysis: CheckCircle2,
  interview_prep: Mic,
  questions_to_ask: HelpCircle,
  risk_assessment: AlertTriangle,
  bottom_line: Pin,
};

const sectionKeys = Object.keys(sectionLabels);

export default function ResearchPacket({ jobId }) {
  const [packet, setPacket] = useState(null);
  const [feedback, setFeedback] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeSection, setActiveSection] = useState(null);
  const [feedbackText, setFeedbackText] = useState('');
  const [saving, setSaving] = useState(false);
  const [editingSection, setEditingSection] = useState(null);
  const [editContent, setEditContent] = useState('');
  const [generating, setGenerating] = useState(false);
  const pollRef = useRef(null);
  const mountedRef = useRef(true);
  const generatingRef = useRef(false);

  const loadPacket = useCallback(async () => {
    try {
      const data = await api.getPacket(jobId);
      if (!mountedRef.current) return;
      setPacket(data.packet);
      setFeedback(data.feedback || []);
      if (data.generating) {
        setGenerating(true);
      } else if (generatingRef.current) {
        // Was generating, now done — we just finished
        generatingRef.current = false;
        setGenerating(false);
        if (pollRef.current) {
          clearInterval(pollRef.current);
          pollRef.current = null;
        }
      }
      return data.generating;
    } catch (e) {
      console.error('Failed to load packet:', e);
    }
    setLoading(false);
    return false;
  }, [jobId, generating]);

  useEffect(() => {
    loadPacket().then(isGen => {
      setLoading(false);
      if (isGen) startPolling();
    });
    return () => {
      mountedRef.current = false;
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [jobId]);

  const startPolling = () => {
    if (pollRef.current) return;
    pollRef.current = setInterval(async () => {
      const still = await loadPacket();
      if (!still && pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    }, 3000);
  };

  const handleGenerate = async () => {
    if (generating) return;
    generatingRef.current = true;
    setGenerating(true);
    try {
      const result = await api.generatePacket(jobId);
      if (result.status === 'already_generating') {
        // already polling
      }
      startPolling();
    } catch (e) {
      console.error('Failed to start generation:', e);
      setGenerating(false);
    }
  };

  const saveFeedback = async (section) => {
    if (!feedbackText.trim()) return;
    setSaving(true);
    try {
      await api.addPacketFeedback(jobId, section || 'general', feedbackText);
      setFeedbackText('');
      const data = await api.getPacket(jobId);
      setFeedback(data.feedback || []);
    } catch (e) {
      console.error('Failed to save feedback:', e);
    }
    setSaving(false);
  };

  const saveSectionEdit = async (section) => {
    setSaving(true);
    try {
      const update = {};
      update[section] = editContent;
      await api.updatePacket(jobId, update);
      setEditingSection(null);
      setEditContent('');
      loadPacket();
    } catch (e) {
      console.error('Failed to save section:', e);
    }
    setSaving(false);
  };

  if (loading) {
    return (
      <div style={{ padding: 24, color: 'var(--text-tertiary)', fontSize: 13 }}>
        Loading research packet...
      </div>
    );
  }

  // No packet + not generating — show generate button
  if (!packet && !generating) {
    return (
      <div style={{ padding: 24, textAlign: 'center' }}>
        <div style={{ color: 'var(--text-tertiary)', fontSize: 13, marginBottom: 16 }}>
          No research packet generated for this job yet.
        </div>
        <button
          onClick={handleGenerate}
          style={{
            height: 36, padding: '0 20px', borderRadius: 8, fontSize: 13, fontWeight: 500,
            background: 'var(--accent)', color: '#fff', border: 'none', cursor: 'pointer',
            display: 'inline-flex', alignItems: 'center', gap: 8,
          }}
        >
          🔍 Generate Research Packet
        </button>
      </div>
    );
  }

  // Currently generating — show spinner
  if (generating && !packet) {
    return (
      <div style={{ padding: 24, textAlign: 'center' }}>
        <div style={{
          display: 'inline-block', width: 28, height: 28,
          border: '3px solid var(--border)', borderTopColor: 'var(--accent)',
          borderRadius: '50%', animation: 'spin 0.8s linear infinite',
          marginBottom: 12,
        }} />
        <div style={{ color: 'var(--text-secondary)', fontSize: 13 }}>
          Researching company... this takes a minute.
        </div>
      </div>
    );
  }

  const sectionFeedback = (section) =>
    feedback.filter(f => f.section === section);

  return (
    <div style={{ padding: 24 }}>
      {/* Regenerate button */}
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'flex-end' }}>
        <button
          onClick={handleGenerate}
          disabled={generating}
          style={{
            height: 30, padding: '0 14px', borderRadius: 6, fontSize: 12, fontWeight: 500,
            background: generating ? 'var(--surface)' : 'var(--surface-elevated)',
            color: generating ? 'var(--text-tertiary)' : 'var(--text-secondary)',
            border: '1px solid var(--border)', cursor: generating ? 'default' : 'pointer',
            display: 'inline-flex', alignItems: 'center', gap: 6,
          }}
        >
          {generating ? (
            <>
              <Loader size={12} style={{ animation: 'spin 1s linear infinite' }} />
              <span>Generating…</span>
            </>
          ) : (
            <>
              <RefreshCw size={12} />
              <span>Regenerate</span>
            </>
          )}
        </button>
      </div>

      {/* Full content view (rendered markdown) */}
      {packet.content ? (
        <div className="packet-markdown" style={{ fontSize: 13, lineHeight: 1.7 }}>
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{packet.content}</ReactMarkdown>
        </div>
      ) : (
        /* Section-by-section view */
        <>
          {sectionKeys.map(key => {
            const content = packet[key];
            if (!content) return null;
            const sectionFb = sectionFeedback(key);
            const isEditing = editingSection === key;

            return (
              <div key={key} style={{
                marginBottom: 20,
                border: '1px solid var(--border)',
                borderRadius: 8,
                overflow: 'hidden',
              }}>
                {/* Section header */}
                <div
                  onClick={() => setActiveSection(activeSection === key ? null : key)}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '10px 16px',
                    background: activeSection === key ? 'var(--surface-elevated)' : 'var(--surface)',
                    cursor: 'pointer',
                    borderBottom: activeSection === key ? '1px solid var(--border)' : 'none',
                  }}
                >
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8, fontSize: 13, fontWeight: 500 }}>
                    {(() => {
                      const Icon = sectionIcons[key];
                      return Icon ? <Icon size={14} style={{ color: 'var(--accent)', flexShrink: 0 }} /> : null;
                    })()}
                    <span>{sectionLabels[key]}</span>
                    {sectionFb.length > 0 && (
                      <span style={{
                        marginLeft: 8, fontSize: 11, background: 'rgba(94,106,210,0.15)',
                        color: 'var(--accent)', padding: '1px 6px', borderRadius: 999,
                      }}>
                        {sectionFb.length} note{sectionFb.length > 1 ? 's' : ''}
                      </span>
                    )}
                  </span>
                  <span style={{ display: 'inline-flex', color: 'var(--text-tertiary)' }}>
                    {activeSection === key ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                  </span>
                </div>

                {/* Section content */}
                {activeSection === key && (
                  <div style={{ padding: 16 }}>
                    {isEditing ? (
                      <div>
                        <textarea
                          value={editContent}
                          onChange={e => setEditContent(e.target.value)}
                          style={{
                            width: '100%', minHeight: 150, padding: 12, fontSize: 13,
                            background: 'var(--bg)', border: '1px solid var(--border)',
                            borderRadius: 6, color: 'var(--text-primary)', resize: 'vertical',
                            fontFamily: 'inherit', lineHeight: 1.6,
                          }}
                        />
                        <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                          <button
                            onClick={() => saveSectionEdit(key)}
                            disabled={saving}
                            style={{
                              height: 30, padding: '0 12px', borderRadius: 6, fontSize: 12,
                              background: 'var(--accent)', color: '#fff', border: 'none',
                              cursor: 'pointer',
                            }}
                          >
                            {saving ? 'Saving...' : 'Save'}
                          </button>
                          <button
                            onClick={() => { setEditingSection(null); setEditContent(''); }}
                            style={{
                              height: 30, padding: '0 12px', borderRadius: 6, fontSize: 12,
                              background: 'transparent', color: 'var(--text-tertiary)',
                              border: '1px solid var(--border)', cursor: 'pointer',
                            }}
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    ) : (
                      <>
                        <div style={{ fontSize: 13, lineHeight: 1.7, whiteSpace: 'pre-line' }}>
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
                        </div>

                        {/* Existing feedback for this section */}
                        {sectionFb.length > 0 && (
                          <div style={{
                            marginTop: 12, paddingTop: 12,
                            borderTop: '1px solid var(--border)',
                          }}>
                            <div style={{ fontSize: 11, fontWeight: 500, color: 'var(--text-tertiary)', marginBottom: 6 }}>
                              YOUR NOTES
                            </div>
                            {sectionFb.map(fb => (
                              <div key={fb.id} style={{
                                padding: '8px 12px', marginBottom: 6, borderRadius: 6,
                                background: 'rgba(94,106,210,0.08)', fontSize: 12,
                                color: 'var(--text-primary)', lineHeight: 1.5,
                              }}>
                                {fb.feedback_text}
                                <span style={{ marginLeft: 8, fontSize: 10, color: 'var(--text-tertiary)' }}>
                                  {new Date(fb.created_at).toLocaleDateString()}
                                </span>
                              </div>
                            ))}
                          </div>
                        )}

                        {/* Add feedback */}
                        <div style={{ marginTop: 12, display: 'flex', gap: 8 }}>
                          <input
                            value={activeSection === key ? feedbackText : ''}
                            onChange={e => setFeedbackText(e.target.value)}
                            onKeyDown={e => e.key === 'Enter' && saveFeedback(key)}
                            placeholder="Add a note..."
                            style={{
                              flex: 1, height: 32, padding: '0 10px', borderRadius: 6,
                              fontSize: 12, background: 'var(--bg)', border: '1px solid var(--border)',
                              color: 'var(--text-primary)', outline: 'none',
                            }}
                          />
                          <button
                            onClick={() => saveFeedback(key)}
                            disabled={saving || !feedbackText.trim()}
                            style={{
                              height: 32, padding: '0 10px', borderRadius: 6, fontSize: 12,
                              background: 'var(--accent)', color: '#fff', border: 'none',
                              cursor: 'pointer', opacity: saving || !feedbackText.trim() ? 0.5 : 1,
                            }}
                          >
                            Note
                          </button>
                        </div>
                      </>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </>
      )}

      {/* General feedback at bottom */}
      <div style={{
        marginTop: 20, padding: 16, border: '1px solid var(--border)',
        borderRadius: 8, background: 'var(--surface)',
      }}>
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 12, fontWeight: 500, color: 'var(--text-secondary)', marginBottom: 8 }}>
          <MessageSquare size={13} style={{ color: 'var(--accent)' }} />
          <span>Overall Notes</span>
        </div>
        {feedback.filter(f => f.section === 'general').length > 0 && (
          <div style={{ marginBottom: 12 }}>
            {feedback.filter(f => f.section === 'general').map(fb => (
              <div key={fb.id} style={{
                padding: '8px 12px', marginBottom: 6, borderRadius: 6,
                background: 'rgba(94,106,210,0.08)', fontSize: 12,
                color: 'var(--text-primary)',
              }}>
                {fb.feedback_text}
              </div>
            ))}
          </div>
        )}
        <div style={{ display: 'flex', gap: 8 }}>
          <input
            value={activeSection === 'general' ? feedbackText : ''}
            onChange={e => setFeedbackText(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && saveFeedback('general')}
            placeholder="General thoughts on this opportunity..."
            style={{
              flex: 1, height: 32, padding: '0 10px', borderRadius: 6, fontSize: 12,
              background: 'var(--bg)', border: '1px solid var(--border)',
              color: 'var(--text-primary)', outline: 'none',
            }}
          />
          <button
            onClick={() => saveFeedback('general')}
            disabled={saving || !feedbackText.trim()}
            style={{
              height: 32, padding: '0 10px', borderRadius: 6, fontSize: 12,
              background: 'var(--accent)', color: '#fff', border: 'none',
              cursor: 'pointer', opacity: saving || !feedbackText.trim() ? 0.5 : 1,
            }}
          >
            Save
          </button>
        </div>
      </div>
    </div>
  );
}
