interface ProjectDot {
  name: string;
  region: string;
  emission: number;
}

interface IsraelMapProps {
  north: number;
  center: number;
  south: number;
  projects?: ProjectDot[];
}

const ISRAEL_PATH =
  'M 108,22 L 130,10 L 155,6 L 178,4 L 195,18 L 203,38 ' +
  'L 205,58 L 200,72 L 186,88 L 175,105 L 170,125 ' +
  'L 168,148 L 172,168 L 168,192 L 163,218 ' +
  'L 158,238 L 152,258 L 142,285 L 128,322 ' +
  'L 108,378 L 98,420 L 92,448 ' +
  'L 86,448 L 72,420 L 55,378 ' +
  'L 38,328 L 25,285 L 18,260 ' +
  'L 18,235 L 22,218 L 28,195 ' +
  'L 34,168 L 38,148 L 42,128 ' +
  'L 46,108 L 52,88 L 60,72 ' +
  'L 55,55 L 68,42 L 82,32 L 95,24 Z';

// Known project locations mapped to 220×470 SVG coordinate space
const KNOWN_COORDS: Record<string, { x: number; y: number }> = {
  'כביש 6 – מקטע עמק יזרעאל': { x: 128, y: 90 },
  'פיתוח נמל חיפה – שלב ב':    { x: 72,  y: 63 },
  'מחלף גלילות – שדרוג מלא':   { x: 60,  y: 150 },
  'קו רכבת קלה ת״א – מקטע B2': { x: 52,  y: 168 },
  'כביש 531 – כביש לכיש':       { x: 54,  y: 210 },
};

// Fallback spread coordinates by region for unknown projects
const REGION_FALLBACK: Record<string, { x: number; y: number }[]> = {
  'צפון': [{ x: 110, y: 70 }, { x: 78, y: 82 }, { x: 138, y: 58 }, { x: 126, y: 100 }, { x: 95, y: 62 }],
  'מרכז': [{ x: 65, y: 155 }, { x: 82, y: 178 }, { x: 55, y: 195 }, { x: 98, y: 163 }, { x: 70, y: 185 }],
  'דרום': [{ x: 76, y: 285 }, { x: 86, y: 312 }, { x: 68, y: 338 }, { x: 82, y: 360 }, { x: 90, y: 280 }],
};

function hashStr(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) & 0x7fffffff;
  return h;
}

function heatColor(ratio: number): string {
  if (ratio <= 0.01) return '#e2e8f0';
  if (ratio < 0.20)  return '#bae6fd';
  if (ratio < 0.45)  return '#86efac';
  if (ratio < 0.68)  return '#fde68a';
  if (ratio < 0.86)  return '#fb923c';
  return '#ef4444';
}

export function IsraelMap({ north, center, south, projects = [] }: IsraelMapProps) {
  const fmtT = (n: number) =>
    `${(n / 1000).toLocaleString('he-IL', { maximumFractionDigits: 0 })}t`;

  const maxRegion = Math.max(north, center, south, 1);
  const northC  = heatColor(north  / maxRegion);
  const centerC = heatColor(center / maxRegion);
  const southC  = heatColor(south  / maxRegion);

  const maxDot = Math.max(...projects.map(p => p.emission), 1);

  const Y_NC = 112;
  const Y_CS = 245;

  return (
    <div className="flex justify-center items-center py-2">
      <svg viewBox="0 0 220 470" width="130" height="277" style={{ overflow: 'visible' }}>
        <defs>
          <clipPath id="il-clip">
            <path d={ISRAEL_PATH} />
          </clipPath>
          <filter id="il-glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="10" />
          </filter>
        </defs>

        {/* ── Zone background fills ── */}
        <g clipPath="url(#il-clip)">
          <rect x="0" y="0" width="220" height="470" fill="#f8fafc" />
          <rect x="0" y="0"     width="220" height={Y_NC}        fill={northC}  opacity="0.35" />
          <rect x="0" y={Y_NC}  width="220" height={Y_CS - Y_NC} fill={centerC} opacity="0.35" />
          <rect x="0" y={Y_CS}  width="220" height={470 - Y_CS}  fill={southC}  opacity="0.35" />

          {/* Water bodies */}
          <ellipse cx="170" cy="88"  rx="10" ry="14" fill="rgba(125,211,252,0.65)" />
          <ellipse cx="158" cy="225" rx="7"  ry="20" fill="rgba(125,211,252,0.50)" />

          {/* ── Project heat dots ── */}
          {projects.map((proj, idx) => {
            const known = KNOWN_COORDS[proj.name];
            let pos: { x: number; y: number };
            if (known) {
              pos = known;
            } else {
              const pts = REGION_FALLBACK[proj.region] ?? REGION_FALLBACK['מרכז'];
              pos = pts[hashStr(proj.name) % pts.length];
            }
            const ratio = proj.emission / maxDot;
            const r     = 10 + Math.sqrt(ratio) * 22;
            const color = heatColor(ratio);
            return (
              <g key={`dot-${idx}`}>
                <title>{proj.name}</title>
                {/* soft outer glow */}
                <circle cx={pos.x} cy={pos.y} r={r * 1.9} fill={color} opacity="0.30" filter="url(#il-glow)" />
                {/* main filled dot */}
                <circle cx={pos.x} cy={pos.y} r={r}       fill={color} opacity="0.72" />
                {/* center pin */}
                <circle cx={pos.x} cy={pos.y} r="2.5" fill="rgba(0,0,0,0.50)" />
              </g>
            );
          })}

          {/* Zone divider lines */}
          <line x1="0" y1={Y_NC} x2="220" y2={Y_NC} stroke="rgba(51,65,85,0.22)" strokeWidth="0.8" strokeDasharray="4,3" />
          <line x1="0" y1={Y_CS} x2="220" y2={Y_CS} stroke="rgba(51,65,85,0.22)" strokeWidth="0.8" strokeDasharray="4,3" />
        </g>

        {/* ── Outline on top ── */}
        <path d={ISRAEL_PATH} fill="none" stroke="#475569" strokeWidth="1.5" strokeLinejoin="round" />

        {/* ── Region labels (outside clip — always visible) ── */}
        {/* North label — upper-right (Golan area, away from dots) */}
        <text x="155" y="34" textAnchor="middle" fontSize="8.5" fontWeight="800" fill="#1e293b" fontFamily="Heebo,Arial,sans-serif">צפון</text>
        <text x="155" y="48" textAnchor="middle" fontSize="11"  fontWeight="900" fill="#0f172a" fontFamily="Heebo,Arial,sans-serif">{fmtT(north)}</text>

        {/* Center label — east side of center zone */}
        <text x="138" y="168" textAnchor="middle" fontSize="8.5" fontWeight="800" fill="#1e293b" fontFamily="Heebo,Arial,sans-serif">מרכז</text>
        <text x="138" y="182" textAnchor="middle" fontSize="11"  fontWeight="900" fill="#0f172a" fontFamily="Heebo,Arial,sans-serif">{fmtT(center)}</text>

        {/* South label — lower Negev */}
        <text x="75" y="344" textAnchor="middle" fontSize="8.5" fontWeight="800" fill="#1e293b" fontFamily="Heebo,Arial,sans-serif">דרום</text>
        <text x="75" y="358" textAnchor="middle" fontSize="11"  fontWeight="900" fill="#0f172a" fontFamily="Heebo,Arial,sans-serif">{fmtT(south)}</text>
      </svg>
    </div>
  );
}
