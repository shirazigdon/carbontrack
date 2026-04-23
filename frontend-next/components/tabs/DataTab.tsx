'use client';
import { useState, useMemo } from 'react';
import { EmissionRow } from '../../lib/api';
import { fmt } from '../../lib/utils';

interface Props { data: EmissionRow[]; }

const COLS: { key: keyof EmissionRow; label: string }[] = [
  { key: 'project_name',      label: 'פרויקט' },
  { key: 'contractor',        label: 'קבלן' },
  { key: 'region',            label: 'אזור' },
  { key: 'year',              label: 'שנה' },
  { key: 'scope',             label: 'Scope' },
  { key: 'category',          label: 'קטגוריה' },
  { key: 'short_text',        label: 'תיאור' },
  { key: 'weight_kg',         label: 'משקל (t)' },
  { key: 'emission_co2e',     label: 'פליטות (t CO₂e)' },
  { key: 'reliability_score', label: 'אמינות' },
  { key: 'reliability_status',label: 'סטטוס' },
  { key: 'matched_by',        label: 'שיטת התאמה' },
];

// Extra columns included in CSV/Excel export but not shown in the table
const EXPORT_EXTRA_COLS: { key: keyof EmissionRow; label: string }[] = [
  { key: 'conversion_assumption', label: 'הנחת המרה' },
  { key: 'measurement_year',      label: 'שנת מדידה' },
];

const ALL_EXPORT_COLS = [...COLS, ...EXPORT_EXTRA_COLS];

function formatCell(c: { key: keyof EmissionRow }, r: EmissionRow): string {
  const v = r[c.key];
  if (v == null) return '';
  if (c.key === 'weight_kg' || c.key === 'emission_co2e') return ((v as number) / 1000).toFixed(3);
  if (c.key === 'reliability_score') return ((v as number) * 100).toFixed(1);
  return String(v);
}

function exportCSV(rows: EmissionRow[]) {
  const header = ALL_EXPORT_COLS.map(c => `"${c.label}"`).join(',');
  const body = rows.map(r =>
    ALL_EXPORT_COLS.map(c => {
      const s = formatCell(c, r);
      return s ? `"${s.replace(/"/g, '""')}"` : '';
    }).join(',')
  ).join('\n');
  const blob = new Blob(['﻿' + header + '\n' + body], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a'); a.href = url; a.download = 'carbontrack-data.csv'; a.click();
  URL.revokeObjectURL(url);
}

function exportExcel(rows: EmissionRow[]) {
  const header = ALL_EXPORT_COLS.map(c => c.label).join('\t');
  const body = rows.map(r =>
    ALL_EXPORT_COLS.map(c => formatCell(c, r)).join('\t')
  ).join('\n');
  const blob = new Blob(['﻿' + header + '\n' + body], { type: 'application/vnd.ms-excel;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a'); a.href = url; a.download = 'carbontrack-data.xls'; a.click();
  URL.revokeObjectURL(url);
}

export function DataTab({ data }: Props) {
  const [search, setSearch] = useState('');
  const [yearFilter, setYearFilter] = useState('');
  const [page, setPage] = useState(0);
  const pageSize = 50;

  const years = useMemo(() => {
    const s = new Set(data.map(r => r.year).filter(Boolean));
    return Array.from(s).sort((a, b) => (b as number) - (a as number));
  }, [data]);

  const filtered = useMemo(() => {
    let rows = data;
    if (yearFilter) rows = rows.filter(r => String(r.year) === yearFilter);
    if (search) {
      const s = search.toLowerCase();
      rows = rows.filter(r =>
        [r.project_name, r.contractor, r.category, r.short_text, r.material, r.region]
          .some(f => f?.toLowerCase().includes(s))
      );
    }
    return rows;
  }, [data, search, yearFilter]);

  const pages = Math.ceil(filtered.length / pageSize);
  const pageData = filtered.slice(page * pageSize, (page + 1) * pageSize);

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <h2 className="font-semibold text-slate-800">נתונים גולמיים</h2>
        <div className="flex items-center gap-2 flex-wrap">
          {/* Year filter */}
          <select
            value={yearFilter}
            onChange={e => { setYearFilter(e.target.value); setPage(0); }}
            className="text-sm border border-border rounded-lg px-3 py-2 bg-card focus:outline-none focus:ring-1 focus:ring-primary"
          >
            <option value="">כל השנים</option>
            {years.map(y => <option key={y} value={String(y)}>{y}</option>)}
          </select>

          {/* Search */}
          <input
            value={search}
            onChange={e => { setSearch(e.target.value); setPage(0); }}
            placeholder="חיפוש..."
            className="text-sm border border-border rounded-lg px-3 py-2 bg-card focus:outline-none focus:ring-1 focus:ring-primary w-44"
          />

          {/* Export buttons */}
          <button
            onClick={() => exportCSV(filtered)}
            className="flex items-center gap-1.5 text-sm px-3 py-2 rounded-lg border border-border bg-white hover:bg-muted transition-colors font-medium text-slate-700"
          >
            ⬇ CSV
          </button>
          <button
            onClick={() => exportExcel(filtered)}
            className="flex items-center gap-1.5 text-sm px-3 py-2 rounded-lg border border-border bg-white hover:bg-muted transition-colors font-medium text-slate-700"
          >
            ⬇ Excel
          </button>
        </div>
      </div>

      <div className="text-xs text-muted-fg">{filtered.length.toLocaleString()} רשומות</div>

      {/* Table */}
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
                  let extra = '';
                  if (val == null)                    display = '—';
                  else if (c.key === 'weight_kg')     display = fmt((val as number) / 1000, 1) + 't';
                  else if (c.key === 'emission_co2e') display = fmt((val as number) / 1000, 1) + 't';
                  else if (c.key === 'reliability_score') display = ((val as number) * 100).toFixed(0) + '%';
                  else if (c.key === 'reliability_status') {
                    const s = String(val);
                    display = s === 'auto_approved' ? '✓ אושר' : s === 'review_required' ? '⚠ לבדיקה' : s === 'rejected' ? '✗ נדחה' : s;
                    extra = s === 'auto_approved' ? 'text-green-700' : s === 'review_required' ? 'text-amber-700' : s === 'rejected' ? 'text-red-700' : '';
                  }
                  else display = String(val);
                  return (
                    <td key={c.key} className={`px-3 py-2 whitespace-nowrap max-w-[200px] truncate text-gray-700 ${extra}`}>{display}</td>
                  );
                })}
              </tr>
            ))}
            {pageData.length === 0 && (
              <tr><td colSpan={COLS.length} className="text-center py-10 text-muted-fg">אין נתונים</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
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
