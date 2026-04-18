# -*- coding: utf-8 -*-
"""
Analyzes BOQ Excel files from the יזמות/פיצול directory.
Outputs a summary of structure and content to a JSON + text report.
"""
import os
import sys
import json
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')

FOLDER = r'C:\Users\user\Documents\יזמות\פיצול'
OUT_JSON = r'c:\Users\user\Documents\GitHub\carbontrack-1\backend\boq_analysis.json'
OUT_TEXT = r'c:\Users\user\Documents\GitHub\carbontrack-1\backend\boq_analysis.txt'

results = []
issues = []

files = sorted([f for f in os.listdir(FOLDER) if f.endswith('.xlsx')])

def safe_val(v):
    if v is None:
        return None
    if isinstance(v, float):
        import math
        if math.isnan(v) or math.isinf(v):
            return None
    return str(v) if not isinstance(v, (int, float, bool)) else v

with open(OUT_TEXT, 'w', encoding='utf-8') as txt:
    txt.write(f"BOQ Files Analysis — {len(files)} files\n")
    txt.write("=" * 80 + "\n\n")

    for fname in files:
        path = os.path.join(FOLDER, fname)
        file_result = {"file": fname, "sheets": []}

        try:
            xl = pd.ExcelFile(path, engine='openpyxl')
            txt.write(f"\n{'='*60}\n FILE: {fname}\n{'='*60}\n")

            for sh in xl.sheet_names:
                df_raw = xl.parse(sh, header=None, nrows=3)
                df_full = xl.parse(sh, header=None)
                
                # Detect header row (first non-empty row)
                header_row_idx = None
                for i, row in df_raw.iterrows():
                    if row.notna().any():
                        header_row_idx = i
                        break

                # Re-read with header
                df = xl.parse(sh, header=header_row_idx if header_row_idx is not None else 0)
                df = df.dropna(how='all').reset_index(drop=True)

                cols = [str(c) for c in df.columns.tolist()]
                n_rows = len(df)
                sample_rows = []

                # Sample up to 5 data rows
                for _, row in df.head(5).iterrows():
                    sample_rows.append({str(k): safe_val(v) for k, v in row.items()})

                # Look for key columns
                col_lower = [c.lower() for c in cols]
                has_boq_code = any(kw in ' '.join(col_lower) for kw in ['קוד', 'סעיף', 'code', 'מק"ט', 'מקט'])
                has_emission = any(kw in ' '.join(col_lower) for kw in ['emission', 'פליטה', 'co2', 'מקדם', 'factor'])
                has_material = any(kw in ' '.join(col_lower) for kw in ['חומר', 'תיאור', 'material', 'description'])
                has_quantity = any(kw in ' '.join(col_lower) for kw in ['כמות', 'quantity', 'qty'])

                sheet_info = {
                    "sheet": sh,
                    "columns": cols,
                    "n_rows": n_rows,
                    "has_boq_code": has_boq_code,
                    "has_emission_factor": has_emission,
                    "has_material": has_material,
                    "has_quantity": has_quantity,
                    "sample": sample_rows,
                }
                file_result["sheets"].append(sheet_info)

                txt.write(f"\n  Sheet: {sh} | {n_rows} rows\n")
                txt.write(f"  Columns ({len(cols)}): {cols}\n")
                txt.write(f"  has_boq_code={has_boq_code} | has_emission={has_emission} | has_material={has_material} | has_qty={has_quantity}\n")
                txt.write(f"  Sample rows:\n")
                for sr in sample_rows[:3]:
                    txt.write(f"    {sr}\n")

                if not has_boq_code:
                    issues.append(f"WARN: {fname}|{sh} — no BOQ code column detected")
                if not has_material:
                    issues.append(f"WARN: {fname}|{sh} — no material description column")

        except Exception as e:
            file_result["error"] = str(e)
            issues.append(f"ERROR: {fname} — {e}")
            txt.write(f"\n  ERROR: {e}\n")

        results.append(file_result)

    # Summary
    txt.write("\n\n" + "="*80 + "\n")
    txt.write("ISSUES SUMMARY\n")
    txt.write("="*80 + "\n")
    for issue in issues:
        txt.write(f"  {issue}\n")
    
    txt.write(f"\nTotal files: {len(files)}\n")
    txt.write(f"Total issues: {len(issues)}\n")

# Save JSON
with open(OUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2, default=str)

print(f"Done! Text report: {OUT_TEXT}")
print(f"JSON report: {OUT_JSON}")
print(f"Issues found: {len(issues)}")
for issue in issues:
    print(f"  {issue}")
