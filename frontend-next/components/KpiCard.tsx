interface KpiCardProps {
  title: string;
  value: string;
  subtitle?: string;
  badge?: string;
  badgeType?: 'down' | 'up' | 'warn';
  variant?: 'default' | 'primary' | 'accent';
}

export function KpiCard({ title, value, subtitle, badge, badgeType, variant = 'default' }: KpiCardProps) {
  const badgeStyle =
    badgeType === 'down' ? { background: '#d8f3e3', color: '#2d6a4f' } :
    badgeType === 'up'   ? { background: '#fde8e8', color: '#e63946' } :
                           { background: '#fef3c7', color: '#92400e' };

  if (variant === 'default') {
    return (
      <div style={{
        background: '#ffffff',
        border: '1.5px solid #b7e4c7',
        borderRadius: '18px',
        padding: '20px',
        boxShadow: '0 2px 12px rgba(27,67,50,0.07)',
        transition: 'box-shadow 0.2s, transform 0.2s',
        position: 'relative',
        overflow: 'hidden',
      }}
      onMouseEnter={e => { (e.currentTarget as HTMLElement).style.transform = 'translateY(-2px)'; (e.currentTarget as HTMLElement).style.boxShadow = '0 8px 24px rgba(27,67,50,0.12)'; }}
      onMouseLeave={e => { (e.currentTarget as HTMLElement).style.transform = ''; (e.currentTarget as HTMLElement).style.boxShadow = '0 2px 12px rgba(27,67,50,0.07)'; }}
      >
        {/* Subtle leaf accent */}
        <div style={{ position: 'absolute', top: -10, left: -10, width: 60, height: 60, borderRadius: '50%', background: 'radial-gradient(circle, #d8f3e3, transparent)', opacity: 0.6 }} />
        <div style={{ position: 'relative' }}>
          <div style={{ fontSize: 11, fontWeight: 500, color: '#4a7c59', marginBottom: 10, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>{title}</span>
            {badge && <span style={{ ...badgeStyle, fontSize: 10, fontWeight: 700, padding: '2px 8px', borderRadius: 99 }}>{badge}</span>}
          </div>
          <div style={{ fontSize: 28, fontWeight: 800, color: '#1b4332', lineHeight: 1, marginBottom: 6, direction: 'ltr', textAlign: 'right' }}>{value}</div>
          {subtitle && <div style={{ fontSize: 11, color: '#74c69d', fontWeight: 500 }}>{subtitle}</div>}
        </div>
      </div>
    );
  }

  const gradients = {
    primary: 'linear-gradient(135deg, #40916c 0%, #52b788 60%, #74c69d 100%)',
    accent:  'linear-gradient(135deg, #52b788 0%, #95d5b2 60%, #b7e4c7 100%)',
  };

  return (
    <div style={{
      background: gradients[variant],
      borderRadius: '18px',
      padding: '20px',
      boxShadow: '0 4px 20px rgba(64,145,108,0.25)',
      position: 'relative',
      overflow: 'hidden',
      transition: 'transform 0.2s',
    }}
    onMouseEnter={e => { (e.currentTarget as HTMLElement).style.transform = 'translateY(-2px)'; }}
    onMouseLeave={e => { (e.currentTarget as HTMLElement).style.transform = ''; }}
    >
      <div style={{ position: 'absolute', top: -20, left: -20, width: 80, height: 80, borderRadius: '50%', background: 'rgba(255,255,255,0.15)' }} />
      <div style={{ position: 'relative' }}>
        <div style={{ fontSize: 11, fontWeight: 500, color: 'rgba(255,255,255,0.8)', marginBottom: 10, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>{title}</span>
          {badge && <span style={{ background: 'rgba(255,255,255,0.25)', color: '#fff', fontSize: 10, fontWeight: 700, padding: '2px 8px', borderRadius: 99 }}>{badge}</span>}
        </div>
        <div style={{ fontSize: 28, fontWeight: 800, color: '#ffffff', lineHeight: 1, marginBottom: 6, direction: 'ltr', textAlign: 'right' }}>{value}</div>
        {subtitle && <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.75)', fontWeight: 500 }}>{subtitle}</div>}
      </div>
    </div>
  );
}
