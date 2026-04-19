import { cn } from '../lib/utils';

interface KpiCardProps {
  title: string;
  value: string;
  subtitle?: string;
  badge?: string;
  badgeType?: 'down' | 'up' | 'warn';
  variant?: 'default' | 'primary' | 'accent';
  icon?: React.ReactNode;
}

export function KpiCard({ title, value, subtitle, badge, badgeType, variant = 'default', icon }: KpiCardProps) {
  const badgeClass = badgeType === 'down'
    ? 'bg-emerald-50 text-emerald-600'
    : badgeType === 'up'
    ? 'bg-red-50 text-red-500'
    : 'bg-amber-50 text-amber-600';

  if (variant === 'default') {
    return (
      <div className="bg-white rounded-2xl p-5 shadow-kpi border border-slate-100 hover:shadow-elevated transition-shadow group relative overflow-hidden">
        <div className="absolute top-0 right-0 w-20 h-20 opacity-[0.04] rounded-full bg-emerald-500 translate-x-6 -translate-y-6 group-hover:opacity-[0.07] transition-opacity" />
        <div className="flex items-start justify-between mb-3">
          <div className="text-xs font-medium text-slate-500">{title}</div>
          {badge && (
            <span className={cn('text-[10px] font-bold px-2 py-0.5 rounded-full', badgeClass)}>{badge}</span>
          )}
        </div>
        <div className="text-3xl font-bold text-slate-900 leading-none mb-1.5 ltr">{value}</div>
        {subtitle && <div className="text-xs text-slate-400 mt-1">{subtitle}</div>}
      </div>
    );
  }

  const gradients: Record<string, string> = {
    primary: 'linear-gradient(135deg, hsl(152,60%,28%), hsl(152,55%,40%))',
    accent:  'linear-gradient(135deg, hsl(160,55%,32%), hsl(85,50%,40%))',
  };

  return (
    <div className="rounded-2xl p-5 relative overflow-hidden hover:scale-[1.01] transition-transform"
      style={{ background: gradients[variant] }}>
      <div className="absolute inset-0 opacity-10"
        style={{ backgroundImage: 'radial-gradient(circle at 80% 20%, white 0%, transparent 60%)' }} />
      <div className="relative">
        <div className="flex items-start justify-between mb-3">
          <div className="text-xs font-medium text-white/70">{title}</div>
          {badge && (
            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-white/20 text-white">{badge}</span>
          )}
        </div>
        <div className="text-3xl font-bold text-white leading-none mb-1.5 ltr">{value}</div>
        {subtitle && <div className="text-xs text-white/60 mt-1">{subtitle}</div>}
      </div>
    </div>
  );
}
