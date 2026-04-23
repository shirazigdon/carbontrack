'use client';
import { useState, useEffect, useRef } from 'react';
import { fetchProcessingStatus, ProcessingRun } from '../../lib/api';

const BACKEND = process.env.NEXT_PUBLIC_API_URL || 'https://calc-carbon-140293665526.me-west1.run.app';
const GCS_BUCKET = 'green_excal';

interface Props {
  userEmail: string;
  settings: { reliabilityThreshold: number; maxClimatiqCandidates: number; maxFactorSpreadPct: number; autoWriteAiApproved: boolean; };
}

export function UploadTab({ userEmail, settings }: Props) {
  const [project, setProject] = useState('');
  const [contractor, setContractor] = useState('');
  const [region, setRegion] = useState('מרכז');
  const [sourceMode, setSourceMode] = useState('auto');
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<{ ok: boolean; msg: string } | null>(null);
  const [run, setRun] = useState<ProcessingRun | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const loadRun = async () => {
    try {
      const { run: r } = await fetchProcessingStatus();
      setRun(r);
    } catch {}
  };

  useEffect(() => {
    loadRun();
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, []);

  const isActive = run && ['running', 'processing', 'in_progress', 'started'].includes(run.status?.toLowerCase() || '');

  useEffect(() => {
    if (isActive) {
      pollRef.current = setInterval(loadRun, 10000);
    } else {
      if (pollRef.current) clearInterval(pollRef.current);
    }
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [isActive]);

  const handleUpload = async () => {
    if (!project || !file) return;
    setUploading(true);
    setResult(null);

    // 20-minute timeout — processing a large Excel with Vertex AI can take many minutes
    const controller = new AbortController();
    const tid = setTimeout(() => controller.abort(), 20 * 60 * 1000);

    try {
      // Step 1: Upload file to GCS via backend /upload endpoint
      const fd = new FormData();
      fd.append('file', file);
      fd.append('bucket', GCS_BUCKET);
      fd.append('project_name', project);
      fd.append('contractor', contractor);
      fd.append('region', region);
      fd.append('source_mode', sourceMode);
      const uploadRes = await fetch(`${BACKEND}/upload`, { method: 'POST', body: fd, signal: controller.signal });
      if (!uploadRes.ok) throw new Error(await uploadRes.text());

      // Step 2: Trigger processing (synchronous — backend returns when done)
      const payload = {
        bucket: GCS_BUCKET,
        file: file.name,
        uploader_email: userEmail,
        project_name: project,
        contractor,
        region,
        source_mode: sourceMode,
        measurement_basis: sourceMode === 'annual_paid_2025' ? 'paid_2025' : 'boq',
        reliability_threshold: settings.reliabilityThreshold,
        max_climatiq_candidates: settings.maxClimatiqCandidates,
        max_factor_spread_pct: settings.maxFactorSpreadPct,
        auto_write_ai_approved: settings.autoWriteAiApproved,
      };
      const res = await fetch(`${BACKEND}/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: controller.signal,
      });
      const data = await res.json();
      if (!res.ok) {
        if (data.error === 'duplicate_file') {
          setResult({ ok: false, msg: 'הקובץ כבר עובד בעבר. כדי לעבד מחדש בחר "כן" בחלונית הבאה.' });
          if (confirm('הקובץ כבר קיים במאגר. האם לעבד מחדש ולדרוס?')) {
            const res2 = await fetch(`${BACKEND}/`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ ...payload, force_reprocess: true }),
              signal: controller.signal,
            });
            const data2 = await res2.json();
            if (!res2.ok) throw new Error(data2.error || 'שגיאה בעיבוד');
            setResult({ ok: true, msg: `עובדו ${(data2.total_rows || 0).toLocaleString()} שורות · ${data2.needs_review_rows || 0} לסקירה` });
          }
        } else {
          throw new Error(data.error || 'שגיאה בעיבוד');
        }
      } else {
        setResult({ ok: true, msg: `עובדו ${(data.total_rows || 0).toLocaleString()} שורות · ${data.needs_review_rows || 0} לסקירה` });
      }
      loadRun();
    } catch (e: unknown) {
      if (e instanceof Error && e.name === 'AbortError') {
        setResult({ ok: false, msg: 'פסק זמן — העיבוד לוקח יותר מ-20 דקות. בדוק שהבאקנד פועל.' });
      } else {
        setResult({ ok: false, msg: `שגיאה: ${e}` });
      }
    } finally {
      clearTimeout(tid);
      setUploading(false);
    }
  };

  const statusLabel = (s: string) => {
    const map: Record<string, string> = { running: 'בריצה', processing: 'בריצה', in_progress: 'בריצה', started: 'בריצה', completed: 'הושלם', done: 'הושלם', success: 'הושלם', failed: 'נכשל', error: 'נכשל' };
    return map[s?.toLowerCase()] || s;
  };

  const pct = run ? Math.min(100, Math.max(0, run.progress_pct ?? (run.rows_total && run.rows_total > 0 ? (run.rows_processed || 0) / run.rows_total * 100 : 0))) : 0;

  return (
    <div className="space-y-5">
      <div>
        <h2 className="font-semibold">קליטת קובץ חדש</h2>
        <p className="text-sm text-muted-fg">העלאת קובץ אקסל/CSV לחישוב פליטות פחמן אוטומטי</p>
      </div>

      {/* Processing progress */}
      {run && (
        <div className="bg-card border border-border rounded-xl p-4 shadow-card">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <span>{isActive ? '⏳' : run.status?.toLowerCase().includes('fail') || run.status?.toLowerCase().includes('error') ? '❌' : '✅'}</span>
              <div>
                <div className="font-semibold text-sm">{statusLabel(run.status || '')} {run.current_stage ? `· ${run.current_stage}` : ''}</div>
                {(run.source_file || run.file_name) && (
                  <div className="text-xs text-muted-fg">{(run.source_file || run.file_name || '').split('/').pop()}</div>
                )}
              </div>
            </div>
            <div className="text-left text-sm text-muted-fg">
              {run.rows_total ? `${(run.rows_processed || 0).toLocaleString()} / ${run.rows_total.toLocaleString()} שורות` : ''} {pct.toFixed(0)}%
            </div>
          </div>
          <div className="h-2 bg-muted rounded-full overflow-hidden">
            <div className="h-full rounded-full transition-all duration-500" style={{ width: `${pct}%`, background: 'var(--grad-primary)' }} />
          </div>
          <button onClick={loadRun} className="mt-2 text-xs text-muted-fg hover:text-primary transition-colors">רענן</button>
        </div>
      )}

      {/* Upload form */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="space-y-3">
          <div>
            <label className="text-xs text-muted-fg uppercase tracking-wide mb-1 block">שם הפרויקט *</label>
            <input value={project} onChange={e => setProject(e.target.value)}
              placeholder="לדוגמה: כביש 6 - מקטע צפון"
              className="w-full text-sm border border-border rounded-lg px-3 py-2.5 bg-muted focus:outline-none focus:ring-2 focus:ring-primary/40" />
          </div>
          <div>
            <label className="text-xs text-muted-fg uppercase tracking-wide mb-1 block">קבלן מבצע</label>
            <input value={contractor} onChange={e => setContractor(e.target.value)}
              placeholder="שם הקבלן"
              className="w-full text-sm border border-border rounded-lg px-3 py-2.5 bg-muted focus:outline-none focus:ring-2 focus:ring-primary/40" />
          </div>
        </div>
        <div className="space-y-3">
          <div>
            <label className="text-xs text-muted-fg uppercase tracking-wide mb-1 block">אזור</label>
            <select value={region} onChange={e => setRegion(e.target.value)}
              className="w-full text-sm border border-border rounded-lg px-3 py-2.5 bg-muted focus:outline-none">
              {['צפון', 'מרכז', 'דרום', 'יו"ש'].map(r => <option key={r}>{r}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-muted-fg uppercase tracking-wide mb-1 block">סוג קובץ</label>
            <select value={sourceMode} onChange={e => setSourceMode(e.target.value)}
              className="w-full text-sm border border-border rounded-lg px-3 py-2.5 bg-muted focus:outline-none">
              <option value="auto">אוטומטי</option>
              <option value="boq">כתב כמויות</option>
              <option value="annual_paid_2025">כתב שנתי 2025 / שולם בפועל</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-muted-fg uppercase tracking-wide mb-1 block">קובץ אקסל/CSV</label>
            <input type="file" accept=".xlsx,.xls,.csv"
              onChange={e => setFile(e.target.files?.[0] || null)}
              className="w-full text-sm text-muted-fg file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-primary/10 file:text-primary hover:file:bg-primary/20 cursor-pointer" />
          </div>
        </div>
      </div>

      <button onClick={handleUpload} disabled={uploading || !project || !file}
        className="w-full sm:w-auto px-6 py-3 rounded-xl text-white font-semibold disabled:opacity-50 transition-opacity hover:opacity-90 text-sm"
        style={{ background: 'var(--grad-primary)' }}>
        {uploading ? '⏳ מעלה ומעבד...' : '🚀 חשב פליטות ושמור'}
      </button>

      {result && (
        <div className={`rounded-xl p-4 text-sm font-medium ${result.ok ? 'bg-success/10 text-success border border-success/20' : 'bg-destructive/10 text-destructive border border-destructive/20'}`}>
          {result.ok ? '✅' : '❌'} {result.msg}
        </div>
      )}

      {/* Info cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {[
          { icon: '🤖', title: 'זיהוי AI', desc: 'המערכת מזהה חומרים אוטומטית ומתאימה מקדמי פליטה מ-Climatiq' },
          { icon: '🔍', title: 'Review חכם', desc: 'שורות עם ציון אמינות נמוך מועברות לבדיקה ידנית' },
          { icon: '📊', title: 'למידה מתמשכת', desc: 'כל אישור ידני מעשיר את מאגר הלמידה' },
        ].map(({ icon, title, desc }) => (
          <div key={title} className="bg-card border border-border rounded-xl p-4 shadow-card">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center text-base">{icon}</div>
              <b className="text-sm">{title}</b>
            </div>
            <p className="text-xs text-muted-fg leading-relaxed">{desc}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
