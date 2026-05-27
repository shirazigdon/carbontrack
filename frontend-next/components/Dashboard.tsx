'use client';
import { useState, useEffect, useMemo, useCallback } from 'react';
import { useAuth } from '../lib/auth';
import { Sidebar } from './Sidebar';
import { DashboardTab } from './tabs/DashboardTab';
import { ReviewTab } from './tabs/ReviewTab';
import { WhatIfTab } from './tabs/WhatIfTab';
import { AiTab } from './tabs/AiTab';
import { UploadTab } from './tabs/UploadTab';
import { DataTab } from './tabs/DataTab';
import { SettingsTab } from './tabs/SettingsTab';
import { AiBubble } from './AiBubble';
import { HomeTab } from './tabs/HomeTab';
import { fetchEmissions, fetchReview, fetchProjects, EmissionRow, ReviewRow } from '../lib/api';

const TAB_META: Record<string, { label: string; desc: string }> = {
  home:      { label: 'עמוד הבית', desc: 'סקירה מהירה וניווט למערכת' },
  dashboard: { label: 'דאשבורד', desc: 'סקירה כללית של פליטות פחמן' },
  review:    { label: 'תור סקירה', desc: 'אישור ודחיית רשומות' },
  whatif:    { label: 'סימולטור What-If', desc: 'השוואת חלופות חומרים' },
  ai:        { label: 'עוזר AI', desc: 'שאל שאלות על הנתונים' },
  upload:    { label: 'קליטת קבצים', desc: 'העלאת קבצי פליטות חדשים' },
  data:      { label: 'נתונים גולמיים', desc: 'כל הרשומות במאגר' },
  settings:  { label: 'הגדרות', desc: 'ניהול סף אמינות ומחירון' },
};

interface Settings {
  reliabilityThreshold: number;
  maxClimatiqCandidates: number;
  maxFactorSpreadPct: number;
  autoWriteAiApproved: boolean;
}

