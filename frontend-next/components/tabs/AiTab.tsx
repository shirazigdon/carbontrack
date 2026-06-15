'use client';
import { useState, useRef, useEffect } from 'react';
import { aiChatStream } from '../../lib/api';
import { EmissionRow } from '../../lib/api';
import { fmt } from '../../lib/utils';

interface Msg { role: 'user' | 'assistant'; content: string; streaming?: boolean; }

interface Props { data: EmissionRow[]; }

const SUGGESTIONS = [
  { icon: '🏆', label: 'פרויקט\nמוביל',      q: 'מה הפרויקט עם הכי הרבה פליטות?' },
  { icon: '📊', label: 'פליטות\nלפי חומר',   q: 'פרט את הפליטות לפי קטגוריית חומר' },
  { icon: '💡', label: 'דרכים\nלצמצם',       q: 'הצע 3 דרכים מעשיות לצמצום פליטות' },
  { icon: '⚖️', label: 'השוואת\nפרויקטים', q: 'השווה בין הפרויקטים לפי פחמן לטון חומר' },
  { icon: '🔥', label: 'חומרים\nפולטים',    q: 'אילו חומרים הם הפולטים הגדולים ביותר?' },
  { icon: '📈', label: 'מגמת\nפליטות',      q: 'מה המגמה של הפליטות לאורך השנים?' },
];

function buildContext(data: EmissionRow[]): string {
  if (!data.length) return 'אין נתונים זמינים.';
  const totalT = data.reduce((s, r) => s + (r.emission_co2e || 0), 0) / 1000;
  const byProj: Record<string, number> = {};
  data.forEach(r => { byProj[r.project_name] = (byProj[r.project_name] || 0) + (r.emission_co2e || 0); });
  const topProj = Object.entries(byProj).sort((a, b) => b[1] - a[1])[0]?.[0] || 'N/A';
  const projCsv = Object.entries(byProj).map(([n, e]) => `${n},${(e / 1000).toFixed(1)}t`).join('\n');
  const byCat: Record<string, number> = {};
  data.forEach(r => { byCat[r.category] = (byCat[r.category] || 0) + (r.emission_co2e || 0); });
  const catCsv = Object.entries(byCat).map(([c, e]) => `${c},${(e / 1000).toFixed(1)}t`).join('\n');
  return `אתה עוזר AI מומחה של מערכת CarbonTrack — מעקב פליטות פחמן לנתיבי ישראל.
תפקידך: לנתח נתונים, לזהות מגמות, להציע המלצות לצמצום פחמן, ולענות בעברית בצורה מקצועית.
מספרים גדולים — הצג בטונות CO₂e. ענה בנקודות קצרות. הצע פעולות מעשיות.

סה"כ ${fmt(totalT)}t CO₂e · פרויקט מוביל: ${topProj}

נתוני פרויקטים:
${projCsv}

פירוט קטגוריות:
${catCsv}`;
}

