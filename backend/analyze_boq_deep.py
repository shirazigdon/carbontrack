# -*- coding: utf-8 -*-
"""
Deep analysis of BOQ Excel files:
1. Understands the structure (column 'חומר' = BOQ code, 'טקסט קצר' = description)
2. Simulates how the current main.py would classify each row
3. Identifies: items with no category, items that might mismatch, items to EXCLUDE
4. Produces a full report per file with classification simulation
"""
import os
import sys
import json
import re
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')

FOLDER = r'C:\Users\user\Documents\יזמות\פיצול'
OUT_JSON = r'c:\Users\user\Documents\GitHub\carbontrack-1\backend\boq_deep_analysis.json'
OUT_TEXT = r'c:\Users\user\Documents\GitHub\carbontrack-1\backend\boq_deep_analysis.txt'

# ─────────────────────────────────────────────
# Replicate the core classification logic from main.py
# ─────────────────────────────────────────────

CATEGORY_RULES = [
    ("Waterproofing",    [r"איטו[םמ]", r"ממברנה", r"ביטומ", r"יריעת\s*hdpe", r"גאוטכני", r"פריימר", r"זפת", r"פוליאוריטן", r"סילר", r"יריעות"]),
    ("Asphalt",          [r"אספלט", r"אספלת", r"תא.?צ", r"תא.?מ", r"\bSMA\b", r"בינדר", r"אמולסיה"]),
    ("Steel Rebar",      [r"זיון", r"מוטות\s*פלדה", r"פלדה\s*מצולעים", r"ת.?י\s*4466", r"רשתות\s*פלדה", r"ברזל\s*בניין"]),
    ("Copper Wire",      [r"כבל.*נחושת", r"נחושת", r"N2XY", r"NYY", r"XLPE", r"גידים", r"כבל\s*חשמל", r"מוליך"]),
    ("Aluminum",         [r"אלומיניום", r"אלומניום", r"פרופיל\s*אלומ", r"NA2XY", r"NA2XSY", r"כבל.*אלומינ", r"פח\s*אלומיניום"]),
    ("HDPE Granulate",   [r"HDPE", r"H\.D\.P\.E", r"פוליאתילן", r"PE100", r"PE-100", r"שרשור.*פוליאתילן", r"צנרת\s*פוליאתילן", r"פוליפרופילן"]),
    ("PVC Pipe",         [r"P\.?V\.?C", r"PVC", r"צינור\s*קשיח", r"מריכף", r"מריפלס", r"צנרת.*פלסטיק"]),
    ("Galvanized Steel", [r"מגולוונ", r"גדר", r"מעקה\s*(?:פלדה|בטיחות)?", r"פח\s*מגולוון", r"עמוד.*פלדה", r"זרוע.*פלדה", r"ארון", r"רמזור", r"תמרור", r"ברזל\s*יצוק", r"מכסה\s*לתא"]),
    ("Lean Concrete",    [r"בטון\s*רזה", r"ב-20", r"בטון\s*מדה", r"מדה\s*מתפלסת"]),
    ("Structural Concrete", [r"בטון", r"יצוק\s*באתר", r"ב-30", r"ב-40", r"כלונס", r"קירות\s*מבטון", r"ב-50", r"רפסודה", r"בלוקים"]),
    ("Crushed Stone",    [r"אגרגט", r"חצץ", r"מצע", r"בקאלש", r"אבן\s*גרוסה", r"שומשום", r"חול", r"מחצבה", r"זיפזיף", r"אדמה", r"סלעים", r"מצע\s*א'"]),
    ("Earthworks",       [r"חפירה", r"עפר\s*עודף", r"הוצאת\s*עפר", r"פינוי\s*עפר", r"דחיסה", r"מילוי\s*עפר", r"עבודות\s*עפר", r"גריפה"]),
    ("Fill Material",    [r"מילוי\s*(?:חוזר|גרוס|אבן|חול|מחוזק)", r"מצע\s*מילוי", r"חומר\s*מילוי", r"מלית", r"מילוי\s*תחת", r"מילוי\s*מסביב", r"טמינה"]),
    ("Paving",           [r"ריצוף", r"אבן\s*שפה", r"שפה\s*(?:טרומ|בטון|אבן)", r"מדרכה", r"אריחי\s*בטון", r"אבן\s*משתלבת"]),
    ("Concrete Pipe",    [r"צ\.?ניקוז", r"צינור.*בטון", r"קולקטור", r"תעלת.*ניקוז"]),
]

