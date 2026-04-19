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
import { fetchEmissions, fetchReview, fetchProjects, EmissionRow, ReviewRow } from '../lib/api';

const TAB_LABELS: Record<string, string> = {
  dashboard: '📊 דאשבורד',
  review: '✅ Review',
  whatif: '⇄ What-If',
  ai: '🤖 AI',
  upload: '☁️ קליטה',
  data: '📋 נתונים',
  settings: '⚙️ הגדרות',
};

interface Settings {
  reliabilityThreshold: number;
  maxClimatiqCandidates: number;
  maxFactorSpreadPct: number;
  autoWriteAiApproved: boolean;
}

export function Dashboard() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState('dashboard');
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

  // Sidebar filters
  const [selectedYear, setSelectedYear] = useState<number | null>(null);
  const [selectedRegions, setSelectedRegions] = useState<string[]>([]);
  const [reliabilityThreshold, setReliabilityThreshold] = useState(0.85);

  const years = useMemo(() => {
    const ys = Array.from(new Set(emissions.map(r => r.year).filter(Boolean) as number[])).sort((a, b) => b - a);
    return ys;
  }, [emissions]);

  const regions = useMemo(() => Array.from(new Set(emissions.map(r => r.region).filter(Boolean) as string[])).sort(), [emissions]);

  const filteredEmissions = useMemo(() => {
    return emissions.filter(r => {
      if (selectedYear && r.year !== selectedYear) return false;
      if (selectedRegions.length && !selectedRegions.includes(r.region)) return false;
      return true;
    });
  }, [emissions, selectedYear, selectedRegions]);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [emRes, revRes, projRes] = await Promise.allSettled([
        fetchEmissions(),
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
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  return (
    <div className="flex h-screen overflow-hidden bg-bg">
      <Sidebar
        activeTab={activeTab}
        onTabChange={setActiveTab}
        reviewCount={review.length}
        filters={{
          projects,
          selectedProjects: [],
          regions,
          selectedRegions,
          years,
          selectedYear,
          reliabilityThreshold,
          onProjectsChange: () => {},
          onRegionsChange: setSelectedRegions,
          onYearChange: setSelectedYear,
          onReliabilityChange: setReliabilityThreshold,
        }}
      />

      <main className="flex-1 overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 z-10 bg-white border-b border-border px-6 py-3 flex items-center justify-between">
          <div style={{ background: 'var(--grad-hero)' }} className="rounded-lg px-3 py-1.5 text-white text-xs font-semibold">
            {TAB_LABELS[activeTab]}
          </div>
          <div className="flex items-center gap-4">
            {loading && <span className="text-xs text-muted-fg animate-pulse">טוען נתונים...</span>}
            <div className="flex items-center gap-2 text-xs text-muted-fg">
              <span className="w-2 h-2 rounded-full bg-success inline-block" />
              BigQuery · {emissions.length.toLocaleString()} רשומות
            </div>
            <button onClick={loadData} className="text-xs text-muted-fg hover:text-primary transition-colors">↻ רענן</button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6">
          {activeTab === 'dashboard' && <DashboardTab data={filteredEmissions} reviewCount={review.length} />}
          {activeTab === 'review' && <ReviewTab data={review} onRefresh={loadData} reliabilityThreshold={reliabilityThreshold} />}
          {activeTab === 'whatif' && <WhatIfTab data={filteredEmissions} />}
          {activeTab === 'ai' && <AiTab data={filteredEmissions} />}
          {activeTab === 'upload' && (
            <UploadTab
              userEmail={user?.email || ''}
              settings={settings}
            />
          )}
          {activeTab === 'data' && <DataTab data={filteredEmissions} />}
          {activeTab === 'settings' && (
            <SettingsTab
              settings={settings}
              onSettingsChange={setSettings}
              projects={projects}
              onProjectDeleted={loadData}
            />
          )}
        </div>
      </main>

      <AiBubble data={filteredEmissions} />
    </div>
  );
}

// Mock data for fallback
const MOCK_EMISSIONS: EmissionRow[] = [
  { project_name: 'כביש 6 - מקטע צפון', contractor: 'שפיר הנדסה', region: 'צפון', category: 'Steel Rebar', weight_kg: 125000, emission_co2e: 231250, reliability_score: 0.92, matched_by: 'exact_match', year: 2026 },
  { project_name: 'כביש 6 - מקטע צפון', contractor: 'שפיר הנדסה', region: 'צפון', category: 'Structural Concrete', weight_kg: 450000, emission_co2e: 148500, reliability_score: 0.88, matched_by: 'ai_match', year: 2026 },
  { project_name: 'מחלף גלילות', contractor: 'דניה סיבוס', region: 'מרכז', category: 'Asphalt', weight_kg: 320000, emission_co2e: 89600, reliability_score: 0.95, matched_by: 'exact_match', year: 2026 },
  { project_name: 'מחלף גלילות', contractor: 'דניה סיבוס', region: 'מרכז', category: 'Galvanized Steel', weight_kg: 85000, emission_co2e: 178500, reliability_score: 0.78, matched_by: 'ai_match', year: 2026 },
  { project_name: 'כביש 1 - מעלה אדומים', contractor: 'סולל בונה', region: 'מרכז', category: 'Structural Concrete', weight_kg: 680000, emission_co2e: 258400, reliability_score: 0.91, matched_by: 'exact_match', year: 2025 },
  { project_name: 'גשר נחל הבשור', contractor: 'אלקטרה בנייה', region: 'דרום', category: 'Galvanized Steel', weight_kg: 42000, emission_co2e: 92400, reliability_score: 0.85, matched_by: 'ai_match', year: 2026 },
  { project_name: 'כביש 90 - ים המלח', contractor: 'מנרב', region: 'דרום', category: 'Asphalt', weight_kg: 210000, emission_co2e: 50400, reliability_score: 0.89, matched_by: 'exact_match', year: 2026 },
  { project_name: 'מנהרות הכרמל', contractor: 'שפיר הנדסה', region: 'צפון', category: 'Structural Concrete', weight_kg: 890000, emission_co2e: 356000, reliability_score: 0.96, matched_by: 'exact_match', year: 2026 },
];
