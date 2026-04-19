'use client';
import { useState, useRef, useEffect } from 'react';
import { aiChat } from '../../lib/api';
import { EmissionRow } from '../../lib/api';
import { fmt } from '../../lib/utils';

interface Msg { role: 'user' | 'assistant'; content: string; }

interface Props { data: EmissionRow[]; }

const SUGGESTIONS = [
  { icon: '🏆', q: 'מה הפרויקט עם הכי הרבה פליטות?' },
  { icon: '📊', q: 'פרט את הפליטות לפי קטגוריית חומר' },
  { icon: '💡', q: 'הצע 3 דרכים מעשיות לצמצום פליטות' },
  { icon: '⚖️', q: 'השווה בין הפרויקטים לפי פחמן לטון חומר' },
  { icon: '🔥', q: 'אילו חומרים הם הפולטים הגדולים ביותר?' },
  { icon: '📈', q: 'מה המגמה של הפליטות לאורך השנים?' },
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
  return `אתה עוזר AI מומחה של מערכת CarbonTrack360 — מעקב פליטות פחמן לנתיבי ישראל.
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
    const newMsgs: Msg[] = [...messages, { role: 'user', content: q }];
    setMessages(newMsgs);
    setInput('');
    setLoading(true);
    try {
      const ctx = buildContext(data);
      const { reply } = await aiChat(newMsgs, ctx);
      setMessages(prev => [...prev, { role: 'assistant', content: reply }]);
    } catch (e) {
      setMessages(prev => [...prev, { role: 'assistant', content: `שגיאה: ${e}` }]);
    }
    setLoading(false);
  };

  return (
    <div className="flex flex-col h-[calc(100vh-180px)] min-h-[500px]">
      {messages.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center gap-6 pb-4">
          <div className="text-center">
            <div className="text-5xl mb-3">🤖</div>
            <h2 className="font-bold text-lg mb-1">עוזר AI של CarbonTrack360</h2>
            <p className="text-sm text-muted-fg max-w-md">שאל אותי כל שאלה על נתוני הפחמן — אנתח, אשווה ואמליץ בזמן אמת</p>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 w-full max-w-xl">
            {SUGGESTIONS.map(({ icon, q }) => (
              <button key={q} onClick={() => send(q)}
                className="text-right p-3 bg-card border border-border rounded-xl text-xs hover:border-primary/40 hover:bg-primary/5 transition-colors shadow-card">
                <span className="mr-1">{icon}</span>{q}
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
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex justify-end">
              <div className="bg-muted rounded-2xl rounded-tl-sm px-4 py-3 text-sm text-muted-fg animate-pulse">מנתח...</div>
            </div>
          )}
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
