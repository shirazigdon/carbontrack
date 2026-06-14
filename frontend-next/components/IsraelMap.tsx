interface IsraelMapProps {
  north: number;
  center: number;
  south: number;
}

// Simplified Israel outline traced from geographic coordinates
// ViewBox: 0 0 220 470
// North ~33.3°N is y≈0, Eilat ~29.5°N is y≈450
// West coast ~34.2°E is x≈10, Golan east ~35.85°E is x≈205
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

function heatColor(val: number, maxVal: number): string {
  const r = maxVal > 0 ? Math.min(val / maxVal, 1) : 0;
  if (r <= 0.01) return '#e2e8f0';
  if (r < 0.25)  return '#bae6fd';
  if (r < 0.50)  return '#86efac';
  if (r < 0.70)  return '#fde68a';
  if (r < 0.87)  return '#fb923c';
  return '#ef4444';
}

export function IsraelMap({ north, center, south }: IsraelMapProps) {
  const fmtT = (n: number) =>
    `${(n / 1000).toLocaleString('he-IL', { maximumFractionDigits: 0 })}t`;

  const maxVal = Math.max(north, center, south, 1);
  const northC  = heatColor(north,  maxVal);
  const centerC = heatColor(center, maxVal);
  const southC  = heatColor(south,  maxVal);

  // Zone y-boundaries (geographic: north/center at ~32.4°N → y≈106; center/south at ~31.3°N → y≈238)
  const Y_NC = 112;
  const Y_CS = 245;

  return (
    <div className="flex justify-center items-center py-2">
      <svg viewBox="0 0 220 470" width="130" height="277" style={{ overflow: 'visible' }}>
        <defs>
          <clipPath id="il-heat-clip">
            <path d={ISRAEL_PATH} />
          </clipPath>
          <filter id="il-blur">
            <feGaussianBlur stdDeviation="6" />
          </filter>
        </defs>

        {/* ── Heat zones clipped to Israel shape ── */}
        <g clipPath="url(#il-heat-clip)">
          {/* Base terrain */}
          <rect x="0" y="0" width="220" height="470" fill="#f8fafc" />
          {/* Soft blurred heat glow */}
          <rect x="0" y="0" width="220" height={Y_NC}   fill={northC}  filter="url(#il-blur)" />
          <rect x="0" y={Y_NC} width="220" height={Y_CS - Y_NC} fill={centerC} filter="url(#il-blur)" />
          <rect x="0" y={Y_CS} width="220" height={470 - Y_CS}  fill={southC}  filter="url(#il-blur)" />
          {/* Solid heat color on top for crisp center */}
          <rect x="0" y="0" width="220" height={Y_NC}   fill={northC}  opacity="0.55" />
          <rect x="0" y={Y_NC} width="220" height={Y_CS - Y_NC} fill={centerC} opacity="0.55" />
          <rect x="0" y={Y_CS} width="220" height={470 - Y_CS}  fill={southC}  opacity="0.55" />

          {/* Sea of Galilee */}
          <ellipse cx="170" cy="88" rx="11" ry="14" fill="rgba(125,211,252,0.75)" />
          {/* Dead Sea */}
          <ellipse cx="158" cy="225" rx="7"  ry="20" fill="rgba(125,211,252,0.55)" />

          {/* Zone dividers */}
          <line x1="0" y1={Y_NC} x2="220" y2={Y_NC}
            stroke="rgba(51,65,85,0.25)" strokeWidth="0.8" strokeDasharray="4,3" />
          <line x1="0" y1={Y_CS} x2="220" y2={Y_CS}
            stroke="rgba(51,65,85,0.25)" strokeWidth="0.8" strokeDasharray="4,3" />
        </g>

        {/* ── Outline ── */}
        <path d={ISRAEL_PATH} fill="none" stroke="#475569" strokeWidth="1.5" strokeLinejoin="round" />

        {/* ── Labels (outside clip so never cut off) ── */}
        {/* North */}
        <text x="128" y="68" textAnchor="middle" fontSize="8.5" fontWeight="800"
          fill="#1e293b" fontFamily="Heebo,Arial,sans-serif">צפון</text>
        <text x="128" y="82" textAnchor="middle" fontSize="11" fontWeight="900"
          fill="#0f172a" fontFamily="Heebo,Arial,sans-serif">{fmtT(north)}</text>

        {/* Center */}
        <text x="92" y="172" textAnchor="middle" fontSize="8.5" fontWeight="800"
          fill="#1e293b" fontFamily="Heebo,Arial,sans-serif">מרכז</text>
        <text x="92" y="186" textAnchor="middle" fontSize="11" fontWeight="900"
          fill="#0f172a" fontFamily="Heebo,Arial,sans-serif">{fmtT(center)}</text>

        {/* South */}
        <text x="72" y="342" textAnchor="middle" fontSize="8.5" fontWeight="800"
          fill="#1e293b" fontFamily="Heebo,Arial,sans-serif">דרום</text>
        <text x="72" y="356" textAnchor="middle" fontSize="11" fontWeight="900"
          fill="#0f172a" fontFamily="Heebo,Arial,sans-serif">{fmtT(south)}</text>
      </svg>
    </div>
  );
}
