from main import detect_composite_split, COMPOSITE_MATERIAL_RECIPES, MIN_WEIGHT_FOR_COMPOSITE_SPLIT_KG, CATEGORY_EMISSION_OVERRIDES

GREEN = "\033[92m"
RED   = "\033[91m"
RESET = "\033[0m"

print("\n" + "="*65)
print("  Composite Material Split — Unit Test")
print("="*65)
print(f"Recipes loaded : {len(COMPOSITE_MATERIAL_RECIPES)}")
print(f"Min threshold  : {MIN_WEIGHT_FOR_COMPOSITE_SPLIT_KG} kg\n")

tests = [
    # (text, weight_kg, should_split, expected_recipe_name)
    ("בטון מזוין B30",                    240_000.0, True,  "Reinforced Concrete"),
    ("ביסוס בטון מזוין 20 סמ",            48_000.0,  True,  "Reinforced Concrete"),
    ("זיון בטון לוחות קומה 3",             12_000.0,  True,  "Reinforced Concrete"),
    ("reinforced concrete slab",           5_000.0,   True,  "Reinforced Concrete"),
    ("קורה דריכת קדם 24 מ'",              10_000.0,  True,  "Prestressed Concrete"),
    ("כבל דריכה post-tensioned",           8_000.0,   True,  "Prestressed Concrete"),
    ("ביטון טרומי מזוין L=6",              3_000.0,   True,  "Precast Reinforced"),
    ("גביון סלסלת סלעים 1x1x1",            2_000.0,   True,  "Gabion"),
    ("גביון",                              5_000.0,   True,  "Gabion"),
    ("צינור PE100 עטוף בטון",              1_500.0,   True,  "Pipe with Concrete Surround"),
    ("עטיפת בטון לצינור",                  1_000.0,   True,  "Pipe with Concrete Surround"),
    # Should NOT split — single category materials
    ("בטון B30 (לא מזוין)",               48_000.0,   False, None),
    ("פלדת זיון ø16",                     5_000.0,    False, None),
    ("גביון",                              300.0,      False, None),  # below threshold
    ("אספלט שטיח",                        10_000.0,   False, None),
    ("צינור HDPE",                         2_000.0,   False, None),
]

PASS, FAIL = 0, 0
for text, weight, expect_split, expect_recipe in tests:
    comps = detect_composite_split(text, weight)
    got_split = comps is not None

    if got_split != expect_split:
        print(f"{RED}FAIL{RESET} [{text}] ({weight:,.0f} kg) — expected split={expect_split}, got split={got_split}")
        FAIL += 1
        continue

    if not got_split:
        print(f"{GREEN}PASS{RESET} SINGLE   '{text}' ({weight:,.0f} kg) — no split (correct)")
        PASS += 1
        continue

    # Check recipe name
    got_recipe = comps[0]["recipe_name"]
    recipe_ok = got_recipe == expect_recipe
    fraction_sum = sum(c["fraction"] for c in comps)
    fractions_ok = abs(fraction_sum - 1.0) < 0.001

    if recipe_ok and fractions_ok:
        total_co2 = sum(c["weight_kg"] * (CATEGORY_EMISSION_OVERRIDES.get(c["category"]) or 0) for c in comps)
        print(f"{GREEN}PASS{RESET} COMPOSITE'{text}' ({weight:,.0f} kg) → {got_recipe}")
        for c in comps:
            ef = CATEGORY_EMISSION_OVERRIDES.get(c["category"])
            co2 = c["weight_kg"] * ef if ef else 0
            print(f"       {c['description']}: {c['weight_kg']:>10,.0f} kg  EF={ef}  CO2e={co2:>10,.0f} kgCO2e")
        print(f"       TOTAL: {total_co2:>40,.0f} kgCO2e  (fraction sum={fraction_sum:.3f})")
        PASS += 1
    else:
        print(f"{RED}FAIL{RESET} COMPOSITE '{text}' — recipe={got_recipe} (expected {expect_recipe}), fraction_sum={fraction_sum}")
        FAIL += 1

print()
print("="*65)
status = f"{GREEN}ALL PASS{RESET}" if FAIL == 0 else f"{RED}{FAIL} FAILED{RESET}"
print(f"  Results: {GREEN}PASS {PASS}{RESET}  |  {RED}FAIL {FAIL}{RESET}  →  {status}")
print("="*65 + "\n")
