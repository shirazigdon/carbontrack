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
        <path className="reg" fill={nc} d="M 90,10 L 115,8 L 140,12 L 160,22 L 170,40 L 168,58 L 155,70 L 148,80 L 138,88 L 125,95 L 112,100 L 100,103 L 88,100 L 78,92 L 68,82 L 60,70 L 55,58 L 55,45 L 58,30 L 70,18 Z" />
        <text className="rl" x="112" y="48">צפון</text>
        <text className="rs" x="112" y="68">{fmt(north)}</text>
        <path className="reg" fill={cc} d="M 88,100 L 100,103 L 112,100 L 125,95 L 138,88 L 148,80 L 152,100 L 155,118 L 150,135 L 145,150 L 140,165 L 136,178 L 125,185 L 112,188 L 100,186 L 88,183 L 78,175 L 72,162 L 68,148 L 65,132 L 65,115 L 68,105 Z" />
        <text className="rl" x="110" y="138">מרכז</text>
        <text className="rs" x="110" y="158">{fmt(center)}</text>
        <path className="reg" fill={sc} d="M 78,175 L 88,183 L 100,186 L 112,188 L 125,185 L 136,178 L 140,195 L 142,212 L 140,230 L 138,250 L 134,270 L 130,290 L 125,310 L 118,330 L 112,355 L 108,380 L 105,405 L 102,425 L 99,445 L 97,465 L 95,490 L 92,510 L 88,490 L 85,468 L 82,445 L 78,420 L 74,395 L 70,370 L 65,348 L 60,325 L 55,302 L 52,278 L 50,255 L 50,230 L 52,208 L 55,192 L 62,182 L 72,178 Z" />
        <text className="rl" x="96" y="340">דרום</text>
        <text className="rs" x="96" y="360">{fmt(south)}</text>
        <rect x="18" y="18" width="72" height="12" rx="6" fill="url(#lgnd)" />
        <text style={{ fontFamily: 'Heebo,sans-serif', fontSize: 12, fill: '#4b5563' }} x="18" y="42">פחות</text>
        <text style={{ fontFamily: 'Heebo,sans-serif', fontSize: 12, fill: '#4b5563' }} x="64" y="42">יותר</text>
      </svg>
    </div>
  );
}
