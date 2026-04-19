import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function fmt(n: number, digits = 0) {
  return n.toLocaleString('he-IL', { maximumFractionDigits: digits });
}

export function fmtTons(kgCO2e: number) {
  return `${fmt(kgCO2e / 1000)}t CO₂e`;
}

export const ENG_ALTERNATIVES: Record<string, [string, string][]> = {
  'Structural Concrete': [
    ['Precast Concrete', 'פרפב מפחית יציקה באתר ומשפר בקרת איכות'],
    ['Timber', 'עץ מהנדס (CLT/Glulam) — חומר פחמן-שלילי'],
    ['Steel Rebar', 'מסגרת פלדה עם קורות-חלל גדולות ופחות מסה'],
  ],
  'Precast Concrete': [
    ['Structural Concrete', 'יציקה מקומית גמישה לצורות מורכבות'],
    ['Carbon Steel (Plate/Section)', 'פרופיל פלדה קל-משקל'],
  ],
  'Asphalt': [
    ['Structural Concrete', 'מדרכת בטון — עמידות גבוהה'],
    ['Crushed Stone / Gravel', 'מעטפת טרשים לכביש שדה'],
  ],
  'Steel Rebar': [
    ['Galvanized Steel', 'עמידות קורוזיה גבוהה'],
    ['Stainless Steel', 'נירוסטה לסביבות אגרסיביות'],
    ['Carbon Steel (Plate/Section)', 'פרופיל פלדה קל-משקל'],
  ],
  'Galvanized Steel': [
    ['Stainless Steel', 'אפס תחזוקה בסביבות ים'],
    ['Aluminum', 'קל-משקל, עמיד קורוזיה'],
  ],
  'Aluminum': [
    ['Galvanized Steel', 'פלדה מגולוונת — עלות נמוכה'],
    ['Carbon Steel (Plate/Section)', 'פלדה קרבון + ציפוי'],
  ],
  'HDPE Pipe': [
    ['PVC', 'צינורות PVC זולים יותר'],
    ['Structural Concrete', 'צינור בטון לניקוז קוטר גדול'],
  ],
  'PVC': [
    ['HDPE Pipe', 'HDPE — גמיש, עמיד UV'],
  ],
};

export function suggestAlternatives(srcCat: string, availableCats: string[]) {
  const candidates = ENG_ALTERNATIVES[srcCat] || [];
  const result = candidates.filter(([cat]) => availableCats.includes(cat) && cat !== srcCat);
  if (!result.length) {
    return availableCats.filter(c => c !== srcCat).map(c => [c, 'חלופה כללית'] as [string, string]);
  }
  return result;
}
