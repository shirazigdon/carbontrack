'use client';
import { useState, useMemo } from 'react';
import { EmissionRow } from '../../lib/api';
import { fmt } from '../../lib/utils';

interface Props { data: EmissionRow[]; }

type SortDir = 'asc' | 'desc';
interface SortState { key: keyof EmissionRow; dir: SortDir }

const COLS: { key: keyof EmissionRow; label: string; numeric?: boolean }[] = [
  { key: 'project_name',      label: 'פרויקט' },
  { key: 'contractor',        label: 'קבלן' },
  { key: 'region',            label: 'אזור' },
  { key: 'year',              label: 'שנה',              numeric: true },
  { key: 'scope',             label: 'Scope' },
  { key: 'category',          label: 'קטגוריה' },
  { key: 'short_text',        label: 'תיאור' },
  { key: 'weight_kg',         label: 'משקל (t)',          numeric: true },
  { key: 'emission_co2e',     label: 'פליטות (t CO₂e)',  numeric: true },
  { key: 'reliability_score', label: 'אמינות',            numeric: true },
  { key: 'reliability_status',label: 'סטטוס' },
  { key: 'matched_by',        label: 'שיטת התאמה' },
];

const EXPORT_EXTRA_COLS: { key: keyof EmissionRow; label: string }[] = [
  { key: 'conversion_assumption', label: 'הנחת המרה' },
  { key: 'measurement_year',      label: 'שנת מדידה' },
];

const ALL_EXPORT_COLS = [...COLS, ...EXPORT_EXTRA_COLS];

const STATUS_LABELS: Record<string, string> = {
  auto_approved:    '✓ אושר',
  review_required:  '⚠ לבדיקה',
  rejected:         '✗ נדחה',
};
const STATUS_COLORS: Record<string, string> = {
  auto_approved:   'text-green-700',
  review_required: 'text-amber-700',
  rejected:        'text-red-700',
};

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

function distinct<T>(arr: T[]): T[] {
  return Array.from(new Set(arr)).filter(v => v != null && v !== '') as T[];
}