EXCLUDE_KEYWORDS = [
    r"\bפירוק\b", r"\bצביעה\b", r"\bקרצוף\b", r"\bגמר\s*פני\b",
    r"\bעבודה\b", r"\bהשכרה\b", r"\bבדיק[הת]\b", r"\bמדיד[הות]\b",
    r"\bתכנון\b", r"\bאחזק[הת]\b", r"\bסילוק\b", r"\bקידוח\b",
    r"\bחציבה\b", r"\bשאיבה\b", r"\bגיזום\b", r"\bטיפול\b",
    r"\bתשלום\b", r"\bפועל\b", r"\bמנהל\s*עבודה\b", r"\bמנוף\b",
    r"\bהעתק[הת]\b", r"\bחישוף\b", r"\bריסוס\b", r"\bעקירת\b",
    r"\bצוות\b", r"\bמשאית\b", r"\bהסרה\b", r"\bמחיר\s*תוספת\b",
    r"תוספת\s+מחיר", r"\bניכוי\b", r"\bקנס\b", r"\bזיכוי\b",
    r"מנהל\s*פרויקט", r"\bליקויי\b",
    # BOQ prefix-level excludes
    r"^60\.", r"^69\.",
]

MATERIAL_INDICATORS = [
    r"בטון", r"אספלט", r"מצע", r"חצץ", r"חול", r"אגרגט",
    r"יריע[ה]?\s*ביטומני", r"ברזל\s*זיון", r"פלדה",
    r"PVC", r"HDPE", r"פוליאתילן", r"PE100", r"N2XY", r"XLPE",
    r"כבל", r"נחושת", r"צינור",
]

BOQ_PREFIX_EXCLUDE = {"60", "69"}
BOQ_SUBPREFIX_EXCLUDE = {"51.01", "57.01", "51.32", "51.35", "51.34", "18.01.06", "18.01.07", "18.01.08", "51.02.004"}


def classify_row(boq_code: str, description: str) -> dict:
    text = str(description or "").strip()
    code = str(boq_code or "").strip()

    # BOQ prefix hard-excludes
    prefix_2 = code.split(".")[0] if "." in code else code
    prefix_5 = ".".join(code.split(".")[:2]) if "." in code else code
    if prefix_2 in BOQ_PREFIX_EXCLUDE or prefix_5 in BOQ_SUBPREFIX_EXCLUDE:
        return {"category": "EXCLUDE", "method": "boq_prefix_exclude", "confidence": 1.0}

    # Check material indicators (prevent over-exclusion)
    has_material = any(re.search(p, text, re.IGNORECASE) for p in MATERIAL_INDICATORS)

    # Exclude patterns
    if not has_material:
        for pat in EXCLUDE_KEYWORDS:
            if re.search(pat, text, re.IGNORECASE):
                return {"category": "EXCLUDE", "method": "exclude_pattern", "confidence": 0.95, "pattern": pat}

    # Category rules
    for cat, patterns in CATEGORY_RULES:
        for pat in patterns:
            if re.search(pat, text, re.IGNORECASE):
                return {"category": cat, "method": "regex_rule", "confidence": 0.92}

    return {"category": "Unknown", "method": "no_match", "confidence": 0.0}


# ─────────────────────────────────────────────
# Analyze all files
# ─────────────────────────────────────────────

files = sorted([f for f in os.listdir(FOLDER) if f.endswith('.xlsx') and not f.startswith('00')])

total_rows = 0
total_classified = 0
total_excluded = 0
total_unknown = 0
total_negative_qty = 0

category_counts = {}
file_summaries = []

