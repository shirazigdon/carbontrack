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
        style={{ width: '100%', maxWidth: 180, display: 'block', margin: '0 auto', filter: 'drop-shadow(0 2px 6px rgba(0,0,0,.12))' }}>
        <defs>
          <style>{`.reg{cursor:default;stroke:#fff;stroke-width:3;stroke-linejoin:round}.rl{font-family:Heebo,sans-serif;font-size:18px;font-weight:800;fill:#1f2937;text-anchor:middle}.rs{font-family:Heebo,sans-serif;font-size:13px;fill:#4b5563;text-anchor:middle}`}</style>
          <linearGradient id="lgnd" x1="0" x2="1" y1="0" y2="0">
            <stop offset="0%" stopColor="rgb(226,243,229)" />
            <stop offset="100%" stopColor="rgb(27,94,32)" />
          </linearGradient>
        </defs>
        <path className="reg" fill={nc} d="M 124,25 Q 132,10 140,15 L 156,25 Q 164,40 156,60 Q 148,80 152,115 L 112,115 Q 114,90 112,75 L 122,70 L 122,60 L 124,25 Z" />
        <text className="rl" x="134" y="65">צפון</text>
        <text className="rs" x="134" y="85">{fmt(north)}</text>
        <path className="reg" fill={cc} d="M 112,115 L 152,115 Q 156,145 152,165 L 146,185 L 148,215 L 92,205 Q 96,175 112,115 Z" />
        <text className="rl" x="122" y="155">מרכז</text>
        <text className="rs" x="122" y="175">{fmt(center)}</text>
        <path className="reg" fill={sc} d="M 92,205 L 148,215 Q 140,280 132,360 Q 124,440 120,500 L 116,500 Q 88,360 76,260 Q 84,225 92,205 Z" />
        <text className="rl" x="112" y="340">דרום</text>
        <text className="rs" x="112" y="360">{fmt(south)}</text>
        <rect x="18" y="18" width="72" height="12" rx="6" fill="url(#lgnd)" />
        <text style={{ fontFamily: 'Heebo,sans-serif', fontSize: 12, fill: '#4b5563' }} x="18" y="42">פחות</text>
        <text style={{ fontFamily: 'Heebo,sans-serif', fontSize: 12, fill: '#4b5563' }} x="64" y="42">יותר</text>
      </svg>
    </div>
  );
}
