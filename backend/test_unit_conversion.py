"""
בדיקה ממצה (Comprehensive Unit Conversion Test)
מריצה את convert_quantity_to_kg על כל הקטגוריות + כל יחידות המידה האפשריות.
בודקת שהפלט הגיוני (לא None, לא שלילי, בטווח סביר).
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from main import (
    convert_quantity_to_kg,
    infer_uom,
    DEFAULT_CATEGORY_CONFIG,
)

# ─── צבעים לטרמינל ────────────────────────────────────────────────────────────
GREEN = "\033[92m"
RED   = "\033[91m"
YELLOW= "\033[93m"
RESET = "\033[0m"

PASS, FAIL, WARN = 0, 0, 0

def report(category, uom, qty, material, result, expected_min=None, expected_max=None, note=""):
    global PASS, FAIL, WARN
    wt = result.weight_kg
    if wt is None:
        print(f"{RED}❌ FAIL{RESET}  [{category}] {uom} qty={qty}  → None  ({material})")
        FAIL += 1
    elif wt <= 0:
        # Weight 0 or negative is almost always wrong for a real material
        print(f"{RED}❌ FAIL{RESET}  [{category}] {uom} qty={qty}  → {wt:,.1f} kg (zero/neg)  ({material})")
        FAIL += 1
    elif expected_min is not None and wt < expected_min:
        print(f"{YELLOW}⚠  WARN{RESET}  [{category}] {uom} qty={qty}  → {wt:,.1f} kg  (expected ≥ {expected_min:,})  ({material}) {note}")
        WARN += 1
    elif expected_max is not None and wt > expected_max:
        print(f"{YELLOW}⚠  WARN{RESET}  [{category}] {uom} qty={qty}  → {wt:,.1f} kg  (expected ≤ {expected_max:,})  ({material}) {note}")
        WARN += 1
    else:
        print(f"{GREEN}✅ PASS{RESET}  [{category}] {uom} qty={qty}  → {wt:,.1f} kg  ({result.assumption})")
        PASS += 1

def run(category, uom, qty, material, expected_min=None, expected_max=None, note=""):
    # infer_uom is not needed here — caller provides the UOM directly
    result = convert_quantity_to_kg(
        category=category,
        quantity=qty,
        material_text=material,
        assumed_uom=uom,
        thickness_cm=None,
        mapping=None,
        cls_meta={},
    )
    report(category, uom, qty, material, result, expected_min, expected_max, note)
    return result

# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*70)
print("  CarbonTrack — Unit Conversion Comprehensive Test")
print("="*70 + "\n")

# ── Lean Concrete ─────────────────────────────────────────────────────────────
print("── Lean Concrete ──────────────────────────────────")
run("Lean Concrete", "m3",  10, "בטון רזה", expected_min=20_000, expected_max=30_000)
run("Lean Concrete", "ton", 10, "בטון רזה", expected_min=9_000,  expected_max=11_000)
run("Lean Concrete", "kg",  100, "בטון רזה", expected_min=90,    expected_max=110)

# ── Structural Concrete ───────────────────────────────────────────────────────
print("\n── Structural Concrete ────────────────────────────")
run("Structural Concrete", "m3",  100, "בטון B30",       expected_min=200_000, expected_max=280_000)
run("Structural Concrete", "ton", 50,  "בטון זרוע",      expected_min=45_000,  expected_max=55_000)
run("Structural Concrete", "kg",  2000,"בטון B40",       expected_min=1_800,   expected_max=2_200)
run("Structural Concrete", "m2",  100, "לוח בטון עובי 20 ס\"מ", expected_min=20_000, expected_max=80_000)
run("Structural Concrete", "m",   50,  "כלונס בטון קוטר 80", expected_min=10_000, expected_max=200_000)

# ── Precast Concrete ──────────────────────────────────────────────────────────
print("\n── Precast Concrete ───────────────────────────────")
run("Precast Concrete", "unit", 20, "ביטון טרומי 1.5 טון", expected_min=10_000, expected_max=60_000)
run("Precast Concrete", "m3",   50, "ביטון טרומי",         expected_min=80_000, expected_max=150_000)
run("Precast Concrete", "ton",  30, "ביטון טרומי",         expected_min=25_000, expected_max=35_000)
run("Precast Concrete", "m2",  200, "פאנל טרומי",          expected_min=10_000, expected_max=120_000)
run("Precast Concrete", "m",    40, "קורה טרומית",         expected_min=5_000,  expected_max=50_000)

# ── Asphalt ───────────────────────────────────────────────────────────────────
print("\n── Asphalt ────────────────────────────────────────")
run("Asphalt", "ton",  500, "אספלט יצוק",              expected_min=450_000,  expected_max=550_000)
run("Asphalt", "m2",   800, "שטיח אספלט עובי 5 ס\"מ",  expected_min=60_000,   expected_max=120_000)
run("Asphalt", "m2",   800, "שטיח אספלט עובי 12 ס\"מ", expected_min=120_000,  expected_max=300_000)
run("Asphalt", "m2",   800, "שטיח אספלט ללא עובי",     expected_min=50_000,   expected_max=200_000, note="5cm default")
run("Asphalt", "m3",   200, "אספלט",                   expected_min=300_000,  expected_max=700_000)
run("Asphalt", "kg",  1000, "תוספת אספלט",             expected_min=900,      expected_max=1_100)

# ── Crushed Stone ─────────────────────────────────────────────────────────────
print("\n── Crushed Stone ──────────────────────────────────")
run("Crushed Stone", "m3",  300, "מצע חצץ",         expected_min=400_000,  expected_max=800_000)
run("Crushed Stone", "ton", 100, "חצץ 1-4 ס\"מ",    expected_min=90_000,   expected_max=110_000)
run("Crushed Stone", "kg",  500, "חצץ",              expected_min=450,      expected_max=550)

# ── Steel Rebar ───────────────────────────────────────────────────────────────
print("\n── Steel Rebar ────────────────────────────────────")
run("Steel Rebar", "ton",  20,   "פלדת זיון ø16",    expected_min=18_000, expected_max=22_000)
run("Steel Rebar", "kg",   500,  "ברזל זיון",        expected_min=450,    expected_max=550)
run("Steel Rebar", "m",    1000, "פלדת זיון ø12",    expected_min=500,    expected_max=5_000,  note="1.58 kg/m default")
run("Steel Rebar", "m2",   300,  "רשת ריצוף פלדה",   expected_min=1_000,  expected_max=5_000,  note="8 kg/m2 default")
run("Steel Rebar", "unit", 100,  "עוגן פלדה",        expected_min=100,    expected_max=2_000,  note="5 kg/unit default")

# ── Galvanized Steel ──────────────────────────────────────────────────────────
print("\n── Galvanized Steel ───────────────────────────────")
run("Galvanized Steel", "m",    100, "קורת פלדה U200",   expected_min=1_000, expected_max=20_000)
run("Galvanized Steel", "unit",  50, "עמוד גדר",         expected_min=2_000, expected_max=50_000, note="250 kg/unit default")
run("Galvanized Steel", "m2",   200, "לוח פלדה",         expected_min=1_000, expected_max=20_000, note="23.6 kg/m2 default")
run("Galvanized Steel", "ton",   10, "פלדה מגולוונת",    expected_min=9_000, expected_max=11_000)
run("Galvanized Steel", "kg",   800, "פלדה מגולוונת",    expected_min=700,   expected_max=900)

# ── Copper Wire (Cable) ───────────────────────────────────────────────────────
print("\n── Copper Wire (Cable) ────────────────────────────")
run("Copper Wire (Cable)", "m",    5000, "כבל נחושת 3x185 ממ\"ר",  expected_min=500,   expected_max=50_000)
run("Copper Wire (Cable)", "m",    2000, "כבל 4x2.5 ממ\"ר",        expected_min=100,   expected_max=5_000)
run("Copper Wire (Cable)", "unit",  100, "קופסת התפלגות נחושת",    expected_min=20,    expected_max=500, note="0.5 kg/unit")
run("Copper Wire (Cable)", "kg",    200, "נחושת",                  expected_min=180,   expected_max=220)

# ── HDPE Granulate ────────────────────────────────────────────────────────────
print("\n── HDPE Granulate ─────────────────────────────────")
run("HDPE Granulate", "m",    800, "צינור HDPE קוטר 315 SDR17",  expected_min=100,   expected_max=20_000)
run("HDPE Granulate", "m",    500, "צינור פוליאתילן 110",         expected_min=100,   expected_max=5_000)
run("HDPE Granulate", "kg",   200, "HDPE",                        expected_min=180,   expected_max=220)
run("HDPE Granulate", "ton",  10,  "גרגירי HDPE",                 expected_min=9_000, expected_max=11_000)
run("HDPE Granulate", "m3",   5,   "HDPE גולמי",                  expected_min=4_000, expected_max=6_000)

# ── PVC Pipe ──────────────────────────────────────────────────────────────────
print("\n── PVC Pipe ───────────────────────────────────────")
run("PVC Pipe", "m",    500, "צינור PVC ניקוז 6 אינץ'",    expected_min=500,   expected_max=10_000)
run("PVC Pipe", "m",    300, "צינור PVC 110 מ\"מ",           expected_min=100,   expected_max=5_000)
run("PVC Pipe", "m",    200, "צינור PVC לא מוגדר",          expected_min=100,   expected_max=5_000, note="default 1.95 kg/m")
run("PVC Pipe", "kg",   100, "PVC",                         expected_min=90,    expected_max=110)

# ── Waterproofing ─────────────────────────────────────────────────────────────
print("\n── Waterproofing ──────────────────────────────────")
run("Waterproofing", "m2",   500, "איטום ביטומני 4 ק\"ג",    expected_min=500,   expected_max=5_000)
run("Waterproofing", "m2",   300, "HDPE הגנה גאוטכנית",      expected_min=100,   expected_max=1_000)
run("Waterproofing", "m",    100, "פסי איטום PVC",           expected_min=20,    expected_max=500,  note="0.8 kg/m default")
run("Waterproofing", "unit",  50, "אטם מעבר צינור",          expected_min=10,    expected_max=500,  note="2 kg/unit default")
run("Waterproofing", "ton",   5,  "ביטומן",                  expected_min=4_500, expected_max=5_500)
run("Waterproofing", "kg",  200,  "ביטומן",                  expected_min=180,   expected_max=220)

# ── Aluminum ──────────────────────────────────────────────────────────────────
print("\n── Aluminum ───────────────────────────────────────")
run("Aluminum", "m",   1000, "כבל אלומיניום 3x120 ממ\"ר",   expected_min=50,   expected_max=5_000)
run("Aluminum", "m",    500, "פרופיל אלומיניום",             expected_min=20,   expected_max=2_000, note="0.10 kg/m default")
run("Aluminum", "unit",  80, "חלון אלומיניום",               expected_min=50,   expected_max=2_000, note="2 kg/unit default")
run("Aluminum", "kg",   300, "אלומיניום גולמי",              expected_min=270,  expected_max=330)

# ── Cementitious Mortar ───────────────────────────────────────────────────────
print("\n── Cementitious Mortar ────────────────────────────")
run("Cementitious Mortar", "m3",   5,  "טיח מלט",         expected_min=5_000,  expected_max=15_000)
run("Cementitious Mortar", "ton",  2,  "מלט",              expected_min=1_800,  expected_max=2_200)
run("Cementitious Mortar", "kg", 500,  "טיח",              expected_min=450,    expected_max=550)

# ── Paving ────────────────────────────────────────────────────────────────────
print("\n── Paving ─────────────────────────────────────────")
run("Paving", "m2",  200, "ריצוף אבן",                 expected_min=10_000, expected_max=50_000)
run("Paving", "m",   100, "אבן שפה",                   expected_min=1_000,  expected_max=20_000)
run("Paving", "unit", 50, "בלוק ריצוף",                expected_min=500,    expected_max=5_000)
run("Paving", "ton",  20, "ריצוף",                     expected_min=18_000, expected_max=22_000)

# ── Earthworks ────────────────────────────────────────────────────────────────
print("\n── Earthworks ─────────────────────────────────────")
run("Earthworks", "m3", 1000, "חפירה",                 expected_min=1_000_000, expected_max=3_000_000)
run("Earthworks", "ton",  500, "עפר",                  expected_min=450_000,   expected_max=550_000)

# ── Fill Material ─────────────────────────────────────────────────────────────
print("\n── Fill Material ──────────────────────────────────")
run("Fill Material", "m3",  500, "מצע",                 expected_min=500_000, expected_max=1_500_000)
run("Fill Material", "ton", 100, "עפר מילוי",           expected_min=90_000,  expected_max=110_000)

# ── Glass ─────────────────────────────────────────────────────────────────────
print("\n── Glass ──────────────────────────────────────────")
run("Glass", "m2",   50, "זכוכית 10 מ\"מ",             expected_min=500,   expected_max=5_000)
run("Glass", "ton",   2, "זכוכית",                      expected_min=1_800, expected_max=2_200)

# ── Wood ──────────────────────────────────────────────────────────────────────
print("\n── Wood ───────────────────────────────────────────")
run("Wood", "m3",  50, "קורות עץ",                      expected_min=10_000, expected_max=40_000)
run("Wood", "ton",  5, "עץ",                            expected_min=4_500,  expected_max=5_500)

# ── Edge cases ────────────────────────────────────────────────────────────────
print("\n── Edge Cases ─────────────────────────────────────")
run("Structural Concrete", "m3", 0.1,  "בטון",          expected_min=100,    expected_max=500, note="tiny qty")
run("Asphalt",             "m2", 10000,"כביש ארוך",      expected_min=100_000,expected_max=3_000_000, note="large m2 asphalt")
run("Galvanized Steel",    "m",  0.5,  "ברגים",          expected_min=1,      expected_max=200, note="sub-meter")

# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*70)
print(f"  Results:  {GREEN}✅ PASS: {PASS}{RESET}  |  {YELLOW}⚠  WARN: {WARN}{RESET}  |  {RED}❌ FAIL: {FAIL}{RESET}")
print("="*70 + "\n")
