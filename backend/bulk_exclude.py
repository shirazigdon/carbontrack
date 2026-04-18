import pandas as pd
from google.cloud import bigquery

file_path = r'C:\Users\user\Downloads\full_item_review.xlsx'
df = pd.read_excel(file_path, sheet_name='רשימת EXCLUDE', header=1)

client = bigquery.Client(project='argon-ace-483810-n9')

def insert_boq(code, desc):
    q = f"""
    INSERT INTO `argon-ace-483810-n9.netivei_emissions_db.boq_code_mapping`
    (boq_map_id, created_at, updated_at, is_active, boq_code, boq_code_prefix, category, notes, source, created_by)
    VALUES
    (GENERATE_UUID(), CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP(), TRUE, '{code}', '{code.split('.')[0] if '.' in code else code}', 'EXCLUDE', 'QA Fix: {desc.replace("'", "")}', 'QA_Review', 'system')
    """
    try:
        client.query(q).result()
    except Exception as e:
        print('Error inserting', code, e)

print(f'Found {len(df)} items to EXCLUDE.')
count = 0
for idx, row in df.iterrows():
    code = str(row.get('קוד פריט')).strip()
    if code != 'nan' and code:
        desc = str(row.get('תיאור'))[:100]
        insert_boq(code, desc)
        count += 1

print(f'Successfully inserted {count} EXCLUDE rules to BigQuery.')
