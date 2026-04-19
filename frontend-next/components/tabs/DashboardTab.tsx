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

const COLORS = ['hsl(142,55%,35%)','hsl(152,45%,42%)','hsl(85,50%,45%)','hsl(38,92%,50%)','hsl(170,50%,40%)','hsl(120,40%,50%)'];

interface Props { data: EmissionRow[]; reviewCount: number; }

export function DashboardTab({ data, reviewCount }: Props) {
  const [barMode, setBarMode] = useState<'total'|'normalized'>('total');
  const curYear = new Date().getFullYear();

  const kpis = useMemo(() => {
    const totalE = data.reduce((s,r) => s+(r.emission_co2e||0), 0);
    const yearlyE = data.filter(r=>(r.year||0)===curYear).reduce((s,r)=>s+(r.emission_co2e||0),0);
    const totalW = data.reduce((s,r)=>s+(r.weight_kg||0),0);
    return { totalE, yearlyE, totalW };
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
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard title={`פליטות ${curYear}`} value={`${fmt(kpis.yearlyE/1000)}t`} subtitle="kg CO₂e" variant="primary"/>
        <KpiCard title='סה"כ פליטות' value={`${fmt(kpis.totalE/1000)}t`} subtitle="מתחילת הפרויקט" badge="↓ 8.3%" badgeType="down"/>
        <KpiCard title="משקל חומרים" value={`${fmt(kpis.totalW/1000)}t`} subtitle='ק"ג'/>
        <KpiCard title="שורות Review" value={`${reviewCount}`} subtitle="ממתינות לאישור" variant={reviewCount===0?'accent':'default'}/>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        <div className="lg:col-span-3 bg-card border border-border rounded-xl p-5 shadow-card">
          <div className="flex items-center justify-between mb-4">
            <div className="font-semibold text-sm text-gray-800">📊 פליטות לפי פרויקט</div>
            <div className="flex gap-1 bg-muted rounded-lg p-1">
              {(['total','normalized'] as const).map(m => (
                <button key={m} onClick={()=>setBarMode(m)}
                  className={`text-xs px-3 py-1 rounded-md transition-colors ${barMode===m?'bg-white shadow-sm font-semibold':'text-gray-500'}`}>
                  {m==='total'?'סה"כ':'נורמלי לטון'}
                </button>
              ))}
            </div>
          </div>
          <ResponsiveContainer width="100%" height={Math.max(200, byProject.length*44)}>
            <BarChart data={byProject} layout="vertical" margin={{left:8,right:56,top:4,bottom:4}}>
              <XAxis type="number" tick={{fontSize:11}} tickFormatter={v=>`${fmt(v)}`}/>
              <YAxis type="category" dataKey="name" width={130} tick={{fontSize:11}}/>
              <Tooltip formatter={(v)=>[`${fmt(Number(v))} ${barMode==='total'?'t CO₂e':'kg/t'}`,'']} contentStyle={{fontFamily:'Heebo',fontSize:12}}/>
              <Bar dataKey={barMode==='total'?'total':'normalized'} fill={COLORS[0]} radius={[0,4,4,0]}
                label={{position:'right',fontSize:10,formatter:(v: unknown)=>fmt(Number(v))}}/>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="lg:col-span-2 bg-card border border-border rounded-xl p-5 shadow-card">
          <div className="font-semibold text-sm text-gray-800 mb-3">🧱 פילוח חומרים</div>
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie data={byCategory} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={50} outerRadius={85}>
                {byCategory.map((_,i)=><Cell key={i} fill={COLORS[i%COLORS.length]}/>)}
              </Pie>
              <Tooltip formatter={(v)=>[`${fmt(Number(v)/1000)}t CO₂e`]} contentStyle={{fontFamily:'Heebo',fontSize:11}}/>
              <Legend wrapperStyle={{fontSize:10}}/>
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="bg-card border border-border rounded-xl p-5 shadow-card">
        <div className="font-semibold text-sm text-gray-800 mb-4">🗺️ פליטות לפי אזור</div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-center">
          <IsraelMap north={byRegion['צפון']||0} center={byRegion['מרכז']||0} south={byRegion['דרום']||0}/>
          <div className="space-y-4">
            {['צפון','מרכז','דרום'].map(r => {
              const val = byRegion[r]||0;
              const maxV = Math.max(...Object.values(byRegion),1);
              const pct = Math.round(val/maxV*100);
              return (
                <div key={r}>
                  <div className="flex justify-between text-sm mb-1.5">
                    <span className="font-medium">{r}</span>
                    <span className="text-muted-fg text-xs">{fmt(val/1000)}t CO₂e</span>
                  </div>
                  <div className="h-2.5 bg-muted rounded-full overflow-hidden">
                    <div className="h-full rounded-full transition-all" style={{width:`${pct}%`,background:'var(--grad-primary)'}}/>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
