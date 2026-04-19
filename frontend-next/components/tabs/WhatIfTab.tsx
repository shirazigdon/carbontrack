'use client';
import { useState, useMemo } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { EmissionRow } from '../../lib/api';
import { suggestAlternatives, fmt, cn } from '../../lib/utils';
import { KpiCard } from '../KpiCard';

interface Props { data: EmissionRow[]; }

export function WhatIfTab({ data }: Props) {
  const allCats = useMemo(() => Array.from(new Set(data.map(r => r.category).filter(Boolean))).sort() as string[], [data]);
  const [src, setSrc] = useState(allCats[0] || '');
  const [chosenAlt, setChosenAlt] = useState('');

  const srcRows = useMemo(() => data.filter(r => r.category === src), [data, src]);
  const currW = srcRows.reduce((s, r) => s + (r.weight_kg || 0), 0);
  const currE = srcRows.reduce((s, r) => s + (r.emission_co2e || 0), 0);
  const srcFactor = currW > 0 ? currE / currW : 0;
  const [qty, setQty] = useState(Math.max(currW, 1000));

  const alts = useMemo(() => {
    const suggestions = suggestAlternatives(src, allCats);
    return suggestions.map(([cat, reason]) => {
      const sub = data.filter(r => r.category === cat);
      const w = sub.reduce((s, r) => s + (r.weight_kg || 0), 0);
      const e = sub.reduce((s, r) => s + (r.emission_co2e || 0), 0);
      const f: number | null = w > 0 ? e / w : null;
      return { cat, reason, factor: f };
    }).sort((a, b) => (a.factor == null ? 1 : 0) - (b.factor == null ? 1 : 0) || (a.factor || 9999) - (b.factor || 9999));
  }, [src, allCats, data]);

  const effectiveAlt = chosenAlt || alts[0]?.cat || '';
  const altRows = data.filter(r => r.category === effectiveAlt);
  const altW = altRows.reduce((s, r) => s + (r.weight_kg || 0), 0);
  const altE = altRows.reduce((s, r) => s + (r.emission_co2e || 0), 0);
  const altFactor = altW > 0 ? altE / altW : 0;
  const projE = qty * altFactor;
  const diff = currE - projE;

  const chartData = [
    { name: src, value: currE / 1000 },
    ...alts.slice(0, 3).filter(a => a.factor != null).map(a => ({
      name: a.cat, value: qty * (a.factor as number) / 1000,
    })),
  ];

  const colors = ['hsl(150,25%,55%)', 'hsl(142,55%,35%)', 'hsl(85,50%,45%)', 'hsl(195,70%,45%)'];
  const sensitivityRows = [70, 85, 100, 115, 130].map(pct => ({
    pct: `${pct}%`,
    qty: fmt(qty * pct / 100 / 1000),
    emission: fmt(qty * pct / 100 * altFactor / 1000, 1),
    saving: `${diff >= 0 ? '+' : ''}${fmt((currE - qty * pct / 100 * altFactor) / 1000, 1)}`,
    isBase: pct === 100,
  }));

  return (
    <div className="space-y-5">
      <div>
        <h2 className="font-semibold">סימולטור חלופות חומרים (What-If)</h2>
        <p className="text-sm text-muted-fg">בחר חומר קיים — המערכת תציע חלופות הנדסיות חכמות</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        <div className="lg:col-span-2 space-y-3">
          <div className="bg-card border border-border rounded-xl p-4 shadow-card">
            <div className="text-xs font-bold text-muted-fg uppercase tracking-wide mb-2">חומר קיים</div>
            <select value={src} onChange={e => { setSrc(e.target.value); setChosenAlt(''); }}
              className="w-full text-sm border border-border rounded-lg px-3 py-2 bg-muted focus:outline-none mb-3">
              {allCats.map(c => <option key={c}>{c}</option>)}
            </select>
            <div className="text-2xl font-bold">{fmt(currE / 1000, 1)}<span className="text-sm font-normal text-muted-fg ml-1">t CO₂e</span></div>
            <div className="text-xs text-muted-fg mt-1">{fmt(currW / 1000)}t חומר · פקטור {srcFactor.toFixed(4)}</div>
          </div>
          <div className="bg-card border border-border rounded-xl p-4 shadow-card">
            <div className="text-xs font-bold text-muted-fg uppercase tracking-wide mb-2">כמות חלופית (ק&quot;ג)</div>
            <input type="number" value={qty} onChange={e => setQty(Number(e.target.value))}
              className="w-full text-sm border border-border rounded-lg px-3 py-2 bg-muted focus:outline-none"
              min={0} step={1000} />
          </div>
        </div>

        <div className="lg:col-span-3 bg-card border border-border rounded-xl p-4 shadow-card">
          <div className="text-xs font-bold text-muted-fg uppercase tracking-wide mb-3">חלופות הנדסיות מומלצות</div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 mb-3">
            {alts.slice(0, 3).map(({ cat, reason, factor }) => {
              const delta = factor != null ? factor - srcFactor : null;
              const isSelected = (chosenAlt || alts[0]?.cat) === cat;
              const pctDelta = delta != null && srcFactor > 0 ? Math.abs(delta / srcFactor * 100) : 0;
              return (
                <button key={cat} onClick={() => setChosenAlt(cat)}
                  className={cn('text-right p-3 rounded-xl border-2 transition-all',
                    isSelected ? 'border-primary/70 bg-primary/5' : 'border-border hover:border-primary/40')}>
                  <div className="font-semibold text-xs mb-1">{cat}</div>
                  <div className="text-[10px] text-muted-fg leading-relaxed mb-2">{reason}</div>
                  {factor != null ? (
                    <div className="text-[10px] flex items-center gap-1">
                      <span className="font-mono">{factor.toFixed(4)}</span>
                      {delta != null && (
                        <span className={cn('font-bold px-1 rounded', delta < 0 ? 'text-success bg-success/10' : 'text-destructive bg-destructive/10')}>
                          {delta < 0 ? '↓' : '↑'}{pctDelta.toFixed(0)}%
                        </span>
                      )}
                    </div>
                  ) : <div className="text-[10px] text-muted-fg">אין נתון במאגר</div>}
                </button>
              );
            })}
          </div>
          <details className="text-xs">
            <summary className="cursor-pointer text-muted-fg hover:text-gray-700">בחירה ידנית מכל הקטגוריות</summary>
            <select value={effectiveAlt} onChange={e => setChosenAlt(e.target.value)}
              className="mt-2 w-full text-sm border border-border rounded-lg px-3 py-2 bg-muted focus:outline-none">
              {allCats.map(c => <option key={c}>{c}</option>)}
            </select>
          </details>
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard title="פליטה נוכחית" value={`${fmt(currE / 1000, 1)}t`} subtitle={`CO₂e · ${fmt(currW / 1000)}t חומר`} />
        <KpiCard title="פקטור חלופה" value={altFactor.toFixed(4)} subtitle="kg CO₂e / kg חומר" />
        <KpiCard title="פליטה חלופית" value={`${fmt(projE / 1000, 1)}t`} subtitle={`CO₂e · ${effectiveAlt}`} variant="primary" />
        {diff > 0
          ? <KpiCard title="חיסכון" value={`${fmt(diff / 1000, 1)}t`} subtitle={`↓ ${currE > 0 ? (diff / currE * 100).toFixed(1) : 0}% פחות פחמן`} variant="accent" />
          : diff < 0
            ? <KpiCard title="תוספת פחמן" value={`${fmt(Math.abs(diff) / 1000, 1)}t`} subtitle={`↑ ${currE > 0 ? (Math.abs(diff) / currE * 100).toFixed(1) : 0}% יותר`} />
            : <KpiCard title="אין שינוי" value="0t" subtitle="פליטות זהות" />}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 bg-card border border-border rounded-xl p-5 shadow-card">
          <div className="font-semibold text-sm mb-4">השוואה ויזואלית</div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={chartData} margin={{ top: 16, right: 16, left: 0, bottom: 4 }}>
              <XAxis dataKey="name" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 11 }} tickFormatter={v => `${fmt(v)}`} />
              <Tooltip formatter={(v) => [`${fmt(Number(v), 1)}t CO₂e`, '']} contentStyle={{ fontFamily: 'Heebo', fontSize: 11 }} />
              <Bar dataKey="value" radius={[4, 4, 0, 0]}
                label={{ position: 'top', fontSize: 9, formatter: (v: unknown) => `${fmt(Number(v), 1)}t` }}>
                {chartData.map((_, i) => (
                  <Cell key={i} fill={colors[i % colors.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="bg-card border border-border rounded-xl p-5 shadow-card">
          <div className="font-semibold text-sm mb-1">ניתוח רגישות</div>
          <div className="text-xs text-muted-fg mb-3">חלופה: {effectiveAlt}</div>
          <table className="w-full text-xs">
            <thead>
              <tr className="text-muted-fg text-[10px] uppercase">
                <th className="text-right pb-2">כמות</th><th className="text-right pb-2">(t)</th>
                <th className="text-right pb-2">פליטה</th><th className="text-right pb-2">חיסכון</th>
              </tr>
            </thead>
            <tbody>
              {sensitivityRows.map(r => (
                <tr key={r.pct} className={cn('border-t border-border', r.isBase && 'bg-primary/5 font-semibold')}>
                  <td className="py-1.5">{r.pct}</td><td>{r.qty}</td>
                  <td>{r.emission}t</td>
                  <td className={cn(r.saving.startsWith('+') ? 'text-success' : 'text-destructive')}>{r.saving}t</td>
                </tr>
              ))}
            </tbody>
          </table>
          {altFactor > 0 && <div className="text-xs text-muted-fg mt-3">שווי כלכלי ETS: ${fmt(diff / 1000 * 25)}</div>}
        </div>
      </div>
    </div>
  );
}
