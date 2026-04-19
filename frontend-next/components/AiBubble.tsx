'use client';
import { useState, useRef, useEffect } from 'react';
import { aiChat, EmissionRow } from '../lib/api';
import { fmt } from '../lib/utils';

interface Msg { role: 'user' | 'assistant'; content: string; }

function buildContext(data: EmissionRow[]): string {
  if (!data.length) return 'אתה עוזר AI מומחה לניתוח פליטות פחמן.';
  const totalT = data.reduce((s, r) => s + (r.emission_co2e || 0), 0) / 1000;
  const byProj: Record<string, number> = {};
  data.forEach(r => { byProj[r.project_name] = (byProj[r.project_name] || 0) + (r.emission_co2e || 0); });
  const topProj = Object.entries(byProj).sort((a, b) => b[1] - a[1])[0]?.[0] || 'N/A';
  return `אתה עוזר AI מומחה של CarbonTrack360 — פליטות פחמן לנתיבי ישראל. ענה קצר ומקצועי בעברית.
סה"כ ${fmt(totalT)}t CO₂e · פרויקט מוביל: ${topProj}`;
}

export function AiBubble({ data }: { data: EmissionRow[] }) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (open) bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, open]);

  const send = async (q: string) => {
    if (!q.trim() || loading) return;
    const newMsgs: Msg[] = [...messages, { role: 'user', content: q }];
    setMessages(newMsgs);
    setInput('');
    setLoading(true);
    setOpen(true);
    try {
      const { reply } = await aiChat(newMsgs.slice(-8), buildContext(data));
      setMessages(prev => [...prev, { role: 'assistant', content: reply }]);
    } catch (e) {
      setMessages(prev => [...prev, { role: 'assistant', content: `שגיאה: ${e}` }]);
    }
    setLoading(false);
  };

  return (
    <>
      {/* FAB */}
      <button
        onClick={() => setOpen(o => !o)}
        className="fixed bottom-6 left-6 w-14 h-14 rounded-full text-white text-xl shadow-elevated z-50 flex items-center justify-center hover:scale-110 transition-transform"
        style={{ background: 'var(--grad-primary)' }}
        title="עוזר AI">
        🤖
        {messages.length > 0 && (
          <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-destructive text-white text-[9px] flex items-center justify-center font-bold">
            {messages.filter(m => m.role === 'assistant').length}
          </span>
        )}
      </button>

      {/* Panel */}
      {open && (
        <div className="fixed bottom-24 left-6 w-80 max-h-[480px] bg-white rounded-2xl shadow-elevated z-50 flex flex-col overflow-hidden border border-border">
          {/* Header */}
          <div style={{ background: 'var(--grad-hero)' }} className="px-4 py-3 flex items-center justify-between flex-shrink-0">
            <div>
              <div className="text-white font-bold text-sm">🤖 עוזר נתונים AI</div>
              <div className="text-white/40 text-[10px]">Vertex AI · Gemini 2.5 Flash</div>
            </div>
            <div className="flex gap-2">
              <button onClick={() => setMessages([])} className="text-white/40 hover:text-white text-xs transition-colors" title="נקה">🗑️</button>
              <button onClick={() => setOpen(false)} className="text-white/60 hover:text-white text-sm" title="סגור">✕</button>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-3 space-y-2 text-sm" dir="rtl">
            {messages.length === 0 && (
              <div className="bg-muted rounded-xl rounded-tl-sm px-3 py-2 text-xs text-gray-600">שלום! שאל אותי על הנתונים 👇</div>
            )}
            {messages.map((m, i) => (
              <div key={i} className={`flex ${m.role === 'user' ? 'justify-start' : 'justify-end'}`}>
                <div className={`max-w-[88%] rounded-xl px-3 py-2 text-xs leading-relaxed whitespace-pre-wrap ${
                  m.role === 'user' ? 'text-white rounded-tr-sm' : 'bg-muted text-gray-700 rounded-tl-sm'
                }`} style={m.role === 'user' ? { background: 'hsl(142,55%,35%)' } : undefined}>
                  {m.content}
                </div>
              </div>
            ))}
            {loading && <div className="flex justify-end"><div className="bg-muted rounded-xl rounded-tl-sm px-3 py-2 text-xs text-muted-fg animate-pulse">מנתח...</div></div>}
            <div ref={bottomRef} />
          </div>

          <div className="text-[10px] text-muted-fg px-4 py-1.5 border-t border-border bg-muted/40" dir="rtl">הקלד בשורה למטה · Enter לשליחה</div>

          {/* Input */}
          <div className="flex gap-2 p-3 border-t border-border flex-shrink-0">
            <input
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), send(input))}
              placeholder="שאל אותי..."
              className="flex-1 text-xs border border-border rounded-lg px-3 py-2 focus:outline-none focus:ring-1 focus:ring-primary bg-muted"
              disabled={loading}
              dir="rtl"
            />
            <button onClick={() => send(input)} disabled={loading || !input.trim()}
              className="text-xs px-3 py-2 rounded-lg text-white disabled:opacity-50 font-semibold"
              style={{ background: 'hsl(142,55%,35%)' }}>
              שלח
            </button>
          </div>
        </div>
      )}
    </>
  );
}
