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
  { id: 'dashboard', label: 'דאשבורד', icon: '📊' },
  { id: 'review', label: 'Review Queue', icon: '✅' },
  { id: 'whatif', label: 'What-If', icon: '⇄' },
  { id: 'ai', label: 'עוזר AI', icon: '🤖' },
  { id: 'upload', label: 'קליטת קבצים', icon: '☁️' },
  { id: 'data', label: 'נתונים', icon: '📋' },
  { id: 'settings', label: 'הגדרות', icon: '⚙️' },
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
    <aside className="w-64 flex-shrink-0 flex flex-col h-screen bg-white border-l border-border overflow-y-auto">
      {/* Brand header */}
      <div style={{ background: 'var(--grad-hero)' }} className="p-4 flex-shrink-0">
        <div className="flex items-center gap-3 pb-3 border-b border-white/10 mb-3">
          <img
            src="https://storage.googleapis.com/green_excal/carbontrack-logo.png"
            className="w-9 h-9 object-contain"
            onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
            alt="logo"
          />
          <div>
            <div className="text-white font-bold text-sm">Carbon₂Track</div>
            <div className="text-white/40 text-[10px]">BI · נתיבי ישראל</div>
          </div>
        </div>
        {user && (
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-white/10 flex items-center justify-center text-white text-sm font-bold flex-shrink-0">
              {(user.name || user.email)[0]?.toUpperCase()}
            </div>
            <div className="min-w-0">
              <div className="text-white/90 text-xs font-medium truncate">{user.name || user.email}</div>
              <div className="text-white/40 text-[10px]">{ROLE_DISPLAY[user.role] || user.role}</div>
            </div>
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-3 space-y-0.5">
        <div className="text-[10px] font-bold uppercase tracking-widest text-muted-fg px-2 py-2">ניווט</div>
        {NAV.map(({ id, label, icon }) => (
          <button
            key={id}
            onClick={() => onTabChange(id)}
            className={cn(
              'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors text-right',
              activeTab === id
                ? 'bg-primary/10 text-primary font-semibold'
                : 'text-gray-600 hover:bg-muted hover:text-gray-900'
            )}
          >
            <span className="text-base w-5 flex-shrink-0 text-center">{icon}</span>
            <span>{label}</span>
            {id === 'review' && reviewCount > 0 && (
              <span className="mr-auto bg-primary/10 text-primary text-[10px] font-bold px-1.5 py-0.5 rounded-full">
                {reviewCount}
              </span>
            )}
          </button>
        ))}
      </nav>

      {/* Filters */}
      <div className="p-3 border-t border-border space-y-3">
        <div className="text-[10px] font-bold uppercase tracking-widest text-muted-fg">סינון</div>

        {/* Year */}
        <div>
          <label className="text-[10px] text-muted-fg uppercase tracking-wide mb-1 block">שנה</label>
          <select
            className="w-full text-xs border border-border rounded-lg px-2 py-1.5 bg-muted focus:outline-none focus:ring-1 focus:ring-primary"
            value={filters.selectedYear ?? ''}
            onChange={e => filters.onYearChange(e.target.value ? Number(e.target.value) : null)}
          >
            <option value="">הכל</option>
            {filters.years.map(y => <option key={y} value={y}>{y}</option>)}
          </select>
        </div>

        {/* Regions */}
        <div>
          <label className="text-[10px] text-muted-fg uppercase tracking-wide mb-1 block">אזור</label>
          <div className="space-y-1">
            {filters.regions.map(r => (
              <label key={r} className="flex items-center gap-2 text-xs cursor-pointer">
                <input
                  type="checkbox"
                  className="accent-primary"
                  checked={filters.selectedRegions.includes(r)}
                  onChange={e => {
                    const next = e.target.checked
                      ? [...filters.selectedRegions, r]
                      : filters.selectedRegions.filter(x => x !== r);
                    filters.onRegionsChange(next);
                  }}
                />
                {r}
              </label>
            ))}
          </div>
        </div>

        {/* Reliability */}
        <div>
          <label className="text-[10px] text-muted-fg uppercase tracking-wide mb-1 block">
            סף אמינות: {filters.reliabilityThreshold.toFixed(2)}
          </label>
          <input
            type="range" min={0.5} max={1} step={0.01}
            value={filters.reliabilityThreshold}
            onChange={e => filters.onReliabilityChange(Number(e.target.value))}
            className="w-full accent-primary"
          />
        </div>

        <button
          onClick={logout}
          className="w-full text-xs text-muted-fg hover:text-destructive transition-colors py-1"
        >
          התנתקות
        </button>
      </div>
    </aside>
  );
}