export function DataTab({ data }: Props) {
  const [search, setSearch]             = useState('');
  const [yearFilter, setYearFilter]     = useState('');
  const [projectFilter, setProject]     = useState('');
  const [contractorFilter, setContractor] = useState('');
  const [categoryFilter, setCategory]   = useState('');
  const [statusFilter, setStatus]       = useState('');
  const [sort, setSort]                 = useState<SortState>({ key: 'emission_co2e', dir: 'desc' });
  const [page, setPage]                 = useState(0);
  const pageSize = 50;

  const years       = useMemo(() => distinct(data.map(r => r.year)).sort((a, b) => (b as number) - (a as number)), [data]);
  const projects    = useMemo(() => distinct(data.map(r => r.project_name)).sort(), [data]);
  const contractors = useMemo(() => distinct(data.map(r => r.contractor)).sort(), [data]);
  const categories  = useMemo(() => distinct(data.map(r => r.category)).sort(), [data]);

  const hasFilters = yearFilter || projectFilter || contractorFilter || categoryFilter || statusFilter || search;

  function resetFilters() {
    setYearFilter(''); setProject(''); setContractor('');
    setCategory(''); setStatus(''); setSearch(''); setPage(0);
  }

  function toggleSort(key: keyof EmissionRow) {
    setSort(s => s.key === key ? { key, dir: s.dir === 'asc' ? 'desc' : 'asc' } : { key, dir: 'desc' });
    setPage(0);
  }

  const filtered = useMemo(() => {
    let rows = data;
    if (yearFilter)       rows = rows.filter(r => String(r.year) === yearFilter);
    if (projectFilter)    rows = rows.filter(r => r.project_name === projectFilter);
    if (contractorFilter) rows = rows.filter(r => r.contractor === contractorFilter);
    if (categoryFilter)   rows = rows.filter(r => r.category === categoryFilter);
    if (statusFilter)     rows = rows.filter(r => r.reliability_status === statusFilter);
    if (search) {
      const s = search.toLowerCase();
      rows = rows.filter(r =>
        [r.project_name, r.contractor, r.category, r.short_text, r.material, r.region]
          .some(f => f?.toLowerCase().includes(s))
      );
    }
    return rows;
  }, [data, yearFilter, projectFilter, contractorFilter, categoryFilter, statusFilter, search]);

  const sorted = useMemo(() => {
    const { key, dir } = sort;
    return [...filtered].sort((a, b) => {
      const av = a[key] ?? '';
      const bv = b[key] ?? '';
      const cmp = typeof av === 'number' && typeof bv === 'number'
        ? av - bv
        : String(av).localeCompare(String(bv), 'he');
      return dir === 'asc' ? cmp : -cmp;
    });
  }, [filtered, sort]);

  const pages    = Math.ceil(sorted.length / pageSize);
  const pageData = sorted.slice(page * pageSize, (page + 1) * pageSize);

  const totalEmission = useMemo(
    () => filtered.reduce((s, r) => s + (r.emission_co2e ?? 0), 0) / 1000,
    [filtered]
  );

  const selectCls = "text-sm border border-border rounded-lg px-2 py-1.5 bg-card focus:outline-none focus:ring-1 focus:ring-primary";

  return (
    <div className="space-y-4">
      {/* ── Header row ── */}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <h2 className="font-semibold text-slate-800">נתונים גולמיים</h2>
        <div className="flex items-center gap-2">
          <button onClick={() => exportCSV(sorted)}
            className="flex items-center gap-1 text-sm px-3 py-1.5 rounded-lg border border-border bg-white hover:bg-muted transition-colors font-medium text-slate-700">
            ⬇ CSV
          </button>
          <button onClick={() => exportExcel(sorted)}
            className="flex items-center gap-1 text-sm px-3 py-1.5 rounded-lg border border-border bg-white hover:bg-muted transition-colors font-medium text-slate-700">
            ⬇ Excel
          </button>
        </div>
      </div>

      {/* ── Filters ── */}
      <div className="bg-muted/50 border border-border rounded-xl p-3 flex flex-wrap gap-2 items-end">
        {/* Project */}
        <div className="flex flex-col gap-0.5">
          <label className="text-[11px] text-muted-fg font-medium">פרויקט</label>
          <select value={projectFilter} onChange={e => { setProject(e.target.value); setPage(0); }} className={selectCls}>
            <option value="">הכל</option>
            {projects.map(p => <option key={p} value={String(p)}>{p}</option>)}
          </select>
        </div>

        {/* Contractor */}
        <div className="flex flex-col gap-0.5">
          <label className="text-[11px] text-muted-fg font-medium">קבלן</label>
          <select value={contractorFilter} onChange={e => { setContractor(e.target.value); setPage(0); }} className={selectCls}>
            <option value="">הכל</option>
            {contractors.map(c => <option key={c} value={String(c)}>{c}</option>)}
          </select>
        </div>

        {/* Category */}
        <div className="flex flex-col gap-0.5">
          <label className="text-[11px] text-muted-fg font-medium">קטגוריה</label>
          <select value={categoryFilter} onChange={e => { setCategory(e.target.value); setPage(0); }} className={selectCls}>
            <option value="">הכל</option>
            {categories.map(c => <option key={c} value={String(c)}>{c}</option>)}
          </select>
        </div>

        {/* Year */}
        <div className="flex flex-col gap-0.5">
          <label className="text-[11px] text-muted-fg font-medium">שנה</label>
          <select value={yearFilter} onChange={e => { setYearFilter(e.target.value); setPage(0); }} className={selectCls}>
            <option value="">הכל</option>
            {years.map(y => <option key={y} value={String(y)}>{y}</option>)}
          </select>
        </div>

        {/* Status */}
        <div className="flex flex-col gap-0.5">
          <label className="text-[11px] text-muted-fg font-medium">סטטוס</label>
          <select value={statusFilter} onChange={e => { setStatus(e.target.value); setPage(0); }} className={selectCls}>
            <option value="">הכל</option>
            <option value="auto_approved">✓ אושר</option>
            <option value="review_required">⚠ לבדיקה</option>
            <option value="rejected">✗ נדחה</option>
          </select>
        </div>

        {/* Free search */}
        <div className="flex flex-col gap-0.5">
          <label className="text-[11px] text-muted-fg font-medium">חיפוש חופשי</label>
          <input value={search} onChange={e => { setSearch(e.target.value); setPage(0); }}
            placeholder="חיפוש..."
            className={`${selectCls} w-36`} />
        </div>

        {/* Reset */}
        {hasFilters && (
          <button onClick={resetFilters}
            className="self-end text-xs px-2.5 py-1.5 rounded-lg border border-border bg-white hover:bg-red-50 hover:border-red-300 hover:text-red-700 transition-colors text-slate-600">
            ✕ נקה
          </button>
        )}
      </div>

      {/* ── Summary strip ── */}
      <div className="flex items-center gap-4 text-xs text-muted-fg">
        <span>{filtered.length.toLocaleString()} רשומות</span>
        <span className="text-slate-700 font-medium">
          סה״כ פליטות: {fmt(totalEmission, 1)} t CO₂e
        </span>
      </div>

      {/* ── Table ── */}
      <div className="bg-card border border-border rounded-xl shadow-card overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="bg-muted border-b border-border">
              {COLS.map(c => {
                const isSorted = sort.key === c.key;
                return (
                  <th key={c.key}
                    onClick={() => toggleSort(c.key)}
                    className="text-right px-3 py-2.5 font-semibold text-muted-fg whitespace-nowrap cursor-pointer select-none hover:text-slate-700 transition-colors">
                    <span className="inline-flex items-center gap-1">
                      {c.label}
                      <span className={`text-[10px] ${isSorted ? 'text-primary' : 'text-border'}`}>
                        {isSorted ? (sort.dir === 'desc' ? '▼' : '▲') : '⇅'}
                      </span>
                    </span>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {pageData.map((row, i) => (
              <tr key={i} className="border-b border-border/60 hover:bg-muted/40 transition-colors">
                {COLS.map(c => {
                  const val = row[c.key];
                  let display: string;
                  let cls = '';
                  if (val == null) {
                    display = '—';
                  } else if (c.key === 'weight_kg') {
                    display = fmt((val as number) / 1000, 1) + 't';
                  } else if (c.key === 'emission_co2e') {
                    display = fmt((val as number) / 1000, 1) + 't';
                  } else if (c.key === 'reliability_score') {
                    display = ((val as number) * 100).toFixed(0) + '%';
                  } else if (c.key === 'reliability_status') {
                    const s = String(val);
                    display = STATUS_LABELS[s] ?? s;
                    cls = STATUS_COLORS[s] ?? '';
                  } else {
                    display = String(val);
                  }
                  return (
                    <td key={c.key} title={display}
                      className={`px-3 py-2 whitespace-nowrap max-w-[200px] truncate text-gray-700 ${cls}`}>
                      {display}
                    </td>
                  );
                })}
              </tr>
            ))}
            {pageData.length === 0 && (
              <tr>
                <td colSpan={COLS.length} className="text-center py-10 text-muted-fg">
                  אין נתונים התואמים את הסינון
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* ── Pagination ── */}
      {pages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <button onClick={() => setPage(0)} disabled={page === 0}
            className="text-xs px-2 py-1.5 rounded-lg border border-border disabled:opacity-40 hover:bg-muted transition-colors">
            «
          </button>
          <button onClick={() => setPage(p => Math.max(0, p - 1))} disabled={page === 0}
            className="text-xs px-3 py-1.5 rounded-lg border border-border disabled:opacity-40 hover:bg-muted transition-colors">
            הקודם
          </button>
          <span className="text-xs text-muted-fg">{page + 1} / {pages}</span>
          <button onClick={() => setPage(p => Math.min(pages - 1, p + 1))} disabled={page === pages - 1}
            className="text-xs px-3 py-1.5 rounded-lg border border-border disabled:opacity-40 hover:bg-muted transition-colors">
            הבא
          </button>
          <button onClick={() => setPage(pages - 1)} disabled={page === pages - 1}
            className="text-xs px-2 py-1.5 rounded-lg border border-border disabled:opacity-40 hover:bg-muted transition-colors">
            »
          </button>
        </div>
      )}
    </div>
  );
}