export function AiTab({ data }: Props) {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  const send = async (q: string) => {
    if (!q.trim() || loading) return;
    const history: Msg[] = [...messages, { role: 'user', content: q }];
    setMessages(history);
    setInput('');
    setLoading(true);

    // Add empty streaming placeholder
    setMessages(prev => [...prev, { role: 'assistant', content: '', streaming: true }]);

    const ctx = buildContext(data);
    const apiMsgs = history.map(m => ({ role: m.role, content: m.content }));

    await aiChatStream(
      apiMsgs,
      ctx,
      (chunk) => {
        setMessages(prev => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          if (last?.streaming) updated[updated.length - 1] = { ...last, content: last.content + chunk };
          return updated;
        });
      },
      () => {
        setMessages(prev => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          if (last?.streaming) updated[updated.length - 1] = { ...last, streaming: false };
          return updated;
        });
        setLoading(false);
      },
      (err) => {
        setMessages(prev => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          if (last?.streaming) updated[updated.length - 1] = { role: 'assistant', content: `שגיאה: ${err}` };
          return updated;
        });
        setLoading(false);
      },
    );
  };

  return (
    <div className="flex flex-col h-[calc(100vh-180px)] min-h-[500px]">
      {messages.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center gap-6 pb-4">
          {/* Enterprise banner */}
          <div className="w-full max-w-xl">
            <div className="flex items-center justify-between rounded-2xl px-4 py-3 border"
              style={{background:'linear-gradient(135deg,#1e1040,#2d1b6e)', borderColor:'rgba(167,139,250,0.3)'}}>
              <div className="flex items-center gap-2.5">
                <span className="text-[10px] font-black tracking-widest uppercase px-2 py-1 rounded-full text-white"
                  style={{background:'linear-gradient(135deg,#7b66b2,#a78bfa)'}}>⚡ ENTERPRISE</span>
                <span className="text-xs text-purple-200/70">Gemini 2.5 Pro · Streaming · ניתוח אוטומטי</span>
              </div>
              <button
                onClick={() => send('נתח את נתוני הפליטות שלנו בצורה מקיפה: זהה את הפרויקט המוביל, החומרים הבעייתיים ביותר, תבניות חריגות, והצע 3 המלצות מעשיות לצמצום פליטות עם אומדן חיסכון.')}
                disabled={loading || data.length === 0}
                className="flex items-center gap-1.5 text-xs font-bold px-3 py-1.5 rounded-xl text-white transition-all hover:opacity-90 disabled:opacity-40"
                style={{background:'linear-gradient(135deg,#7b66b2,#a78bfa)'}}>
                {loading ? <><span className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin"/>מנתח...</> : <>⚡ ניתוח אוטומטי</>}
              </button>
            </div>
          </div>

          <div className="text-center">
            <div className="text-5xl mb-3">🤖</div>
            <h2 className="font-bold text-lg mb-1">עוזר AI של CarbonTrack</h2>
            <p className="text-sm text-muted-fg max-w-md">שאל אותי כל שאלה על נתוני הפחמן — אנתח, אשווה ואמליץ בזמן אמת</p>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 w-full max-w-xl">
            {SUGGESTIONS.map(({ icon, label, q }) => (
              <button key={q} onClick={() => send(q)}
                className="flex flex-col items-center justify-center gap-2 px-3 py-6 bg-card border border-border rounded-2xl hover:border-primary/40 hover:bg-primary/5 transition-colors shadow-card min-h-[110px] text-center">
                <span className="text-3xl">{icon}</span>
                <span className="text-sm font-semibold text-slate-700 leading-snug whitespace-pre-line">{label}</span>
              </button>
            ))}
          </div>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto space-y-3 pb-4 px-1">
          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === 'user' ? 'justify-start' : 'justify-end'}`}>
              <div className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap ${
                m.role === 'user'
                  ? 'text-white rounded-tr-sm'
                  : 'bg-muted text-gray-800 rounded-tl-sm'
              }`} style={m.role === 'user' ? { background: 'var(--grad-primary)' } : undefined}>
                {m.content}
                {m.streaming && <span className="inline-block w-2 h-4 bg-purple-400 animate-pulse ml-1 rounded-sm align-middle" />}
              </div>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>
      )}

      {messages.length > 0 && (
        <button onClick={() => setMessages([])}
          className="text-xs text-muted-fg hover:text-destructive transition-colors mb-2 self-end">
          נקה שיחה
        </button>
      )}

      <div className="flex gap-2 mt-auto">
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), send(input))}
          placeholder="שאל אותי על הנתונים... (Enter לשליחה)"
          className="flex-1 text-sm border border-border rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-primary/40 bg-card shadow-card"
          disabled={loading}
        />
        <button onClick={() => send(input)} disabled={loading || !input.trim()}
          className="px-4 py-3 rounded-xl text-white font-semibold disabled:opacity-50 transition-opacity hover:opacity-90"
          style={{ background: 'var(--grad-primary)' }}>
          שלח
        </button>
      </div>
    </div>
  );
}
