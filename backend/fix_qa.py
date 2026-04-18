from google.cloud import bigquery
from datetime import datetime, timezone

client = bigquery.Client(project='argon-ace-483810-n9')

def insert_boq(code, category, desc=''):
    q = f"""
    INSERT INTO `argon-ace-483810-n9.netivei_emissions_db.boq_code_mapping`
    (boq_map_id, created_at, updated_at, is_active, boq_code, boq_code_prefix, category, notes, source, created_by)
    VALUES
    (GENERATE_UUID(), CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP(), TRUE, '{code}', '{code.split('.')[0] if '.' in code else code}', '{category}', 'QA Fix: {desc}', 'QA_Review', 'system')
    """
    client.query(q).result()

def insert_catalog(exact=None, regex=None, category='EXCLUDE', notes=''):
    q = f"""
    INSERT INTO `argon-ace-483810-n9.netivei_emissions_db.catalog_mapping`
    (mapping_id, created_at, is_active, exact_material, material_regex, category, confidence, notes)
    VALUES
    (GENERATE_UUID(), CURRENT_TIMESTAMP(), TRUE, {'NULL' if exact is None else f"'{exact}'"}, {'NULL' if regex is None else f"'{regex}'"}, '{category}', 2.0, 'QA Fix: {notes}')
    """
    client.query(q).result()

print('Applying QA fixes to BigQuery...')

# 1. Specific BOQ code fixes
insert_boq('18.01.9992', 'Waterproofing', 'איטום מעברי צינור בשוחה')
insert_boq('08.05.9500', 'EXCLUDE', 'אבן דרך')
insert_boq('08.10.9018', 'EXCLUDE', 'מפסק חשמל ציוד')

# 2. Add regexes for equipment/labor that got wrongly mapped
# For 51.23.04xx (excavation), let's use a regex for BOQ code matching if possible. 
# But catalog_mapping only matches material descriptions, not BOQ codes!
# Let's add regexes for the material text:
regexes_to_exclude = [
    'חפירת תעל', 'מדבק.*ציפור', 'מפסק', 'אסלה', 'כיור', 'קיר אקוסטי', 'כותרת.*בטון', r'\bB41\b', 'מסילות'
]
for r in regexes_to_exclude:
    insert_catalog(regex=r, category='EXCLUDE', notes='QA finding regex')

print('QA fixes applied successfully.')
