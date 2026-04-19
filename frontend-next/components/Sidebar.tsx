'use client';
import { cn } from '../lib/utils';
import { useAuth } from '../lib/auth';

const ROLE_DISPLAY: Record<string, string> = {
  management: 'הנהלה',
  support: 'תומכי הלחימה',
  project_manager: 'מנהל פרויקט',
  sustainability: 'קיימות (ESG)',
  regulator: 'רגולטור',
};

const NAV = [
  { id: 'dashboard', label: 'דאשבורד', icon: <IconDashboard /> },
  { id: 'review',    label: 'תור סקירה', icon: <IconReview /> },
  { id: 'whatif',   label: 'סימולטור What-If', icon: <IconWhatIf /> },
  { id: 'ai',       label: 'עוזר AI', icon: <IconAI /> },
  { id: 'upload',   label: 'קליטת קבצים', icon: <IconUpload /> },
  { id: 'data',     label: 'נתונים גולמיים', icon: <IconData /> },
  { id: 'settings', label: 'הגדרות', icon: <IconSettings /> },
];

interface SidebarProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
  reviewCount?: number;
  filters: {
    projects: string[];
    selectedProjects: string[];
    regions: string[];
    selectedRegions: string[];
    years: number[];
    selectedYear: number | null;
    reliabilityThreshold: number;
    onProjectsChange: (v: string[]) => void;
    onRegionsChange: (v: string[]) => void;
    onYearChange: (v: number | null) => void;
    onReliabilityChange: (v: number) => void;
  };
}