with open(OUT_TEXT, 'w', encoding='utf-8') as txt:
    txt.write("BOQ DEEP ANALYSIS — Classification Simulation\n")
    txt.write("=" * 80 + "\n\n")

    for fname in files:
        path = os.path.join(FOLDER, fname)
        try:
            xl = pd.ExcelFile(path, engine='openpyxl')
            for sh in xl.sheet_names:
                df = xl.parse(sh)

                # Normalize column names
                df.columns = [str(c).strip() for c in df.columns]

                # Find boq_code column: 'חומר' or first unnamed that looks like a code
                boq_col = None
                mat_col = None
                qty_col = None

                for col in df.columns:
                    cl = col.lower()
                    if col in ['חומר', 'קוד פריט'] or 'חומר' in col:
                        boq_col = col
                    if col in ['טקסט קצר', 'תיאור'] or 'תיאור' in col or 'טקסט' in col:
                        mat_col = col
                    if 'כמות' in col or 'qty' in cl:
                        qty_col = col

                # Handle the "Unnamed" header files (like 02_איטום_Waterproofing.xlsx)
                if boq_col is None:
                    unnamed_cols = [c for c in df.columns if 'Unnamed' in c or 'קוד' in c]
                    # Check if row 0 is actually the real header
                    if len(df) > 0:
                        first_row = df.iloc[0]
                        for col in df.columns:
                            v = str(first_row[col] or "")
                            if 'קוד' in v or 'code' in v.lower():
                                # Re-read with row 1 as header
                                df = xl.parse(sh, header=1)
                                df.columns = [str(c).strip() for c in df.columns]
                                for c2 in df.columns:
                                    if 'קוד' in c2 or 'חומר' in c2:
                                        boq_col = c2
                                    if 'תיאור' in c2 or 'טקסט' in c2:
                                        mat_col = c2
                                    if 'כמות' in c2:
                                        qty_col = c2
                                break

                if boq_col is None or mat_col is None:
                    txt.write(f"\nSKIP {fname}/{sh} — could not detect required columns (boq={boq_col}, mat={mat_col})\n")
                    continue

                df = df.dropna(subset=[boq_col, mat_col], how='all').reset_index(drop=True)

                results_rows = []
                cats = {"EXCLUDE": 0, "Unknown": 0}
                neg_qty = 0

                for _, row in df.iterrows():
                    boq = str(row.get(boq_col, "") or "").strip()
                    desc = str(row.get(mat_col, "") or "").strip()
                    qty = row.get(qty_col, 0) if qty_col else 0
                    try:
                        qty_f = float(str(qty).replace(",", "")) if qty else 0
                    except Exception:
                        qty_f = 0

                    if not boq and not desc:
                        continue

                    clf = classify_row(boq, desc)
                    cat = clf["category"]
                    cats[cat] = cats.get(cat, 0) + 1

                    if qty_f < 0:
                        neg_qty += 1

                    results_rows.append({
                        "boq_code": boq,
                        "description": desc[:80],
                        "quantity": qty_f,
                        "category": cat,
                        "method": clf.get("method"),
                        "confidence": clf.get("confidence"),
                    })

                n = len(results_rows)
                n_excl = cats.get("EXCLUDE", 0)
                n_unk = cats.get("Unknown", 0)
                n_classified = n - n_excl - n_unk

                total_rows += n
                total_classified += n_classified
                total_excluded += n_excl
                total_unknown += n_unk
                total_negative_qty += neg_qty

                for cat, cnt in cats.items():
                    category_counts[cat] = category_counts.get(cat, 0) + cnt

                summary = {
                    "file": fname, "sheet": sh, "total_rows": n,
                    "classified": n_classified, "excluded": n_excl, "unknown": n_unk,
                    "negative_qty": neg_qty,
                    "categories": cats,
                    "unknown_rows": [r for r in results_rows if r["category"] == "Unknown"][:20],
                    "all_rows": results_rows,
                }
                file_summaries.append(summary)

                txt.write(f"\n{'='*60}\n")
                txt.write(f"FILE: {fname} | Sheet: {sh}\n")
                txt.write(f"Total: {n} | Classified: {n_classified} | Excluded: {n_excl} | Unknown: {n_unk} | Negative qty: {neg_qty}\n")
                txt.write(f"Categories: {dict(sorted(cats.items(), key=lambda x: -x[1]))}\n")

                if n_unk > 0:
                    txt.write(f"\n  ⚠️  UNKNOWN rows ({n_unk}):\n")
                    for r in results_rows:
                        if r["category"] == "Unknown":
                            txt.write(f"    [{r['boq_code']}] {r['description'][:70]}\n")

        except Exception as e:
            txt.write(f"\nERROR {fname}: {e}\n")
            import traceback
            txt.write(traceback.format_exc())

    txt.write("\n\n" + "=" * 80 + "\n")
    txt.write("GLOBAL SUMMARY\n")
    txt.write("=" * 80 + "\n")
    txt.write(f"Total rows across all files: {total_rows}\n")
    txt.write(f"Classified correctly:        {total_classified} ({100*total_classified//total_rows if total_rows else 0}%)\n")
    txt.write(f"Excluded (non-material):     {total_excluded} ({100*total_excluded//total_rows if total_rows else 0}%)\n")
    txt.write(f"Unknown (needs AI/review):   {total_unknown} ({100*total_unknown//total_rows if total_rows else 0}%)\n")
    txt.write(f"Negative quantity rows:      {total_negative_qty}\n")
    txt.write(f"\nCategory breakdown:\n")
    for cat, cnt in sorted(category_counts.items(), key=lambda x: -x[1]):
        pct = 100 * cnt // total_rows if total_rows else 0
        txt.write(f"  {cat:<30} {cnt:>5} rows ({pct}%)\n")

# Save JSON
safe_summaries = []
for s in file_summaries:
    sc = {k: v for k, v in s.items() if k != "all_rows"}
    safe_summaries.append(sc)

with open(OUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(safe_summaries, f, ensure_ascii=False, indent=2, default=str)

print(f"Done!")
print(f"Text report: {OUT_TEXT}")
print(f"JSON report: {OUT_JSON}")
print(f"\nGLOBAL SUMMARY:")
print(f"  Total rows:  {total_rows}")
print(f"  Classified:  {total_classified} ({100*total_classified//total_rows if total_rows else 0}%)")
print(f"  Excluded:    {total_excluded} ({100*total_excluded//total_rows if total_rows else 0}%)")
print(f"  Unknown:     {total_unknown} ({100*total_unknown//total_rows if total_rows else 0}%)")
print(f"  Negative qty:{total_negative_qty}")
print(f"\nCategory counts:")
for cat, cnt in sorted(category_counts.items(), key=lambda x: -x[1]):
    print(f"  {cat:<30} {cnt}")
