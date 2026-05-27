interface IsraelMapProps {
  north: number;
  center: number;
  south: number;
}

export function IsraelMap({ north, center, south }: IsraelMapProps) {
  const fmt = (n: number) => `${(n / 1000).toLocaleString('he-IL', { maximumFractionDigits: 0 })}t`;

  return (
    <div className="flex justify-center items-center py-2">
      <div style={{ position: 'relative', width: '150px', height: '400px', borderRadius: '16px', overflow: 'hidden', boxShadow: '0 8px 24px rgba(27,67,50,0.15)', border: '2px solid #e2e8f0', backgroundColor: '#e2e8f0' }}>
        <img 
          src="https://upload.wikimedia.org/wikipedia/commons/thumb/e/e0/Israel_relief_location_map.jpg/512px-Israel_relief_location_map.jpg" 
          alt="מפת ישראל" 
          style={{ width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'center' }} 
        />
        
        {/* Overlay Darkening slightly to make labels pop */}
        <div style={{ position: 'absolute', inset: 0, backgroundColor: 'rgba(27,67,50,0.1)' }} />

        {/* North */}
        <div style={{ position: 'absolute', top: '15%', left: '50%', transform: 'translateX(-50%)', backgroundColor: 'rgba(255,255,255,0.9)', backdropFilter: 'blur(4px)', padding: '6px 14px', borderRadius: '10px', boxShadow: '0 4px 12px rgba(0,0,0,0.1)', border: '1px solid rgba(255,255,255,0.6)', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
          <span style={{ fontSize: '11px', fontWeight: 800, color: '#475569' }}>צפון</span>
          <span style={{ fontSize: '14px', fontWeight: 900, color: '#059669' }}>{fmt(north)}</span>
        </div>

        {/* Center */}
        <div style={{ position: 'absolute', top: '45%', left: '50%', transform: 'translateX(-50%)', backgroundColor: 'rgba(255,255,255,0.9)', backdropFilter: 'blur(4px)', padding: '6px 14px', borderRadius: '10px', boxShadow: '0 4px 12px rgba(0,0,0,0.1)', border: '1px solid rgba(255,255,255,0.6)', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
          <span style={{ fontSize: '11px', fontWeight: 800, color: '#475569' }}>מרכז</span>
          <span style={{ fontSize: '14px', fontWeight: 900, color: '#059669' }}>{fmt(center)}</span>
        </div>

        {/* South */}
        <div style={{ position: 'absolute', top: '75%', left: '50%', transform: 'translateX(-50%)', backgroundColor: 'rgba(255,255,255,0.9)', backdropFilter: 'blur(4px)', padding: '6px 14px', borderRadius: '10px', boxShadow: '0 4px 12px rgba(0,0,0,0.1)', border: '1px solid rgba(255,255,255,0.6)', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
          <span style={{ fontSize: '11px', fontWeight: 800, color: '#475569' }}>דרום</span>
          <span style={{ fontSize: '14px', fontWeight: 900, color: '#059669' }}>{fmt(south)}</span>
        </div>
      </div>
    </div>
  );
}
