from google.cloud import bigquery

project = 'argon-ace-483810-n9'
client = bigquery.Client(project=project)

query = '''
ALTER TABLE `argon-ace-483810-n9.netivei_emissions_db.boq_code_mapping`
ADD COLUMN IF NOT EXISTS emission_factor FLOAT64,
ADD COLUMN IF NOT EXISTS emission_factor_source STRING,
ADD COLUMN IF NOT EXISTS emission_factor_notes STRING;
'''

try:
    client.query(query).result()
    print('ALTER TABLE successful!')
except Exception as e:
    print('Error:', e)