export function Dashboard({ demoMode = false }: { demoMode?: boolean }) {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState('home');
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [emissions, setEmissions] = useState<EmissionRow[]>([]);
  const [review, setReview] = useState<ReviewRow[]>([]);
  const [projects, setProjects] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  const [settings, setSettings] = useState<Settings>({
    reliabilityThreshold: 0.85,
    maxClimatiqCandidates: 5,
    maxFactorSpreadPct: 15,
    autoWriteAiApproved: true,
  });

  const [selectedYear, setSelectedYear]           = useState<number | null>(null);
  const [selectedRegions, setSelectedRegions]     = useState<string[]>([]);
  const [selectedProject, setSelectedProject]     = useState<string>('');
  const [selectedContractor, setSelectedContractor] = useState<string>('');
  const [reliabilityThreshold, setReliabilityThreshold] = useState(0.85);

  const years = useMemo(() =>
    Array.from(new Set(emissions.map(r => r.year).filter(Boolean) as number[])).sort((a, b) => b - a),
  [emissions]);

  const regions = useMemo(() =>
    Array.from(new Set(emissions.map(r => r.region).filter(Boolean) as string[])).sort(),
  [emissions]);

  const allProjects = useMemo(() =>
    Array.from(new Set(emissions.map(r => r.project_name).filter(Boolean) as string[])).sort(),
  [emissions]);

  const allContractors = useMemo(() =>
    Array.from(new Set(emissions.map(r => r.contractor).filter(Boolean) as string[])).sort(),
  [emissions]);

  const filteredEmissions = useMemo(() => {
    return emissions.filter(r => {
      if (selectedYear && r.year !== selectedYear) return false;
      if (selectedRegions.length && !selectedRegions.includes(r.region)) return false;
      if (selectedProject && r.project_name !== selectedProject) return false;
      if (selectedContractor && r.contractor !== selectedContractor) return false;
      return true;
    });
  }, [emissions, selectedYear, selectedRegions, selectedProject, selectedContractor]);

  const loadData = useCallback(async (project?: string) => {
    if (demoMode) {
      const rows = project ? DEMO_EMISSIONS.filter(r => r.project_name === project) : DEMO_EMISSIONS;
      setEmissions(rows);
      setProjects([...new Set(DEMO_EMISSIONS.map(r => r.project_name))]);
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const [emRes, revRes, projRes] = await Promise.allSettled([
        fetchEmissions(project),
        fetchReview(),
        fetchProjects(),
      ]);
      if (emRes.status === 'fulfilled') {
        const rows = emRes.value.items.map(r => ({
          ...r,
          year: r.year || (r.calculation_date ? new Date(r.calculation_date).getFullYear() : new Date().getFullYear()),
        }));
        setEmissions(rows);
      } else {
        setEmissions(MOCK_EMISSIONS);
      }
      if (revRes.status === 'fulfilled') setReview(revRes.value.items);
      if (projRes.status === 'fulfilled') setProjects(projRes.value.projects);
    } catch {
      setEmissions(MOCK_EMISSIONS);
    }
    setLoading(false);
  }, [demoMode]);

  useEffect(() => { loadData(); }, [loadData]);

  const meta = TAB_META[activeTab];

  const displayName = demoMode ? 'מבקר' : (user?.name || user?.email || '');

  return (
    <div className="flex h-screen overflow-hidden relative" style={{ background: '#f7fbf7' }}>
      
      {/* Demo mode banner */}
      {demoMode && (
        <div className="fixed top-0 left-0 right-0 z-[100] text-center text-xs font-semibold py-1.5 text-white" style={{ background: 'linear-gradient(90deg,#2d6a4f,#40916c,#2d6a4f)', letterSpacing: '0.05em' }}>
          🌿 מצב הדגמה — נתונים לדוגמה בלבד
        </div>
      )}

      {/* Mobile overlay */}
      {isSidebarOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-40 md:hidden"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      {/* Sidebar wrapper */}
      <div className={`
        fixed inset-y-0 right-0 z-50 transform transition-transform duration-300 ease-in-out
        md:relative md:translate-x-0
        ${isSidebarOpen ? 'translate-x-0' : 'translate-x-full'}
      `}>
        <Sidebar
          activeTab={activeTab}
          onTabChange={(tab) => { setActiveTab(tab); setIsSidebarOpen(false); }}
          reviewCount={review.length}
          filters={{
            projects: allProjects,
            selectedProject,
            contractors: allContractors,
            selectedContractor,
            regions,
            selectedRegions,
            years,
            selectedYear,
            reliabilityThreshold,
            onProjectChange: (p: string) => {
              setSelectedProject(p);
              loadData(p || undefined);
            },
            onContractorChange: setSelectedContractor,
            onRegionsChange: setSelectedRegions,
            onYearChange: setSelectedYear,
            onReliabilityChange: setReliabilityThreshold,
          }}
        />
      </div>

      <main className={`flex-1 overflow-y-auto flex flex-col min-w-0 ${demoMode ? 'mt-7' : ''}`}>
        {/* Top header */}
        <header className="sticky top-0 z-10 border-b px-4 md:px-6 py-0 flex-shrink-0" style={{ background: 'rgba(247,251,247,0.9)', backdropFilter: 'blur(14px)', borderColor: '#b7e4c7' }}>
          <div className="flex items-center justify-between h-14">
            <div className="flex items-center gap-2 md:gap-3">
              <button 
                onClick={() => setIsSidebarOpen(true)}
                className="md:hidden p-1.5 -mr-1.5 text-slate-600 rounded-lg hover:bg-slate-100"
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="3" y1="12" x2="21" y2="12"></line><line x1="3" y1="6" x2="21" y2="6"></line><line x1="3" y1="18" x2="21" y2="18"></line></svg>
              </button>
              <div>
                <div className="font-semibold text-sm" style={{ color: '#1b4332' }}>{meta.label}</div>
                <div className="text-[11px] text-slate-400 leading-tight">{meta.desc}</div>
              </div>
            </div>
            <div className="flex items-center gap-2 md:gap-3">
              {loading && (
                <div className="hidden md:flex items-center gap-1.5 text-xs text-slate-400">
                  <div className="w-3 h-3 border-2 border-slate-300 border-t-emerald-500 rounded-full animate-spin" />
                  טוען...
                </div>
              )}
              <div className="flex items-center gap-1.5 text-xs rounded-full px-2 md:px-3 py-1" style={{ color: '#4a7c59', background: '#d8f3e3', border: '1px solid #b7e4c7' }}>
                <span className="w-1.5 h-1.5 rounded-full inline-block" style={{ background: '#52b788' }} />
                <span className="hidden md:inline">{emissions.length.toLocaleString()} רשומות</span>
                <span className="md:hidden">{emissions.length}</span>
              </div>
              <button onClick={() => loadData(selectedProject || undefined)}
                className="w-8 h-8 flex items-center justify-center rounded-full border border-slate-200 text-slate-400 hover:text-slate-600 hover:border-slate-300 hover:bg-slate-50 transition-all text-sm">
                ↻
              </button>
            </div>
          </div>
        </header>

        {/* Content */}
        <div className="flex-1 p-6 tab-content">
          {activeTab === 'home'      && <HomeTab data={filteredEmissions} reviewCount={review.length} userName={displayName} onNavigate={setActiveTab} />}
          {activeTab === 'dashboard' && <DashboardTab data={filteredEmissions} reviewCount={review.length} />}
          {activeTab === 'review'    && <ReviewTab data={review} onRefresh={loadData} reliabilityThreshold={reliabilityThreshold} />}
          {activeTab === 'whatif'    && <WhatIfTab data={filteredEmissions} />}
          {activeTab === 'ai'        && <AiTab data={filteredEmissions} />}
          {activeTab === 'upload'    && <UploadTab userEmail={user?.email || ''} settings={settings} />}
          {activeTab === 'data'      && <DataTab data={filteredEmissions} />}
          {activeTab === 'settings'  && <SettingsTab settings={settings} onSettingsChange={setSettings} projects={projects} onProjectDeleted={loadData} />}
        </div>
      </main>

      <AiBubble data={filteredEmissions} />
    </div>
  );
}

const MOCK_EMISSIONS: EmissionRow[] = [
  { project_name: 'כביש 6 - מקטע צפון', contractor: 'שפיר הנדסה', region: 'צפון', category: 'Steel Rebar', weight_kg: 125000, emission_co2e: 231250, reliability_score: 0.92, matched_by: 'exact_match', year: 2026 },
  { project_name: 'כביש 6 - מקטע צפון', contractor: 'שפיר הנדסה', region: 'צפון', category: 'Structural Concrete', weight_kg: 450000, emission_co2e: 148500, reliability_score: 0.88, matched_by: 'ai_match', year: 2026 },
  { project_name: 'מחלף גלילות', contractor: 'דניה סיבוס', region: 'מרכז', category: 'Asphalt', weight_kg: 320000, emission_co2e: 89600, reliability_score: 0.95, matched_by: 'exact_match', year: 2026 },
  { project_name: 'מחלף גלילות', contractor: 'דניה סיבוס', region: 'מרכז', category: 'Galvanized Steel', weight_kg: 85000, emission_co2e: 178500, reliability_score: 0.78, matched_by: 'ai_match', year: 2026 },
];

const DEMO_EMISSIONS: EmissionRow[] = [
  // ── כביש 6 – עמק יזרעאל (שפיר הנדסה, צפון) ──────────────────────────────
  { project_name: 'כביש 6 – מקטע עמק יזרעאל', contractor: 'שפיר הנדסה', region: 'צפון', category: 'Structural Concrete', weight_kg: 850000,  emission_co2e: 126650,  reliability_score: 0.94, matched_by: 'exact_match', year: 2026 },
  { project_name: 'כביש 6 – מקטע עמק יזרעאל', contractor: 'שפיר הנדסה', region: 'צפון', category: 'Steel Rebar',          weight_kg: 180000,  emission_co2e: 358200,  reliability_score: 0.96, matched_by: 'exact_match', year: 2026 },
  { project_name: 'כביש 6 – מקטע עמק יזרעאל', contractor: 'שפיר הנדסה', region: 'צפון', category: 'Asphalt',              weight_kg: 1200000, emission_co2e: 56640,   reliability_score: 0.97, matched_by: 'exact_match', year: 2026 },
  { project_name: 'כביש 6 – מקטע עמק יזרעאל', contractor: 'שפיר הנדסה', region: 'צפון', category: 'Fill Material',        weight_kg: 2500000, emission_co2e: 12000,   reliability_score: 0.91, matched_by: 'catalog_match', year: 2026 },
  { project_name: 'כביש 6 – מקטע עמק יזרעאל', contractor: 'שפיר הנדסה', region: 'צפון', category: 'Crushed Stone',        weight_kg: 820000,  emission_co2e: 3936,    reliability_score: 0.93, matched_by: 'catalog_match', year: 2026 },
  { project_name: 'כביש 6 – מקטע עמק יזרעאל', contractor: 'שפיר הנדסה', region: 'צפון', category: 'Galvanized Steel',     weight_kg: 72000,   emission_co2e: 208080,  reliability_score: 0.89, matched_by: 'ai_match',      year: 2026 },
  { project_name: 'כביש 6 – מקטע עמק יזרעאל', contractor: 'שפיר הנדסה', region: 'צפון', category: 'HDPE Granulate',       weight_kg: 44000,   emission_co2e: 84920,   reliability_score: 0.92, matched_by: 'exact_match', year: 2026 },
  { project_name: 'כביש 6 – מקטע עמק יזרעאל', contractor: 'שפיר הנדסה', region: 'צפון', category: 'Waterproofing',        weight_kg: 11000,   emission_co2e: 22000,   reliability_score: 0.88, matched_by: 'catalog_match', year: 2026 },
  { project_name: 'כביש 6 – מקטע עמק יזרעאל', contractor: 'שפיר הנדסה', region: 'צפון', category: 'Precast Concrete',     weight_kg: 95000,   emission_co2e: 17290,   reliability_score: 0.95, matched_by: 'exact_match', year: 2026 },

  // ── מחלף גלילות – שדרוג מלא (דניה סיבוס, מרכז) ───────────────────────────
  { project_name: 'מחלף גלילות – שדרוג מלא', contractor: 'דניה סיבוס', region: 'מרכז', category: 'Structural Concrete', weight_kg: 1200000, emission_co2e: 178800,  reliability_score: 0.95, matched_by: 'exact_match', year: 2026 },
  { project_name: 'מחלף גלילות – שדרוג מלא', contractor: 'דניה סיבוס', region: 'מרכז', category: 'Steel Rebar',          weight_kg: 240000,  emission_co2e: 477600,  reliability_score: 0.97, matched_by: 'exact_match', year: 2026 },
  { project_name: 'מחלף גלילות – שדרוג מלא', contractor: 'דניה סיבוס', region: 'מרכז', category: 'Asphalt',              weight_kg: 950000,  emission_co2e: 44840,   reliability_score: 0.96, matched_by: 'exact_match', year: 2026 },
  { project_name: 'מחלף גלילות – שדרוג מלא', contractor: 'דניה סיבוס', region: 'מרכז', category: 'Fill Material',        weight_kg: 3200000, emission_co2e: 15360,   reliability_score: 0.90, matched_by: 'catalog_match', year: 2026 },
  { project_name: 'מחלף גלילות – שדרוג מלא', contractor: 'דניה סיבוס', region: 'מרכז', category: 'Crushed Stone',        weight_kg: 1100000, emission_co2e: 5280,    reliability_score: 0.92, matched_by: 'catalog_match', year: 2026 },
  { project_name: 'מחלף גלילות – שדרוג מלא', contractor: 'דניה סיבוס', region: 'מרכז', category: 'Galvanized Steel',     weight_kg: 118000,  emission_co2e: 341020,  reliability_score: 0.91, matched_by: 'ai_match',      year: 2026 },
  { project_name: 'מחלף גלילות – שדרוג מלא', contractor: 'דניה סיבוס', region: 'מרכז', category: 'Structural Steel',     weight_kg: 84000,   emission_co2e: 242760,  reliability_score: 0.93, matched_by: 'exact_match', year: 2026 },
  { project_name: 'מחלף גלילות – שדרוג מלא', contractor: 'דניה סיבוס', region: 'מרכז', category: 'Precast Concrete',     weight_kg: 96000,   emission_co2e: 17472,   reliability_score: 0.94, matched_by: 'exact_match', year: 2026 },
  { project_name: 'מחלף גלילות – שדרוג מלא', contractor: 'דניה סיבוס', region: 'מרכז', category: 'PVC Pipe',             weight_kg: 32000,   emission_co2e: 99200,   reliability_score: 0.89, matched_by: 'catalog_match', year: 2026 },

  // ── קו רכבת קלה ת"א – מקטע B2 (אלקטרה בנייה, מרכז) ─────────────────────
  { project_name: 'קו רכבת קלה ת״א – מקטע B2', contractor: 'אלקטרה בנייה', region: 'מרכז', category: 'Structural Concrete', weight_kg: 2800000, emission_co2e: 417200,  reliability_score: 0.96, matched_by: 'exact_match', year: 2026 },
  { project_name: 'קו רכבת קלה ת״א – מקטע B2', contractor: 'אלקטרה בנייה', region: 'מרכז', category: 'Steel Rebar',          weight_kg: 520000,  emission_co2e: 1034800, reliability_score: 0.97, matched_by: 'exact_match', year: 2026 },
  { project_name: 'קו רכבת קלה ת״א – מקטע B2', contractor: 'אלקטרה בנייה', region: 'מרכז', category: 'Structural Steel',     weight_kg: 320000,  emission_co2e: 924800,  reliability_score: 0.95, matched_by: 'exact_match', year: 2026 },
  { project_name: 'קו רכבת קלה ת״א – מקטע B2', contractor: 'אלקטרה בנייה', region: 'מרכז', category: 'Asphalt',              weight_kg: 340000,  emission_co2e: 16048,   reliability_score: 0.94, matched_by: 'catalog_match', year: 2025 },
  { project_name: 'קו רכבת קלה ת״א – מקטע B2', contractor: 'אלקטרה בנייה', region: 'מרכז', category: 'Galvanized Steel',     weight_kg: 88000,   emission_co2e: 254320,  reliability_score: 0.91, matched_by: 'ai_match',      year: 2025 },
  { project_name: 'קו רכבת קלה ת״א – מקטע B2', contractor: 'אלקטרה בנייה', region: 'מרכז', category: 'Copper Wire (Cable)',  weight_kg: 15000,   emission_co2e: 57150,   reliability_score: 0.93, matched_by: 'exact_match', year: 2025 },
  { project_name: 'קו רכבת קלה ת״א – מקטע B2', contractor: 'אלקטרה בנייה', region: 'מרכז', category: 'Aluminum',             weight_kg: 22000,   emission_co2e: 181280,  reliability_score: 0.92, matched_by: 'exact_match', year: 2026 },
  { project_name: 'קו רכבת קלה ת״א – מקטע B2', contractor: 'אלקטרה בנייה', region: 'מרכז', category: 'Precast Concrete',     weight_kg: 185000,  emission_co2e: 33670,   reliability_score: 0.95, matched_by: 'exact_match', year: 2026 },
  { project_name: 'קו רכבת קלה ת״א – מקטע B2', contractor: 'אלקטרה בנייה', region: 'מרכז', category: 'HDPE Granulate',       weight_kg: 68000,   emission_co2e: 131240,  reliability_score: 0.90, matched_by: 'catalog_match', year: 2026 },

  // ── כביש 531 – כביש לכיש (סולל בונה, דרום) ──────────────────────────────
  { project_name: 'כביש 531 – כביש לכיש',       contractor: 'סולל בונה',     region: 'דרום',  category: 'Structural Concrete', weight_kg: 640000,  emission_co2e: 95360,   reliability_score: 0.93, matched_by: 'exact_match', year: 2025 },
  { project_name: 'כביש 531 – כביש לכיש',       contractor: 'סולל בונה',     region: 'דרום',  category: 'Steel Rebar',          weight_kg: 128000,  emission_co2e: 254720,  reliability_score: 0.95, matched_by: 'exact_match', year: 2025 },
  { project_name: 'כביש 531 – כביש לכיש',       contractor: 'סולל בונה',     region: 'דרום',  category: 'Asphalt',              weight_kg: 1800000, emission_co2e: 84960,   reliability_score: 0.97, matched_by: 'exact_match', year: 2025 },
  { project_name: 'כביש 531 – כביש לכיש',       contractor: 'סולל בונה',     region: 'דרום',  category: 'Fill Material',        weight_kg: 4200000, emission_co2e: 20160,   reliability_score: 0.91, matched_by: 'catalog_match', year: 2025 },
  { project_name: 'כביש 531 – כביש לכיש',       contractor: 'סולל בונה',     region: 'דרום',  category: 'Crushed Stone',        weight_kg: 1500000, emission_co2e: 7200,    reliability_score: 0.92, matched_by: 'catalog_match', year: 2025 },
  { project_name: 'כביש 531 – כביש לכיש',       contractor: 'סולל בונה',     region: 'דרום',  category: 'Galvanized Steel',     weight_kg: 55000,   emission_co2e: 158950,  reliability_score: 0.88, matched_by: 'ai_match',      year: 2025 },
  { project_name: 'כביש 531 – כביש לכיש',       contractor: 'סולל בונה',     region: 'דרום',  category: 'Waterproofing',        weight_kg: 18000,   emission_co2e: 36000,   reliability_score: 0.87, matched_by: 'catalog_match', year: 2025 },

  // ── פיתוח נמל חיפה – שלב ב (מנרב, צפון) ─────────────────────────────────
  { project_name: 'פיתוח נמל חיפה – שלב ב',    contractor: 'מנרב',          region: 'צפון',  category: 'Structural Concrete', weight_kg: 1800000, emission_co2e: 268200,  reliability_score: 0.96, matched_by: 'exact_match', year: 2026 },
  { project_name: 'פיתוח נמל חיפה – שלב ב',    contractor: 'מנרב',          region: 'צפון',  category: 'Steel Rebar',          weight_kg: 350000,  emission_co2e: 696500,  reliability_score: 0.97, matched_by: 'exact_match', year: 2026 },
  { project_name: 'פיתוח נמל חיפה – שלב ב',    contractor: 'מנרב',          region: 'צפון',  category: 'Structural Steel',     weight_kg: 180000,  emission_co2e: 520200,  reliability_score: 0.95, matched_by: 'exact_match', year: 2026 },
  { project_name: 'פיתוח נמל חיפה – שלב ב',    contractor: 'מנרב',          region: 'צפון',  category: 'Waterproofing',        weight_kg: 45000,   emission_co2e: 90000,   reliability_score: 0.90, matched_by: 'catalog_match', year: 2026 },
  { project_name: 'פיתוח נמל חיפה – שלב ב',    contractor: 'מנרב',          region: 'צפון',  category: 'Galvanized Steel',     weight_kg: 62000,   emission_co2e: 179180,  reliability_score: 0.91, matched_by: 'ai_match',      year: 2026 },
  { project_name: 'פיתוח נמל חיפה – שלב ב',    contractor: 'מנרב',          region: 'צפון',  category: 'Precast Concrete',     weight_kg: 220000,  emission_co2e: 40040,   reliability_score: 0.94, matched_by: 'exact_match', year: 2026 },
  { project_name: 'פיתוח נמל חיפה – שלב ב',    contractor: 'מנרב',          region: 'צפון',  category: 'Fill Material',        weight_kg: 1800000, emission_co2e: 8640,    reliability_score: 0.89, matched_by: 'catalog_match', year: 2026 },
  { project_name: 'פיתוח נמל חיפה – שלב ב',    contractor: 'מנרב',          region: 'צפון',  category: 'Aluminum',             weight_kg: 18000,   emission_co2e: 148320,  reliability_score: 0.92, matched_by: 'exact_match', year: 2026 },
];
