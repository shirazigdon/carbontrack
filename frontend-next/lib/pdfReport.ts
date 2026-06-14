import { EmissionRow } from './api';

const PALETTE = ['#1b4332', '#2d6a4f', '#40916c', '#52b788', '#74c69d', '#8b6f47', '#5b9bd5', '#9b8fc7'];

function fmt(n: number, digits = 0): string {
  return n.toLocaleString('he-IL', { maximumFractionDigits: digits });
}

function esc(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

export function exportExecPdf(data: EmissionRow[], userName: string): void {
  if (!data.length) {
    alert('אין נתונים זמינים להכנת הדוח');
    return;
  }

  const curYear = new Date().getFullYear();
  const totalE  = data.reduce((s, r) => s + (r.emission_co2e || 0), 0);
  const yearE   = data.filter(r => r.year === curYear).reduce((s, r) => s + (r.emission_co2e || 0), 0);
  const totalW  = data.reduce((s, r) => s + (r.weight_kg || 0), 0);
  const projCount = new Set(data.map(r => r.project_name).filter(Boolean)).size;
  const avgRel  = data.length ? data.reduce((s, r) => s + (r.reliability_score || 0), 0) / data.length : 0;
  const today   = new Date().toLocaleDateString('he-IL', { year: 'numeric', month: 'long', day: 'numeric' });

  // By project — normalized: kg CO₂e per tonne of material
  const projMap: Record<string, {e: number; w: number}> = {};
  data.forEach(r => { const p = r.project_name || '?'; projMap[p] = projMap[p] || {e:0,w:0}; projMap[p].e += r.emission_co2e||0; projMap[p].w += r.weight_kg||0; });
  const byProject = Object.entries(projMap)
    .map(([name, {e, w}]) => ({ name, t: w > 0 ? e / (w / 1000) : 0 }))
    .sort((a, b) => b.t - a.t).slice(0, 7);
  const maxP = Math.max(...byProject.map(p => p.t), 1);
  const byProjectTotal = Object.entries(projMap)
    .map(([name, {e}]) => ({ name, t: e / 1000 }))
    .sort((a, b) => b.t - a.t).slice(0, 7);
  const maxPTotal  = Math.max(...byProjectTotal.map(p => p.t), 1);
  const topProjTotal = byProjectTotal[0];

  // By category
  const catMap: Record<string, number> = {};
  data.forEach(r => { const c = r.category || '?'; catMap[c] = (catMap[c] || 0) + (r.emission_co2e || 0); });
  const byCategory = Object.entries(catMap)
    .map(([name, v]) => ({ name, v }))
    .sort((a, b) => b.v - a.v).slice(0, 8);
  const totalCatE = byCategory.reduce((s, c) => s + c.v, 0);

  // By region
  const regMap: Record<string, number> = {};
  data.forEach(r => { const reg = r.region || '?'; regMap[reg] = (regMap[reg] || 0) + (r.emission_co2e || 0); });
  const REGIONS = ['צפון', 'מרכז', 'דרום'];
  const maxReg = Math.max(...REGIONS.map(r => regMap[r] || 0), 1);

  // Conic gradient for donut chart
  let acc = 0;
  const conicParts = byCategory.map((c, i) => {
    const pct = totalCatE > 0 ? c.v / totalCatE * 100 : 0;
    const seg = `${PALETTE[i % PALETTE.length]} ${acc.toFixed(1)}% ${(acc + pct).toFixed(1)}%`;
    acc += pct;
    return seg;
  });
  const donutGrad = `conic-gradient(${conicParts.join(', ')})`;

  const totalRows = data.length;

  const barRows = (items: { name: string; t: number }[], max: number, unit = 't') =>
    items.map((p, i) => `
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:9px">
        <div style="font-size:10px;color:#475569;width:165px;flex-shrink:0;text-align:right;white-space:nowrap;overflow:hidden;text-overflow:ellipsis" title="${esc(p.name)}">${esc(p.name)}</div>
        <div style="flex:1;height:22px;background:#f1f5f9;border-radius:5px;overflow:hidden;position:relative">
          <div style="position:absolute;right:0;top:0;height:100%;width:${Math.round(p.t / max * 100)}%;background:${PALETTE[i % PALETTE.length]};border-radius:5px"></div>
        </div>
        <div style="font-size:10px;color:#64748b;font-weight:700;width:65px;flex-shrink:0;text-align:left">${fmt(p.t, 1)} ${unit}</div>
      </div>`).join('');

  const html = `<!DOCTYPE html>
<html dir="rtl" lang="he">
<head>
<meta charset="UTF-8">
<title>דוח מנהלים – CarbonTrack</title>
<link href="https://fonts.googleapis.com/css2?family=Heebo:wght@400;600;700;800;900&display=swap" rel="stylesheet">
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: 'Heebo', 'Arial Hebrew', Arial, sans-serif;
    background: #ffffff;
    direction: rtl;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
    color: #1a1a1a;
  }
  @page { size: A4 portrait; margin: 0; }
  @media print { .page-break { page-break-after: always; } }
  .section-label {
    font-size: 9px; font-weight: 700; color: #52b788;
    margin-bottom: 10px; letter-spacing: 1px; text-transform: uppercase;
  }
  .footer {
    padding: 10px 36px;
    border-top: 1px solid #e8f5ee;
    background: #f7fbf7;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .footer span { font-size: 8px; color: #94a3b8; }
  table { width: 100%; border-collapse: collapse; font-size: 10px; }
  thead tr { background: #1b4332; color: #fff; }
  thead th { padding: 9px 12px; text-align: right; font-weight: 700; }
  thead th:first-child { border-radius: 8px 0 0 0; }
  thead th:last-child { border-radius: 0 8px 0 0; }
  tbody tr:nth-child(even) { background: #f7fbf7; }
  tbody tr { border-bottom: 1px solid #e8f5ee; }
  tbody td { padding: 8px 12px; color: #475569; }
</style>
</head>
<body>

<!-- ══════════════ PAGE 1 ══════════════ -->
<div class="page-break" style="width:210mm;background:#fff">

  <!-- Header -->
  <div style="background:linear-gradient(135deg,#1b4332 0%,#2d6a4f 60%,#40916c 100%);padding:28px 36px 24px;display:flex;justify-content:space-between;align-items:flex-start">
    <div>
      <div style="color:#95d5b2;font-size:10px;font-weight:700;letter-spacing:1px;margin-bottom:8px">נתיבי ישראל — ניהול תשתיות בע"מ</div>
      <div style="color:#fff;font-size:24px;font-weight:900;margin-bottom:7px">דוח מנהלים – פליטות פחמן</div>
      <div style="color:rgba(255,255,255,0.65);font-size:11px">הוכן עבור: ${esc(userName)} &nbsp;·&nbsp; ${today}</div>
      <div style="color:rgba(255,255,255,0.5);font-size:10px;margin-top:4px">תקופה: ינואר 2025 – דצמבר 2025</div>
    </div>
    <div style="text-align:left;margin-top:4px">
      <div style="color:#95d5b2;font-size:17px;font-weight:900">🌿 CarbonTrack</div>
      <div style="color:rgba(255,255,255,0.4);font-size:9px;margin-top:8px;line-height:1.6">מערכת ניהול פליטות פחמן</div>
    </div>
  </div>

  <!-- KPI Strip -->
  <div style="padding:16px 36px 14px;background:#f7fbf7;border-bottom:1.5px solid #d8f3dc">
    <div class="section-label">מדדי ביצוע עיקריים</div>
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px">
      ${[
        { label: 'סה"כ פליטות', val: `${fmt(totalE / 1000, 1)}t`, sub: 'כלל הפרויקטים', color: '#2d6a4f' },
        { label: 'פרויקטים פעילים', val: `${projCount}`, sub: 'במאגר הנתונים', color: '#40916c' },
        { label: 'אמינות ממוצעת', val: `${Math.round(avgRel * 100)}%`, sub: 'ציון אמינות נתונים', color: '#52b788' },
      ].map(({ label, val, sub, color }) => `
        <div style="background:#fff;border-radius:10px;padding:13px 14px;border:1px solid #d8f3dc;box-shadow:0 2px 8px rgba(27,67,50,0.05)">
          <div style="font-size:9px;color:#6b9e75;font-weight:600;margin-bottom:6px">${label}</div>
          <div style="font-size:22px;font-weight:900;color:${color};margin-bottom:3px">${val}</div>
          <div style="font-size:9px;color:#94a3b8">${sub}</div>
        </div>`).join('')}
    </div>
  </div>

  <!-- Insights Row -->
  <div style="padding:14px 36px;border-bottom:1px solid #e8f5ee">
    <div class="section-label">תובנות מפתח</div>
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px">
      <div style="background:#eef8f2;border-radius:10px;padding:12px 14px;border:1px solid #b7e4c7">
        <div style="font-size:9px;color:#40916c;font-weight:700;margin-bottom:5px">🏭 הפולט הגדול ביותר</div>
        <div style="font-size:12px;font-weight:800;color:#1b4332;margin-bottom:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${esc(topProjTotal?.name || '—')}</div>
        <div style="font-size:10px;color:#40916c">${topProjTotal ? fmt(topProjTotal.t, 1) + 't CO₂e' : ''}</div>
      </div>
      <div style="background:#fff8ee;border-radius:10px;padding:12px 14px;border:1px solid #fde68a">
        <div style="font-size:9px;color:#d97706;font-weight:700;margin-bottom:5px">🧱 חומר מזהם עיקרי</div>
        <div style="font-size:12px;font-weight:800;color:#78350f;margin-bottom:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${esc(byCategory[0]?.name || '—')}</div>
        <div style="font-size:10px;color:#d97706">${byCategory[0] ? fmt(byCategory[0].v / 1000, 1) + 't CO₂e' : ''}</div>
      </div>
      <div style="background:#f0f4ff;border-radius:10px;padding:12px 14px;border:1px solid #c7d2fe">
        <div style="font-size:9px;color:#6366f1;font-weight:700;margin-bottom:5px">📦 משקל חומרים כולל</div>
        <div style="font-size:12px;font-weight:800;color:#312e81;margin-bottom:3px">${fmt(totalW / 1000, 1)}t</div>
        <div style="font-size:10px;color:#6366f1">${totalRows.toLocaleString('he-IL')} רשומות</div>
      </div>
    </div>
  </div>

  <!-- Bar Chart 1: פליטות כוללות לפי פרויקט -->
  <div style="padding:14px 36px 10px;border-bottom:1px solid #f1f5f9">
    <div style="font-size:13px;font-weight:700;color:#1b4332;margin-bottom:2px">פליטות כוללות לפי פרויקט</div>
    <div style="font-size:9px;color:#94a3b8;margin-bottom:12px">t CO₂e – סה"כ פליטות לכל פרויקט בתקופה · ${byProjectTotal.length} פרויקטים</div>
    ${barRows(byProjectTotal, maxPTotal, 't')}
  </div>

  <!-- Bar Chart 2: השוואה מנורמלת (בסוף) -->
  <div style="padding:14px 36px 12px">
    <div style="font-size:13px;font-weight:700;color:#475569;margin-bottom:2px">השוואת אינטנסיביות פליטות בין פרויקטים</div>
    <div style="font-size:9px;color:#94a3b8;margin-bottom:12px">ק"ג CO₂e לטון חומר (נורמלי לפי משקל) – מי מזהם יותר לטון?</div>
    ${barRows(byProject, maxP, 'kg/t')}
  </div>

  <div class="footer">
    <span>נתיבי ישראל</span>
    <span>עמ' 1 מתוך 2 · הופק: ${today}</span>
  </div>
</div>

<!-- ══════════════ PAGE 2 ══════════════ -->
<div style="width:210mm;background:#fff">

  <!-- Mini Header -->
  <div style="background:#1b4332;padding:12px 36px;display:flex;justify-content:space-between;align-items:center">
    <div style="color:#95d5b2;font-size:12px;font-weight:700">🌿 CarbonTrack – דוח מנהלים</div>
    <div style="color:rgba(255,255,255,0.55);font-size:10px">פילוח מפורט · עמ' 2 מתוך 2</div>
  </div>

  <!-- Two-Column: Donut + Region -->
  <div style="padding:18px 36px;display:grid;grid-template-columns:1fr 1fr;gap:28px;border-bottom:1px solid #e8f5ee">

    <!-- Donut -->
    <div>
      <div style="font-size:13px;font-weight:700;color:#1b4332;margin-bottom:3px">פילוח לפי חומר</div>
      <div style="font-size:9px;color:#94a3b8;margin-bottom:14px">אחוז מסך הפליטות</div>
      <div style="display:flex;flex-direction:column;align-items:center">
        <div style="width:150px;height:150px;border-radius:50%;background:${donutGrad};position:relative;flex-shrink:0">
          <div style="position:absolute;width:94px;height:94px;background:#fff;border-radius:50%;top:50%;left:50%;transform:translate(-50%,-50%);display:flex;flex-direction:column;align-items:center;justify-content:center">
            <div style="font-size:18px;font-weight:900;color:#1b4332">${byCategory.length}</div>
            <div style="font-size:8px;color:#94a3b8">חומרים</div>
            <div style="font-size:7px;color:#b0bec5;margin-top:1px">עיקריים</div>
          </div>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:3px 10px;margin-top:12px;width:100%">
          ${byCategory.map((c, i) => `
            <div style="display:flex;align-items:center;gap:5px;font-size:8px;color:#475569;white-space:nowrap;overflow:hidden">
              <div style="width:8px;height:8px;border-radius:2px;background:${PALETTE[i % PALETTE.length]};flex-shrink:0"></div>
              <span style="overflow:hidden;text-overflow:ellipsis">${esc(c.name)}</span>
            </div>`).join('')}
        </div>
      </div>
    </div>

    <!-- Region Breakdown -->
    <div>
      <div style="font-size:13px;font-weight:700;color:#1b4332;margin-bottom:3px">פליטות לפי אזור</div>
      <div style="font-size:9px;color:#94a3b8;margin-bottom:20px">t CO₂e לפי אזור גיאוגרפי</div>
      ${REGIONS.map((r, i) => {
        const val = regMap[r] || 0;
        const pct = totalE > 0 ? (val / totalE * 100).toFixed(1) : '0';
        const barW = Math.round(val / maxReg * 100);
        return `
        <div style="margin-bottom:18px">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
            <div>
              <span style="font-size:13px;font-weight:700;color:#1b4332">${r}</span>
              <span style="font-size:9px;color:#94a3b8;margin-right:6px">${pct}%</span>
            </div>
            <span style="font-size:12px;font-weight:700;color:#40916c">${fmt(val / 1000, 1)}t</span>
          </div>
          <div style="height:12px;background:#f1f5f9;border-radius:6px;overflow:hidden;position:relative">
            <div style="position:absolute;right:0;top:0;height:100%;width:${barW}%;background:${PALETTE[i]};border-radius:6px"></div>
          </div>
        </div>`;
      }).join('')}
    </div>
  </div>

  <!-- Categories Table -->
  <div style="padding:16px 36px 14px">
    <div style="font-size:13px;font-weight:700;color:#1b4332;margin-bottom:3px">ריכוז חומרים לפי פליטות</div>
    <div style="font-size:9px;color:#94a3b8;margin-bottom:12px">ממוין לפי סך CO₂e – ${byCategory.length} חומרים מובילים</div>
    <table>
      <thead>
        <tr>
          <th style="width:32px">#</th>
          <th>חומר</th>
          <th>פליטות (t CO₂e)</th>
          <th>% מהסך</th>
        </tr>
      </thead>
      <tbody>
        ${byCategory.map((cat, i) => `
          <tr>
            <td style="color:#94a3b8;font-weight:700;text-align:center">${i + 1}</td>
            <td style="color:#1b4332;font-weight:600">
              <span style="display:inline-block;width:8px;height:8px;border-radius:2px;background:${PALETTE[i % PALETTE.length]};margin-left:7px;vertical-align:middle"></span>
              ${esc(cat.name)}
            </td>
            <td style="color:#40916c;font-weight:700">${fmt(cat.v / 1000, 1)}t</td>
            <td style="color:#64748b">${totalE > 0 ? (cat.v / totalE * 100).toFixed(1) : '0'}%</td>
          </tr>`).join('')}
      </tbody>
    </table>
  </div>

  <!-- Reliability summary -->
  <div style="padding:12px 36px 14px;border-top:1px solid #f1f5f9">
    <div style="font-size:9px;color:#94a3b8;font-weight:600;margin-bottom:8px">פירוט אמינות נתונים</div>
    <div style="display:flex;gap:14px;flex-wrap:wrap">
      ${[
        { label: 'גבוהה (≥0.9)', count: data.filter(r => r.reliability_score >= 0.9).length, color: '#40916c' },
        { label: 'בינונית (0.7–0.9)', count: data.filter(r => r.reliability_score >= 0.7 && r.reliability_score < 0.9).length, color: '#d97706' },
        { label: 'נמוכה (<0.7)', count: data.filter(r => r.reliability_score < 0.7).length, color: '#dc2626' },
      ].map(({ label, count, color }) => `
        <div style="display:flex;align-items:center;gap:6px;font-size:9px;color:#475569">
          <div style="width:10px;height:10px;border-radius:50%;background:${color}"></div>
          ${label}: <strong style="color:${color}">${count.toLocaleString('he-IL')} (${totalRows ? Math.round(count / totalRows * 100) : 0}%)</strong>
        </div>`).join('')}
    </div>
  </div>

  <div class="footer">
    <span>נתיבי ישראל</span>
    <span>עמ' 2 מתוך 2 · הופק: ${today}</span>
  </div>
</div>

<script>
  document.fonts.ready.then(function() {
    setTimeout(function() { window.print(); }, 500);
  });
</script>
</body>
</html>`;

  const win = window.open('', '_blank', 'width=900,height=720');
  if (!win) {
    alert('לא ניתן לפתוח חלון הדפסה. אנא אשר חלונות קופצים לאתר זה ונסה שנית.');
    return;
  }
  win.document.write(html);
  win.document.close();
}
