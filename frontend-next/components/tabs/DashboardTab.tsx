'use client';
import { useMemo, useState } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from 'recharts';
import { KpiCard } from '../KpiCard';
import { IsraelMap } from '../IsraelMap';
import { EmissionRow } from '../../lib/api';
import { fmt } from '../../lib/utils';

const COLORS = ['#059669','#10b981','#34d399','#f59e0b','#6ee7b7','#a7f3d0'];

interface Props { data: EmissionRow[]; reviewCount: number; }

export function DashboardTab({ data, reviewCount }: Props) {
  const [barMode, setBarMode] = useState<'total'|'normalized'>('total');
  const curYear = new Date().getFullYear();

  const kpis = useMemo(() => {
    const totalE = data.reduce((s,r) => s+(r.emission_co2e||0), 0);
    const yearlyE = data.filter(r=>(r.year||0)===curYear).reduce((s,r)=>s+(r.emission_co2e||0),0);
    const totalW = data.reduce((s,r)=>s+(r.weight_kg||0),0);
    const avgReliability = data.length > 0 ? data.reduce((s,r)=>s+(r.reliability_score||0),0)/data.length : 0;
    return { totalE, yearlyE, totalW, avgReliability };
  }, [data, curYear]);

  const byProject = useMemo(() => {
    const map: Record<string,{e:number;w:number}> = {};
    data.forEach(r => {
      const p = r.project_name||'Unknown';
      map[p] = map[p]||{e:0,w:0};
      map[p].e += r.emission_co2e||0;
      map[p].w += r.weight_kg||0;
    });
    return Object.entries(map).map(([name,{e,w}]) => ({
      name, total: e/1000, normalized: w>0 ? e/(w/1000) : 0,
    })).sort((a,b) => barMode==='total' ? a.total-b.total : a.normalized-b.normalized);
  }, [data, barMode]);

  const byCategory = useMemo(() => {
    const map: Record<string,number> = {};
    data.forEach(r => { const c=r.category||'Unknown'; map[c]=(map[c]||0)+(r.emission_co2e||0); });
    return Object.entries(map).map(([name,value]) => ({name,value}));
  }, [data]);

  const byRegion = useMemo(() => {
    const map: Record<string,number> = {};
    data.forEach(r => { const reg=r.region||'Unknown'; map[reg]=(map[reg]||0)+(r.emission_co2e||0); });
    return map;
  }, [data]);

  return (
    <div className="space-y-5">
      {/* KPI row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard title={`פליטות ${curYear}`} value={`${fmt(kpis.yearlyE/1000,1)}t`} subtitle="CO₂e שנה נוכחית" variant="primary"/>
        <KpiCard title='סה"כ פליטות' value={`${fmt(kpis.totalE/1000,1)}t`} subtitle="כלל הפרויקטים" badge="↓ 8.3%" badgeType="down"/>
        <KpiCard title="משקל חומרים" value={`${fmt(kpis.totalW/1000)}t`} subtitle='סה"כ'/>
        <KpiCard title="שורות Review" value={`${reviewCount}`} subtitle="ממתינות לאישור" variant={reviewCount>0?'accent':'default'}/>
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        <div className="lg:col-span-3 bg-white border border-slate-200 rounded-2xl p-5 shadow-card">
          <div className="flex items-center justify-between mb-5">
            <div>
              <div className="font-semibold text-sm text-slate-800">פליטות לפי פרויקט</div>
              <div className="text-xs text-slate-400 mt-0.5">t CO₂e</div>
            </div>
            <div className="flex gap-1 bg-slate-100 rounded-lg p-0.5">
              {(['total','normalized'] as const).map(m => (
                <button key={m} onClick={()=>setBarMode(m)}
                  className={`text-xs px-3 py-1.5 rounded-md transition-all font-medium ${barMode===m?'bg-white shadow-sm text-slate-800':'text-slate-500 hover:text-slate-700'}`}>
                  {m==='total'?'סה"כ':'נורמלי'}
                </button>
              ))}
            </div>
          </div>
          <ResponsiveContainer width="100%" height={Math.max(200, byProject.length*46)}>
            <BarChart data={byProject} layout="vertical" margin={{left:8,right:60,top:4,bottom:4}}>
              <XAxis type="number" tick={{fontSize:10,fill:'#94a3b8'}} tickFormatter={v=>`${fmt(v)}`} axisLine={false} tickLine={false}/>
              <YAxis type="category" dataKey="name" width={130} tick={{fontSize:11,fill:'#475569'}} axisLine={false} tickLine={false}/>
              <Tooltip
                formatter={(v)=>[`${fmt(Number(v),1)} ${barMode==='total'?'t CO₂e':'kg/t'}`,'']}
                contentStyle={{fontFamily:'Heebo',fontSize:12,borderRadius:'12px',border:'1px solid #e2e8f0',boxShadow:'0 4px 12px rgba(0,0,0,0.08)'}}
              />
              <Bar dataKey={barMode==='total'?'total':'normalized'} fill="#059669" radius={[0,6,6,0]}
                label={{position:'right',fontSize:10,fill:'#64748b',formatter:(v: unknown)=>fmt(Number(v),1)}}/>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="lg:col-span-2 bg-white border border-slate-200 rounded-2xl p-5 shadow-card">
          <div className="font-semibold text-sm text-slate-800 mb-1">פילוח לפי חומר</div>
          <div className="text-xs text-slate-400 mb-3">אחוז מסך הפליטות</div>
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie data={byCategory} dataKey="value" nameKey="name" cx="50%" cy="48%" innerRadius={55} outerRadius={90} paddingAngle={2}>
                {byCategory.map((_,i)=><Cell key={i} fill={COLORS[i%COLORS.length]}/>)}
              </Pie>
              <Tooltip formatter={(v)=>[`${fmt(Number(v)/1000,1)}t CO₂e`]} contentStyle={{fontFamily:'Heebo',fontSize:11,borderRadius:'10px',border:'1px solid #e2e8f0'}}/>
              <Legend wrapperStyle={{fontSize:10,color:'#64748b'}}/>
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Map row */}
      <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-card">
        <div className="font-semibold text-sm text-slate-800 mb-1">פליטות לפי אזור גיאוגרפי</div>
        <div className="text-xs text-slate-400 mb-5">t CO₂e לפי אזור</div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-center">
          <IsraelMap north={byRegion['צפון']||0} center={byRegion['מרכז']||0} south={byRegion['דרום']||0}/>
          <div className="space-y-5">
            {['צפון','מרכז','דרום'].map((r,i) => {
              const val = byRegion[r]||0;
              const maxV = Math.max(...Object.values(byRegion),1);
              const pct = Math.round(val/maxV*100);
              const pctOfTotal = kpis.totalE > 0 ? (val/kpis.totalE*100).toFixed(1) : '0';
              return (
                <div key={r}>
                  <div className="flex justify-between items-end mb-2">
                    <div>
                      <span className="text-sm font-semibold text-slate-700">{r}</span>
                      <span className="text-xs text-slate-400 mr-2">{pctOfTotal}%</span>
                    </div>
                    <span className="text-sm font-mono font-bold text-slate-600">{fmt(val/1000,1)}t</span>
                  </div>
                  <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                    <div className="h-full rounded-full transition-all" style={{width:`${pct}%`,background:COLORS[i]}}/>
                  </div>
                </div>
              );
            })}
            <div className="pt-3 border-t border-slate-100">
              <div className="flex justify-between text-xs text-slate-400">
                <span>ממוצע אמינות</span>
                <span className="font-semibold text-emerald-600">{(kpis.avgReliability*100).toFixed(0)}%</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
