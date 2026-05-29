import { useEffect, useState, useRef } from 'react';
import api from '../api/client';
import { Search, Star, Loader, CheckCircle2, AlertCircle, Save } from 'lucide-react';
import { useOutletContext } from 'react-router-dom';

export default function Settings() {
  const { theme, setTheme } = useOutletContext();
  const [themeCardHover, setThemeCardHover] = useState(false);
  const [profile, setProfile] = useState(null);
  const [savingLLM, setSavingLLM] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const [scraping, setScraping] = useState(false);
  const [scrapeResult, setScrapeResult] = useState(null);
  const [scoring, setScoring] = useState(false);
  const [scoreResult, setScoreResult] = useState(null);
  const pollRef = useRef(null);
  const scorePollRef = useRef(null);

  useEffect(() => {
    api.getProfile().then(p => {
      setProfile(p);
    }).catch(e => console.error("Failed to load profile config:", e));

    api.getScrapeStatus().then(status => {
      if (status.running) {
        setScraping(true);
        startPolling();
      } else if (status.result) {
        setScrapeResult(status.result);
      } else if (status.error) {
        setScrapeResult({ error: status.error });
      }
    }).catch(() => {});

    api.getScoreStatus().then(status => {
      if (status.running) {
        setScoring(true);
        startScorePolling();
      } else if (status.result) {
        setScoreResult(status.result);
      } else if (status.error) {
        setScoreResult({ error: status.error });
      }
    }).catch(() => {});

    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
      if (scorePollRef.current) clearInterval(scorePollRef.current);
    };
  }, []);

  const startPolling = () => {
    if (pollRef.current) return;
    pollRef.current = setInterval(async () => {
      try {
        const status = await api.getScrapeStatus();
        if (!status.running) {
          clearInterval(pollRef.current);
          pollRef.current = null;
          setScraping(false);
          if (status.result) setScrapeResult(status.result);
          else if (status.error) setScrapeResult({ error: status.error });
        }
      } catch (e) {
        // ignore poll errors
      }
    }, 3000);
  };

  const startScorePolling = () => {
    if (scorePollRef.current) return;
    scorePollRef.current = setInterval(async () => {
      try {
        const status = await api.getScoreStatus();
        if (!status.running) {
          clearInterval(scorePollRef.current);
          scorePollRef.current = null;
          setScoring(false);
          if (status.result) setScoreResult(status.result);
          else if (status.error) setScoreResult({ error: status.error });
        }
      } catch (e) {
        // ignore poll errors
      }
    }, 3000);
  };

  const runScrape = async () => {
    setScrapeResult(null);
    try {
      const result = await api.triggerScrape();
      if (result.status === 'started' || result.status === 'already_running') {
        setScraping(true);
        startPolling();
      }
    } catch (e) {
      if (e.response?.status === 409) {
        setScraping(true);
        startPolling();
      } else {
        setScrapeResult({ error: e.message });
      }
    }
  };

  const runScore = async () => {
    setScoreResult(null);
    try {
      const result = await api.triggerScore();
      if (result.status === 'started' || result.status === 'already_running') {
        setScoring(true);
        startScorePolling();
      }
    } catch (e) {
      if (e.response?.status === 409) {
        setScoring(true);
        startScorePolling();
      } else {
        setScoreResult({ error: e.message });
      }
    }
  };

  const handleProviderChange = (providerVal) => {
    let defaultModel = 'glm-5.1';
    let defaultUrl = 'https://api.z.ai/api/coding/paas/v4/chat/completions';
    
    if (providerVal === 'openai') {
      defaultModel = 'gpt-4o-mini';
      defaultUrl = 'https://api.openai.com/v1/chat/completions';
    } else if (providerVal === 'openrouter') {
      defaultModel = 'google/gemini-2.5-flash';
      defaultUrl = 'https://openrouter.ai/api/v1/chat/completions';
    } else if (providerVal === 'custom') {
      defaultModel = '';
      defaultUrl = '';
    }

    setProfile({
      ...profile,
      llm_provider: providerVal,
      llm_model: defaultModel,
      llm_api_url: defaultUrl,
    });
  };

  const saveLLMSettings = async () => {
    setSavingLLM(true); setSaveSuccess(false);
    try {
      await api.updateProfile({
        llm_provider: profile.llm_provider,
        llm_api_key: profile.llm_api_key,
        llm_model: profile.llm_model,
        llm_api_url: profile.llm_api_url,
      });
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 2000);
    } catch (e) {
      console.error("Failed to save LLM settings:", e);
    } finally {
      setSavingLLM(false);
    }
  };

  const sectionStyle = {
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: 8,
    padding: 20,
    marginBottom: 16,
    transition: 'all 200ms cubic-bezier(0.4, 0, 0.2, 1)',
  };
  const labelStyle = { fontSize: 11, fontWeight: 500, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em', display: 'block', marginBottom: 8 };
  const headerStyle = { fontSize: 14, fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em', display: 'block', marginBottom: 12 };

  const inp = {
    width: '100%', height: 32, background: 'var(--surface)', border: '1px solid var(--border)',
    borderRadius: 6, padding: '0 10px', fontSize: 13, color: 'var(--text-primary)', outline: 'none',
  };
  const selectStyle = {
    ...inp, cursor: 'pointer', appearance: 'none',
    backgroundImage: `url("data:image/svg+xml;charset=UTF-8,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='rgba(150,150,150,0.8)' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3e%3cpolyline points='6 9 12 15 18 9'%3e%3c/polyline%3e%3c/svg%3e")`,
    backgroundRepeat: 'no-repeat', backgroundPosition: 'right 10px center', backgroundSize: '16px',
    paddingRight: '30px',
  };

  return (
    <div>
      <h1 style={{ fontSize: 20, fontWeight: 600, letterSpacing: '-0.02em', marginBottom: 24 }}>System Control Panel</h1>

      {/* Theme Switcher */}
      <div
        onMouseEnter={() => setThemeCardHover(true)}
        onMouseLeave={() => {
          setThemeCardHover(false);
        }}
        style={{
          ...sectionStyle,
          marginBottom: 20,
          borderLeft: '4px solid var(--accent)',
          transform: themeCardHover ? 'translateY(-2px)' : 'none',
          boxShadow: themeCardHover ? 'var(--shadow-md)' : 'var(--shadow-sm)',
          borderTopColor: themeCardHover ? 'var(--accent)' : 'var(--border)',
          borderRightColor: themeCardHover ? 'var(--accent)' : 'var(--border)',
          borderBottomColor: themeCardHover ? 'var(--accent)' : 'var(--border)',
          transition: 'all 200ms cubic-bezier(0.4, 0, 0.2, 1)',
        }}
      >
        <div style={headerStyle}>App Interface Theme</div>
        <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 16, lineHeight: 1.5 }}>
          Customize the visual theme of the BusyBee portal. Choose between light, dark, or the signature BusyBee honeycomb palette.
        </p>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          {[
            { id: 'light', label: 'Sleek Arctic (Light)', bg: '#F3F4F6', color: '#1F2937', accent: '#585EC7' },
            { id: 'dark', label: 'Cyberpunk Midnight (Dark)', bg: '#070709', color: '#F3F4F6', accent: '#6E78DC' },
            { id: 'busybee', label: 'BusyBee Honeycomb (Light)', bg: '#FAF6EE', color: '#292524', accent: '#D97706' },
            { id: 'busybee-dark', label: 'BusyBee Honey Midnight (Dark)', bg: '#0F0D0C', color: '#F5EBE1', accent: '#E29E3F' },
          ].map(t => {
            const active = theme === t.id;
            return (
              <button
                key={t.id}
                onClick={() => setTheme(t.id)}
                style={{
                  flex: 1,
                  minWidth: '180px',
                  padding: '12px 16px',
                  borderRadius: 8,
                  border: `2px solid ${active ? 'var(--accent)' : 'var(--border)'}`,
                  background: active ? 'var(--surface-elevated)' : 'var(--surface)',
                  color: 'var(--text-primary)',
                  cursor: 'pointer',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 8,
                  alignItems: 'flex-start',
                  boxShadow: active ? 'var(--shadow-md)' : 'none',
                  transform: active ? 'translateY(-1px)' : 'none',
                  transition: 'all 150ms ease',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%', alignItems: 'center' }}>
                  <span style={{ fontWeight: 600, fontSize: 12 }}>{t.label}</span>
                  <div style={{
                    width: 14,
                    height: 14,
                    borderRadius: '50%',
                    border: `2px solid ${active ? 'var(--accent)' : 'var(--border)'}`,
                    background: active ? 'var(--accent)' : 'transparent',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }} />
                </div>
                {/* Visual Preview Bar */}
                <div style={{ display: 'flex', gap: 6, width: '100%', marginTop: 4 }}>
                  <div style={{ width: 14, height: 14, borderRadius: '50%', background: t.bg, border: '1px solid var(--border)' }} />
                  <div style={{ width: 14, height: 14, borderRadius: '50%', background: t.accent }} />
                  <div style={{ width: 14, height: 14, borderRadius: '50%', background: t.color }} />
                </div>
              </button>
            );
          })}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 16 }}>
        <div
          onMouseEnter={e => {
            e.currentTarget.style.transform = 'translateY(-2px)';
            e.currentTarget.style.boxShadow = 'var(--shadow-md)';
            e.currentTarget.style.borderTopColor = 'var(--accent)';
            e.currentTarget.style.borderRightColor = 'var(--accent)';
            e.currentTarget.style.borderBottomColor = 'var(--accent)';
          }}
          onMouseLeave={e => {
            e.currentTarget.style.transform = 'none';
            e.currentTarget.style.boxShadow = 'var(--shadow-sm)';
            e.currentTarget.style.borderTopColor = 'var(--border)';
            e.currentTarget.style.borderRightColor = 'var(--border)';
            e.currentTarget.style.borderBottomColor = 'var(--border)';
          }}
          style={{ ...sectionStyle, marginBottom: 0, borderLeft: '4px solid var(--accent)' }}
        >
          <div style={headerStyle}>Manual Job Scrape</div>
          <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 16, lineHeight: 1.5 }}>
            Trigger a manual scan of enabled scraper sources. The system will look for new job postings matching your search terms.
          </p>
          <button onClick={runScrape} disabled={scraping} className="settings-action-btn settings-action-btn-accent">
            {scraping ? <Loader size={14} style={{ animation: 'spin 1s linear infinite' }} /> : <Search size={14} />}
            <span>{scraping ? 'Scanning...' : 'Search Now'}</span>
          </button>
          {scrapeResult && (
            <p style={{ marginTop: 12, fontSize: 13, color: 'var(--text-secondary)' }}>
              {scrapeResult.error ? (
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, color: 'var(--error)' }}>
                  <AlertCircle size={14} /> {scrapeResult.error}
                </span>
              ) : (
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, color: 'var(--success)' }}>
                  <CheckCircle2 size={14} /> Found {scrapeResult.new} new jobs ({scrapeResult.total} total)
                </span>
              )}
            </p>
          )}
        </div>

        <div
          onMouseEnter={e => {
            e.currentTarget.style.transform = 'translateY(-2px)';
            e.currentTarget.style.boxShadow = 'var(--shadow-md)';
            e.currentTarget.style.borderTopColor = '#E2A347';
            e.currentTarget.style.borderRightColor = '#E2A347';
            e.currentTarget.style.borderBottomColor = '#E2A347';
          }}
          onMouseLeave={e => {
            e.currentTarget.style.transform = 'none';
            e.currentTarget.style.boxShadow = 'var(--shadow-sm)';
            e.currentTarget.style.borderTopColor = 'var(--border)';
            e.currentTarget.style.borderRightColor = 'var(--border)';
            e.currentTarget.style.borderBottomColor = 'var(--border)';
          }}
          style={{ ...sectionStyle, marginBottom: 0, borderLeft: '4px solid #E2A347' }}
        >
          <div style={headerStyle}>Rate Unscored Jobs</div>
          <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 16, lineHeight: 1.5 }}>
            Analyze and score all unscored jobs in the database against your resume skills using the GLM-5.1 LLM agent.
          </p>
          <button onClick={runScore} disabled={scoring} className="settings-action-btn settings-action-btn-warning">
            {scoring ? <Loader size={14} style={{ animation: 'spin 1s linear infinite' }} /> : <Star size={14} />}
            <span>{scoring ? 'Rating...' : 'Rate Jobs'}</span>
          </button>
          {scoreResult && (
            <p style={{ marginTop: 12, fontSize: 13, color: 'var(--text-secondary)' }}>
              {scoreResult.error ? (
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, color: 'var(--error)' }}>
                  <AlertCircle size={14} /> {scoreResult.error}
                </span>
              ) : (
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, color: 'var(--success)' }}>
                  <CheckCircle2 size={14} /> Processed {scoreResult.scored} jobs ({scoreResult.skipped} auto-rejected, {scoreResult.failed} failed{scoreResult.reset_retries ? `, ${scoreResult.reset_retries} retried` : ''})
                </span>
              )}
            </p>
          )}
        </div>
      </div>

      {/* LLM Settings */}
      {profile && (
        <div
          onMouseEnter={e => {
            e.currentTarget.style.transform = 'translateY(-2px)';
            e.currentTarget.style.boxShadow = 'var(--shadow-md)';
            e.currentTarget.style.borderTopColor = '#A855F7';
            e.currentTarget.style.borderRightColor = '#A855F7';
            e.currentTarget.style.borderBottomColor = '#A855F7';
          }}
          onMouseLeave={e => {
            e.currentTarget.style.transform = 'none';
            e.currentTarget.style.boxShadow = 'var(--shadow-sm)';
            e.currentTarget.style.borderTopColor = 'var(--border)';
            e.currentTarget.style.borderRightColor = 'var(--border)';
            e.currentTarget.style.borderBottomColor = 'var(--border)';
          }}
          style={{ ...sectionStyle, marginTop: 16, borderLeft: '4px solid #A855F7' }}
        >
          <div style={headerStyle}>LLM Provider Configuration</div>
          <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 16, lineHeight: 1.5 }}>
            Configure the LLM client that powers job scoring, matching analysis, and resume tailoring.
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 12, marginBottom: 16 }}>
            <div>
              <label style={{ ...labelStyle, textTransform: 'none', fontSize: 11 }}>Provider</label>
              <select
                value={profile.llm_provider || 'zai'}
                onChange={e => handleProviderChange(e.target.value)}
                style={selectStyle}
              >
                <option value="zai">Z.AI (GLM-5.1 / MiniMax)</option>
                <option value="openai">OpenAI (Direct API)</option>
                <option value="openrouter">OpenRouter (Gemini, Claude, Llama...)</option>
                <option value="custom">Custom (OpenAI Compatible)</option>
              </select>
            </div>
            <div>
              <label style={{ ...labelStyle, textTransform: 'none', fontSize: 11 }}>Model ID</label>
              <input
                value={profile.llm_model || ''}
                onChange={e => setProfile({ ...profile, llm_model: e.target.value })}
                placeholder="e.g. gpt-4o-mini"
                style={inp}
              />
            </div>
            <div style={{ gridColumn: 'span 2' }}>
              <label style={{ ...labelStyle, textTransform: 'none', fontSize: 11 }}>API Base URL</label>
              <input
                value={profile.llm_api_url || ''}
                onChange={e => setProfile({ ...profile, llm_api_url: e.target.value })}
                placeholder="e.g. https://api.openai.com/v1/chat/completions"
                disabled={profile.llm_provider !== 'custom'}
                style={{ ...inp, opacity: profile.llm_provider === 'custom' ? 1 : 0.6 }}
              />
            </div>
          </div>
          <div style={{ marginBottom: 16 }}>
            <label style={{ ...labelStyle, textTransform: 'none', fontSize: 11 }}>API Key</label>
            <input
              type="password"
              value={profile.llm_api_key || ''}
              onChange={e => setProfile({ ...profile, llm_api_key: e.target.value })}
              placeholder={profile.llm_api_key ? '••••••••••••••••' : 'Enter API key (leave blank to use .env defaults)'}
              style={inp}
            />
          </div>
          <button onClick={saveLLMSettings} disabled={savingLLM} className="settings-action-btn settings-action-btn-accent">
            {savingLLM ? <Loader size={14} style={{ animation: 'spin 1s linear infinite' }} /> : saveSuccess ? <CheckCircle2 size={14} /> : <Save size={14} />}
            <span>{savingLLM ? 'Saving...' : saveSuccess ? 'Saved!' : 'Save LLM Settings'}</span>
          </button>
        </div>
      )}
    </div>
  );
}
