import { BrowserRouter, Routes, Route, NavLink, Outlet, useLocation } from 'react-router-dom';
import { LayoutDashboard, Briefcase, Target, CheckCircle, BarChart3, User, Settings, Menu, X, Moon, Sun, ChevronRight, ChevronLeft, Palette } from 'lucide-react';
import { useState, useEffect, useRef } from 'react';
import Dashboard from './pages/Dashboard';
import NewJobs from './pages/NewJobs';
import AppliedJobs from './pages/AppliedJobs';
import AllJobs from './pages/AllJobs';
import Profile from './pages/Profile';
import JobDetail from './pages/JobDetail';
import SettingsPage from './pages/Settings';
import BusyBeeIcon from './components/BusyBeeIcon';

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/new', icon: Briefcase, label: 'New Jobs' },
  { to: '/will-apply', icon: Target, label: 'Will Apply' },
  { to: '/applied', icon: CheckCircle, label: 'Applied' },
  { to: '/all', icon: BarChart3, label: 'All Jobs' },
  { to: '/profile', icon: User, label: 'Profile' },
  { to: '/settings', icon: Settings, label: 'Settings' },
];

function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [theme, setTheme] = useState(() => {
    const saved = localStorage.getItem('jobTrackerTheme');
    if (saved) return saved;
    const oldDark = localStorage.getItem('jobTrackerDark');
    if (oldDark !== null) return oldDark === 'true' ? 'dark' : 'light';
    return 'dark'; // default
  });
  const location = useLocation();
  const mainRef = useRef(null);

  useEffect(() => {
    if (mainRef.current) {
      mainRef.current.scrollTop = 0;
    }
  }, [location.pathname]);

  useEffect(() => {
    document.documentElement.classList.remove('light', 'dark', 'busybee', 'busybee-dark');
    document.documentElement.classList.add(theme);
    localStorage.setItem('jobTrackerTheme', theme);
  }, [theme]);

  return (
    <div style={{ display: 'flex', height: '100vh', position: 'relative', overflow: 'hidden' }}>
      {/* Background glow blobs */}
      <div style={{
        position: 'absolute', width: '500px', height: '500px',
        background: 'radial-gradient(circle, var(--accent-muted) 0%, transparent 70%)',
        top: '-150px', right: '-150px', filter: 'blur(80px)', pointerEvents: 'none', zIndex: 0,
      }} />
      <div style={{
        position: 'absolute', width: '600px', height: '600px',
        background: 'radial-gradient(circle, rgba(168,85,247,0.06) 0%, transparent 70%)',
        bottom: '-200px', left: '-200px', filter: 'blur(90px)', pointerEvents: 'none', zIndex: 0,
      }} />

      {sidebarOpen && (
        <div
          onClick={() => setSidebarOpen(false)}
          style={{
            position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)',
            zIndex: 20,
          }}
        />
      )}

      {/* Sidebar */}
      <aside style={{
        position: 'fixed', top: 0, bottom: 0, left: 0,
        width: collapsed ? 48 : 240,
        background: 'var(--surface)', borderRight: '1px solid var(--border)',
        zIndex: 30,
        transform: sidebarOpen ? 'translateX(0)' : 'translateX(-100%)',
        transition: 'width 150ms ease, transform 150ms ease',
        display: 'flex', flexDirection: 'column',
        overflow: 'hidden',
      }}
      className="lg:!transform-none"
      >
        {/* Sidebar Header */}
        <div style={{
          padding: collapsed ? '16px 0' : '16px',
          borderBottom: '1px solid var(--border)',
          display: 'flex',
          flexDirection: collapsed ? 'column' : 'row',
          alignItems: 'center',
          justifyContent: collapsed ? 'center' : 'space-between',
          gap: collapsed ? 12 : 8,
        }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: collapsed ? 'center' : 'flex-start',
            gap: 8,
            overflow: 'hidden',
            width: collapsed ? '100%' : 'auto',
          }}>
            <BusyBeeIcon size={collapsed ? 28 : 32} />
            {!collapsed && (
              <div style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.1 }}>
                <span style={{ fontSize: 16, fontWeight: 700, letterSpacing: '-0.03em', background: 'linear-gradient(135deg, var(--accent), #8B5CF6)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                  BusyBee
                </span>
                <span style={{ fontSize: 10, color: 'var(--text-tertiary)', fontWeight: 600, letterSpacing: '0.05em', textTransform: 'uppercase' }}>
                  Job Tracker
                </span>
              </div>
            )}
          </div>
          <div style={{
            display: 'flex',
            flexDirection: collapsed ? 'column' : 'row',
            gap: 4,
            flexShrink: 0,
            justifyContent: 'center',
            alignItems: 'center',
            width: collapsed ? '100%' : 'auto',
          }}>
            <button
              onClick={() => setCollapsed(!collapsed)}
              style={{
                padding: 6, borderRadius: 4, border: 'none', cursor: 'pointer',
                background: 'transparent', color: 'var(--text-tertiary)',
                display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
              }}
              title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            >
              {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
            </button>
            <button
              className="lg:!hidden"
              onClick={() => setSidebarOpen(false)}
              style={{
                padding: 6, borderRadius: 4, border: 'none', cursor: 'pointer',
                background: 'transparent', color: 'var(--text-tertiary)',
                display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
              }}
            >
              <X size={16} />
            </button>
          </div>
        </div>

        {/* Nav */}
        <nav style={{ padding: 8, flex: 1, overflow: 'hidden' }}>
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              onClick={() => setSidebarOpen(false)}
              style={({ isActive }) => ({
                display: 'flex', alignItems: 'center', gap: 10,
                padding: '6px 8px', borderRadius: 6, fontSize: 13,
                fontWeight: isActive ? 500 : 400,
                color: isActive ? 'var(--accent)' : 'var(--text-secondary)',
                background: isActive ? 'var(--accent-muted)' : 'transparent',
                textDecoration: 'none', transition: 'all 150ms ease',
                marginBottom: 2, whiteSpace: 'nowrap', overflow: 'hidden',
              })}
              onMouseEnter={e => { if (!e.currentTarget.classList.contains('active')) e.currentTarget.style.background = 'var(--surface-hover)'; }}
              onMouseLeave={e => { if (!e.currentTarget.classList.contains('active')) e.currentTarget.style.background = 'transparent'; }}
              title={collapsed ? label : ''}
            >
              <Icon size={16} style={{ flexShrink: 0 }} />
              {!collapsed && label}
            </NavLink>
          ))}
        </nav>

        {/* Sidebar Footer with Theme Switcher */}
        <div style={{
          padding: collapsed ? '12px 0' : '12px 16px',
          borderTop: '1px solid var(--border)',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
        }}>
          <button
            onClick={() => setTheme(t => t === 'light' ? 'busybee' : t === 'busybee' ? 'busybee-dark' : t === 'busybee-dark' ? 'dark' : 'light')}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: collapsed ? 'center' : 'flex-start',
              gap: 10,
              padding: '8px 10px',
              borderRadius: 6,
              fontSize: 13,
              border: 'none',
              cursor: 'pointer',
              background: 'var(--surface-hover)',
              color: 'var(--text-secondary)',
              transition: 'all 150ms ease',
              width: collapsed ? '32px' : '100%',
              height: '32px',
            }}
            title={theme === 'light' ? 'Switch to BusyBee Light' : theme === 'busybee' ? 'Switch to BusyBee Dark' : theme === 'busybee-dark' ? 'Switch to Dark Mode' : 'Switch to Light Mode'}
            onMouseEnter={e => e.currentTarget.style.background = 'var(--border)'}
            onMouseLeave={e => e.currentTarget.style.background = 'var(--surface-hover)'}
          >
            {theme === 'light' ? <Sun size={16} style={{ flexShrink: 0 }} /> : theme === 'dark' ? <Moon size={16} style={{ flexShrink: 0 }} /> : <Palette size={16} style={{ flexShrink: 0, color: theme === 'busybee' ? '#D97706' : '#E29E3F' }} />}
            {!collapsed && (
              <span style={{ whiteSpace: 'nowrap', overflow: 'hidden' }}>
                {theme === 'light' ? 'Light Mode' : theme === 'dark' ? 'Dark Mode' : theme === 'busybee' ? 'BusyBee Light' : 'BusyBee Dark'}
              </span>
            )}
          </button>
        </div>
      </aside>

      {/* Main */}
      <main
        ref={mainRef}
        style={{
          flex: 1,
          height: '100vh',
          overflowY: 'auto',
          transition: 'padding-left 150ms ease',
        }}
        className={collapsed ? "lg:pl-[48px]" : "lg:pl-[240px]"}
      >
        {/* Mobile header */}
        <div
          className="lg:!hidden"
          style={{
            padding: '12px 16px', borderBottom: '1px solid var(--border)',
            background: 'var(--surface)', display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          }}
        >
          <button onClick={() => setSidebarOpen(true)} style={{ background: 'none', border: 'none', color: 'var(--text-primary)', cursor: 'pointer' }}>
            <Menu size={20} />
          </button>
          <button
            onClick={() => setTheme(t => t === 'light' ? 'busybee' : t === 'busybee' ? 'busybee-dark' : t === 'busybee-dark' ? 'dark' : 'light')}
            style={{ padding: 6, borderRadius: 4, border: 'none', cursor: 'pointer', background: 'transparent', color: 'var(--text-tertiary)' }}
          >
            {theme === 'light' ? <Sun size={16} /> : theme === 'dark' ? <Moon size={16} /> : <Palette size={16} style={{ color: theme === 'busybee' ? '#D97706' : '#E29E3F' }} />}
          </button>
        </div>
        <div style={{ padding: '24px', maxWidth: '100%', margin: '0 auto', width: '100%' }}>
          <Outlet context={{ theme, setTheme }} />
        </div>
      </main>
    </div>
  );
}

function ScrollToTop() {
  // Scroll is now handled by mainRef in Layout
  return null;
}

export default function App() {
  return (
    <BrowserRouter>
      <ScrollToTop />
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="new" element={<NewJobs />} />
          <Route path="will-apply" element={<AppliedJobs filter="will_apply" />} />
          <Route path="applied" element={<AppliedJobs filter="applied" />} />
          <Route path="all" element={<AllJobs />} />
          <Route path="profile" element={<Profile />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="job/:id" element={<JobDetail />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
