'use client';
import { useState, useMemo } from 'react';
import { ReviewRow, approveReview, rejectReview } from '../../lib/api';
import { cn } from '../../lib/utils';

interface Props { data: ReviewRow[]; onRefresh: () => void; reliabilityThreshold: number; }

export function ReviewTab({ data, onRefresh, reliabilityThreshold }: Props) {
  const [search, setSearch] = useState('');
  const [projFilter, setProjFilter] = useState('הכל');
  const [catFilter, setCatFilter] = useState('הכל');
  const [scoreFilter, setScoreFilter] = useState('הכל');
  const [loading, setLoading] = useState<string|null>(null);

  const projects = useMemo(() => ['הכל', ...Array.from(new Set(data.map(r=>r.project_name).filter(Boolean))).sort()], [data]);
  const cats = useMemo(() => ['הכל', ...Array.from(new Set(data.map(r=>r.suggested_category).filter(Boolean))).sort()], [data]);

  const filtered = useMemo(() => data.filter(r => {
    const s = search.toLowerCase();
    const matchSearch = !s || [r.short_text,r.material,r.boq_code,r.suggested_category,r.project_name].some(f=>f?.toLowerCase().includes(s));
    const matchProj = projFilter==='הכל' || r.project_name===projFilter;
    const matchCat = catFilter==='הכל' || r.suggested_category===catFilter;
    const sc = r.reliability_score||0;
    const matchScore = scoreFilter==='הכל'
      || (scoreFilter==='נמוך (<80%)'&&sc<0.8)
      || (scoreFilter==='בינוני (80-90%)'&&sc>=0.8&&sc<0.9)
      || (scoreFilter==='גבוה (>90%)'&&sc>=0.9);
    return matchSearch&&matchProj&&matchCat&&matchScore;
  }), [data, search, projFilter, catFilter, scoreFilter]);

  const handleApprove = async (id: string) => {
    setLoading(id+'-ap');
    try { await approveReview(id); onRefresh(); } catch(e) { alert('שגיאה: '+e); }
    setLoading(null);
  };
  const handleReject = async (id: string) => {
    setLoading(id+'-rj');
    try { await rejectReview(id); onRefresh(); } catch(e) { alert('שגיאה: '+e); }
    setLoading(null);
  };

  if (!data.length) return (
    <div className="bg-card border border-border rounded-xl p-12 text-center shadow-card">
      <div className="text-5xl mb-3">✅</div>
      <div className="font-semibold">אין שורות שמחכות ל-Review</div>
      <div className="text-muted-fg text-sm mt-1">כל הנתונים אושרו</div>
    </div>
  );

  const low = data.filter(r=>(r.reliability_score||0)<reliabilityThreshold);

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-card border border-border rounded-xl p-4 shadow-card">
          <div className="text-muted-fg text-xs mb-1">ממתינים לאישור</div>
          <div className="text-2xl font-bold">{data.length.toLocaleString()}</div>
        </div>
        <div className="bg-card border border-border rounded-xl p-4 shadow-card">
          <div className="text-muted-fg text-xs mb-1">מתחת לסף ({reliabilityThreshold.toFixed(2)})</div>
          <div className="text-2xl font-bold text-destructive">{low.length.toLocaleString()}</div>
        </div>
      </div>

      <div className="bg-card border border-border rounded-xl p-4 shadow-card flex flex-wrap gap-3">
        <input value={search} onChange={e=>setSearch(e.target.value)}
          placeholder="חיפוש חופשי..."
          className="flex-1 min-w-[180px] text-sm border border-border rounded-lg px-3 py-2 focus:outline-none focus:ring-1 focus:ring-primary bg-muted"/>
        <select value={projFilter} onChange={e=>setProjFilter(e.target.value)}
          className="text-sm border border-border rounded-lg px-2 py-2 bg-muted focus:outline-none">
          {projects.map(p=><option key={p}>{p}</option>)}
        </select>
        <select value={catFilter} onChange={e=>setCatFilter(e.target.value)}
          className="text-sm border border-border rounded-lg px-2 py-2 bg-muted focus:outline-none">
          {cats.map(c=><option key={c}>{c}</option>)}
        </select>
        <select value={scoreFilter} onChange={e=>setScoreFilter(e.target.value)}
          className="text-sm border border-border rounded-lg px-2 py-2 bg-muted focus:outline-none">
          {['הכל','נמוך (<80%)','בינוני (80-90%)','גבוה (>90%)'].map(s=><option key={s}>{s}</option>)}
        </select>
      </div>

      <div className="text-xs text-muted-fg">מוצגות {filtered.length.toLocaleString()} מתוך {data.length.toLocaleString()} שורות</div>

      <div className="space-y-3">
        {filtered.map(row => {
          const sc = row.reliability_score||0;
          const scoreColor = sc<0.8?'text-destructive':sc<0.9?'text-warning':'text-success';
          return (
            <div key={row.review_id} className="bg-card border border-border rounded-xl p-4 shadow-card">
              <div className="flex justify-between items-start mb-3">
                <div>
                  <div className="font-semibold">{row.short_text||row.material}</div>
                  <div className="text-xs text-muted-fg mt-0.5">{row.project_name} · {row.boq_code}</div>
                </div>
                <span className="text-xs font-bold bg-warning/10 text-warning px-2 py-1 rounded-full">דורש בדיקה</span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-3">
                {[
                  ['קטגוריה מוצעת', row.suggested_category],
                  ['יחידה מוצעת', row.suggested_uom],
                  ['ציון אמינות', (sc*100).toFixed(0)+'%'],
                  ['סיבת Review', row.review_reason],
                ].map(([label, val]) => (
                  <div key={label}>
                    <div className="text-[10px] text-muted-fg uppercase tracking-wide mb-0.5">{label}</div>
                    <div className={cn('text-sm font-medium', label==='ציון אמינות'&&scoreColor)}>{val}</div>
                  </div>
                ))}
              </div>
              <div className="flex items-center justify-between border-t border-border pt-3">
                <div className="flex gap-4 text-xs text-muted-fg">
                  {row.factor_spread_pct!=null&&<span>פיזור פקטור: <b>{row.factor_spread_pct}%</b></span>}
                  {row.climatiq_candidate_count!=null&&<span>מועמדים: <b>{row.climatiq_candidate_count}</b></span>}
                </div>
                <div className="flex gap-2">
                  <button onClick={()=>handleApprove(row.review_id)} disabled={!!loading}
                    className="text-xs font-semibold px-3 py-1.5 rounded-lg text-white hover:opacity-90 disabled:opacity-50 transition-opacity"
                    style={{background:'var(--grad-primary)'}}>
                    {loading===row.review_id+'-ap'?'..':'אשר'}
                  </button>
                  <button onClick={()=>handleReject(row.review_id)} disabled={!!loading}
                    className="text-xs font-semibold px-3 py-1.5 rounded-lg border border-border bg-card hover:bg-muted disabled:opacity-50 transition-colors">
                    {loading===row.review_id+'-rj'?'..':'דחה'}
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
