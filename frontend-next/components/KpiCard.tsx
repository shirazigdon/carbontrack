import { cn } from '../lib/utils';

interface KpiCardProps {
  title: string;
  value: string;
  subtitle?: string;
  badge?: string;
  badgeType?: 'down' | 'up' | 'warn';
  variant?: 'default' | 'primary' | 'accent';
}

export function KpiCard({ title, value, subtitle, badge, badgeType, variant = 'default' }: KpiCardProps) {
  const badgeClass = badgeType === 'down'
    ? 'bg-success/15 text-success'
    : badgeType === 'up'
    ? 'bg-destructive/15 text-destructive'
    : 'bg-warning/15 text-warning';

  return (
    <div className={cn(
      'rounded-xl p-5 transition-transform hover:scale-[1.02]',
      variant === 'default' && 'bg-card border border-border shadow-card',
      variant === 'primary' && 'text-white',
      variant === 'accent' && 'text-white',
    )}
    style={variant === 'primary' ? { background: 'var(--grad-primary)' }
         : variant === 'accent' ? { background: 'var(--grad-accent)' }
         : undefined}
    >
      <div className={cn('text-sm font-medium mb-3', variant === 'default' ? 'text-muted-fg' : 'text-white/80')}>
        {title}
      </div>
      <div className={cn('text-3xl font-bold leading-none mb-2 ltr', variant === 'default' ? 'text-gray-900' : 'text-white')}>
        {value}
      </div>
      <div className="flex items-center gap-2 mt-1">
        {badge && (
          <span className={cn('text-xs font-bold px-2 py-0.5 rounded-full', badgeClass)}>
            {badge}
          </span>
        )}
        {subtitle && (
          <span className={cn('text-xs', variant === 'default' ? 'text-muted-fg' : 'text-white/70')}>
            {subtitle}
          </span>
        )}
      </div>
    </div>
  );
}
