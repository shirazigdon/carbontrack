interface IsraelMapProps {
  north: number;
  center: number;
  south: number;
}

function mapColor(val: number, max: number): string {
  if (max === 0) return '#d4edda';
  const t = val / max;
  const r = Math.round(200 - t * 155);
  const g = Math.round(230 - t * 100);
  const b = Math.round(200 - t * 165);
  return `rgb(${r},${g},${b})`;
}

export function IsraelMap({ north, center, south }: IsraelMapProps) {
  const max = Math.max(north, center, south, 1);
  const nc = mapColor(north, max);
  const cc = mapColor(center, max);
  const sc = mapColor(south, max);
  const fmt = (n: number) => `${(n / 1000).toLocaleString('he-IL', { maximumFractionDigits: 0 })}t`;

  return (
    <div className="flex justify-center items-center py-1">
      <svg viewBox="0 0 220 520" xmlns="http://www.w3.org/2000/svg"
        style={{ width: '100%', maxWidth: 260, display: 'block', margin: '0 auto', filter: 'drop-shadow(0 4px 12px rgba(0,0,0,.12))' }}>
        <defs>
          <style>{`.reg{cursor:default;stroke:#fff;stroke-width:3;stroke-linejoin:round;transition:all 0.3s ease}.reg:hover{opacity:0.9;stroke-width:4;filter:brightness(1.05)}.rl{font-family:Heebo,sans-serif;font-size:18px;font-weight:800;fill:#1f2937;text-anchor:middle;pointer-events:none}.rs{font-family:Heebo,sans-serif;font-size:13px;fill:#4b5563;text-anchor:middle;pointer-events:none}`}</style>
          <linearGradient id="lgnd" x1="0" x2="1" y1="0" y2="0">
            <stop offset="0%" stopColor="rgb(226,243,229)" />
            <stop offset="100%" stopColor="rgb(27,94,32)" />
          </linearGradient>
        </defs>
        
        <path className="reg" fill={nc} d="M 70,110 L 65,85 L 80,75 L 90,20 L 120,10 L 150,30 L 140,60 Q 132,70 140,80 L 135,120 Z" />
        <text className="rl" x="115" y="65">צפון</text>
        <text className="rs" x="115" y="85">{fmt(north)}</text>
        
        <path className="reg" fill={cc} d="M 70,110 L 135,120 L 135,180 L 135,210 L 45,210 Q 55,160 70,110 Z" />
        <text className="rl" x="90" y="160">מרכז</text>
        <text className="rs" x="90" y="180">{fmt(center)}</text>
        
        <path className="reg" fill={sc} d="M 45,210 L 135,210 Q 125,235 130,260 L 120,380 L 105,500 L 95,500 L 45,260 Q 40,235 45,210 Z" />
        <text className="rl" x="90" y="340">דרום</text>
        <text className="rs" x="90" y="360">{fmt(south)}</text>
        
        <rect x="18" y="18" width="72" height="12" rx="6" fill="url(#lgnd)" />
        <text style={{ fontFamily: 'Heebo,sans-serif', fontSize: 12, fill: '#4b5563' }} x="18" y="42">פחות</text>
        <text style={{ fontFamily: 'Heebo,sans-serif', fontSize: 12, fill: '#4b5563' }} x="64" y="42">יותר</text>
      </svg>
    </div>
  );
}