export function Sidebar({ activeTab, onTabChange, reviewCount = 0, filters }: SidebarProps) {
  const { user, logout } = useAuth();

  return (
    <aside className="flex-shrink-0 flex flex-col h-screen overflow-y-auto" style={{ width: 'var(--sidebar-width)', background: '#0f1729' }}>

      {/* Brand */}
      <div className="px-5 pt-6 pb-5 border-b" style={{ borderColor: 'rgba(255,255,255,0.07)' }}>
        <div className="flex items-center gap-2.5 mb-5">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0" style={{ background: 'linear-gradient(135deg,#059669,#10b981)' }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 22V12M12 12C12 7 7 4 3 6M12 12C12 7 17 4 21 6" />
            </svg>
          </div>
          <div>
            <div className="text-white font-bold text-sm leading-tight">Carbon₂Track</div>
            <div className="text-xs" style={{ color: 'rgba(255,255,255,0.35)' }}>נתיבי ישראל</div>
          </div>
        </div>

        {user && (
          <div className="flex items-center gap-2.5 rounded-xl px-3 py-2.5" style={{ background: 'rgba(255,255,255,0.06)' }}>
            <div className="w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold text-white flex-shrink-0"
              style={{ background: 'linear-gradient(135deg,#059669,#10b981)' }}>
              {(user.name || user.email)[0]?.toUpperCase()}
            </div>
            <div className="min-w-0">
              <div className="text-xs font-medium truncate" style={{ color: 'rgba(255,255,255,0.85)' }}>{user.name || user.email}</div>
              <div className="text-[10px] truncate" style={{ color: 'rgba(255,255,255,0.35)' }}>{ROLE_DISPLAY[user.role] || user.role}</div>
            </div>
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-0.5">
        <div className="text-[9px] font-bold uppercase tracking-widest px-3 mb-2" style={{ color: 'rgba(255,255,255,0.25)' }}>תפריט ראשי</div>
        {NAV.map(({ id, label, icon }) => {
          const isActive = activeTab === id;
          return (
            <button key={id} onClick={() => onTabChange(id)}
              className={cn('w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-medium transition-all text-right group')}
              style={isActive
                ? { background: 'rgba(16,185,129,0.15)', color: '#34d399' }
                : { color: 'rgba(255,255,255,0.5)' }}
              onMouseEnter={e => { if (!isActive) (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.05)'; (e.currentTarget as HTMLElement).style.color = 'rgba(255,255,255,0.8)'; }}
              onMouseLeave={e => { if (!isActive) { (e.currentTarget as HTMLElement).style.background = 'transparent'; (e.currentTarget as HTMLElement).style.color = 'rgba(255,255,255,0.5)'; } }}
            >
              <span className="w-4 h-4 flex-shrink-0 flex items-center justify-center opacity-90">{icon}</span>
              <span className="flex-1">{label}</span>
              {id === 'review' && reviewCount > 0 && (
                <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-full" style={{ background: 'rgba(16,185,129,0.25)', color: '#34d399' }}>
                  {reviewCount}
                </span>
              )}
              {isActive && <span className="w-1 h-1 rounded-full flex-shrink-0" style={{ background: '#10b981' }} />}
            </button>
          );
        })}
      </nav>

      {/* Filters */}
      <div className="px-4 py-4 space-y-4 border-t" style={{ borderColor: 'rgba(255,255,255,0.07)' }}>
        <div className="text-[9px] font-bold uppercase tracking-widest" style={{ color: 'rgba(255,255,255,0.25)' }}>סינון נתונים</div>

        <div>
          <label className="text-[10px] mb-1.5 block" style={{ color: 'rgba(255,255,255,0.4)' }}>שנה</label>
          <select
            className="w-full text-xs rounded-lg px-3 py-1.5 focus:outline-none transition-colors"
            style={{ background: 'rgba(255,255,255,0.06)', color: 'rgba(255,255,255,0.7)', border: '1px solid rgba(255,255,255,0.1)' }}
            value={filters.selectedYear ?? ''}
            onChange={e => filters.onYearChange(e.target.value ? Number(e.target.value) : null)}
          >
            <option value="">כל השנים</option>
            {filters.years.map(y => <option key={y} value={y}>{y}</option>)}
          </select>
        </div>

        {filters.regions.length > 0 && (
          <div>
            <label className="text-[10px] mb-1.5 block" style={{ color: 'rgba(255,255,255,0.4)' }}>אזור</label>
            <div className="space-y-1.5">
              {filters.regions.map(r => (
                <label key={r} className="flex items-center gap-2 text-xs cursor-pointer" style={{ color: 'rgba(255,255,255,0.55)' }}>
                  <input type="checkbox" className="accent-emerald-500 w-3 h-3"
                    checked={filters.selectedRegions.includes(r)}
                    onChange={e => {
                      const next = e.target.checked ? [...filters.selectedRegions, r] : filters.selectedRegions.filter(x => x !== r);
                      filters.onRegionsChange(next);
                    }} />
                  {r}
                </label>
              ))}
            </div>
          </div>
        )}

        <div>
          <label className="text-[10px] mb-1.5 flex justify-between" style={{ color: 'rgba(255,255,255,0.4)' }}>
            <span>סף אמינות</span>
            <span style={{ color: '#34d399' }}>{filters.reliabilityThreshold.toFixed(2)}</span>
          </label>
          <input type="range" min={0.5} max={1} step={0.01}
            value={filters.reliabilityThreshold}
            onChange={e => filters.onReliabilityChange(Number(e.target.value))}
            className="w-full h-1.5 rounded-full appearance-none cursor-pointer accent-emerald-500" />
        </div>

        <button onClick={logout}
          className="w-full flex items-center justify-center gap-2 text-xs rounded-xl py-2 transition-all"
          style={{ color: 'rgba(255,255,255,0.35)', border: '1px solid rgba(255,255,255,0.07)' }}
          onMouseEnter={e => { (e.currentTarget as HTMLElement).style.color = '#f87171'; (e.currentTarget as HTMLElement).style.borderColor = 'rgba(248,113,113,0.2)'; }}
          onMouseLeave={e => { (e.currentTarget as HTMLElement).style.color = 'rgba(255,255,255,0.35)'; (e.currentTarget as HTMLElement).style.borderColor = 'rgba(255,255,255,0.07)'; }}
        >
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9" />
          </svg>
          התנתקות
        </button>
      </div>
    </aside>
  );
}

function IconDashboard() {
  return <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/>
    <rect x="14" y="14" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/>
  </svg>;
}
function IconReview() {
  return <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>
  </svg>;
}
function IconWhatIf() {
  return <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M7 16V4m0 0L3 8m4-4 4 4M17 8v12m0 0 4-4m-4 4-4-4"/>
  </svg>;
}
function IconAI() {
  return <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 2a2 2 0 0 1 2 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 0 1 7 7h1a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1h-1v1a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-1H2a1 1 0 0 1-1-1v-3a1 1 0 0 1 1-1h1a7 7 0 0 1 7-7h1V5.73c-.6-.34-1-.99-1-1.73a2 2 0 0 1 2-2z"/>
    <circle cx="9" cy="14" r="1"/><circle cx="15" cy="14" r="1"/>
  </svg>;
}
function IconUpload() {
  return <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
  </svg>;
}
function IconData() {
  return <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14c0 1.66 4.03 3 9 3s9-1.34 9-3V5"/><path d="M3 12c0 1.66 4.03 3 9 3s9-1.34 9-3"/>
  </svg>;
}
function IconSettings() {
  return <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="3"/>
    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
  </svg>;
}
