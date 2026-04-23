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
  { id: 'home',      label: 'עמוד הבית', icon: <IconHome /> },
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
    selectedProject: string;
    contractors: string[];
    selectedContractor: string;
    regions: string[];
    selectedRegions: string[];
    years: number[];
    selectedYear: number | null;
    reliabilityThreshold: number;
    onProjectChange: (v: string) => void;
    onContractorChange: (v: string) => void;
    onRegionsChange: (v: string[]) => void;
    onYearChange: (v: number | null) => void;
    onReliabilityChange: (v: number) => void;
  };
}

export function Sidebar({ activeTab, onTabChange, reviewCount = 0, filters }: SidebarProps) {
  const { user, logout } = useAuth();

  return (
    <aside className="flex-shrink-0 flex flex-col h-screen overflow-y-auto" style={{ width: 'var(--sidebar-width)', background: '#1b4332' }}>

      {/* Brand */}
      <div className="px-5 pt-6 pb-5 border-b" style={{ borderColor: 'rgba(183,228,199,0.12)' }}>
        <div className="flex items-center gap-2.5 mb-5">
          <img
            src="https://storage.googleapis.com/green_excal/carbontrack-logo.png"
            className="w-9 h-9 object-contain flex-shrink-0"
            alt="CarbonTrack"
            onError={e => { (e.target as HTMLImageElement).style.display = 'none'; }}
          />
          <div>
            <div className="font-bold text-sm leading-tight" style={{ color: '#d8f3e3' }}>Carbon₂Track</div>
            <div className="text-[10px]" style={{ color: 'rgba(183,228,199,0.5)' }}>נתיבי ישראל</div>
          </div>
        </div>

        {user && (
          <div className="flex items-center gap-2.5 rounded-2xl px-3 py-2.5" style={{ background: 'rgba(183,228,199,0.09)' }}>
            <div className="w-7 h-7 rounded-xl flex items-center justify-center text-xs font-bold flex-shrink-0"
              style={{ background: 'linear-gradient(135deg,#52b788,#95d5b2)', color: '#1b4332' }}>
              {(user.name || user.email)[0]?.toUpperCase()}
            </div>
            <div className="min-w-0">
              <div className="text-xs font-medium truncate" style={{ color: '#d8f3e3' }}>{user.name || user.email}</div>
              <div className="text-[10px] truncate" style={{ color: 'rgba(183,228,199,0.5)' }}>{ROLE_DISPLAY[user.role] || user.role}</div>
            </div>
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-0.5">
        <div className="text-[9px] font-semibold uppercase tracking-widest px-3 mb-2" style={{ color: 'rgba(183,228,199,0.35)' }}>תפריט ראשי</div>
        {NAV.map(({ id, label, icon }) => {
          const isActive = activeTab === id;
          return (
            <button key={id} onClick={() => onTabChange(id)}
              className={cn('w-full flex items-center gap-3 px-3 py-2.5 rounded-2xl text-xs font-medium transition-all text-right')}
              style={isActive
                ? { background: 'rgba(149,213,178,0.18)', color: '#95d5b2' }
                : { color: 'rgba(183,228,199,0.55)' }}
              onMouseEnter={e => { if (!isActive) { (e.currentTarget as HTMLElement).style.background = 'rgba(183,228,199,0.07)'; (e.currentTarget as HTMLElement).style.color = '#b7e4c7'; } }}
              onMouseLeave={e => { if (!isActive) { (e.currentTarget as HTMLElement).style.background = 'transparent'; (e.currentTarget as HTMLElement).style.color = 'rgba(183,228,199,0.55)'; } }}
            >
              <span className="w-4 h-4 flex-shrink-0 flex items-center justify-center">{icon}</span>
              <span className="flex-1">{label}</span>
              {id === 'review' && reviewCount > 0 && (
                <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-full" style={{ background: 'rgba(149,213,178,0.22)', color: '#95d5b2' }}>
                  {reviewCount}
                </span>
              )}
              {isActive && <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: '#95d5b2' }} />}
            </button>
          );
        })}
      </nav>

      {/* Filters */}
      <div className="px-4 py-4 space-y-3 border-t" style={{ borderColor: 'rgba(183,228,199,0.12)' }}>
        <div className="flex items-center justify-between">
          <span className="text-[9px] font-semibold uppercase tracking-widest" style={{ color: 'rgba(183,228,199,0.35)' }}>סינון נתונים</span>
          {(filters.selectedProject || filters.selectedContractor || filters.selectedYear || filters.selectedRegions.length > 0) && (
            <button
              onClick={() => {
                filters.onProjectChange('');
                filters.onContractorChange('');
                filters.onYearChange(null);
                filters.onRegionsChange([]);
              }}
              className="text-[9px] px-1.5 py-0.5 rounded"
              style={{ color: 'rgba(252,165,165,0.8)', background: 'rgba(252,165,165,0.08)' }}>
              ✕ נקה
            </button>
          )}
        </div>

        {/* Project filter */}
        {filters.projects.length > 0 && (
          <div>
            <label className="text-[10px] mb-1 block" style={{ color: 'rgba(183,228,199,0.5)' }}>פרויקט</label>
            <select
              className="w-full text-xs rounded-xl px-2 py-1.5 focus:outline-none"
              style={{ background: 'rgba(183,228,199,0.07)', color: '#b7e4c7', border: '1px solid rgba(183,228,199,0.15)' }}
              value={filters.selectedProject}
              onChange={e => filters.onProjectChange(e.target.value)}
            >
              <option value="">כל הפרויקטים</option>
              {filters.projects.map(p => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>
        )}

        {/* Contractor filter */}
        {filters.contractors.length > 0 && (
          <div>
            <label className="text-[10px] mb-1 block" style={{ color: 'rgba(183,228,199,0.5)' }}>קבלן</label>
            <select
              className="w-full text-xs rounded-xl px-2 py-1.5 focus:outline-none"
              style={{ background: 'rgba(183,228,199,0.07)', color: '#b7e4c7', border: '1px solid rgba(183,228,199,0.15)' }}
              value={filters.selectedContractor}
              onChange={e => filters.onContractorChange(e.target.value)}
            >
              <option value="">כל הקבלנים</option>
              {filters.contractors.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
        )}

        {/* Year filter */}
        <div>
          <label className="text-[10px] mb-1 block" style={{ color: 'rgba(183,228,199,0.5)' }}>שנה</label>
          <select
            className="w-full text-xs rounded-xl px-2 py-1.5 focus:outline-none"
            style={{ background: 'rgba(183,228,199,0.07)', color: '#b7e4c7', border: '1px solid rgba(183,228,199,0.15)' }}
            value={filters.selectedYear ?? ''}
            onChange={e => filters.onYearChange(e.target.value ? Number(e.target.value) : null)}
          >
            <option value="">כל השנים</option>
            {filters.years.map(y => <option key={y} value={y}>{y}</option>)}
          </select>
        </div>

        {/* Region checkboxes */}
        {filters.regions.length > 0 && (
          <div>
            <label className="text-[10px] mb-1 block" style={{ color: 'rgba(183,228,199,0.5)' }}>אזור</label>
            <div className="space-y-1">
              {filters.regions.map(r => (
                <label key={r} className="flex items-center gap-2 text-xs cursor-pointer" style={{ color: 'rgba(183,228,199,0.65)' }}>
                  <input type="checkbox" className="w-3 h-3 accent-[#95d5b2]"
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

        <button onClick={logout}
          className="w-full flex items-center justify-center gap-2 text-xs rounded-2xl py-2 transition-all"
          style={{ color: 'rgba(183,228,199,0.4)', border: '1px solid rgba(183,228,199,0.1)' }}
          onMouseEnter={e => { (e.currentTarget as HTMLElement).style.color = '#fca5a5'; (e.currentTarget as HTMLElement).style.borderColor = 'rgba(252,165,165,0.2)'; }}
          onMouseLeave={e => { (e.currentTarget as HTMLElement).style.color = 'rgba(183,228,199,0.4)'; (e.currentTarget as HTMLElement).style.borderColor = 'rgba(183,228,199,0.1)'; }}
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

function IconHome() {
  return <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>
  </svg>;
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
