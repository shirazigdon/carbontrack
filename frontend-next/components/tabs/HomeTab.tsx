'use client';
import { useMemo } from 'react';
import { EmissionRow } from '../../lib/api';
import { fmt } from '../../lib/utils';

interface Props {
  data: EmissionRow[];
  reviewCount: number;
  userName: string;
  onNavigate: (tab: string) => void;
}

const QUICK_ACTIONS = [
  { id: 'dashboard', icon: '📊', title: 'דאשבורד', desc: 'סקירת KPI, גרפים ומפת פליטות', color: '#059669', bg: '#f0fdf4' },
  { id: 'review',   icon: '✅', title: 'תור סקירה', desc: 'אשרי או דחי רשומות ממתינות', color: '#f59e0b', bg: '#fffbeb' },
  { id: 'whatif',   icon: '⚡', title: 'סימולטור What-If', desc: 'השוואת חלופות חומרים ופוטנציאל חיסכון', color: '#6366f1', bg: '#f5f3ff' },
  { id: 'ai',       icon: '🤖', title: 'עוזר AI', desc: 'שאל שאלות על נתוני הפליטות', color: '#0ea5e9', bg: '#f0f9ff' },
  { id: 'upload',   icon: '📤', title: 'קליטת קבצים', desc: 'העלה קבצי פליטות לעיבוד', color: '#8b5cf6', bg: '#faf5ff' },
  { id: 'data',     icon: '🗃️', title: 'נתונים גולמיים', desc: 'עיון ובחינת כל הרשומות', color: '#64748b', bg: '#f8fafc' },
];

function greeting(name: string) {
  const h = new Date().getHours();
  const salut = h < 12 ? 'בוקר טוב' : h < 17 ? 'צהריים טובים' : 'ערב טוב';
  const first = name.split(' ')[0] || name;
  return `${salut}, ${first}`;
}

