'use client';
import { useState, useMemo } from 'react';
import { EmissionRow } from '../../lib/api';
import { fmt } from '../../lib/utils';

interface Props { data: EmissionRow[]; }

const COLS: { key: keyof EmissionRow; label: string }[] = [
  { key: 'project_name', label: 'פרויקט' },
  { key: 'contractor', label: 'קבלן' },
  { key: 'region', label: 'אזור' },
  { key: 'category', label: 'קטגוריה' },
  { key: 'short_text', label: 'תיאור' },
  { key: 'weight_kg', label: 'משקל (t)' },
  { key: 'emission_co2e', label: 'פליטות (t)' },
  { key: 'reliability_score', label: 'אמינות' },
  { key: 'matched_by', label: 'שיטת התאמה' },
];

export function DataTab({ data }: Props) {
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(0);
  const pageSize = 50;

  const filtered = useMemo(() => {
    if (!search) return data;
    const s = search.toLowerCase();
    return data.filter(r =>
      [r.project_name, r.contractor, r.category, r.short_text, r.material, r.region].some(f => f?.toLowerCase().includes(s))
    );
  }, [data, search]);

  const pages = Math.ceil(filtered.length / pageSize);
  const pageData = filtered.slice(page * pageSize, (page + 1) * pageSize);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <h2 className="font-semibold">נתונים מסוננים</h2>
        <input value={search} onChange={e => { setSearch(e.target.value); setPage(0); }}
          placeholder="חיפוש..."
          className="text-sm border border-border rounded-lg px-3 py-2 bg-card focus:outline-none focus:ring-1 focus:ring-primary w-52" />
      </div>

      <div className="text-xs text-muted-fg">{filtered.length.toLocaleString()} רשומות</div>

      <div className="bg-card border border-border rounded-xl shadow-card overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="bg-muted border-b border-border">
              {COLS.map(c => (
                <th key={c.key} className="text-right px-3 py-2.5 font-semibold text-muted-fg whitespace-nowrap">{c.label}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {pageData.map((row, i) => (
              <tr key={i} className="border-b border-border/60 hover:bg-muted/40 transition-colors">
                {COLS.map(c => {
                  const val = row[c.key];
                  let display: string;
                  if (val == null) display = '—';
                  else if (c.key === 'weight_kg') display = fmt((val as number) / 1000, 1) + 't';
                  else if (c.key === 'emission_co2e') display = fmt((val as number) / 1000, 1) + 't';
                  else if (c.key === 'reliability_score') display = ((val as number) * 100).toFixed(0) + '%';
                  else display = String(val);
                  return (
                    <td key={c.key} className="px-3 py-2 whitespace-nowrap max-w-[200px] truncate text-gray-700">{display}</td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {pages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <button onClick={() => setPage(p => Math.max(0, p - 1))} disabled={page === 0}
            className="text-xs px-3 py-1.5 rounded-lg border border-border disabled:opacity-40 hover:bg-muted transition-colors">
            הקודם
          </button>
          <span className="text-xs text-muted-fg">{page + 1} / {pages}</span>
          <button onClick={() => setPage(p => Math.min(pages - 1, p + 1))} disabled={page === pages - 1}
            className="text-xs px-3 py-1.5 rounded-lg border border-border disabled:opacity-40 hover:bg-muted transition-colors">
            הבא
          </button>
        </div>
      )}
    </div>
  );
}
