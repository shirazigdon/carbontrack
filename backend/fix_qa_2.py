from google.cloud import bigquery
client = bigquery.Client(project='argon-ace-483810-n9')

def insert_boq(code, category, desc):
    q = f"""
    INSERT INTO `argon-ace-483810-n9.netivei_emissions_db.boq_code_mapping`
    (boq_map_id, created_at, updated_at, is_active, boq_code, boq_code_prefix, category, notes, source, created_by)
    VALUES
    (GENERATE_UUID(), CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP(), TRUE, '{code}', '{code.split('.')[0]}', '{category}', 'QA Fix 2: {desc}', 'QA_Review', 'system')
    """
    client.query(q).result()

def insert_catalog(regex, category, desc):
    q = f"""
    INSERT INTO `argon-ace-483810-n9.netivei_emissions_db.catalog_mapping`
    (mapping_id, created_at, is_active, exact_material, material_regex, category, confidence, notes)
    VALUES
    (GENERATE_UUID(), CURRENT_TIMESTAMP(), TRUE, NULL, '{regex}', '{category}', 2.0, 'QA Fix 2: {desc}')
    """
    client.query(q).result()

print("Applying specific QA 2 fixes to BQ...")

# Exact BOQ fixes
insert_boq('T57.92.0011', 'Precast Concrete', 'שוחות בקרה טרומיות')
insert_boq('B41.01.0711', 'EXCLUDE', 'הפעלה ומגוף')
insert_boq('40.01.0031', 'EXCLUDE', 'סלעים מקומיים מהשטח (no embodied carbon)')
insert_boq('08.04.0110', 'EXCLUDE', 'פתיחת אספלט')
insert_boq('08.04.0100', 'EXCLUDE', 'פתיחת אספלט')
insert_boq('51.99.9913', 'Galvanized Steel', 'פסי רכבת (steel)')
insert_boq('51.99.9965', 'Copper Wire (Cable)', 'כבל נחושת')

# Regex fixes for services that were caught as materials
insert_catalog('פתיחת אספלט', 'EXCLUDE', 'שירות פתיחת אספלט')
insert_catalog('תיקון משטח', 'EXCLUDE', 'שירות תיקון')
insert_catalog('התקנת כיור|התקנת אסלה|משאבות לביוב', 'EXCLUDE', 'ציוד אינסטלציה (לא חומר גלם)')

print("Done.")