export function HomeTab({ data, reviewCount, userName, onNavigate }: Props) {
  const curYear = new Date().getFullYear();

  const stats = useMemo(() => {
    const totalE = data.reduce((s, r) => s + (r.emission_co2e || 0), 0);
    const yearE  = data.filter(r => r.year === curYear).reduce((s, r) => s + (r.emission_co2e || 0), 0);
    const totalW = data.reduce((s, r) => s + (r.weight_kg || 0), 0);
    const projects = new Set(data.map(r => r.project_name).filter(Boolean)).size;
    const avgRel = data.length ? data.reduce((s, r) => s + (r.reliability_score || 0), 0) / data.length : 0;
    return { totalE, yearE, totalW, projects, avgRel };
  }, [data, curYear]);

  const topProject = useMemo(() => {
    const map: Record<string, number> = {};
    data.forEach(r => { const p = r.project_name || '?'; map[p] = (map[p] || 0) + (r.emission_co2e || 0); });
    const sorted = Object.entries(map).sort((a, b) => b[1] - a[1]);
    return sorted[0];
  }, [data]);

  const topCategory = useMemo(() => {
    const map: Record<string, number> = {};
    data.forEach(r => { const c = r.category || '?'; map[c] = (map[c] || 0) + (r.emission_co2e || 0); });
    const sorted = Object.entries(map).sort((a, b) => b[1] - a[1]);
    return sorted[0];
  }, [data]);

  return (
    <div className="space-y-6 max-w-5xl mx-auto">

      {/* Hero welcome */}
      <div className="rounded-3xl overflow-hidden relative" style={{ background: 'linear-gradient(135deg, #1b4332 0%, #2d6a4f 60%, #40916c 100%)' }}>
        <div className="absolute inset-0 opacity-25"
          style={{ backgroundImage: 'radial-gradient(circle at 80% 50%, #95d5b2 0%, transparent 55%), radial-gradient(circle at 15% 80%, #52b788 0%, transparent 45%)' }} />
        <div className="relative px-8 py-8 flex items-center justify-between gap-6 flex-wrap">
          <div>
            <p className="text-sm font-medium mb-1" style={{ color: '#95d5b2' }}>{new Date().toLocaleDateString('he-IL', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}</p>
            <h1 className="text-3xl font-black text-white mb-2">{greeting(userName)} 👋</h1>
            <p className="text-white/50 text-sm">ברוכה הבאה למערכת Carbon₂Track — נתיבי ישראל</p>
          </div>
          <div className="flex gap-3 flex-wrap">
            {reviewCount > 0 && (
              <button onClick={() => onNavigate('review')}
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold text-white transition-all hover:scale-105"
                style={{ background: 'rgba(245,158,11,0.25)', border: '1px solid rgba(245,158,11,0.4)' }}>
                <span className="w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold" style={{ background: '#f59e0b' }}>{reviewCount}</span>
                רשומות ממתינות לאישור
              </button>
            )}
            <button onClick={() => onNavigate('upload')}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold text-white transition-all hover:scale-105"
              style={{ background: 'rgba(16,185,129,0.2)', border: '1px solid rgba(16,185,129,0.35)' }}>
              📤 העלאת קובץ חדש
            </button>
          </div>
        </div>
      </div>

      {/* KPI strip */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { label: `פליטות ${curYear}`, value: `${fmt(stats.yearE / 1000, 1)}t`, sub: 'CO₂e', color: '#059669' },
          { label: 'סה"כ פליטות', value: `${fmt(stats.totalE / 1000, 1)}t`, sub: 'כל הפרויקטים', color: '#0f172a' },
          { label: 'פרויקטים', value: `${stats.projects}`, sub: 'פעילים', color: '#6366f1' },
          { label: 'ממוצע אמינות', value: `${(stats.avgRel * 100).toFixed(0)}%`, sub: 'accuracy', color: '#0ea5e9' },
        ].map(({ label, value, sub, color }) => (
          <div key={label} className="bg-white rounded-2xl p-5 border border-slate-100 shadow-card">
            <div className="text-xs text-slate-400 mb-2">{label}</div>
            <div className="text-2xl font-black ltr" style={{ color }}>{value}</div>
            <div className="text-[11px] text-slate-400 mt-0.5">{sub}</div>
          </div>
        ))}
      </div>

      {/* Quick actions */}
      <div>
        <h2 className="text-sm font-bold text-slate-700 mb-3">ניווט מהיר</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {QUICK_ACTIONS.map(({ id, icon, title, desc, color, bg }) => (
            <button key={id} onClick={() => onNavigate(id)}
              className="group text-right p-4 rounded-2xl border border-slate-100 bg-white hover:shadow-elevated hover:border-slate-200 hover:-translate-y-0.5 transition-all">
              <div className="w-10 h-10 rounded-xl flex items-center justify-center text-xl mb-3 transition-transform group-hover:scale-110"
                style={{ background: bg }}>
                {icon}
              </div>
              <div className="font-semibold text-sm text-slate-800 mb-1">{title}</div>
              <div className="text-xs text-slate-400 leading-relaxed">{desc}</div>
              <div className="mt-2 text-[11px] font-semibold" style={{ color }}>פתח ←</div>
            </button>
          ))}
        </div>
      </div>

      {/* Insights row */}
      {data.length > 0 && (
        <div>
          <h2 className="text-sm font-bold text-slate-700 mb-3">תובנות מהירות</h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">

            {topProject && (
              <InsightCard
                icon="🏗️"
                title="הפרויקט המוביל"
                value={topProject[0]}
                sub={`${fmt(topProject[1] / 1000, 1)}t CO₂e`}
                onClick={() => onNavigate('dashboard')}
              />
            )}

            {topCategory && (
              <InsightCard
                icon="🧱"
                title="חומר עיקרי"
                value={topCategory[0]}
                sub={`${fmt(topCategory[1] / 1000, 1)}t CO₂e`}
                onClick={() => onNavigate('whatif')}
              />
            )}

            <InsightCard
              icon="📦"
              title="משקל כולל"
              value={`${fmt(stats.totalW / 1000, 1)}t`}
              sub="חומרים שנסרקו"
              onClick={() => onNavigate('data')}
            />
          </div>
        </div>
      )}
    </div>
  );
}

function InsightCard({ icon, title, value, sub, onClick }: {
  icon: string; title: string; value: string; sub: string; onClick: () => void;
}) {
  return (
    <button onClick={onClick}
      className="group text-right p-4 rounded-2xl bg-white border border-slate-100 shadow-card hover:shadow-elevated hover:-translate-y-0.5 transition-all w-full">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-lg">{icon}</span>
        <span className="text-xs text-slate-400 font-medium">{title}</span>
      </div>
      <div className="font-bold text-slate-800 text-sm leading-snug mb-1 truncate">{value}</div>
      <div className="text-xs text-primary font-semibold">{sub}</div>
    </button>
  );
}
