import json
from google.cloud import bigquery
import pandas as pd

project = 'argon-ace-483810-n9'
client = bigquery.Client(project=project)
dataset = 'netivei_emissions_db'

print('Fetching boq_code_mapping from BigQuery...')
query = f'SELECT boq_code, category FROM `{project}.{dataset}.boq_code_mapping` WHERE is_active = TRUE'

try:
    df_bq = client.query(query).to_dataframe()
    mapping = dict(zip(df_bq['boq_code'], df_bq['category']))
    print(f'Loaded {len(mapping)} mappings from BQ.')
    
    with open('boq_deep_analysis.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    total_unknown = 0
    resolved = 0
    resolved_cats = {}
    
    for file_data in data:
        for row in file_data.get('unknown_rows', []):
            total_unknown += 1
            boq = str(row.get('boq_code', '')).strip()
            if boq in mapping:
                resolved += 1
                cat = mapping[boq]
                resolved_cats[cat] = resolved_cats.get(cat, 0) + 1
                
    print(f'\n--- BQ Resolution Simulation ---')
    print(f'Total unknown rows analyzed (sampled): {total_unknown}')
    print(f'Resolved by BQ mapping: {resolved} ({(resolved/total_unknown*100) if total_unknown else 0:.1f}%)')
    print('Resolved into categories:')
    for k, v in resolved_cats.items():
        print(f'  {k}: {v}')
except Exception as e:
    print(f'Error: {e}')
