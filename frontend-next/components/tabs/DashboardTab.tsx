'use client';
import { useMemo, useState } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell,
} from 'recharts';
import { KpiCard } from '../KpiCard';
import { IsraelMap } from '../IsraelMap';
import { EmissionRow } from '../../lib/api';
import { fmt } from '../../lib/utils';

const COLORS = [
  '#5b9bd5', '#52b788', '#e8a87c', '#9b8fc7',
  '#e07b7b', '#f59e0b', '#6366f1', '#14b8a6',
  '#ec4899', '#8b6f47', '#f97316', '#10b981',
];

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
    return Object.entries(map)
      .map(([name,value]) => ({name,value}))
      .sort((a,b) => b.value - a.value)
      .slice(0, 8);
  }, [data]);

  const byRegion = useMemo(() => {
    const map: Record<string,number> = {};
    data.forEach(r => { const reg=r.region||'Unknown'; map[reg]=(map[reg]||0)+(r.emission_co2e||0); });
    return map;
  }, [data]);

  const byCategoryFactor = useMemo(() => {
    const map: Record<string,{e:number;w:number}> = {};
    data.forEach(r => {
      const c = r.category || 'Unknown';
      map[c] = map[c] || { e: 0, w: 0 };
      map[c].e += r.emission_co2e || 0;
      map[c].w += r.weight_kg || 0;
    });
    return Object.entries(map)
      .map(([name, { e, w }]) => ({ name, factor: w > 0 ? e / w : 0 }))
      .filter(item => item.name !== 'Unknown' && item.factor > 0)
      .sort((a, b) => b.factor - a.factor)
      .slice(0, 10);
  }, [data]);

  const totalCatE = byCategory.reduce((s, c) => s + c.value, 0);

  const cardStyle = { background: '#ffffff', border: '1.5px solid #b7e4c7', boxShadow: '0 4px 24px rgba(27,67,50,0.08)' };

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
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* Bar: by project */}
        <div className="rounded-3xl p-6 lg:p-8" style={cardStyle}>
          <div className="flex items-center justify-between mb-5">
            <div>
              <div className="font-bold text-base text-slate-800">פליטות לפי פרויקט</div>
              <div className="text-xs text-slate-400 mt-0.5 font-medium">t CO₂e</div>
            </div>
            <div className="flex gap-1 bg-slate-100 rounded-lg p-0.5">
              {(['total','normalized'] as const).map(m => (
                <button key={m} onClick={()=>setBarMode(m)}
                  className={`text-xs px-3 py-1.5 rounded-md transition-all font-semibold ${barMode===m?'bg-white shadow-sm text-slate-800':'text-slate-500 hover:text-slate-700'}`}>
                  {m==='total'?'סה"כ':'נורמלי'}
                </button>
              ))}
            </div>
          </div>
          <ResponsiveContainer width="100%" height={Math.max(360, byProject.length*46)}>
            <BarChart data={byProject} layout="vertical" margin={{left:8,right:60,top:36,bottom:4}}>
              <XAxis type="number" tick={{fontSize:10,fill:'#94a3b8'}} tickFormatter={v=>`${fmt(v)}`} axisLine={false} tickLine={false}/>
              <YAxis type="category" dataKey="name" width={130} tick={{fontSize:11,fill:'#475569',fontWeight:600}} axisLine={false} tickLine={false}/>
              <Tooltip
                formatter={(v)=>[`${fmt(Number(v),1)} ${barMode==='total'?'t CO₂e':'kg/t'}`,'']}
                contentStyle={{fontFamily:'Heebo',fontSize:12,borderRadius:'12px',border:'1px solid #e2e8f0',boxShadow:'0 4px 12px rgba(0,0,0,0.08)'}}
              />
              <Bar dataKey={barMode==='total'?'total':'normalized'} fill="#5b9bd5" radius={[0,6,6,0]}
                label={{position:'right',fontSize:11,fill:'#64748b',fontWeight:700,formatter:(v: unknown)=>fmt(Number(v),1)}}/>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Pie: by category — chart left, legend right */}
        <div className="rounded-3xl p-6 lg:p-8" style={cardStyle}>
          <div className="font-bold text-base text-slate-800 mb-0.5">פילוח לפי חומר</div>
          <div className="text-xs text-slate-400 font-medium mb-4">8 חומרים מובילים · % מסך הפליטות</div>
          <div className="flex gap-4 items-center">
            {/* Pie */}
            <div className="flex-shrink-0" style={{width:200}}>
              <ResponsiveContainer width={200} height={200}>
                <PieChart>
                  <Pie data={byCategory} dataKey="value" nameKey="name"
                    cx="50%" cy="50%" innerRadius={55} outerRadius={88} paddingAngle={2}>
                    {byCategory.map((_,i)=><Cell key={i} fill={COLORS[i%COLORS.length]}/>)}
                  </Pie>
                  <Tooltip
                    formatter={(v)=>[`${fmt(Number(v)/1000,1)}t CO₂e`]}
                    contentStyle={{fontFamily:'Heebo',fontSize:12,borderRadius:'10px',border:'1px solid #e2e8f0',boxShadow:'0 4px 12px rgba(0,0,0,0.08)'}}/>
                </PieChart>
              </ResponsiveContainer>
            </div>
            {/* External legend */}
            <div className="flex-1 space-y-2 min-w-0">
              {byCategory.map((cat, i) => {
                const pct = totalCatE > 0 ? (cat.value / totalCatE * 100) : 0;
                return (
                  <div key={cat.name} className="flex items-center gap-2">
                    <div className="flex-shrink-0 rounded-sm" style={{width:10,height:10,background:COLORS[i%COLORS.length]}}/>
                    <span className="text-xs text-slate-600 font-medium flex-1 truncate min-w-0">{cat.name}</span>
                    <span className="text-xs font-bold text-slate-700 flex-shrink-0">{fmt(cat.value/1000,1)}t</span>
                    <span className="text-[10px] text-slate-400 flex-shrink-0 w-8 text-left">{pct.toFixed(0)}%</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Relative Pollution Chart */}
      <div className="rounded-3xl p-6 lg:p-8" style={cardStyle}>
        <div className="font-bold text-base text-slate-800 mb-0.5">זיהום יחסי לפי חומר (פקטור פליטה)</div>
        <div className="text-xs text-slate-400 font-medium mb-8">ק"ג CO₂e לכל ק"ג חומר (10 המזהמים ביותר)</div>
        <ResponsiveContainer width="100%" height={400}>
          <BarChart data={byCategoryFactor} margin={{left:8,right:16,top:40,bottom:12}}>
            <XAxis dataKey="name" tick={{fontSize:10,fill:'#475569',fontWeight:600}} axisLine={false} tickLine={false} />
            <YAxis tick={{fontSize:10,fill:'#94a3b8'}} axisLine={false} tickLine={false} />
            <Tooltip
              formatter={(v)=>[`${Number(v).toFixed(3)} kg/kg`,'']}
              contentStyle={{fontFamily:'Heebo',fontSize:12,borderRadius:'12px',border:'1px solid #e2e8f0',boxShadow:'0 4px 12px rgba(0,0,0,0.08)'}}
            />
            <Bar dataKey="factor" fill="#e8a87c" radius={[6,6,0,0]} maxBarSize={50}
                label={{position:'top',fontSize:11,fill:'#64748b',fontWeight:700,formatter:(v: unknown)=>Number(v).toFixed(2)}}/>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Map row */}
      <div className="rounded-2xl p-5" style={{ background: '#ffffff', border: '1.5px solid #b7e4c7', boxShadow: '0 2px 12px rgba(27,67,50,0.07)' }}>
        <div className="font-bold text-sm text-slate-800 mb-0.5">פליטות לפי אזור גיאוגרפי</div>
        <div className="text-xs text-slate-400 font-medium mb-5">t CO₂e לפי אזור</div>
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
                      <span className="text-sm font-bold text-slate-700">{r}</span>
                      <span className="text-xs text-slate-400 mr-2">{pctOfTotal}%</span>
                    </div>
                    <span className="text-sm font-bold text-slate-600">{fmt(val/1000,1)}t</span>
                  </div>
                  <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                    <div className="h-full rounded-full transition-all" style={{width:`${pct}%`,background:COLORS[i]}}/>
                  </div>
                </div>
              );
            })}
            <div className="pt-3 border-t border-slate-100">
              <div className="flex justify-between text-xs text-slate-400">
                <span className="font-medium">ממוצע אמינות</span>
                <span className="font-bold text-emerald-600">{Math.round(kpis.avgReliability * 100)}%</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
