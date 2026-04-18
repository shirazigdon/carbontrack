from google.cloud import bigquery
client = bigquery.Client(project='argon-ace-483810-n9')
query = """
SELECT boq_code, category FROM `argon-ace-483810-n9.netivei_emissions_db.boq_code_mapping`
WHERE category != 'EXCLUDE' AND boq_code LIKE '07.%'
"""
rows = list(client.query(query).result())
print('07.% mappings:', len(rows))
if len(rows) > 0:
    for r in rows[:10]:
        print(dict(r))
