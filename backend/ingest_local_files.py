import os
import sys
import json
import traceback
from datetime import datetime, timezone
import pandas as pd

# Load environment variable setup
os.environ["GCP_PROJECT"] = "argon-ace-483810-n9"

# We must mock 'append_rows_json' before any BQ operations happen in process_dataframe
import main
from main import process_dataframe, BQ_DETAILS_TABLE, BQ_SUMMARY_TABLE, BQ_REVIEW_QUEUE_TABLE

FOLDER = r"C:\Users\user\Documents\יזמות\פיצול"
RESULTS_FOLDER = os.path.join(FOLDER, "תוצאות")
os.makedirs(RESULTS_FOLDER, exist_ok=True)

# Mock BQ insertion to capture rows instead
captured_details = []
captured_summaries = []
captured_reviews = []

original_append = main.append_rows_json

def mock_append_rows_json(table_id: str, rows: list):
    global captured_details, captured_summaries, captured_reviews
    if table_id == BQ_DETAILS_TABLE:
        captured_details.extend(rows)
    elif table_id == BQ_SUMMARY_TABLE:
        captured_summaries.extend(rows)
    elif table_id == BQ_REVIEW_QUEUE_TABLE:
        captured_reviews.extend(rows)
    else:
        # We skip learning tables updates during this local simulation
        pass

main.append_rows_json = mock_append_rows_json

# Also mock update_processing_progress which calls BQ
def mock_update_processing_progress(*args, **kwargs):
    pass
main.update_processing_progress = mock_update_processing_progress
main.upsert_processing_run_started = lambda *args, **kwargs: None
main.insert_processing_run_finished = lambda *args, **kwargs: None

def process_all_files():
    files = sorted([f for f in os.listdir(FOLDER) if f.endswith('.xlsx') and not f.startswith('00') and not f.startswith('~')])
    
    total_stats = {
        "files_processed": 0,
        "total_emissions": 0.0,
        "rows_processed": 0,
        "rows_needed_review": 0,
        "rows_auto_approved": 0,
        "excluded": 0
    }
    
    print(f"Starting local ingestion simulation. Saving results to: {RESULTS_FOLDER}")
    
    # Warm caches manually
    main.load_boq_code_mapping_rows()
    main.load_catalog_mapping_rows()
    main.load_unit_conversion_rules()
    main.load_materials_catalog()
    
    for fname in files:
        path = os.path.join(FOLDER, fname)
        print(f"\nProcessing {fname}...")
        try:
            xl = pd.ExcelFile(path, engine='openpyxl')
            
            # Reset captured per file
            global captured_details, captured_summaries, captured_reviews
            captured_details = []
            captured_summaries = []
            captured_reviews = []
            
            for sh in xl.sheet_names:
                df = xl.parse(sh)
                
                # Cleanup cols
                df.columns = [str(c).strip() for c in df.columns]
                
                # Detect the actual columns
                boq_col = None
                mat_col = None
                qty_col = None
                
                for col in df.columns:
                    cl = col.lower()
                    if col in ['חומר', 'קוד פריט'] or 'חומר' in col: boq_col = col
                    if col in ['טקסט קצר', 'תיאור'] or 'תיאור' in col or 'טקסט' in col: mat_col = col
                    if 'כמות' in col or 'qty' in cl: qty_col = col
                
                if boq_col is None:
                    if len(df) > 0:
                        first_row = df.iloc[0]
                        has_code = False
                        for col in df.columns:
                            v = str(first_row[col] or "")
                            if 'קוד' in v or 'code' in v.lower() or 'חומר' in v:
                                has_code = True
                                break
                        if has_code:
                            df = xl.parse(sh, header=1)
                            df.columns = [str(c).strip() for c in df.columns]
                            for c2 in df.columns:
                                if 'קוד' in c2 or 'חומר' in c2: boq_col = c2
                                if 'תיאור' in c2 or 'טקסט' in c2: mat_col = c2
                                if 'כמות' in c2: qty_col = c2
                
                if boq_col is None or mat_col is None:
                    print(f"  -> Skipping sheet {sh} - columns not found")
                    continue
                
                # Standardize columns for process_dataframe
                df = df.rename(columns={
                    boq_col: "boq_code",
                    mat_col: "material",
                })
                if qty_col:
                    df = df.rename(columns={qty_col: "quantity"})
                else:
                    df["quantity"] = 0
                
                # We need a unit column
                unit_col = None
                for c in df.columns:
                    if 'יחידה' in c or 'unit' in c.lower() or 'יח' == c:
                        unit_col = c
                if unit_col:
                    df = df.rename(columns={unit_col: "unit"})
                else:
                    df["unit"] = ""
                
                df = df.dropna(subset=["boq_code", "material"], how='all').reset_index(drop=True)
                if len(df) == 0:
                    continue
                    
                metadata = {
                    "run_id": f"local-{int(datetime.now().timestamp())}",
                    "source_file": fname,
                    "project_name": fname.replace(".xlsx", ""),
                    "source_mode": "boq"
                }
                
                print(f"  -> Sheet {sh}: {len(df)} rows")
                # Run the pipeline
                result_stats = process_dataframe(df, metadata)
                # Ensure pending rows are flushed
                if hasattr(main, '_flush_detail_rows'):
                    pass # It's a nested function, but process_dataframe flushes at the end anyway.
                
            # Save results for this file
            if captured_details:
                res_df = pd.DataFrame(captured_details)
                # Keep relevant columns for output
                cols = ['boq_code', 'material', 'original_quantity', 'assumed_uom', 'category', 'emission_co2e', 'review_required', 'reliability_score']
                existing_cols = [c for c in cols if c in res_df.columns]
                
                out_path = os.path.join(RESULTS_FOLDER, f"res_{fname}")
                res_df.to_excel(out_path, index=False)
                
                file_emissions = sum(r.get('emission_co2e') or 0.0 for r in captured_details)
                file_reviews = len([r for r in captured_details if r.get('review_required')])
                file_auto = len([r for r in captured_details if not r.get('review_required') and r.get('category') != 'EXCLUDE'])
                file_excl = len([r for r in captured_details if r.get('category') == 'EXCLUDE'])
                
                print(f"  => Saved {len(captured_details)} rows to res_{fname}")
                print(f"  => Total Emissions: {file_emissions:,.2f} kgCO2e")
                print(f"  => Needs Review: {file_reviews} | Auto Approved: {file_auto} | Excluded: {file_excl}")
                
                total_stats["files_processed"] += 1
                total_stats["total_emissions"] += file_emissions
                total_stats["rows_processed"] += len(captured_details)
                total_stats["rows_needed_review"] += file_reviews
                total_stats["rows_auto_approved"] += file_auto
                total_stats["excluded"] += file_excl
                
        except Exception as e:
            print(f"Error on {fname}: {e}")
            traceback.print_exc()

    print("\n--- GLOBAL SUMMARY ---")
    print(json.dumps(total_stats, indent=2))
    
    with open(os.path.join(RESULTS_FOLDER, "summary.json"), "w") as f:
        json.dump(total_stats, f, indent=2)

if __name__ == '__main__':
    process_all_files()
