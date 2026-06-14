interface IsraelMapProps {
  north: number;
  center: number;
  south: number;
}

export function IsraelMap({ north, center, south }: IsraelMapProps) {
  const fmt = (n: number) => `${(n / 1000).toLocaleString('he-IL', { maximumFractionDigits: 0 })}t`;

  return (
    <div className="flex justify-center items-center py-2">
      <svg viewBox="0 0 130 360" width="130" height="360" style={{ overflow: 'visible' }}>
        <defs>
          <filter id="map-shadow">
            <feDropShadow dx="0" dy="2" stdDeviation="3" floodOpacity="0.12"/>
          </filter>
        </defs>

        {/* North region — Galilee & Golan */}
        <path
          d="M18,8 L65,2 L108,10 L112,32 L110,55 L112,78 L107,98 L98,105 L18,105 L8,80 L10,55 L8,32 Z"
          fill="rgba(82,183,136,0.22)" stroke="#52b788" strokeWidth="1.5" strokeLinejoin="round"
          filter="url(#map-shadow)"
        />
        {/* Center region — Sharon & Judea */}
        <path
          d="M18,105 L98,105 L100,128 L97,150 L100,175 L95,200 L22,200 L18,175 L15,150 L18,128 Z"
          fill="rgba(91,155,213,0.22)" stroke="#5b9bd5" strokeWidth="1.5" strokeLinejoin="round"
          filter="url(#map-shadow)"
        />
        {/* South region — Negev */}
        <path
          d="M22,200 L95,200 L88,230 L78,262 L67,300 L58,345 L55,357 L50,357 L47,345 L38,300 L27,262 L17,230 Z"
          fill="rgba(232,168,124,0.22)" stroke="#e8a87c" strokeWidth="1.5" strokeLinejoin="round"
          filter="url(#map-shadow)"
        />

        <text x="58" y="50" textAnchor="middle" fontSize="10" fontWeight="800" fill="#1b4332" fontFamily="Heebo, Arial, sans-serif">צפון</text>
        <text x="58" y="66" textAnchor="middle" fontSize="13" fontWeight="900" fill="#059669" fontFamily="Heebo, Arial, sans-serif">{fmt(north)}</text>

        <text x="57" y="148" textAnchor="middle" fontSize="10" fontWeight="800" fill="#1e40af" fontFamily="Heebo, Arial, sans-serif">מרכז</text>
        <text x="57" y="164" textAnchor="middle" fontSize="13" fontWeight="900" fill="#2563eb" fontFamily="Heebo, Arial, sans-serif">{fmt(center)}</text>

        <text x="52" y="272" textAnchor="middle" fontSize="10" fontWeight="800" fill="#78350f" fontFamily="Heebo, Arial, sans-serif">דרום</text>
        <text x="52" y="288" textAnchor="middle" fontSize="13" fontWeight="900" fill="#d97706" fontFamily="Heebo, Arial, sans-serif">{fmt(south)}</text>
      </svg>
    </div>
  );
}
