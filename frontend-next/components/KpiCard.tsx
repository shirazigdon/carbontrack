interface KpiCardProps {
  title: string;
  value: string;
  subtitle?: string;
  badge?: string;
  badgeType?: 'down' | 'up' | 'warn';
  variant?: 'default' | 'primary' | 'accent';
}

const card: React.CSSProperties = {
  background: '#ffffff',
  border: '1px solid #ddd9d0',
  borderRadius: 18,
  padding: '20px 22px',
  boxShadow: '0 2px 10px rgba(44,62,45,0.06)',
  transition: 'box-shadow 0.2s, transform 0.2s',
  position: 'relative',
  overflow: 'hidden',
};

export function KpiCard({ title, value, subtitle, badge, badgeType, variant = 'default' }: KpiCardProps) {
  const badgeStyle: React.CSSProperties =
    badgeType === 'down' ? { background: '#eef8f2', color: '#2d6a4f', border: '1px solid #b7e4c7' } :
    badgeType === 'up'   ? { background: '#fde8e8', color: '#c0392b', border: '1px solid #fca5a5' } :
                           { background: '#fff3e0', color: '#e07b1a', border: '1px solid #fcd9a0' };

  if (variant === 'default') {
    return (
      <div style={card}
        onMouseEnter={e => { const el = e.currentTarget as HTMLElement; el.style.transform = 'translateY(-2px)'; el.style.boxShadow = '0 8px 24px rgba(44,62,45,0.11)'; }}
        onMouseLeave={e => { const el = e.currentTarget as HTMLElement; el.style.transform = ''; el.style.boxShadow = card.boxShadow as string; }}
      >
        {/* Subtle nature texture circle */}
        <div style={{ position: 'absolute', top: -16, left: -16, width: 64, height: 64, borderRadius: '50%', background: 'radial-gradient(circle, #eef8f2, transparent)', opacity: 0.8, pointerEvents: 'none' }} />
        <div style={{ position: 'relative' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
            <span style={{ fontSize: 12, fontWeight: 500, color: '#6b7c6b' }}>{title}</span>
            {badge && (
              <span style={{ ...badgeStyle, fontSize: 10, fontWeight: 700, padding: '2px 8px', borderRadius: 99 }}>{badge}</span>
            )}
          </div>
          <div style={{ fontSize: 30, fontWeight: 800, color: '#2c3e2d', lineHeight: 1, marginBottom: 6, direction: 'ltr', textAlign: 'right' }}>{value}</div>
          {subtitle && <div style={{ fontSize: 12, color: '#94a89a', fontWeight: 400 }}>{subtitle}</div>}
        </div>
      </div>
    );
  }

  // Primary = sage green gradient
  if (variant === 'primary') {
    return (
      <div style={{ ...card, background: 'linear-gradient(135deg, #40916c, #52b788)', border: 'none', boxShadow: '0 4px 20px rgba(64,145,108,0.28)' }}
        onMouseEnter={e => { (e.currentTarget as HTMLElement).style.transform = 'translateY(-2px)'; }}
        onMouseLeave={e => { (e.currentTarget as HTMLElement).style.transform = ''; }}
      >
        <div style={{ position: 'absolute', top: -20, left: -20, width: 80, height: 80, borderRadius: '50%', background: 'rgba(255,255,255,0.12)', pointerEvents: 'none' }} />
        <div style={{ position: 'relative' }}>
          <div style={{ fontSize: 12, fontWeight: 500, color: 'rgba(255,255,255,0.78)', marginBottom: 12 }}>{title}</div>
          <div style={{ fontSize: 30, fontWeight: 800, color: '#fff', lineHeight: 1, marginBottom: 6, direction: 'ltr', textAlign: 'right' }}>{value}</div>
          {subtitle && <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.65)' }}>{subtitle}</div>}
        </div>
      </div>
    );
  }

  // Accent = sky blue gradient
  return (
    <div style={{ ...card, background: 'linear-gradient(135deg, #3a7fc1, #5b9bd5)', border: 'none', boxShadow: '0 4px 20px rgba(91,155,213,0.28)' }}
      onMouseEnter={e => { (e.currentTarget as HTMLElement).style.transform = 'translateY(-2px)'; }}
      onMouseLeave={e => { (e.currentTarget as HTMLElement).style.transform = ''; }}
    >
      <div style={{ position: 'absolute', top: -20, left: -20, width: 80, height: 80, borderRadius: '50%', background: 'rgba(255,255,255,0.12)', pointerEvents: 'none' }} />
      <div style={{ position: 'relative' }}>
        <div style={{ fontSize: 12, fontWeight: 500, color: 'rgba(255,255,255,0.78)', marginBottom: 12 }}>{title}</div>
        <div style={{ fontSize: 30, fontWeight: 800, color: '#fff', lineHeight: 1, marginBottom: 6, direction: 'ltr', textAlign: 'right' }}>{value}</div>
        {subtitle && <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.65)' }}>{subtitle}</div>}
      </div>
    </div>
  );
}
