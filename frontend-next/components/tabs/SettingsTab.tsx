'use client';
import { useState } from 'react';
import { deleteProject } from '../../lib/api';

interface Settings {
  reliabilityThreshold: number;
  maxClimatiqCandidates: number;
  maxFactorSpreadPct: number;
  autoWriteAiApproved: boolean;
}

interface Props {
  settings: Settings;
  onSettingsChange: (s: Settings) => void;
  projects: string[];
  onProjectDeleted: () => void;
}

export function SettingsTab({ settings, onSettingsChange, projects, onProjectDeleted }: Props) {
  const [local, setLocal] = useState(settings);
  const [saved, setSaved] = useState(false);
  const [delProject, setDelProject] = useState('');
  const [confirmDel, setConfirmDel] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [delMsg, setDelMsg] = useState<{ ok: boolean; msg: string } | null>(null);

  const [catMat, setCatMat] = useState('');
  const [catFactor, setCatFactor] = useState('');
  const [uEmail, setUEmail] = useState('');
  const [uName, setUName] = useState('');
  const [uRole, setURole] = useState('הנהלה');

  const save = () => {
    onSettingsChange(local);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const handleDelete = async () => {
    if (!delProject) return;
    setDeleting(true);
    try {
      await deleteProject(delProject);
      setDelMsg({ ok: true, msg: `הפרויקט "${delProject}" נמחק` });
      setDelProject('');
      setConfirmDel(false);
      onProjectDeleted();
    } catch (e) {
      setDelMsg({ ok: false, msg: `שגיאה: ${e}` });
    }
    setDeleting(false);
  };

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Thresholds */}
        <div className="bg-card border border-border rounded-xl p-5 shadow-card space-y-4">
          <h3 className="font-semibold text-sm">ספים ופרמטרים</h3>
          {[
            { label: 'סף אמינות לאישור אוטומטי', key: 'reliabilityThreshold' as const, min: 0.5, max: 0.99, step: 0.01 },
            { label: 'מקסימום תוצאות Climatiq', key: 'maxClimatiqCandidates' as const, min: 1, max: 20, step: 1 },
            { label: 'סטיית פקטור מותרת (%)', key: 'maxFactorSpreadPct' as const, min: 1, max: 100, step: 1 },
          ].map(({ label, key, min, max, step }) => (
            <div key={key}>
              <label className="text-xs text-muted-fg uppercase tracking-wide mb-1 block">{label}</label>
              <div className="flex items-center gap-3">
                <input type="number" value={local[key]} min={min} max={max} step={step}
                  onChange={e => setLocal(prev => ({ ...prev, [key]: Number(e.target.value) }))}
                  className="w-24 text-sm border border-border rounded-lg px-2 py-1.5 bg-muted focus:outline-none" />
                <input type="range" value={local[key]} min={min} max={max} step={step}
                  onChange={e => setLocal(prev => ({ ...prev, [key]: Number(e.target.value) }))}
                  className="flex-1 accent-primary" />
              </div>
            </div>
          ))}
          <div className="flex items-center gap-2">
            <input type="checkbox" id="autoWrite" checked={local.autoWriteAiApproved}
              onChange={e => setLocal(prev => ({ ...prev, autoWriteAiApproved: e.target.checked }))}
              className="accent-primary" />
            <label htmlFor="autoWrite" className="text-sm cursor-pointer">כתיבה אוטומטית לטבלאות</label>
          </div>
          <button onClick={save}
            className="px-5 py-2 rounded-lg text-white text-sm font-semibold transition-opacity hover:opacity-90"
            style={{ background: 'var(--grad-primary)' }}>
            {saved ? '✅ נשמר' : 'שמור הגדרות'}
          </button>
        </div>

        {/* Catalog + User */}
        <div className="space-y-4">
          <div className="bg-card border border-border rounded-xl p-5 shadow-card space-y-3">
            <h3 className="font-semibold text-sm">קטלוג חברה / רגולטור</h3>
            <div>
              <label className="text-xs text-muted-fg uppercase tracking-wide mb-1 block">שם חומר/סעיף</label>
              <input value={catMat} onChange={e => setCatMat(e.target.value)} placeholder="לדוגמה: בטון B30"
                className="w-full text-sm border border-border rounded-lg px-3 py-2 bg-muted focus:outline-none" />
            </div>
            <div>
              <label className="text-xs text-muted-fg uppercase tracking-wide mb-1 block">מקדם פליטה</label>
              <input type="number" value={catFactor} onChange={e => setCatFactor(e.target.value)} step={0.0001}
                className="w-full text-sm border border-border rounded-lg px-3 py-2 bg-muted focus:outline-none" />
            </div>
            <button onClick={() => { setCatMat(''); setCatFactor(''); alert('נשמר לקטלוג'); }}
              className="text-sm px-4 py-2 rounded-lg border border-border hover:bg-muted transition-colors">
              שמור לקטלוג
            </button>
          </div>

          <div className="bg-card border border-border rounded-xl p-5 shadow-card space-y-3">
            <h3 className="font-semibold text-sm">הוספת משתמש</h3>
            {[
              { label: 'אימייל', val: uEmail, set: setUEmail, placeholder: 'user@company.com' },
              { label: 'שם מלא', val: uName, set: setUName, placeholder: 'ישראל ישראלי' },
            ].map(({ label, val, set, placeholder }) => (
              <div key={label}>
                <label className="text-xs text-muted-fg uppercase tracking-wide mb-1 block">{label}</label>
                <input value={val} onChange={e => set(e.target.value)} placeholder={placeholder}
                  className="w-full text-sm border border-border rounded-lg px-3 py-2 bg-muted focus:outline-none" />
              </div>
            ))}
            <div>
              <label className="text-xs text-muted-fg uppercase tracking-wide mb-1 block">תפקיד</label>
              <select value={uRole} onChange={e => setURole(e.target.value)}
                className="w-full text-sm border border-border rounded-lg px-3 py-2 bg-muted focus:outline-none">
                {['הנהלה', 'מנהל פרויקט', 'קיימות (ESG)', 'רגולטור'].map(r => <option key={r}>{r}</option>)}
              </select>
            </div>
            <button onClick={() => { setUEmail(''); setUName(''); alert('משתמש נשמר'); }}
              className="text-sm px-4 py-2 rounded-lg border border-border hover:bg-muted transition-colors">
              שמור משתמש
            </button>
          </div>
        </div>
      </div>

      {/* Delete project */}
      <div className="bg-card border border-destructive/20 rounded-xl p-5 shadow-card">
        <h3 className="font-semibold text-sm text-destructive mb-3">מחיקת פרויקט</h3>
        <div className="flex gap-3 items-center flex-wrap">
          <select value={delProject} onChange={e => { setDelProject(e.target.value); setConfirmDel(false); setDelMsg(null); }}
            className="text-sm border border-border rounded-lg px-3 py-2 bg-muted focus:outline-none">
            <option value="">בחר פרויקט למחיקה</option>
            {projects.map(p => <option key={p}>{p}</option>)}
          </select>
          {delProject && !confirmDel && (
            <button onClick={() => setConfirmDel(true)}
              className="text-sm px-4 py-2 rounded-lg bg-destructive/10 text-destructive border border-destructive/20 hover:bg-destructive/20 transition-colors">
              מחק את {delProject}
            </button>
          )}
          {confirmDel && (
            <div className="flex items-center gap-2">
              <span className="text-xs text-destructive font-medium">האם בטוח?</span>
              <button onClick={handleDelete} disabled={deleting}
                className="text-sm px-4 py-2 rounded-lg bg-destructive text-white hover:opacity-90 disabled:opacity-50">
                {deleting ? 'מוחק...' : 'כן, מחק'}
              </button>
              <button onClick={() => setConfirmDel(false)}
                className="text-sm px-3 py-2 rounded-lg border border-border hover:bg-muted">
                ביטול
              </button>
            </div>
          )}
        </div>
        {delMsg && (
          <div className={`mt-3 text-sm ${delMsg.ok ? 'text-success' : 'text-destructive'}`}>{delMsg.msg}</div>
        )}
      </div>
    </div>
  );
}
