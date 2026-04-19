import io
import json
import logging
import math
import os
import re
import traceback
import threading
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeoutError
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple
from google.cloud import bigquery
import logging
import traceback
import pandas as pd
import requests
from flask import Flask, jsonify, request
from google import genai
from google.genai import types
from google.cloud import bigquery, storage
from google.cloud.exceptions import NotFound

# ==========================================================
# CONFIG
# ==========================================================
PROJECT_ID = os.environ.get("GCP_PROJECT", "argon-ace-483810-n9")
BQ_PROJECT_ID = os.environ.get("BQ_PROJECT_ID", PROJECT_ID)
DATASET_ID = os.environ.get("BQ_DATASET_ID", "netivei_emissions_db")
DATASET_LOCATION = os.environ.get("BQ_DATASET_LOCATION", "me-west1")

BQ_PROCESSING_RUNS_TABLE = os.environ.get(
    "BQ_PROCESSING_RUNS_TABLE",
    f"{BQ_PROJECT_ID}.{DATASET_ID}.processing_runs",
)
BQ_SUMMARY_TABLE = os.environ.get(
    "BQ_SUMMARY_TABLE",
    f"{BQ_PROJECT_ID}.{DATASET_ID}.emissions_summary",
)
BQ_DETAILS_TABLE = os.environ.get(
    "BQ_DETAILS_TABLE",
    f"{BQ_PROJECT_ID}.{DATASET_ID}.emissions_details",
)
BQ_MAPPING_TABLE = os.environ.get(
    "BQ_MAPPING_TABLE",
    f"{BQ_PROJECT_ID}.{DATASET_ID}.catalog_mapping",
)
BQ_CATALOG_TABLE = os.environ.get(
    "BQ_CATALOG_TABLE",
    f"{BQ_PROJECT_ID}.{DATASET_ID}.materials_catalog",
)
BQ_REVIEW_QUEUE_TABLE = os.environ.get(
    "BQ_REVIEW_QUEUE_TABLE",
    f"{BQ_PROJECT_ID}.{DATASET_ID}.review_queue",
)
BQ_FACTOR_CACHE_TABLE = os.environ.get(
    "BQ_FACTOR_CACHE_TABLE",
    f"{BQ_PROJECT_ID}.{DATASET_ID}.climatiq_factor_cache",
)
BQ_UNIT_RULES_TABLE = os.environ.get(
    "BQ_UNIT_RULES_TABLE",
    f"{BQ_PROJECT_ID}.{DATASET_ID}.unit_conversion_rules",
)
BQ_CONCRETE_PIPE_TABLE = os.environ.get(
    "BQ_CONCRETE_PIPE_TABLE",
    f"{BQ_PROJECT_ID}.{DATASET_ID}.concrete_pipe_catalog",
)
BQ_CABLE_TABLE = os.environ.get(
    "BQ_CABLE_TABLE",
    f"{BQ_PROJECT_ID}.{DATASET_ID}.cable_cross_section_catalog",
)
BQ_BOQ_MAPPING_TABLE = os.environ.get(
    "BQ_BOQ_MAPPING_TABLE",
    f"{BQ_PROJECT_ID}.{DATASET_ID}.boq_code_mapping",
)
BQ_ANNUAL_PAID_ITEMS_2025_RAW_TABLE = os.environ.get(
    "BQ_ANNUAL_PAID_ITEMS_2025_RAW_TABLE",
    f"{BQ_PROJECT_ID}.{DATASET_ID}.annual_paid_items_2025_raw",
)

BQ_ANNUAL_PAID_ITEMS_2025_REFERENCE_VIEW = os.environ.get(
    "BQ_ANNUAL_PAID_ITEMS_2025_REFERENCE_VIEW",
    f"{BQ_PROJECT_ID}.{DATASET_ID}.v_annual_2025_material_reference",
)

CLIMATIQ_BASE_URL = os.environ.get("CLIMATIQ_BASE_URL", "https://api.climatiq.io/data/v1")
CLIMATIQ_DATA_VERSION = os.environ.get("CLIMATIQ_DATA_VERSION", "^21")
CLIMATIQ_REGION = os.environ.get("CLIMATIQ_REGION")
CLIMATIQ_SOURCE = os.environ.get("CLIMATIQ_SOURCE")
HTTP_TIMEOUT = int(os.environ.get("HTTP_TIMEOUT", "25"))

VERTEX_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", PROJECT_ID)
VERTEX_LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "global")
VERTEX_MODEL = os.environ.get("VERTEX_MODEL", "gemini-2.5-flash")
USE_VERTEX_CLASSIFIER = os.environ.get("USE_VERTEX_CLASSIFIER", "true").lower() == "true"
AUTO_APPROVE_CONFIDENCE = float(os.environ.get("AUTO_APPROVE_CONFIDENCE", "0.85"))
DEFAULT_RELIABILITY_THRESHOLD = float(os.environ.get("DEFAULT_RELIABILITY_THRESHOLD", "0.85"))
DEFAULT_MAX_CLIMATIQ_CANDIDATES = int(os.environ.get("DEFAULT_MAX_CLIMATIQ_CANDIDATES", "5"))
DEFAULT_MAX_FACTOR_SPREAD_PCT = float(os.environ.get("DEFAULT_MAX_FACTOR_SPREAD_PCT", "15"))
DEFAULT_AUTO_WRITE_AI_APPROVED = os.environ.get("DEFAULT_AUTO_WRITE_AI_APPROVED", "true").lower() == "true"

AUTO_WRITE_MAPPINGS = os.environ.get("AUTO_WRITE_MAPPINGS", "true").lower() == "true"

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()

# ==========================================================
# APP + CLIENTS
# ==========================================================
app = Flask(__name__)
from flask_cors import CORS
CORS(app, resources={r"/*": {"origins": "*"}})
logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("calc-carbon")

storage_client = storage.Client(project=PROJECT_ID)
bq_client = bigquery.Client(project=BQ_PROJECT_ID)

genai_client = genai.Client(
    vertexai=True,
    project=VERTEX_PROJECT,
    location=VERTEX_LOCATION,
)

# ==========================================================
# CATEGORY CONFIG
# ==========================================================
DEFAULT_CATEGORY_CONFIG: Dict[str, Dict[str, Any]] = {
    "Lean Concrete": {
        "climatiq_search": "concrete",
        "density_kg_m3": 2400.0,
        "default_uom": "m3",
    },
    "Structural Concrete": {
        "climatiq_search": "concrete",
        "density_kg_m3": 2400.0,
        "default_uom": "m3",
        "kg_per_meter": 1200.0,    # pile/column default: ~80cm avg diameter (π×0.16×2400)
        "kg_per_m2": 240.0,        # slab default: ~10cm thickness × 2400 kg/m3
    },
    "Precast Concrete": {
        "climatiq_search": "precast concrete",
        "density_kg_m3": 2400.0,
        "default_uom": "unit",
        "kg_per_unit": 1500.0,
        "kg_per_m2": 240.0,        # panel default: ~10cm thickness × 2400 kg/m3
        "kg_per_meter": 400.0,     # beam/lintel default
    },
    "Asphalt": {
        "climatiq_search": "asphalt",
        "density_kg_m3": 2350.0,
        "default_uom": "m2_cm_or_ton",
        "kg_per_m2_per_cm": 23.50,
    },
    "Crushed Stone": {
        "climatiq_search": "gravel",
        "density_kg_m3": 2000.0,
        "default_uom": "m3",
    },
    "Steel Rebar": {
        "climatiq_search": "steel rebar",
        "density_kg_m3": 7850.0,
        "default_uom": "ton_or_kg",
        "kg_per_unit": 5.0,        # anchor bolt/insert default
        "kg_per_meter": 1.58,      # ø16mm rebar default
        "kg_per_m2": 8.0,          # rebar mesh default ~10kg/m2
    },
    "Galvanized Steel": {
        "climatiq_search": "galvanized steel",
        "density_kg_m3": 7850.0,
        "default_uom": "m_or_unit",
        "kg_per_meter": 30.0,
        "kg_per_m2": 23.6,         # 3mm steel sheet: 0.003 × 7850 kg/m3
        "kg_per_unit": 250.0,
    },
    "Copper Wire (Cable)": {
        "climatiq_search": "copper",
        "density_kg_m3": 8960.0,
        "default_uom": "m_with_mm2",
        "kg_per_meter": 0.13,
        "kg_per_unit": 0.5,        # connector/terminal/junction box
    },
    "HDPE Granulate": {
        "climatiq_search": "hdpe",
        "density_kg_m3": 950.0,
        "default_uom": "m_with_sdr_or_m2_mm",
        "kg_per_meter": 0.51,
    },
    "PVC Pipe": {
        "climatiq_search": "pvc",
        "density_kg_m3": 1400.0,
        "default_uom": "m_by_nominal_inch",
        "kg_per_meter": 1.95,
    },
    "Concrete Pipe": {
        "climatiq_search": "concrete pipe",
        "density_kg_m3": 2400.0,
        "default_uom": "m_or_unit",
    },
    "Waterproofing": {
        "climatiq_search": "bitumen",
        "density_kg_m3": 1035.0,
        "default_uom": "m2",
        "kg_per_m2_membrane": 4.0,
        "kg_per_m2_protection": 0.675,
        "kg_per_unit": 2.0,        # small waterstop / penetration seal / seal plug fallback
        "kg_per_meter": 0.8,       # hydrophilic/PVC waterstop strip fallback
    },
    "Aluminum": {
        "climatiq_search": "aluminum",
        "density_kg_m3": 2700.0,
        "default_uom": "m_with_mm2",
        "kg_per_meter": 0.10,
        "kg_per_unit": 2.0,        # window frame/panel section default
    },
    "Glass": {
        "climatiq_search": "glass",
        "density_kg_m3": 2500.0,
        "default_uom": "m2_or_m3_or_unit",
    },
    "Wood": {
        "climatiq_search": "softwood timber",
        "density_kg_m3": 500.0,
        "default_uom": "m3",
    },
    "Cementitious Mortar": {
        "climatiq_search": "mortar",
        "density_kg_m3": 1900.0,
        "default_uom": "m3_or_ton",
    },
    # --- categories that exist in BOQ tables but were missing from code ---
    "Earthworks": {
        # Excavation, backfill, compaction — tracked as moved soil/gravel
        # Emission factor: diesel equipment fuel consumption per m3
        "climatiq_search": "excavation earthworks",
        "density_kg_m3": 1800.0,   # loose soil/gravel
        "default_uom": "m3",
    },
    "Fill Material": {
        # Sub-base fill, granular backfill — crushed stone or soil
        "climatiq_search": "gravel fill",
        "density_kg_m3": 1900.0,   # compacted granular fill
        "default_uom": "m3",
        "kg_per_m2_per_cm": 19.0,  # for m2 rows with thickness
    },
    "Paving": {
        # Paving stones, kerb stones, interlocking blocks — precast concrete
        "climatiq_search": "precast concrete",
        "density_kg_m3": 2400.0,
        "default_uom": "m2_or_m_or_unit",
        "kg_per_unit": 50.0,       # average kerb stone / paving block
        "kg_per_meter": 80.0,      # kerb stone per linear meter
        "kg_per_m2": 120.0,        # paving/tiles default proxy (~5cm concrete/stone pavers)
    },
}

ALLOWED_CATEGORIES = list(DEFAULT_CATEGORY_CONFIG.keys()) + ["Unknown", "EXCLUDE"]

# ICE DB 2019 emission factor overrides (kgCO2e/kg)
# Used when Climatiq returns a known-wrong factor for a category.
# Source: ICE DB v3.0 (University of Bath, 2019)
CATEGORY_EMISSION_OVERRIDES: Dict[str, float] = {
    "Copper Wire (Cable)":  3.81,   # ICE DB: Copper, primary & secondary — 3.81 kgCO2e/kg
    "Aluminum":             8.24,   # Primary aluminium (Israel: infrastructure uses primary, not recycled)
    "Structural Concrete":  0.149,  # ICE DB: Concrete (reinforced) — Climatiq returning ~5x too low
    "Lean Concrete":        0.107,  # ICE DB: Concrete (not reinforced)
    "Precast Concrete":     0.182,  # ICE DB: Precast concrete (includes reinforcement)
    "Fill Material":        0.0048, # ICE DB: General aggregate/fill
    "Earthworks":           0.0024, # ICE DB: Earthworks, bulk excavation
    "Crushed Stone":        0.0048, # ICE DB: Aggregate — Climatiq returns 0.01 (2x high)
    "Waterproofing":        2.000,  # ICE DB: Bituminous membrane — Climatiq returns 0.22 (9x low)
    "Cementitious Mortar":  0.208,  # ICE DB: Mortar — Climatiq returns near zero
    "Galvanized Steel":     2.890,  # ICE DB: Galvanized steel — Climatiq returns 2.284 (21% low)
    "PVC Pipe":             3.100,  # ICE DB: PVC — Climatiq returns 2.43 (22% low)
    "Asphalt":              0.0472, # ICE DB: Asphalt — Climatiq API always fails for this category
    "Steel Rebar":          1.990,  # ICE DB: Steel rebar — Climatiq returns 1.72 (13% low)
    "HDPE Granulate":       1.930,  # ICE DB: HDPE — Climatiq returns 1.795 (7% low)
}

# ==========================================================
# COMPOSITE MATERIAL RECIPES
# ==========================================================
# Each recipe defines a composite material that is really a mixture of
# two or more category components. Each component has:
#   "category"  – must be in CATEGORY_EMISSION_OVERRIDES / DEFAULT_CATEGORY_CONFIG
#   "fraction"  – mass fraction (must sum to 1.0)
#   "description" – human-readable label for the sub-row
#
# Only applied when total weight_kg >= the recipe's min_weight_kg
# (default 500 kg) to avoid noise from tiny quantities.

MIN_WEIGHT_FOR_COMPOSITE_SPLIT_KG: float = 500.0

COMPOSITE_MATERIAL_RECIPES: List[Dict[str, Any]] = [
    # ── Reinforced Concrete (בטון מזוין) ─────────────────────────────────
    # ICE DB: typical reinforced slab has ~100-160 kg rebar/m³ (2400 kg/m³ concrete)
    # => ~5% steel by mass, 95% concrete
    {
        "name": "Reinforced Concrete",
        "name_he": "בטון מזוין",
        "patterns": [
            r"בטון\s*מזו?[יין]",
            r"reinforced\s*concrete",
            r"בטון\s*(?:B|G)\d+.*זיון",
            r"זיון.*בטון",
        ],
        "min_weight_kg": 500.0,
        "components": [
            {"category": "Structural Concrete", "fraction": 0.95, "description": "בטון מזוין — רכיב בטון (95%)"},
            {"category": "Steel Rebar",         "fraction": 0.05, "description": "בטון מזוין — רכיב זיון (5%)"},
        ],
    },
    # ── Prestressed / Post-tensioned Concrete ────────────────────────────
    # Higher steel ratio: ~7% (tendons + stirrups)
    {
        "name": "Prestressed Concrete",
        "name_he": "בטון דחוס / פרה-מתוח",
        "patterns": [
            r"בטון\s*(?:דחוס|פרה.?מתוח|פרה.?נפוח)",
            r"post.?tens|pre.?stress|prestress",
            r"קורה\s*דריכת\s*קדם",
            r"כבל\s*דריכה",
        ],
        "min_weight_kg": 1000.0,
        "components": [
            {"category": "Structural Concrete", "fraction": 0.93, "description": "בטון דחוס — רכיב בטון (93%)"},
            {"category": "Steel Rebar",         "fraction": 0.07, "description": "בטון דחוס — רכיב פלדה/כבלים (7%)"},
        ],
    },
    # ── Precast Reinforced (ביטון טרומי מזוין) ───────────────────────────
    {
        "name": "Precast Reinforced",
        "name_he": "ביטון טרומי מזוין",
        "patterns": [
            r"טרומי\s*מזו?[יין]",
            r"precast.*reinforc",
            r"מזוין.*טרומי",
        ],
        "min_weight_kg": 500.0,
        "components": [
            {"category": "Precast Concrete", "fraction": 0.94, "description": "טרומי מזוין — רכיב בטון טרומי (94%)"},
            {"category": "Steel Rebar",      "fraction": 0.06, "description": "טרומי מזוין — רכיב זיון (6%)"},
        ],
    },
    # ── Composite Steel-Concrete Column / Beam ───────────────────────────
    {
        "name": "Composite Steel-Concrete",
        "name_he": "עמוד/קורה קומפוזיטי פלדה-בטון",
        "patterns": [
            r"composite.*steel.*concrete",
            r"פלדה\s*ממולאת?\s*בטון",
            r"עמוד\s*קומפוזיטי",
        ],
        "min_weight_kg": 1000.0,
        "components": [
            {"category": "Galvanized Steel",    "fraction": 0.40, "description": "קומפוזיט — רכיב פלדה (40%)"},
            {"category": "Structural Concrete", "fraction": 0.60, "description": "קומפוזיט — רכיב בטון (60%)"},
        ],
    },
    # ── Gabion (גביון / סלסלת סלעים) ─────────────────────────────────────
    # Wire basket + stones: ~3% steel wire, ~97% crushed stone by mass
    {
        "name": "Gabion",
        "name_he": "גביון / סלסלת סלעים",
        "patterns": [
            r"גביון",
            r"gabion",
            r"סלסלת\s*סלעים",
            r"סל\s*(?:גבי|סלע|אבן)",
        ],
        "min_weight_kg": 500.0,
        "components": [
            {"category": "Crushed Stone",    "fraction": 0.97, "description": "גביון — רכיב סלעים (97%)"},
            {"category": "Galvanized Steel", "fraction": 0.03, "description": "גביון — רכיב רשת פלדה (3%)"},
        ],
    },
    # ── Full Road Pavement (אספלט + מצע) ─────────────────────────────────
    {
        "name": "Full Road Pavement",
        "name_he": "מבנה כביש מלא (אספלט + מצע)",
        "patterns": [
            r"מבנה\s*(?:כביש|מסלול)\s*מלא",
            r"full\s*pavement\s*structure",
            r"(?:כביש|מסלול).*אספלט.*חצץ",
        ],
        "min_weight_kg": 5000.0,
        "components": [
            {"category": "Asphalt",       "fraction": 0.50, "description": "מסלול מלא — רכיב אספלט (50%)"},
            {"category": "Crushed Stone", "fraction": 0.50, "description": "מסלול מלא — רכיב מצע (50%)"},
        ],
    },
    # ── HDPE Pipe with Concrete Surround ─────────────────────────────────
    {
        "name": "Pipe with Concrete Surround",
        "name_he": "צינור עטוף בטון",
        "patterns": [
            r"עטיפ[תה]\s*בטון",
            r"צינור.*(?:עטוף|ממולא)\s*בטון",
            r"concrete\s*surround",
        ],
        "min_weight_kg": 500.0,
        "components": [
            {"category": "Structural Concrete", "fraction": 0.85, "description": "צינור עטוף — רכיב עטיפת בטון (85%)"},
            {"category": "HDPE Granulate",      "fraction": 0.15, "description": "צינור עטוף — רכיב צינור פלסטיק (15%)"},
        ],
    },
    # ── Concrete with Permanent PVC Formwork ─────────────────────────────
    {
        "name": "Concrete with PVC Formwork",
        "name_he": "בטון עם ביס/מודולה קבוע PVC",
        "patterns": [
            r"ביס\s*(?:קבוע|מודולה|pvc)",
            r"מודולה.*(?:pvc|פלסטי)",
            r"pvc\s*permanent\s*formwork",
        ],
        "min_weight_kg": 500.0,
        "components": [
            {"category": "Structural Concrete", "fraction": 0.90, "description": "בטון עם ביס — רכיב בטון (90%)"},
            {"category": "PVC Pipe",            "fraction": 0.10, "description": "בטון עם ביס — רכיב PVC (10%)"},
        ],
    },
]


def detect_composite_split(
    material_text: str,
    weight_kg: float,
) -> Optional[List[Dict[str, Any]]]:
    """
    If material_text matches a composite recipe AND weight_kg >= threshold,
    returns a list of component dicts (one per sub-material):
        [{"category", "fraction", "weight_kg", "description", "recipe_name"}, ...]
    Otherwise returns None → process as a single-category row.
    """
    if not material_text or not weight_kg or weight_kg <= 0:
        return None
    text_norm = normalize_text(material_text)
    for recipe in COMPOSITE_MATERIAL_RECIPES:
        min_w = float(recipe.get("min_weight_kg", MIN_WEIGHT_FOR_COMPOSITE_SPLIT_KG))
        if weight_kg < min_w:
            continue
        for pattern in recipe["patterns"]:
            try:
                if re.search(pattern, text_norm, flags=re.IGNORECASE):
                    return [
                        {
                            "category":    c["category"],
                            "fraction":    c["fraction"],
                            "weight_kg":   round(weight_kg * c["fraction"], 3),
                            "description": c["description"],
                            "recipe_name": recipe["name"],
                        }
                        for c in recipe["components"]
                    ]
            except re.error:
                logger.warning("Composite recipe pattern error: %s", pattern)
    return None


CATEGORY_RULES: List[Tuple[str, List[str]]] = [
    ("Waterproofing",
     [r"איטו[םמ]", r"ממברנה", r"ביטומ", r"יריעת\s*hdpe", r"גאוטכני", r"פריימר", r"זפת", r"פוליאוריטן", r"סילר",
      r"יריעות"]),
    ("Asphalt", [r"אספלט", r"אספלת", r"תא.?צ", r"תא.?מ", r"\bSMA\b", r"בינדר", r"אמולסיה"]),
    ("Steel Rebar", [r"זיון", r"מוטות\s*פלדה", r"פלדה\s*מצולעים", r"ת.?י\s*4466", r"רשתות\s*פלדה", r"ברזל\s*בניין"]),
    ("Copper Wire (Cable)", [r"כבל.*נחושת", r"נחושת", r"N2XY", r"NYY", r"XLPE", r"גידים", r"כבל\s*חשמל", r"מוליך"]),
    ("Aluminum", [r"אלומיניום", r"אלומניום", r"פרופיל\s*אלומ", r"NA2XY", r"NA2XSY", r"כבל.*אלומינ", r"אלומינ.*כבל", r"פח\s*אלומיניום"]),
    ("HDPE Granulate",
     [r"HDPE", r"H\.D\.P\.E", r"פוליאתילן", r"PE100", r"PE-100", r"יק.?ע", r"שרשור.*פוליאתילן", r"צנרת\s*פוליאתילן",
      r"פוליגל", r"פוליפרופילן", r"פלסטי"]),
    ("PVC Pipe", [r"P\.?V\.?C", r"PVC", r"צינור\s*קשיח", r"מריכף", r"מריפלס", r"צנרת.*פלסטיק"]),
    ("Galvanized Steel",
     [r"מגולוונ", r"גדר", r"מעקה\s*(?:פלדה|בטיחות)?", r"פח\s*מגולוון", r"עמוד.*פלדה", r"זרוע.*פלדה", r"ארון", r"רמזור",
      r"תמרור", r"ברזל\s*יצוק", r"מכסה\s*לתא"]),
    ("Lean Concrete", [r"בטון\s*רזה", r"ב-20", r"בטון\s*מדה", r"מדה\s*מתפלסת"]),
    ("Structural Concrete",
     [r"בטון", r"יצוק\s*באתר", r"ב-30", r"ב-40", r"כלונס", r"קירות\s*מבטון", r"ב-50", r"רפסודה", r"בלוקים"]),
    ("Crushed Stone",
     [r"אגרגט", r"חצץ", r"מצע", r"בקאלש", r"אבן\s*גרוסה", r"שומשום", r"חול", r"מחצבה", r"זיפזיף", r"אדמה", r"סלעים",
      r"מצע\s*א'"]),
    # --- new categories ---
    ("Earthworks",
     [r"חפירה", r"עפר\s*עודף", r"הוצאת\s*עפר", r"פינוי\s*עפר", r"דחיסה", r"מילוי\s*עפר",
      r"עבודות\s*עפר", r"גריפה"]),
    ("Fill Material",
     [r"מילוי\s*(?:חוזר|גרוס|אבן|חול|מחוזק)", r"מצע\s*מילוי", r"חומר\s*מילוי",
      r"מלית", r"מילוי\s*תחת", r"מילוי\s*מסביב", r"טמינה"]),
    ("Paving",
     [r"ריצוף", r"אבן\s*שפה", r"שפה\s*(?:טרומ|בטון|אבן)", r"מדרכה",
      r"ריצוף\s*(?:אבן|גרניט|שיש|קרמיק|אריח)", r"אריחי\s*בטון", r"אבן\s*משתלבת"]),
]

FINANCIAL_ADJUSTMENT_PATTERNS = [
    r"ניכוי(?:ים)?",
    r"קנס(?:ות)?",
    r"קיזוז(?:ים)?",
    r"זיכוי(?:ים)?",
    r"חיוב(?:ים)?",
    r"לו[\"׳']?ז",
    r"ליקויי\s*בטיחות",
    r"ליקויי\s*הבטחת\s*איכות",
    r"מנהל\s*פרויקט",
]

EXCLUDE_PATTERNS = [
    r"\bפ[י]?רוק\b",
    r"\bפוליסטר[ין]\b",
    r"\bEPS\b",
    r"\bXPS\b",
    r"תוספת\s+מחיר",            # price supplement "תוספת מחיר X" — NOT physical material
    r"תוספת\s+למחיר",           # "addition to price" — accounting item only
    r"תוספת\s+לסעיפי\s+צינור",  # "addition to pipe items" — pricing only
    r"תוספת\s+לביצוע\s+מחיר",  # "addition to execution price" — pricing only
    r"\bצביעה\b",
    r"\bקרצוף\b",
    r"\bתוספת\s*מחיר\b",
    r"\bגמר\s*פני\b",
    r"\bעבודה\b",
    r"\bהשכרה\b",
    r"\bחפירה\b",
    r"\bבדיק[הת]\b",
    r"\bמדיד[הות]\b",
    r"\bתכנון\b",
    r"\bאחזק[הת]\b",
    r"\bסילוק\b",
    r"\bקידוח\b",
    r"\bחציבה\b",
    r"\bשאיבה\b",
    r"\bגיזום\b",
    r"\bטיפול\b",
    r"\bתשלום\b",
    r"\bפועל\b",
    r"\bמנהל\s*עבודה\b",
    r"\bיעה\s*אופני\b",
    r"\bמחפרון\b",
    r"\bמנוף\b",
    r"\bהעתק[הת]\b",
    r"\bחישוף\b",
    r"\bריסוס\b",
    r"\bעקירת\b",
    r"\bצוות\b",
    r"\bמשאית\b",
    r"\bביובית\b",
    r"\bהסרה\b",
    r"\bהסרת\b",
]

# Pre-compiled for performance — used in should_exclude()
_EXCLUDE_PATTERNS_COMPILED = [re.compile(p, re.IGNORECASE) for p in EXCLUDE_PATTERNS]

MATERIAL_INDICATOR_PATTERNS = [
    r"בטון",
    r"בטקל",
    r"CLSM",
    r"אספלט",
    r"מצע",
    r"סומסום",
    r"שומשום",
    r"חול",
    r"אגרגט",
    r"חצץ",
    r"יריע[התו]?\s+ביטומני",
    r"אמולסי",
    r"תחליב\s*ביטומני",
    r"ברזל\s*זיון",
    r"פלדה",
    r"PVC",
    r"HDPE",
    r"פוליאתילן",
    r"PE100",
    r"N2XY",
    r"XLPE",
    r"כבל",
    r"נחושת",
    r"צינור",
]


SUSPECT_NON_MATERIAL_PATTERNS = [
    r"\bתוספת\s*מחיר\b",
    r"\bפירוק\b",
    r"\bקרצוף\b",
    r"\bגמר\b",
    r"\bעבודה\b",
    r"\bהתקנה\b",
    r"\bאספקה\s*והתקנה\b",
    r"\bהשכרה\b",
    r"\bתחזוקה\b",
    r"\bתיקון\b",
]

THICKNESS_CM_PATTERNS = [
    r"""עובי\s*(\d+(?:\.\d+)?)\s*ס["'׳]?מ""",
    r"""(\d+(?:\.\d+)?)\s*ס["'׳]?מ\s*עובי""",
    r"""\d+(?:\.\d+)?\s*/\s*\d+(?:\.\d+)?\s*/\s*(\d+(?:\.\d+)?)\s*ס["'׳]?מ""",
    # Format: _עובי 5_ or עובי 5 (without ס"מ — common in asphalt BOQ codes)
    r"""[_\s]עובי\s*(\d+(?:\.\d+)?)[_\s]""",
    r"""עובי\s+שכבה\s+(\d+(?:\.\d+)?)""",  # הטלאה בעובי שכבה 5 ס"מ
]

POSSIBLE_MATERIAL_COLUMNS = [
    "טקסט קצר", "תיאור", "description", "material", "item", "short_text",
    "תאור חומר/שירות חוזה", "תיאור חומר/שירות חוזה"
]

POSSIBLE_QUANTITY_COLUMNS = [
    "כמות יעד", "כמות", "quantity", "qty", "amount", "כמות בקבלות טובין"
]

POSSIBLE_UNIT_COLUMNS = [
    "יחידה", "יח'", 'יח"', "unit", "uom", "measure", "יחידת מידה בחוזה"
]

POSSIBLE_BOQ_CODE_COLUMNS = [
    "קוד", "סעיף", "boq_code", "item_code", "code", "material", "חומר/שירות חוזה",
    "חומר"
]
ANNUAL_2025_LAYOUT_COLUMNS = {
    "boq_code": ["חומר/שירות חוזה"],
    "material": ["תאור חומר/שירות חוזה", "תיאור חומר/שירות חוזה"],
    "unit": ["יחידת מידה בחוזה"],
    "quantity": ["כמות בקבלות טובין"],
}
SOURCE_MODE_AUTO = "auto"
SOURCE_MODE_BOQ = "boq"
SOURCE_MODE_ANNUAL = "annual_paid_2025"

VERTEX_CLASSIFICATION_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "category": {"type": "STRING"},
        "confidence": {"type": "NUMBER", "minimum": 0, "maximum": 1},
        "review_required": {"type": "BOOLEAN"},
        "inferred_uom": {"type": "STRING"},
        "reason": {"type": "STRING"},
        "excluded": {"type": "BOOLEAN"},
        "extracted_element_type": {"type": "STRING"},
        "extracted_dimension_cm": {"type": "INTEGER"},
    },
    "required": ["category", "confidence", "review_required", "inferred_uom", "reason", "excluded"],
}

VERTEX_SYSTEM_INSTRUCTION = f"""
You classify Hebrew civil infrastructure BOQ material lines.

Rules:
1. Pick exactly one category from: {', '.join(ALLOWED_CATEGORIES)}.
2. If the line is labor, service, demolition, surcharge, finishing, or non-material, set category='EXCLUDE' and excluded=true.
3. Use inferred_uom from this enum when possible: kg, ton, m3, m2, m, unit, unknown.
4. If the line is a concrete pipe, manhole, precast wall, or curbstone, populate extracted_element_type with one of: concrete_pipe, precast_manhole, precast_wall, curbstone.
5. extracted_dimension_cm should be the main diameter/size in centimeters when available.
6. Keep review_required=true when confidence < 0.8 or details are missing for conversion.
7. Return JSON only.
"""


# ==========================================================
# DATACLASSES
# ==========================================================
@dataclass
class ConversionResult:
    original_quantity: float
    original_uom: Optional[str]
    assumed_uom: str
    weight_kg: Optional[float]
    factor_used: Optional[float]
    assumption: str
    thickness_cm: Optional[float] = None


EMISSIONS_DETAILS_DEFAULTS: Dict[str, Any] = {
    "error_message": None,
    "emission_co2e": None,
    "emission_factor_source": None,
    "emission_factor_id": None,
    "status": None,
    "excluded": False,
    "source_bucket": None,
    "conversion_assumption": None,
    "weight_kg": None,
    "assumed_uom": None,
    "uploader_email": None,
    "matched": False,
    "original_uom": None,
    "original_quantity": None,
    "conversion_factor_used": None,
    "boq_code": None,
    "review_required": False,
    "classification_confidence": None,
    "category_rule": None,
    "material": None,
    "category": None,
    "thickness_cm_extracted": None,
    "normalized_material": None,
    "project_type": None,
    "project_name": None,
    "calculation_date": None,
    "climatiq_activity_id": None,
    "run_id": None,
    "classification_method": None,
    "source_file": None,
    "item_code": None,
    "short_text": None,
    "quantity": None,
    "quantity_unit": None,
    "quantity_kg": None,
    "ef_id": None,
    "error_msg": None,
    "data_source": None,
    "contractor": None,
    "region": None,
    "reliability_score": None,   # computed per row — 0.0-1.0
    "reliability_status": None,  # auto_approved / review_required / rejected
}


def complete_emissions_detail_row(row: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    metadata = metadata or {}
    out = dict(EMISSIONS_DETAILS_DEFAULTS)
    out.update({
        "run_id": metadata.get("run_id"),
        "source_file": metadata.get("source_file"),
        "source_bucket": metadata.get("source_bucket"),
        "uploader_email": metadata.get("uploader_email"),
        "project_type": metadata.get("project_type"),
        "project_name": metadata.get("project_name"),
        "contractor": metadata.get("contractor"),
        "region": metadata.get("region"),
    })
    out.update(row)
    out["item_code"] = out.get("item_code") or out.get("boq_code")
    out["quantity_unit"] = out.get("quantity_unit") or out.get("assumed_uom") or out.get("original_uom")
    out["quantity_kg"] = out.get("quantity_kg") if out.get("quantity_kg") is not None else out.get("weight_kg")
    out["ef_id"] = out.get("ef_id") or out.get("emission_factor_id")
    out["error_msg"] = out.get("error_msg") or out.get("error_reason") or out.get("error_message")
    out["data_source"] = out.get("data_source") or out.get("emission_factor_source")
    out["matched"] = bool(out.get("matched"))
    out["review_required"] = bool(out.get("review_required"))
    out["excluded"] = bool(out.get("excluded"))
    out["short_text"] = out.get("short_text") or out.get("material")
    out["normalized_material"] = out.get("normalized_material") or out.get("material")
    out["calculation_date"] = out.get("calculation_date") or datetime.now(timezone.utc).isoformat()
    return out


# ==========================================================
# HELPERS
# ==========================================================
HEBREW_QUOTES = str.maketrans({
    "׳": "'",
    "״": '"',
})

PVC_DEFAULTS = {
    4.0: 1.95,
    6.0: 4.19,
    8.0: 8.19,
}


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    text = str(value)
    text = text.replace("\xa0", " ").replace("\u200f", " ").replace("\u200e", " ")
    text = text.strip().translate(HEBREW_QUOTES)
    text = re.sub(r"\s+", " ", text)
    if text.lower() in {"nan", "none", "null", "nat"}:
        return ""
    return text


def normalize_for_compare(value: Any) -> str:
    text = normalize_text(value).lower()
    text = text.replace('"', "").replace("'", "")
    text = re.sub(r"[\-_/]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def choose_existing_column(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    normalized = {normalize_for_compare(col): col for col in df.columns}
    for candidate in candidates:
        if candidate in df.columns:
            return candidate
        norm = normalize_for_compare(candidate)
        if norm in normalized:
            return normalized[norm]
    return None


def detect_input_layout(df: pd.DataFrame, requested_source_mode: Optional[str] = None) -> str:
    requested = normalize_for_compare(requested_source_mode)
    annual_aliases = {normalize_for_compare(x) for x in
                      [SOURCE_MODE_ANNUAL, 'annual', 'yearly', 'paid_2025', 'כתב שנתי']}
    boq_aliases = {normalize_for_compare(x) for x in [SOURCE_MODE_BOQ, 'כתב כמויות']}
    if requested in annual_aliases:
        return SOURCE_MODE_ANNUAL
    if requested in boq_aliases:
        return SOURCE_MODE_BOQ

    annual_hits = 0
    for candidates in ANNUAL_2025_LAYOUT_COLUMNS.values():
        if choose_existing_column(df, candidates):
            annual_hits += 1
    return SOURCE_MODE_ANNUAL if annual_hits >= 3 else SOURCE_MODE_BOQ


def build_work_dataframe(df: pd.DataFrame, requested_source_mode: Optional[str] = None) -> Tuple[pd.DataFrame, str]:
    df = df.copy()
    df.columns = [str(c).replace("\n", " ").replace("\r", " ").strip() for c in df.columns]
    source_mode = detect_input_layout(df, requested_source_mode)

    if source_mode == SOURCE_MODE_ANNUAL:
        material_col = choose_existing_column(df, ANNUAL_2025_LAYOUT_COLUMNS["material"])
        quantity_col = choose_existing_column(df, ANNUAL_2025_LAYOUT_COLUMNS["quantity"])
        unit_col = choose_existing_column(df, ANNUAL_2025_LAYOUT_COLUMNS["unit"])
        boq_code_col = choose_existing_column(df, ANNUAL_2025_LAYOUT_COLUMNS["boq_code"])
    else:
        material_col = choose_existing_column(df, POSSIBLE_MATERIAL_COLUMNS)
        quantity_col = choose_existing_column(df, POSSIBLE_QUANTITY_COLUMNS)
        unit_col = choose_existing_column(df, POSSIBLE_UNIT_COLUMNS)
        boq_code_col = choose_existing_column(df, POSSIBLE_BOQ_CODE_COLUMNS)

    if not material_col or not quantity_col:
        raise ValueError("Missing required columns: material/description and quantity")

    cols = [material_col, quantity_col]
    if unit_col:
        cols.append(unit_col)
    if boq_code_col and boq_code_col not in cols:
        cols.append(boq_code_col)

    work_df = df[cols].copy()
    work_df = work_df.rename(columns={material_col: "material", quantity_col: "quantity"})
    work_df["unit"] = work_df[unit_col] if unit_col else None
    work_df["boq_code"] = work_df[boq_code_col] if boq_code_col else None
    work_df["source_mode"] = source_mode
    return work_df, source_mode


def safe_float(value: Any) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        f = float(value)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except Exception:
        return None


def extract_thickness_cm(text: str) -> Optional[float]:
    for pattern in THICKNESS_CM_PATTERNS:
        m = re.search(pattern, text, flags=re.IGNORECASE)
        if m:
            try:
                return float(m.group(1))
            except Exception:
                return None
    return None


def extract_mm2(text: str) -> Optional[float]:
    m = re.search(r"(\d+(?:\.\d+)?)\s*[xX×*]\s*(\d+(?:\.\d+)?)\s*(?:ממ.?ר|mm2|mm\^2)?", text, flags=re.IGNORECASE)
    if m:
        return float(m.group(1)) * float(m.group(2))

    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:ממ.?ר|mm2|mm\^2)", text, flags=re.IGNORECASE)
    if m:
        return float(m.group(1))

    return None


def extract_cores_and_mm2(text: str) -> Tuple[Optional[int], Optional[float]]:
    m = re.search(r"(\d+)\s*[xX×*]\s*(\d+(?:\.\d+)?)\s*(?:ממ.?ר|mm2|mm\^2)?", text, flags=re.IGNORECASE)
    if m:
        return int(m.group(1)), float(m.group(2))
    mm2 = extract_mm2(text)
    return None, mm2


def extract_inch_diameter(text: str) -> Optional[float]:
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:\"|אינץ|inch)", text, flags=re.IGNORECASE)
    if m:
        return float(m.group(1))
    return None


def extract_diameter_mm(text: str) -> Optional[int]:
    # Prefer explicit mm values.
    m = re.search(r"(?:קוטר\s*)?(\d{2,4})\s*מ(?:מ|""|מ)", text, flags=re.IGNORECASE)
    if m:
        return int(float(m.group(1)))

    # Convert cm to mm.
    m = re.search(r"(?:קוטר\s*)?(\d{2,3})\s*ס[\"'׳]?מ", text, flags=re.IGNORECASE)
    if m:
        return int(float(m.group(1)) * 10)

    inch = extract_inch_diameter(text)
    if inch is not None:
        return int(round(inch * 25.4))
    return None


def extract_pipe_class(text: str) -> Optional[str]:
    patterns = [
        r"דרג\s*(\d+)",
        r"class\s*(\d+)",
        r"מחלקה\s*(\d+)",
    ]
    for pattern in patterns:
        m = re.search(pattern, text, flags=re.IGNORECASE)
        if m:
            return f"דרג {m.group(1)}"
    return None


def parse_boq_prefixes(boq_code: Optional[str]) -> List[str]:
    code = normalize_text(boq_code)
    if not code:
        return []
    parts = [p for p in re.split(r"[^0-9A-Za-z]+", code) if p]
    prefixes: List[str] = []
    if not parts:
        return [code]
    for i in range(len(parts), 0, -1):
        prefixes.append(".".join(parts[:i]))
    prefixes.append(parts[0])
    seen = []
    for item in prefixes:
        if item and item not in seen:
            seen.append(item)
    return seen


def should_exclude(text: str) -> Tuple[bool, Optional[str], Optional[str]]:
    text = normalize_text(text)
    if not text:
        return True, "empty_material_text", None

    for pattern in FINANCIAL_ADJUSTMENT_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return True, "financial_adjustment_non_material", pattern

    has_material_indicator = any(
        re.search(pattern, text, flags=re.IGNORECASE)
        for pattern in MATERIAL_INDICATOR_PATTERNS
    )

    # Critical rule: if the text clearly contains a material indicator, do not
    # auto-exclude it just because it also mentions execution verbs like
    # excavation / drilling / removal / installation. Those rows should keep
    # flowing to catalog + conversion logic.
    if has_material_indicator:
        return False, None, None

    for pattern in _EXCLUDE_PATTERNS_COMPILED:
        if pattern.search(text):
            return True, "exclude_pattern_non_material", pattern

    return False, None, None


def normalize_uom(raw_unit: Optional[str]) -> Optional[str]:
    if raw_unit is None:
        return None

    text = normalize_for_compare(raw_unit)
    mapping = {
        "kg": "kg", "קג": "kg",
        "ton": "ton", "tons": "ton", "t": "ton", "to": "ton", "טון": "ton",
        "m3": "m3", "מק": "m3", "מ3": "m3", 'מ"ק': "m3", "cum": "m3",
        "m2": "m2", "מר": "m2", "מ2": "m2", 'מ"ר': "m2", "sqm": "m2",
        "m": "m", "מ": "m", "lm": "m", "מטר": "m", 'מ"א': "m",
        "km": "km",
        "unit": "unit", "ea": "unit", "יחידה": "unit", "יח": "unit", 'יח׳': "unit", 'יח"': "unit",
        "tag": "unit", "std": "unit", "p": "unit", "dun": "unit",
        "cmp": "unit", "mic": "unit", "mon": "unit", "h": "hour", "hr": "hour",
        "-": None,
        "m2_cm_or_ton": "m2_cm_or_ton",
        "ton_or_kg": "ton_or_kg",
        "m_with_mm2": "m_with_mm2",
        "m_with_sdr_or_m2_mm": "m_with_sdr_or_m2_mm",
        "m_by_nominal_inch": "m_by_nominal_inch",
        "m_or_unit": "m_or_unit",
    }
    return mapping.get(text)


def sanitize_for_json(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass
    if isinstance(value, dict):
        return {str(k): sanitize_for_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [sanitize_for_json(v) for v in value]
    try:
        import numpy as np  # type: ignore
        if isinstance(value, (np.integer, np.floating, np.bool_)):
            return sanitize_for_json(value.item())
    except Exception:
        pass
    return str(value)


# ==========================================================
# BIGQUERY LOOKUPS
# ==========================================================
def ensure_dataset_exists() -> None:
    dataset_ref = bigquery.Dataset(f"{BQ_PROJECT_ID}.{DATASET_ID}")
    dataset_ref.location = DATASET_LOCATION
    try:
        bq_client.get_dataset(dataset_ref)
    except NotFound:
        bq_client.create_dataset(dataset_ref)
        logger.info("Created dataset %s.%s", BQ_PROJECT_ID, DATASET_ID)


def get_table_columns(table_id: str) -> set:
    table = bq_client.get_table(table_id)
    return {field.name for field in table.schema}


def query_to_dicts(query: str) -> List[Dict[str, Any]]:
    try:
        return [dict(row.items()) for row in bq_client.query(query).result()]
    except Exception as exc:
        logger.warning("Failed query_to_dicts for query=%s error=%s", query, exc)
        return []


@lru_cache(maxsize=1)
def load_catalog_mapping_rows() -> List[Dict[str, Any]]:
    rows = query_to_dicts(
        f"SELECT * FROM `{BQ_MAPPING_TABLE}` WHERE is_active = TRUE ORDER BY confidence DESC, created_at DESC"
    )
    for row in rows:
        row["_exact_norm"] = normalize_for_compare(row.get("exact_material")) if row.get("exact_material") else ""
        row["_boq_norm"] = normalize_for_compare(row.get("boq_code")) if row.get("boq_code") else ""
        row["_boq_prefix_norm"] = normalize_for_compare(row.get("boq_code_prefix")) if row.get("boq_code_prefix") else ""
    logger.info("Loaded %s active catalog mappings", len(rows))
    return rows


@lru_cache(maxsize=1)
def load_boq_code_mapping_rows() -> List[Dict[str, Any]]:
    rows = query_to_dicts(
        f"SELECT * FROM `{BQ_BOQ_MAPPING_TABLE}` WHERE is_active = TRUE ORDER BY updated_at DESC"
    )
    for row in rows:
        row["_boq_code_norm"] = normalize_for_compare(row.get("boq_code")) if row.get("boq_code") else ""
        row["_boq_prefix_norm"] = normalize_for_compare(row.get("boq_code_prefix")) if row.get(
            "boq_code_prefix") else ""
    logger.info("Loaded %s active BOQ mappings", len(rows))
    return rows


@lru_cache(maxsize=1)
def load_unit_conversion_rules() -> List[Dict[str, Any]]:
    rows = query_to_dicts(
        f"SELECT * FROM `{BQ_UNIT_RULES_TABLE}` WHERE is_active = TRUE ORDER BY updated_at DESC"
    )
    for row in rows:
        row["_category_norm"] = normalize_for_compare(row.get("category")) if row.get("category") else ""
        row["_input_norm"] = normalize_uom(row.get("input_uom")) if row.get("input_uom") else None
    logger.info("Loaded %s active unit conversion rules", len(rows))
    return rows


@lru_cache(maxsize=1)
def load_annual_paid_items_reference_rows() -> List[Dict[str, Any]]:
    query = f"""
    SELECT
      item_code,
      item_description,
      contract_uom,
      rows_count AS seen_count,
      last_seen_at
    FROM `{BQ_ANNUAL_PAID_ITEMS_2025_REFERENCE_VIEW}`
    """
    rows = query_to_dicts(query)
    if not rows:
        fallback_query = f"""
        SELECT
          item_code,
          item_description,
          contract_uom,
          COUNT(*) AS seen_count,
          MAX(ingested_at) AS last_seen_at
        FROM `{BQ_ANNUAL_PAID_ITEMS_2025_RAW_TABLE}`
        WHERE measurement_year = 2025
          AND source_mode = 'annual_paid_2025'
          AND COALESCE(TRIM(CAST(notes AS STRING)), '') != 'financial_adjustment_non_material'
          AND COALESCE(TRIM(CAST(item_description AS STRING)), '') != ''
          AND COALESCE(TRIM(CAST(contract_uom AS STRING)), '') NOT IN ('', '-')
          AND COALESCE(TRIM(CAST(item_code AS STRING)), '') != ''
        GROUP BY 1,2,3
        """
        rows = query_to_dicts(fallback_query)

    filtered_rows: List[Dict[str, Any]] = []
    for row in rows:
        desc = normalize_text(row.get("item_description"))
        boq = normalize_text(row.get("item_code"))
        uom = normalize_text(row.get("contract_uom"))
        excluded, _, _ = should_exclude(desc)
        if excluded:
            continue
        if not desc or not boq or not uom or uom == "-":
            continue
        row["_desc_norm"] = normalize_for_compare(desc)
        row["_boq_norm"] = normalize_for_compare(boq)
        row["_uom_norm"] = normalize_uom(uom)
        filtered_rows.append(row)
    logger.info("Loaded %s annual paid-items 2025 reference rows", len(filtered_rows))
    return filtered_rows


def match_annual_paid_item_reference(material_text: str, boq_code: Optional[str], provided_uom: Optional[str]) -> \
Optional[Dict[str, Any]]:
    rows = load_annual_paid_items_reference_rows()
    if not rows:
        return None

    material_norm = normalize_for_compare(material_text)
    boq_norm = normalize_for_compare(boq_code)
    provided_uom_norm = normalize_uom(provided_uom) if provided_uom else None

    exact_candidates: List[Dict[str, Any]] = []
    boq_candidates: List[Dict[str, Any]] = []
    desc_candidates: List[Dict[str, Any]] = []

    for row in rows:
        row_boq = row.get("_boq_norm") or ""
        row_desc = row.get("_desc_norm") or ""
        if boq_norm and row_boq == boq_norm:
            if material_norm and row_desc == material_norm:
                exact_candidates.append(row)
            boq_candidates.append(row)
        if material_norm and row_desc == material_norm:
            desc_candidates.append(row)

    def _pick_best(candidates: List[Dict[str, Any]], match_type: str) -> Optional[Dict[str, Any]]:
        if not candidates:
            return None
        preferred = candidates
        if provided_uom_norm:
            same_uom = [r for r in candidates if r.get("_uom_norm") == provided_uom_norm]
            if same_uom:
                preferred = same_uom
        preferred = sorted(
            preferred,
            key=lambda r: (
                0 if (provided_uom_norm and r.get("_uom_norm") == provided_uom_norm) else 1,
                -(int(r.get("seen_count") or 0)),
                str(r.get("last_seen_at") or ""),
            ),
        )
        chosen = dict(preferred[0])
        chosen["_match_type"] = match_type
        return chosen

    return (
            _pick_best(exact_candidates, "annual_2025_reference_exact")
            or _pick_best(boq_candidates, "annual_2025_reference_boq")
            or _pick_best(desc_candidates, "annual_2025_reference_description")
    )


@lru_cache(maxsize=1)
def load_materials_catalog() -> Dict[Tuple[str, int], float]:
    catalog: Dict[Tuple[str, int], float] = {}
    rows = query_to_dicts(f"SELECT * FROM `{BQ_CATALOG_TABLE}`")
    for row in rows:
        weight = safe_float(row.get("weight_kg"))
        if weight is None:
            continue
        element_type = row.get("element_type") or row.get("material_type") or row.get("sub_type")
        dim = row.get("dimension_cm")
        if dim is None:
            dim_label = normalize_text(row.get("dimension_label"))
            m = re.search(r"(\d+)", dim_label)
            dim = int(m.group(1)) if m else None
        et = normalize_text(element_type)
        if et and dim is not None:
            try:
                catalog[(et, int(dim))] = weight
            except Exception:
                continue
    logger.info("Loaded %s materials catalog items", len(catalog))
    return catalog


@lru_cache(maxsize=1)
def load_concrete_pipe_catalog() -> List[Dict[str, Any]]:
    rows = query_to_dicts(
        f"SELECT * FROM `{BQ_CONCRETE_PIPE_TABLE}` WHERE is_active = TRUE ORDER BY diameter_mm, class_label"
    )
    logger.info("Loaded %s concrete pipe catalog rows", len(rows))
    return rows


@lru_cache(maxsize=1)
def load_cable_cross_section_catalog() -> List[Dict[str, Any]]:
    rows = query_to_dicts(
        f"SELECT * FROM `{BQ_CABLE_TABLE}` WHERE is_active = TRUE ORDER BY conductor_material, cores_count, cross_section_mm2"
    )
    logger.info("Loaded %s cable catalog rows", len(rows))
    return rows


def fetch_regulator_catalog() -> Dict[str, Dict[str, Any]]:
    query = f"SELECT material_name, emission_factor, preferred_source FROM `{PROJECT_ID}.{DATASET_ID}.regulator_settings`"
    try:
        results = bq_client.query(query).to_dataframe()
        if results.empty:
            return {}
        results["material_name_norm"] = results["material_name"].map(normalize_for_compare)
        return results.set_index("material_name_norm")[["emission_factor", "preferred_source"]].to_dict("index")
    except Exception as exc:
        logger.error("Error fetching regulator catalog: %s", exc)
        return {}


# ==========================================================
# GCS INPUT
# ==========================================================
import io
import math
import pandas as pd
from google.cloud import bigquery


# ==========================================================
# BIGQUERY RUN UPDATE
# ==========================================================
def update_processing_run(
        run_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        rows_processed: Optional[int] = None,
        rows_total: Optional[int] = None,
        progress_pct: Optional[float] = None,
        current_stage: Optional[str] = None,
        status: Optional[str] = None,
        error_message: Optional[str] = None,
        finished: Optional[bool] = False,
        finished_at: Optional[datetime] = None,
        extra_fields: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
) -> None:
    """Safe MERGE-based upsert for processing_runs with legacy kwarg support."""
    if not run_id:
        return

    metadata = dict(metadata or {})
    extra_fields = dict(extra_fields or {})

    for key, value in list(kwargs.items()):
        mapped_key = "source_file" if key == "filename" else key
        if mapped_key in {"source_file", "source_bucket", "uploader_email", "project_type", "project_name"}:
            if value is not None:
                metadata[mapped_key] = value
        else:
            extra_fields[mapped_key] = value

    source_file = metadata.get("source_file")
    source_bucket = metadata.get("source_bucket")
    uploader_email = metadata.get("uploader_email")
    project_type = metadata.get("project_type")
    project_name = metadata.get("project_name")

    rows_processed = int(rows_processed or 0)
    rows_total = int(rows_total or 0)
    progress_pct = float(progress_pct if progress_pct is not None else (round((rows_processed / rows_total) * 100, 2) if rows_total else 0.0))
    current_stage = current_stage or "Running"
    status = status or "running"
    finished = bool(finished)
    safe_error_message = str(error_message)[:9000] if error_message else None

    set_assignments = [
        "source_file = S.source_file",
        "source_bucket = S.source_bucket",
        "uploader_email = S.uploader_email",
        "project_type = S.project_type",
        "project_name = S.project_name",
        "status = S.status",
        "rows_total = S.rows_total",
        "rows_processed = S.rows_processed",
        "progress_pct = S.progress_pct",
        "current_stage = S.current_stage",
        "error_message = S.error_message",
        "updated_at = S.now_ts",
        "finished_at = COALESCE(S.finished_at, IF(S.finished, S.now_ts, T.finished_at))",
    ]
    insert_columns = [
        "run_id", "created_at", "updated_at", "finished_at",
        "source_file", "source_bucket", "uploader_email", "project_type", "project_name",
        "status", "rows_total", "rows_processed", "progress_pct", "current_stage", "error_message",
    ]
    insert_values = [
        "S.run_id", "S.now_ts", "S.now_ts", "COALESCE(S.finished_at, IF(S.finished, S.now_ts, NULL))",
        "S.source_file", "S.source_bucket", "S.uploader_email", "S.project_type", "S.project_name",
        "S.status", "S.rows_total", "S.rows_processed", "S.progress_pct", "S.current_stage", "S.error_message",
    ]

    query_parameters = [
        bigquery.ScalarQueryParameter("run_id", "STRING", run_id),
        bigquery.ScalarQueryParameter("source_file", "STRING", source_file),
        bigquery.ScalarQueryParameter("source_bucket", "STRING", source_bucket),
        bigquery.ScalarQueryParameter("uploader_email", "STRING", uploader_email),
        bigquery.ScalarQueryParameter("project_type", "STRING", project_type),
        bigquery.ScalarQueryParameter("project_name", "STRING", project_name),
        bigquery.ScalarQueryParameter("status", "STRING", status),
        bigquery.ScalarQueryParameter("rows_total", "INT64", rows_total),
        bigquery.ScalarQueryParameter("rows_processed", "INT64", rows_processed),
        bigquery.ScalarQueryParameter("progress_pct", "FLOAT64", progress_pct),
        bigquery.ScalarQueryParameter("current_stage", "STRING", current_stage),
        bigquery.ScalarQueryParameter("error_message", "STRING", safe_error_message),
        bigquery.ScalarQueryParameter("finished", "BOOL", finished),
        bigquery.ScalarQueryParameter("finished_at", "TIMESTAMP", finished_at),
    ]

    schema_columns = None
    try:
        schema_columns = get_table_columns(BQ_PROCESSING_RUNS_TABLE)
    except Exception:
        logger.exception("Could not read processing_runs schema")

    for key, value in extra_fields.items():
        if not schema_columns or key in schema_columns:
            alias = f"extra_{key}"
            sql_type = "STRING"
            if isinstance(value, bool):
                sql_type = "BOOL"
            elif isinstance(value, int):
                sql_type = "INT64"
            elif isinstance(value, float):
                sql_type = "FLOAT64"
            query_parameters.append(bigquery.ScalarQueryParameter(alias, sql_type, value))
            set_assignments.append(f"{key} = S.{key}")
            insert_columns.append(key)
            insert_values.append(f"S.{key}")

    extra_selects = []
    for key in extra_fields.keys():
        if not schema_columns or key in schema_columns:
            alias = f"extra_{key}"
            extra_selects.append(f"@{alias} AS {key}")

    query = f"""
    MERGE `{BQ_PROCESSING_RUNS_TABLE}` T
    USING (
      SELECT
        @run_id AS run_id,
        @source_file AS source_file,
        @source_bucket AS source_bucket,
        @uploader_email AS uploader_email,
        @project_type AS project_type,
        @project_name AS project_name,
        @status AS status,
        @rows_total AS rows_total,
        @rows_processed AS rows_processed,
        @progress_pct AS progress_pct,
        @current_stage AS current_stage,
        @error_message AS error_message,
        @finished_at AS finished_at,
        CURRENT_TIMESTAMP() AS now_ts,
        @finished AS finished
        {"," if extra_selects else ""} {' , '.join(extra_selects)}
    ) S
    ON T.run_id = S.run_id
    WHEN MATCHED THEN
      UPDATE SET {", ".join(set_assignments)}
    WHEN NOT MATCHED THEN
      INSERT ({", ".join(insert_columns)})
      VALUES ({", ".join(insert_values)})
    """
    job_config = bigquery.QueryJobConfig(query_parameters=query_parameters)

    attempts = 3
    for attempt in range(1, attempts + 1):
        try:
            bq_client.query(query, job_config=job_config).result()
            return
        except Exception as exc:
            if attempt == attempts:
                logger.exception("Failed updating processing run %s", run_id)
                return
            sleep_s = min(2 ** attempt + random.random(), 5)
            logger.warning("Retrying processing_runs merge for %s after error: %s", run_id, exc)
            time.sleep(sleep_s)


# ==========================================================
# GCS INPUT
# ==========================================================
def read_input_from_gcs(bucket_name: str, file_name: str, run_id: str | None = None) -> pd.DataFrame:
    """
    Reads CSV/XLSX from GCS, cleans it, updates processing_runs with stage/progress,
    and returns a cleaned DataFrame.
    """

    try:
        if run_id:
            update_processing_run(
                run_id,
                status="running",
                current_stage="מאתר קובץ ב-GCS",
                progress_pct=1,
                rows_processed=0,
            )

        blob = storage_client.bucket(bucket_name).blob(file_name)
        if not blob.exists():
            raise FileNotFoundError(f"File '{file_name}' not found in bucket '{bucket_name}'")

        if run_id:
            update_processing_run(
                run_id,
                current_stage="מוריד קובץ מ-GCS",
                progress_pct=3,
            )

        data = blob.download_as_bytes()
        lower = file_name.lower()

        if run_id:
            update_processing_run(
                run_id,
                current_stage="קורא קובץ לטבלת נתונים",
                progress_pct=8,
            )

        if lower.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(data))
        elif lower.endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(data), engine="openpyxl", engine_kwargs={"read_only": True, "data_only": True})
        else:
            raise ValueError(f"Unsupported file type: {file_name}")

        # עדכון לפי מספר שורות גולמי לפני ניקוי
        raw_rows = len(df)

        if run_id:
            update_processing_run(
                run_id,
                current_stage="מנקה שמות עמודות וערכים",
                progress_pct=12,
                rows_total=raw_rows,
            )

        # ניקוי שמות עמודות
        df.columns = [str(c).strip() for c in df.columns]

        # ניקוי רווחים מתאים טקסטואליים
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].map(lambda x: x.strip() if isinstance(x, str) else x)

        if run_id:
            update_processing_run(
                run_id,
                current_stage="ממיר ערכים ריקים ומסיר שורות ריקות",
                progress_pct=16,
            )

        # המרת מחרוזות ריקות / רווחים ל-NA
        df = df.replace(r"^\s*$", pd.NA, regex=True)

        # הסרת שורות ריקות לגמרי
        df = df.dropna(how="all").reset_index(drop=True)

        if df.empty:
            raise ValueError("הקובץ ריק לאחר ניקוי שורות ריקות")

        cleaned_rows = len(df)

        if run_id:
            update_processing_run(
                run_id,
                current_stage="הקובץ נקרא בהצלחה",
                progress_pct=20,
                rows_total=cleaned_rows,
                rows_in_file=cleaned_rows,
                rows_processed=0,
                filename=file_name,
                source_file=file_name,
                source_bucket=bucket_name,
            )

        return df

    except Exception as e:
        if run_id:
            update_processing_run(
                run_id,
                status="failed",
                current_stage="כשל בקריאת קובץ",
                error_message=str(e),
                finished=True,
                finished_at=datetime.now(timezone.utc),
            )

        raise


def get_progress_update_interval(total_rows: int) -> int:
    """
    Returns update interval so progress updates roughly every 1%.
    Minimum 1 row.
    """
    if total_rows <= 0:
        return 1
    return max(1, math.ceil(total_rows / 100))



# ==========================================================
# MATCHING
# ==========================================================
def match_by_boq_code(boq_code: Optional[str]) -> Optional[Dict[str, Any]]:
    if not boq_code:
        return None
    prefixes = [normalize_for_compare(x) for x in parse_boq_prefixes(boq_code)]
    if not prefixes:
        return None
    rows = load_boq_code_mapping_rows()

    for code_norm in prefixes:
        for row in rows:
            if row.get("_boq_code_norm") and row["_boq_code_norm"] == code_norm:
                matched = dict(row)
                matched["_match_type"] = "boq_exact"
                return matched
    for code_norm in prefixes:
        for row in rows:
            if row.get("_boq_prefix_norm") and row["_boq_prefix_norm"] == code_norm:
                matched = dict(row)
                matched["_match_type"] = "boq_prefix"
                return matched
    return None


def match_by_catalog(material_text: str, boq_code: Optional[str]) -> Optional[Dict[str, Any]]:
    material_text = normalize_text(material_text)
    if not material_text:
        return None

    material_norm = normalize_for_compare(material_text)
    boq_prefixes = [normalize_for_compare(x) for x in parse_boq_prefixes(boq_code)]
    rows = load_catalog_mapping_rows()

    best_row: Optional[Dict[str, Any]] = None
    best_score = float("-inf")

    for row in rows:
        score = 0.0
        exact_norm = row.get("_exact_norm") or ""
        regex_pattern = row.get("material_regex")
        row_boq_norm = row.get("_boq_norm") or ""
        row_boq_prefix_norm = row.get("_boq_prefix_norm") or ""
        confidence = float(row.get("confidence") or 0.0)
        matched_by = None

        if exact_norm:
            if exact_norm == material_norm:
                score += 120
                matched_by = "catalog_exact_material"
            elif exact_norm in material_norm:
                score += 95
                matched_by = "catalog_exact_material"

        if regex_pattern:
            try:
                if re.search(regex_pattern, material_text, flags=re.IGNORECASE):
                    score += 85
                    matched_by = matched_by or "catalog_regex"
            except re.error:
                logger.warning("Invalid material_regex ignored: %s", regex_pattern)

        if score <= 0:
            continue

        if boq_prefixes:
            if row_boq_norm and row_boq_norm in boq_prefixes:
                score += 35
                matched_by = matched_by or "catalog_exact_boq"
            elif row_boq_prefix_norm and row_boq_prefix_norm in boq_prefixes:
                score += 20
                matched_by = matched_by or "catalog_boq_prefix"
            elif row_boq_norm or row_boq_prefix_norm:
                score -= 8

        score += confidence * 10
        if not row.get("exact_material") and regex_pattern:
            score -= 3

        if score > best_score:
            best_row = dict(row)
            best_score = score
            best_row["_match_type"] = matched_by or "catalog_mapping"
            best_row["_match_score"] = round(score, 2)

    if best_row and best_score >= 60:
        return best_row
    return None


def hard_classification_override(material_text: str) -> Optional[Tuple[str, str]]:
    text = normalize_text(material_text)

    if re.search(r"זכוכית|טריפלקס", text, flags=re.IGNORECASE):
        return "Glass", "Hard override: glass detected"

    if re.search(r"\bעץ\b|אורן|קורות\s*עץ|לביד|סנדוויץ", text, flags=re.IGNORECASE):
        return "Wood", "Hard override: wood detected"

    if re.search(r"מלט|מלת|טיט|מרגמה|רובה|דייס|צמנט", text, flags=re.IGNORECASE):
        return "Cementitious Mortar", "Hard override: cement/mortar detected"

    if re.search(r"אלומיניום|אלומניום|פרופיל\s*אלומ", text, flags=re.IGNORECASE):
        return "Aluminum", "Hard override: aluminum detected"

    # עמוד פלדה/תאורה — מסווג לפעמים כ-Copper Wire בגלל boq prefix 08.04/08.10
    if re.search(r"עמוד\s*(?:פלד|תאורה|מפלד)|עמוד\s*קוני|עמוד\s*בגובה", text, flags=re.IGNORECASE):
        return "Galvanized Steel", "Hard override: steel pole → Galvanized Steel"

    # מוטות מייתדים = dowel bars, אינסרט להארכת זיון = rebar extension insert → Steel Rebar
    if re.search(r"מייתד|מוט\s*מייתד|אינסרט\s*להארכת\s*זיון", text, flags=re.IGNORECASE):
        return "Steel Rebar", "Hard override: dowel bar/rebar insert → Steel Rebar"

    # תוספת מחיר — price supplement, not a physical material
    # Only "תוספת מחיר" — NOT "תוספת עבור" which is a real physical item
    if re.search(r"תוספת\s+מחיר|תוספת\s+למחיר", text, flags=re.IGNORECASE):
        return None, "Hard override: תוספת מחיר → EXCLUDE (price supplement)"

    # דיפון קשיח — חומר גרוס/מחצבה, לא פלדה
    if re.search(r"דיפון\s*קשיח", text, flags=re.IGNORECASE):
        return "Crushed Stone", "Hard override: rigid sheathing → Crushed Stone"

    # CLSM = Controlled Low Strength Material = בטון זורם/רזה
    if re.search(r"\bCLSM\b|בטון\s*זורם|בטון\s*נוזלי|חוזק\s*של\s*\d+-\d+", text, flags=re.IGNORECASE):
        return "Lean Concrete", "Hard override: CLSM → Lean Concrete"

    # הידוק מבוקר / גריסה וניפוי = פעולות עיבוד קרקע, לא חומרים
    if re.search(r"הידוק\s*(?:מבוקר|קרקע|יסוד)|גריסה\s*וניפוי|ניפוי\s*וגריסה", text, flags=re.IGNORECASE):
        return None, "Hard override: compaction/screening operation → EXCLUDE"

    # זריעה / זיבול / גינון = שירותי נוף
    if re.search(r"\bזריע[הת]?\b|\bזיבול\b|הכשרת\s*קרקע\s*לגינון|איסוף\s*פקעות", text, flags=re.IGNORECASE):
        return None, "Hard override: landscaping service → EXCLUDE"

    # פוליסטירן מוקצף / EPS / XPS — חומר בידוד, לא בטון
    if re.search(r"פוליסטר[ין]|פוליסטי|\bEPS\b|\bXPS\b|סנדוויץ.*בידוד|בידוד.*תרמי", text, flags=re.IGNORECASE):
        return None, "Hard override: polystyrene insulation → EXCLUDE"

    # יריעת ניקוז גיאוטכנית
    if re.search(r"יריע[ות]+\s*ניקוז|גיאוקומפוזיט|geo.?composite", text, flags=re.IGNORECASE):
        return "Waterproofing", "Hard override: drainage membrane → Waterproofing"

    # אבנות/סלעים בגדלים שונים — Crushed Stone, לא פלדה
    if re.search(r"אבנ[יות]+\s*בגודל|תערובת\s*אבנ|בולדר|סלעי[ם]?\s*\d|אבן\s*(?:טבע|מקומ)", text, flags=re.IGNORECASE):
        return "Crushed Stone", "Hard override: rocks/boulders → Crushed Stone"

    # מילוי מובא / חומר מילוי — Fill Material, לא Crushed Stone
    # Fill material uses transport+compaction factor, not quarry production
    if re.search(r"מילוי\s*מובא|חומר\s*(?:א|ב|ג|מילוי)\s*(?:מובא|סוג)|מילוי\s*חוזר|מילוי\s*להחלפת", text, flags=re.IGNORECASE):
        return "Fill Material", "Hard override: imported fill → Fill Material"

    # חצץ שטוף / חצץ מדורג → Crushed Stone (לא פלדה מגולוונת!)
    if re.search(r"חצץ\s*(?:שטוף|מדורג|מסונן|ל?הידוק|בכל\s*הגדלים)", text, flags=re.IGNORECASE):
        return "Crushed Stone", "Hard override: gravel → Crushed Stone"

    # גוף תאורה / גוף LED → EXCLUDE (ציוד חשמלי)
    if re.search(r"גוף\s*(?:תאורה|LED|לד)|פנס\s*(?:LED|לד|מהבהב)|מנורה\s*(?:LED|לד)", text, flags=re.IGNORECASE):
        return None, "Hard override: LED lighting → EXCLUDE"

    # פינוי פסולת → EXCLUDE (שירות הסרה, לא חומר)
    if re.search(r"פינוי\s*(?:פסולת|חומר\s*קיים|שפכים)|פינוי\s*הקיים\s*באתר", text, flags=re.IGNORECASE):
        return None, "Hard override: waste removal → EXCLUDE"

    # נקז בקירות / נקז אורכי → PVC Pipe
    if re.search(r"נקז[ים]*\s*(?:בקירות|אורכי)\s*(?:בקוטר|כולל|שרשורי)", text, flags=re.IGNORECASE):
        return "PVC Pipe", "Hard override: wall drain → PVC Pipe"

    # מוליך הארקה מנחושת → Copper Wire
    if re.search(r"מוליך\s*הארקה.*נחושת|הארקה.*נחושת.*שזור", text, flags=re.IGNORECASE):
        return "Copper Wire (Cable)", "Hard override: copper grounding conductor → Copper Wire"

    # ריצוף/אריחים/גרניט פורצלן/קרמיקה → Paving
    if re.search(r"גרניט\s*פורצלן|פורצלן|קרמיק|קרמיקה|אריחים?\s*עמידי?\s*חומצות|אריחי?\s*גרניט|ריצוף\s*באריח", text, flags=re.IGNORECASE):
        return "Paving", "Hard override: tile/porcelain flooring → Paving"

    # מתזים/השקיה/מגופים לגינון/שיקום השקיה = ציוד או מערכת שירות, לא חומר קטלוגי
    if re.search(r"מתז|שיקום\s*מערכות\s*השקיה|מגוף\s*ברונזה\s*לגינון|מערכות\s*השקיה", text, flags=re.IGNORECASE):
        return None, "Hard override: irrigation equipment/service → EXCLUDE"

    # צינור שרשורי מחורר / צינור ניקוז פלסטי → PVC Pipe
    if re.search(r"צינור\s*שרשורי\s*מחורר|שרשורי\s*מחורר|צינור\s*ניקוז", text, flags=re.IGNORECASE):
        return "PVC Pipe", "Hard override: corrugated/perforated drainage pipe → PVC Pipe"

    # צמנטבורד / cement board → Cementitious Mortar
    if re.search(r"צמנט\s*בורד|צמנטבורד|cement\s*board|fiber\s*cement", text, flags=re.IGNORECASE):
        return "Cementitious Mortar", "Hard override: cement board → Cementitious Mortar"

    # אטמי מים PVC נשארים ב-PVC; עצרי מים/איטום מעברים → Waterproofing
    if re.search(r"אטמי?\s*מים\s*מ.?\s*P\.?V\.?C|waterstop\s*pvc", text, flags=re.IGNORECASE):
        return "PVC Pipe", "Hard override: PVC waterstop → PVC Pipe"
    if re.search(r"עצר\s*מים|איטום\s*מעברי?\s*צינור|איטום\s*מעברים|פקק\s*מתועש|אלסטוסיל", text, flags=re.IGNORECASE):
        return "Waterproofing", "Hard override: waterstop/sealant/penetration sealing → Waterproofing"

    # בד גיאוטכני / יריעות HDPE להגנה/הפרדה → Waterproofing
    if re.search(r"בד\s*גיאוטכני|גיאוטכני|יריעת\s*HDPE|שטיח\s*גומי\s*מבודד", text, flags=re.IGNORECASE):
        return "Waterproofing", "Hard override: geotextile / protection sheet → Waterproofing"

    # סלעים/בולדרים מקומיים או טבעיים = חומר קיים באתר, לא חומר נרכש
    if re.search(r"בולדרים?\s*מאבנים\s*מקומיות|בולדרים?\s*טבעיים|אבן\s*טבעית\s*מקומית|סלעים?\s*מקומיים", text, flags=re.IGNORECASE):
        return None, "Hard override: local/natural boulders are existing site material → EXCLUDE"

    # אבן דרך = ריהוט/סימון, לא חומר מסיבי
    if re.search(r"אבן\s*דרך", text, flags=re.IGNORECASE):
        return None, "Hard override: milestone/marker stone → EXCLUDE"

    # כלים סניטריים / ציוד אינסטלציה מוגמר → EXCLUDE
    if re.search(r"אסלה|כיור|משתנ(?:ה|ות)|עביט|סוללה\s*לכיור|קערות?\s*מטבח|מזרם", text, flags=re.IGNORECASE):
        return None, "Hard override: sanitary fixture/equipment → EXCLUDE"

    # ציוד חשמלי מובהק → EXCLUDE
    if re.search(r"מנתק\s*הספק|מפסק\s*חשמל|מרכזיית\s*הדלקה|לוח\s*מונים", text, flags=re.IGNORECASE):
        return None, "Hard override: electrical equipment → EXCLUDE"

    # פסי רכבת / מסילה / ריתוך מסילה → Steel Rebar (פלדה)
    if re.search(r"פסי?\s*רכבת|מסילה\s*בודדת|ריתוך\s*(?:אלומינו-תרמי|חשמלי).*מסילה", text, flags=re.IGNORECASE):
        return "Steel Rebar", "Hard override: rail steel → Steel Rebar"

    # כותרת לעמודים / ניצבים מבטון → Structural Concrete
    if re.search(r"כותרת\s*לעמודים|ניצבים\s*מבטון", text, flags=re.IGNORECASE):
        return "Structural Concrete", "Hard override: column cap/pedestal concrete → Structural Concrete"

    # שלט/תמרור/חיבור שלט לעמוד = פלדה מגולוונת
    if re.search(r"שלט|תמרור", text, flags=re.IGNORECASE):
        return "Galvanized Steel", "Hard override: sign/sign support → Galvanized Steel"

    return None


def contains_suspect_non_material_text(material_text: str) -> bool:
    text = normalize_text(material_text)
    return any(re.search(p, text, flags=re.IGNORECASE) for p in SUSPECT_NON_MATERIAL_PATTERNS)


def _vertex_json_call(prompt: str, system_instruction: str, schema: Dict[str, Any]) -> Dict[str, Any]:
    response = genai_client.models.generate_content(
        model=VERTEX_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.1,
            response_mime_type="application/json",
            response_schema=schema,
        ),
    )
    raw = response.text or "{}"
    return json.loads(raw)


def _safe_vertex_json_call(prompt: str, system_instruction: str, schema: Dict[str, Any], material_text: str) -> Dict[str, Any]:
    attempts = 3
    last_exc = None
    for attempt in range(1, attempts + 1):
        try:
            logger.info("Vertex call attempt=%s material=%s", attempt, material_text[:120])
            return _vertex_json_call(prompt, system_instruction, schema)
        except Exception as exc:
            last_exc = exc
            logger.warning("Vertex call failed attempt=%s material=%s error=%s", attempt, material_text[:120], exc)
            time.sleep(min(2 ** attempt + random.random(), 6))
    raise last_exc


def classify_with_vertex_dual(material_text: str) -> Dict[str, Any]:
    engineer_1_instruction = VERTEX_SYSTEM_INSTRUCTION + "\nYou are Civil Engineer A. Focus on identifying the dominant material category, unit, and whether this is a true material line."
    engineer_2_instruction = VERTEX_SYSTEM_INSTRUCTION + "\nYou are Civil Engineer B. Be skeptical. Reject service / surcharge / labor / demolition lines aggressively."

    e1 = _safe_vertex_json_call(
        f"Classify this BOQ line: {material_text}",
        engineer_1_instruction,
        VERTEX_CLASSIFICATION_SCHEMA,
        material_text,
    )
    e2 = _safe_vertex_json_call(
        f"Review this BOQ line independently: {material_text}",
        engineer_2_instruction,
        VERTEX_CLASSIFICATION_SCHEMA,
        material_text,
    )

    c1 = e1.get("category", "Unknown")
    c2 = e2.get("category", "Unknown")
    conf1 = float(e1.get("confidence", 0) or 0)
    conf2 = float(e2.get("confidence", 0) or 0)
    agree = c1 == c2 and c1 in ALLOWED_CATEGORIES

    if agree:
        category = c1
        confidence = round((conf1 + conf2) / 2.0, 4)
        inferred_uom = e1.get("inferred_uom") if e1.get("inferred_uom") == e2.get("inferred_uom") else (
                    e1.get("inferred_uom") or e2.get("inferred_uom") or "unknown")
        excluded = bool(e1.get("excluded") or e2.get("excluded") or category == "EXCLUDE")
        review_required = bool(e1.get("review_required") or e2.get("review_required") or confidence < 0.8)
        reason = f"Dual Vertex agreement on {category}"
    else:
        category = "Unknown"
        confidence = round(min(conf1, conf2), 4)
        inferred_uom = e1.get("inferred_uom") or e2.get("inferred_uom") or "unknown"
        excluded = False
        review_required = True
        reason = f"Dual Vertex disagreement: A={c1}, B={c2}"

    return {
        "category": category,
        "confidence": confidence,
        "review_required": review_required,
        "inferred_uom": inferred_uom,
        "reason": reason,
        "excluded": excluded,
        "extracted_element_type": e1.get("extracted_element_type") or e2.get("extracted_element_type"),
        "extracted_dimension_cm": e1.get("extracted_dimension_cm") or e2.get("extracted_dimension_cm"),
        "engineer_1": e1,
        "engineer_2": e2,
        "agree": agree,
    }


def classify_with_vertex_resilient(material_text: str) -> Dict[str, Any]:
    """
    Prefer dual review for higher quality, but fall back to single-call model and finally to Unknown.
    """
    try:
        return classify_with_vertex_dual(material_text)
    except Exception as exc:
        logger.exception("Dual Vertex classification failed for material=%s", material_text[:120])
        try:
            single = classify_with_vertex(material_text)
            single.setdefault("reason", f"Single Vertex fallback after dual failure: {exc}")
            single.setdefault("review_required", True)
            return single
        except Exception as exc2:
            logger.exception("Single Vertex fallback failed for material=%s", material_text[:120])
            return {
                "category": "Unknown",
                "confidence": 0.0,
                "review_required": True,
                "inferred_uom": "unknown",
                "reason": f"Vertex failure: {exc2}",
                "excluded": False,
                "extracted_element_type": None,
                "extracted_dimension_cm": None,
                "engineer_1": None,
                "engineer_2": None,
                "agree": False,
            }


def classify_with_vertex(material_text: str) -> Dict[str, Any]:
    prompt = f"""
Classify this Hebrew civil infrastructure BOQ line and infer likely unit.

Text:
{material_text}
"""
    response = genai_client.models.generate_content(
        model=VERTEX_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=VERTEX_SYSTEM_INSTRUCTION,
            temperature=0.1,
            response_mime_type="application/json",
            response_schema=VERTEX_CLASSIFICATION_SCHEMA,
        ),
    )
    raw = response.text or "{}"
    data = json.loads(raw)
    category = data.get("category", "Unknown")
    if category not in ALLOWED_CATEGORIES:
        data["category"] = "Unknown"
        data["review_required"] = True
        data["reason"] = f"Unsupported category returned by model: {category}"
    return data


def merge_mapping_sources(material_text: str, boq_code: Optional[str]) -> Dict[str, Optional[Dict[str, Any]]]:
    catalog_mapping = match_by_catalog(material_text, boq_code)
    boq_mapping = match_by_boq_code(boq_code)
    return {"catalog": catalog_mapping, "boq": boq_mapping}


def choose_category_from_sources(sources: Dict[str, Optional[Dict[str, Any]]]) -> Tuple[Optional[str], Optional[str], Optional[Dict[str, Any]]]:
    catalog_mapping = sources.get("catalog")
    boq_mapping = sources.get("boq")

    catalog_category = catalog_mapping.get("category") if catalog_mapping else None
    boq_category = boq_mapping.get("category") if boq_mapping else None

    if catalog_category == "EXCLUDE" or boq_category == "EXCLUDE":
        chosen = catalog_mapping if catalog_category == "EXCLUDE" else boq_mapping
        return "EXCLUDE", "merged_mapping", chosen

    if catalog_category and boq_category and catalog_category == boq_category:
        return catalog_category, "merged_mapping", catalog_mapping or boq_mapping
    if catalog_category:
        return catalog_category, "catalog_mapping", catalog_mapping
    if boq_category:
        return boq_category, "boq_code_mapping", boq_mapping
    return None, None, None


# BOQ chapter prefixes that are always admin/service — never physical materials
BOQ_PREFIX_EXCLUDE = {
    "60",   # admin, misc, bonuses, cameras, traffic management
    "69",   # misc/general items
}
# BOQ prefix patterns for T/B project-specific items → EXCLUDE
BOQ_TPREFIX_EXCLUDE_PATTERNS = [
    r"^T51\.01\.",   # T51.01.xxxx = project-specific demolition/removal
    r"^T51\.0[0-9]\.",  # T51.0x = project-specific earthworks operations
]
# Sub-chapter prefixes that are operations/services within otherwise material chapters
BOQ_SUBPREFIX_EXCLUDE = {
    "51.01",  # earthworks operations: demolition, tree removal, cleaning, fencing
    "57.01",  # sewer/pipe inspection and video survey services
    "51.32",  # road marking and line painting — service, not material
    "51.35",  # temporary traffic equipment (barriers, signs, lights) — rental, not material
    "51.34",  # road markers and reflectors — small items, negligible mass
    "18.01.06",  # pipe pressure testing and mandrel operations — service
    "18.01.07",  # pipe inspection services
    "18.01.08",  # pipe-related services
    "51.02.004",  # soil compaction operations (הידוק קרקע) — not a material
    "51.23.04",  # drainage trench excavation (חפירת תעלת ניקוז) — earthworks/service
}
# Sub-chapter prefixes that force a specific category (material, but wrong default)
BOQ_SUBPREFIX_FORCE = {
    "18.01.04": "HDPE Granulate",  # polyethylene pipes (telecom/infra)
    "18.01.05": "HDPE Granulate",
}
# BOQ sub-chapter prefixes that need forced category override
BOQ_SUBPREFIX_CATEGORY = {
    "51.05.28": "Crushed Stone",   # rocks/boulders/aggregates — NOT Galvanized Steel
    "51.05.30": "Crushed Stone",   # washed/graded gravel — NOT Galvanized Steel
    "41.01.03": "HDPE Granulate",  # irrigation PE pipes
    "41.01.04": "HDPE Granulate",
    "41.01.05": "HDPE Granulate",
    "08.04.11": "PVC Pipe",        # PVC conduit/pipes
    "08.04.12": "HDPE Granulate",  # PE pipes in electrical chapter
    "08.04.57": "EXCLUDE",         # LED lighting fixtures — electrical equipment
    "51.07.01": "PVC Pipe",        # drainage / perforated corrugated pipes
}


def classify_category_smart(material_text: str, boq_code: Optional[str]) -> Tuple[
    Optional[str], Dict[str, Any], Optional[Dict[str, Any]]]:
    text = normalize_text(material_text)

    # ── Early exit: BOQ chapter/sub-chapter is always a service, never a material ──
    if boq_code:
        code_norm = str(boq_code).strip()
        prefix_2 = code_norm.split(".")[0]
        prefix_5 = ".".join(code_norm.split(".")[:2]) if "." in code_norm else code_norm
        prefix_8 = ".".join(code_norm.split(".")[:3])[:8] if code_norm.count(".") >= 2 else prefix_5

        # T/B prefix = project-specific items → check if service/removal
        if any(re.match(p, code_norm) for p in BOQ_TPREFIX_EXCLUDE_PATTERNS):
            return None, {
                "method": "boq_prefix_exclude",
                "reason": f"BOQ T/B-prefix {code_norm} is a project-specific service item",
                "confidence": 1.0, "excluded": True, "review_required": False,
                "inferred_uom": "unknown", "matched_by": "boq_tprefix_exclude",
                "exclusion_code": "T_PREFIX",
            }, None

        if prefix_2 in BOQ_PREFIX_EXCLUDE or prefix_5 in BOQ_SUBPREFIX_EXCLUDE or prefix_8 in BOQ_SUBPREFIX_EXCLUDE:
            return None, {
                "method": "boq_prefix_exclude",
                "reason": f"BOQ prefix {prefix_5 or prefix_2} is an admin/service chapter",
                "confidence": 1.0,
                "excluded": True,
                "review_required": False,
                "inferred_uom": "unknown",
                "matched_by": "boq_prefix_exclude",
                "exclusion_code": f"BOQ_{prefix_2}",
            }, None

        # Force category for known misclassified BOQ sub-prefixes
        forced_cat = (BOQ_SUBPREFIX_CATEGORY.get(prefix_8) or BOQ_SUBPREFIX_CATEGORY.get(prefix_5)
                      or BOQ_SUBPREFIX_FORCE.get(prefix_8) or BOQ_SUBPREFIX_FORCE.get(prefix_5))
        if forced_cat:
            return forced_cat, {
                "method": "boq_prefix_override",
                "reason": f"BOQ prefix {prefix_8} forced to {forced_cat}",
                "confidence": 0.99,
                "excluded": False,
                "review_required": False,
                "inferred_uom": "unknown",
                "matched_by": "boq_prefix_override",
            }, None

    excluded, exclusion_code, pattern = should_exclude(text)
    if excluded:
        return None, {
            "method": "exclude_pattern",
            "reason": exclusion_code or f"Excluded by pattern: {pattern}",
            "confidence": 1.0,
            "excluded": True,
            "review_required": False,
            "inferred_uom": "unknown",
            "matched_by": exclusion_code or "exclude_pattern",
            "exclusion_code": exclusion_code,
        }, None

    # Run precise semantic hard-overrides before generic catalog/BOQ matching.
    # This prevents broad mapping rows from swallowing known edge cases.
    hard = hard_classification_override(text)
    if hard:
        category, reason = hard
        is_exclude = category is None
        return category, {
            "method": "hard_override",
            "reason": reason,
            "confidence": 0.995,
            "excluded": is_exclude,
            "review_required": False,
            "inferred_uom": "unknown",
            "matched_by": "hard_override",
            "exclusion_code": "HARD_OVERRIDE" if is_exclude else None,
            "catalog_mapping": None,
            "boq_mapping": None,
        }, None

    sources = merge_mapping_sources(text, boq_code)
    category, source_method, chosen_mapping = choose_category_from_sources(sources)
    catalog_mapping = sources.get("catalog")
    boq_mapping = sources.get("boq")

    if category == "EXCLUDE":
        reason_bits = []
        if catalog_mapping and catalog_mapping.get("category") == "EXCLUDE":
            reason_bits.append(f"catalog excluded {catalog_mapping.get('mapping_id')}")
        if boq_mapping and boq_mapping.get("category") == "EXCLUDE":
            reason_bits.append(f"boq excluded {boq_mapping.get('boq_map_id') or boq_mapping.get('boq_code') or boq_mapping.get('boq_code_prefix')}")
        return None, {
            "method": source_method or "merged_mapping",
            "reason": "; ".join(reason_bits) or "Mapping excluded",
            "confidence": max(float((catalog_mapping or {}).get("confidence") or 0), 0.99 if boq_mapping else 0),
            "excluded": True,
            "review_required": False,
            "inferred_uom": (boq_mapping or {}).get("forced_uom") or (catalog_mapping or {}).get("forced_uom") or "unknown",
            "matched_by": "+".join([x for x in [
                (catalog_mapping or {}).get("_match_type"),
                (boq_mapping or {}).get("_match_type"),
            ] if x]) or (source_method or "merged_mapping"),
            "catalog_mapping": catalog_mapping,
            "boq_mapping": boq_mapping,
        }, chosen_mapping

    if category:
        reason_bits = []
        if catalog_mapping:
            reason_bits.append(f"catalog={catalog_mapping.get('mapping_id')}")
        if boq_mapping:
            reason_bits.append(f"boq={boq_mapping.get('boq_map_id') or boq_mapping.get('boq_code') or boq_mapping.get('boq_code_prefix')}")
        confidence_candidates = [
            float((catalog_mapping or {}).get("confidence") or 0),
            0.98 if boq_mapping else 0.0,
        ]
        return category, {
            "method": source_method or "merged_mapping",
            "reason": "Matched " + " + ".join(reason_bits),
            "confidence": max(confidence_candidates),
            "excluded": False,
            "review_required": False,
            "inferred_uom": (boq_mapping or {}).get("forced_uom") or (catalog_mapping or {}).get("forced_uom") or "unknown",
            "matched_by": "+".join([x for x in [
                (catalog_mapping or {}).get("_match_type"),
                (boq_mapping or {}).get("_match_type"),
            ] if x]) or (source_method or "merged_mapping"),
            "catalog_mapping": catalog_mapping,
            "boq_mapping": boq_mapping,
        }, chosen_mapping

    for category, patterns in CATEGORY_RULES:
        for pattern in patterns:
            if re.search(pattern, text, flags=re.IGNORECASE):
                return category, {
                    "method": "regex_rule",
                    "reason": f"Matched regex: {pattern}",
                    "confidence": 0.92,
                    "excluded": False,
                    "review_required": False,
                    "inferred_uom": "unknown",
                    "matched_by": "regex_rule",
                }, None

    if USE_VERTEX_CLASSIFIER:
        ai = classify_with_vertex_resilient(text)
        if ai.get("excluded") is True or ai.get("category") == "EXCLUDE":
            return None, {
                "method": "vertex_ai",
                "reason": ai.get("reason", "Excluded by Vertex"),
                "confidence": float(ai.get("confidence", 0.0)),
                "excluded": True,
                "review_required": bool(ai.get("review_required", False)),
                "inferred_uom": ai.get("inferred_uom", "unknown"),
                "matched_by": "vertex_ai",
                "ai_engineer_1": ai.get("engineer_1"),
                "ai_engineer_2": ai.get("engineer_2"),
            }, None

        category = ai.get("category", "Unknown")
        if category == "Unknown":
            return None, {
                "method": "vertex_ai",
                "reason": ai.get("reason", "Unknown by Vertex"),
                "confidence": float(ai.get("confidence", 0.0)),
                "excluded": False,
                "review_required": True,
                "inferred_uom": ai.get("inferred_uom", "unknown"),
                "matched_by": "vertex_ai",
                "extracted_element_type": ai.get("extracted_element_type"),
                "extracted_dimension_cm": ai.get("extracted_dimension_cm"),
                "ai_engineer_1": ai.get("engineer_1"),
                "ai_engineer_2": ai.get("engineer_2"),
            }, None

        return category, {
            "method": "vertex_ai",
            "reason": ai.get("reason", "Classified by Vertex"),
            "confidence": float(ai.get("confidence", 0.0)),
            "excluded": False,
            "review_required": bool(ai.get("review_required", False)),
            "inferred_uom": ai.get("inferred_uom", "unknown"),
            "matched_by": "vertex_ai",
            "extracted_element_type": ai.get("extracted_element_type"),
            "extracted_dimension_cm": ai.get("extracted_dimension_cm"),
        }, None

    return None, {
        "method": "none",
        "reason": "No category rule matched",
        "confidence": 0.0,
        "excluded": False,
        "review_required": True,
        "inferred_uom": "unknown",
        "matched_by": "none",
    }, None


# ==========================================================
# UNIT INFERENCE + SPECIAL CATALOGS
# ==========================================================
def infer_uom(material_text: str, category: Optional[str], ai_uom: Optional[str], provided_uom: Optional[str],
              mapping: Optional[Dict[str, Any]], cls_meta: Optional[Dict[str, Any]] = None) -> Tuple[str, Optional[float], str]:
    text = normalize_text(material_text)
    thickness_cm = extract_thickness_cm(text)
    cls_meta = cls_meta or {}

    normalized_provided = normalize_uom(provided_uom)
    if normalized_provided:
        if normalized_provided == "km":
            return "m", thickness_cm, "Provided UOM km -> normalized to meter basis"
        return normalized_provided, thickness_cm, f"Provided UOM -> {normalized_provided}"

    boq_mapping = cls_meta.get("boq_mapping") or {}
    catalog_mapping = cls_meta.get("catalog_mapping") or mapping or {}

    boq_forced_uom = normalize_uom(boq_mapping.get("forced_uom") or boq_mapping.get("uom") or boq_mapping.get("unit"))
    if boq_forced_uom:
        return boq_forced_uom, thickness_cm, f"BOQ mapping UOM -> {boq_forced_uom}"

    forced_uom = normalize_uom(catalog_mapping.get("forced_uom"))
    if forced_uom:
        return forced_uom, thickness_cm, f"Catalog mapping forced_uom -> {forced_uom}"

    annual_reference_uom = normalize_uom(cls_meta.get("annual_reference_uom"))
    if annual_reference_uom:
        return annual_reference_uom, thickness_cm, f"Annual reference UOM -> {annual_reference_uom}"

    ai_uom_norm = normalize_uom(ai_uom)
    if ai_uom_norm and ai_uom_norm != "unknown":
        return ai_uom_norm, thickness_cm, f"AI inferred UOM -> {ai_uom_norm}"

    if category == "Asphalt":
        if thickness_cm is not None:
            return "m2", thickness_cm, "Asphalt with explicit thickness -> m2"
        return "ton", thickness_cm, "Asphalt fallback -> ton"

    if category in {"Lean Concrete", "Structural Concrete", "Crushed Stone", "Wood", "Cementitious Mortar"}:
        return "m3", thickness_cm, f"{category} default -> m3"

    if category == "Steel Rebar":
        return "ton", thickness_cm, "Steel rebar default -> ton"

    if category in {"Copper Wire (Cable)", "HDPE Granulate", "PVC Pipe", "Concrete Pipe", "Aluminum"}:
        return "m", thickness_cm, f"{category} default -> meter"

    if category == "Precast Concrete":
        return "unit", thickness_cm, "Precast default -> unit"

    if category == "Galvanized Steel":
        return "m", thickness_cm, "Galvanized steel default -> meter"

    if category == "Waterproofing":
        return "m2", thickness_cm, "Waterproofing default -> m2"

    if category == "Glass":
        return "m2", thickness_cm, "Glass fallback -> m2"

    return "unknown", thickness_cm, "Unknown UOM"


def match_unit_rule(category: Optional[str], assumed_uom: Optional[str], material_text: str) -> Optional[
    Dict[str, Any]]:
    if not category or not assumed_uom:
        return None
    category_norm = normalize_for_compare(category)
    input_uom = normalize_uom(assumed_uom)
    text = normalize_text(material_text)
    rules = load_unit_conversion_rules()

    exact_candidates: List[Dict[str, Any]] = []
    generic_candidates: List[Dict[str, Any]] = []
    for rule in rules:
        if rule.get("_category_norm") and rule["_category_norm"] != category_norm:
            continue
        if rule.get("_input_norm") and rule["_input_norm"] != input_uom:
            continue
        pattern = rule.get("material_regex")
        if pattern:
            try:
                if re.search(pattern, text, flags=re.IGNORECASE):
                    exact_candidates.append(rule)
            except re.error:
                continue
        else:
            generic_candidates.append(rule)

    if exact_candidates:
        return exact_candidates[0]
    if generic_candidates:
        return generic_candidates[0]
    return None


def copper_or_aluminum_kg_per_m(area_mm2: float, density_kg_m3: float) -> float:
    return area_mm2 * 1e-6 * density_kg_m3


def lookup_concrete_pipe_kg_per_m(material_text: str) -> Tuple[Optional[float], str]:
    diameter_mm = extract_diameter_mm(material_text)
    class_label = extract_pipe_class(material_text)
    if diameter_mm is None:
        return None, "Concrete pipe: diameter not found"

    rows = load_concrete_pipe_catalog()
    best: Optional[Dict[str, Any]] = None
    for row in rows:
        row_diameter = row.get("diameter_mm")
        if row_diameter is None:
            continue
        if int(row_diameter) != int(diameter_mm):
            continue
        row_class = normalize_for_compare(row.get("class_label")) if row.get("class_label") else ""
        if class_label and row_class == normalize_for_compare(class_label):
            best = row
            break
        if best is None:
            best = row

    if best is None:
        return None, f"Concrete pipe catalog miss for diameter {diameter_mm}mm"

    weight = safe_float(best.get("weight_kg_per_meter"))
    if weight is None:
        return None, "Concrete pipe catalog row missing weight_kg_per_meter"
    return weight, f"Concrete pipe catalog {diameter_mm}mm {best.get('class_label') or ''}".strip()


def lookup_cable_kg_per_m(category: str, material_text: str) -> Tuple[Optional[float], str]:
    rows = load_cable_cross_section_catalog()
    conductor = "Copper" if category == "Copper Wire (Cable)" else "Aluminum"
    cores, mm2 = extract_cores_and_mm2(material_text)
    if mm2 is None:
        return None, "Cable cross-section not found"

    # Try exact catalog match first.
    candidates: List[Tuple[float, Dict[str, Any]]] = []
    for row in rows:
        if normalize_for_compare(row.get("conductor_material")) != normalize_for_compare(conductor):
            continue
        row_mm2 = safe_float(row.get("cross_section_mm2"))
        if row_mm2 is None:
            continue
        if cores is not None and row.get("cores_count") not in {None, cores}:
            continue
        candidates.append((abs(row_mm2 - mm2), row))

    if candidates:
        _, best = sorted(candidates, key=lambda x: x[0])[0]
        weight = safe_float(best.get("conductor_kg_per_meter"))
        if weight is not None:
            return weight, f"Cable catalog {best.get('cable_pattern') or f'{cores}x{mm2}'}"

    # Formula fallback — total copper/aluminum mass = cores × mm2 × density
    density = DEFAULT_CATEGORY_CONFIG[category]["density_kg_m3"]
    if cores is None:
        factor = copper_or_aluminum_kg_per_m(mm2, density)
        return factor, f"Cable formula using {mm2} mm2"
    # cores x mm2: conductor area per meter in m^2 = cores × mm2 × 1e-6
    # Also add ~15% for insulation/sheath (practical cable weight > bare conductor)
    factor = round(cores * mm2 * 1e-6 * density * 1.15, 4)
    return factor, f"Cable formula using {cores}x{mm2} mm2"


def lookup_material_catalog_weight(material_text: str, cls_meta: Dict[str, Any]) -> Tuple[Optional[float], str]:
    extracted_type = cls_meta.get("extracted_element_type")
    extracted_dim = cls_meta.get("extracted_dimension_cm")
    if not extracted_type or extracted_dim is None:
        return None, "No extracted element/dimension for materials catalog"
    catalog = load_materials_catalog()
    key = (normalize_text(extracted_type), int(extracted_dim))
    weight = catalog.get(key)
    if weight is None:
        return None, f"Materials catalog miss for {key[0]} {key[1]}cm"
    return weight, f"Materials catalog {key[0]} {key[1]}cm"


def convert_quantity_to_kg(
        category: str,
        quantity: float,
        material_text: str,
        assumed_uom: str,
        thickness_cm: Optional[float],
        mapping: Optional[Dict[str, Any]],
        cls_meta: Dict[str, Any],
) -> ConversionResult:
    cfg = DEFAULT_CATEGORY_CONFIG.get(category, {})
    text = normalize_text(material_text)

    rule = match_unit_rule(category, assumed_uom, text)

    if assumed_uom == "ton":
        factor = 1000.0
        return ConversionResult(quantity, "ton", assumed_uom, quantity * factor, factor, "1 ton = 1000 kg",
                                thickness_cm)

    if assumed_uom == "kg":
        return ConversionResult(quantity, "kg", assumed_uom, quantity, 1.0, "Already in kg", thickness_cm)

    if category == "Concrete Pipe" and assumed_uom == "m":
        factor, reason = lookup_concrete_pipe_kg_per_m(text)
        if factor is not None:
            return ConversionResult(quantity, "m", assumed_uom, quantity * factor, factor, reason, thickness_cm)

    if category in {"Copper Wire (Cable)", "Aluminum"} and assumed_uom == "m":
        factor, reason = lookup_cable_kg_per_m(category, text)
        if factor is not None:
            return ConversionResult(quantity, "m", assumed_uom, quantity * factor, factor, reason, thickness_cm)

    if assumed_uom == "unit":
        factor, reason = lookup_material_catalog_weight(text, cls_meta)
        if factor is not None:
            return ConversionResult(quantity, "unit", assumed_uom, quantity * factor, factor, reason, thickness_cm)

    if mapping and safe_float(mapping.get("kg_per_unit")) is not None and assumed_uom == "unit":
        factor = float(mapping["kg_per_unit"])
        return ConversionResult(quantity, "unit", assumed_uom, quantity * factor, factor, "Mapping kg_per_unit",
                                thickness_cm)

    if mapping and safe_float(mapping.get("kg_per_meter")) is not None and assumed_uom == "m":
        factor = float(mapping["kg_per_meter"])
        return ConversionResult(quantity, "m", assumed_uom, quantity * factor, factor, "Mapping kg_per_meter",
                                thickness_cm)

    if mapping and safe_float(mapping.get("density_kg_m3")) is not None and assumed_uom == "m3":
        density = float(mapping["density_kg_m3"])
        return ConversionResult(quantity, "m3", assumed_uom, quantity * density, density,
                                f"Mapping density {density} kg/m3", thickness_cm)

    if rule:
        if assumed_uom == "m3" and safe_float(rule.get("density_kg_m3")) is not None:
            density = float(rule["density_kg_m3"])
            return ConversionResult(quantity, "m3", assumed_uom, quantity * density, density,
                                    f"Unit rule density {density} kg/m3", thickness_cm)

        if assumed_uom == "m" and safe_float(rule.get("kg_per_meter")) is not None:
            factor = float(rule["kg_per_meter"])
            return ConversionResult(quantity, "m", assumed_uom, quantity * factor, factor, "Unit rule kg_per_meter",
                                    thickness_cm)

        if assumed_uom == "unit" and safe_float(rule.get("kg_per_unit")) is not None:
            factor = float(rule["kg_per_unit"])
            return ConversionResult(quantity, "unit", assumed_uom, quantity * factor, factor, "Unit rule kg_per_unit",
                                    thickness_cm)

        if assumed_uom == "m2":
            if safe_float(rule.get("kg_per_m2_per_cm")) is not None and thickness_cm is not None:
                per_cm = float(rule["kg_per_m2_per_cm"])
                factor = per_cm * thickness_cm
                return ConversionResult(quantity, "m2", assumed_uom, quantity * factor, factor,
                                        f"Unit rule kg_per_m2_per_cm * {thickness_cm}cm", thickness_cm)
            if safe_float(rule.get("kg_per_m2")) is not None:
                factor = float(rule["kg_per_m2"])
                return ConversionResult(quantity, "m2", assumed_uom, quantity * factor, factor, "Unit rule kg_per_m2",
                                        thickness_cm)

    if assumed_uom == "m3":
        density = safe_float(cfg.get("density_kg_m3"))
        if density is not None:
            return ConversionResult(quantity, "m3", assumed_uom, quantity * density, density,
                                    f"Default density {density} kg/m3", thickness_cm)

    if assumed_uom == "m2":
        if category == "Asphalt":
            if thickness_cm is None and mapping and mapping.get("thickness_cm") is not None:
                thickness_cm = float(mapping["thickness_cm"])
            if thickness_cm is None:
                # Try to extract thickness from text (e.g. "עובי 5 ס'מ", "10.1-12.0 ס"מ")
                # Reuse the existing THICKNESS_CM_PATTERNS from the module
                for _tp in THICKNESS_CM_PATTERNS:
                    import re as _re
                    _tm = _re.search(_tp, text, flags=_re.IGNORECASE)
                    if _tm:
                        try:
                            thickness_cm = float(_tm.group(1).replace(",", "."))
                        except Exception:
                            pass
                        break
            if thickness_cm is not None:
                factor = cfg["kg_per_m2_per_cm"] * thickness_cm
                return ConversionResult(quantity, "m2", assumed_uom, quantity * factor, factor,
                                        f"Asphalt default {cfg['kg_per_m2_per_cm']} kg/m2/cm * {thickness_cm}cm",
                                        thickness_cm)
            # No thickness found anywhere — use 5cm as conservative default
            default_thickness = 5.0
            factor = cfg["kg_per_m2_per_cm"] * default_thickness
            return ConversionResult(quantity, "m2", assumed_uom, quantity * factor, factor,
                                    f"Asphalt m2 default thickness {default_thickness}cm assumed",
                                    default_thickness)

        if category == "Waterproofing":
            if re.search(r"גאוטכני|hdpe|הגנה", text, flags=re.IGNORECASE):
                factor = cfg.get("kg_per_m2_protection")
                return ConversionResult(quantity, "m2", assumed_uom, quantity * factor, factor,
                                        "Protection layer default kg/m2", thickness_cm)
            factor = cfg.get("kg_per_m2_membrane")
            return ConversionResult(quantity, "m2", assumed_uom, quantity * factor, factor,
                                    "Bituminous membrane default kg/m2", thickness_cm)

        # Glass — extract thickness in mm from text for accurate kg/m2
        if category == "Glass":
            # Try to extract mm thickness: "8 מ'מ", "10mm", "12מ\"מ"
            import re as _re
            _gm = _re.search(r'(\d+(?:\.\d+)?)\s*(?:מ(?:["״\'\\]?)מ|mm)', text, flags=_re.IGNORECASE)
            if _gm:
                thickness_mm = float(_gm.group(1))
                # Sanity: normal glass 3-40mm, laminated up to 60mm
                if 2 <= thickness_mm <= 80:
                    factor = round(DEFAULT_CATEGORY_CONFIG["Glass"]["density_kg_m3"] * thickness_mm / 1000.0, 3)
                    return ConversionResult(quantity, "m2", assumed_uom, quantity * factor, factor,
                                            f"Glass {thickness_mm:.0f}mm: {factor} kg/m2", thickness_cm)
            # Default: assume 6mm architectural glass (~15 kg/m2)
            factor = 15.0
            return ConversionResult(quantity, "m2", assumed_uom, quantity * factor, factor,
                                    "Glass m2 default 6mm: 15 kg/m2", thickness_cm)

        if category == "Fill Material":
            per_cm = safe_float(cfg.get("kg_per_m2_per_cm"))
            if per_cm is not None and thickness_cm is not None:
                factor = per_cm * thickness_cm
                return ConversionResult(quantity, "m2", assumed_uom, quantity * factor, factor,
                                        f"Fill Material {per_cm} kg/m2/cm * {thickness_cm}cm", thickness_cm)
            density = safe_float(cfg.get("density_kg_m3"))
            if density is not None and thickness_cm is not None:
                factor = density * thickness_cm / 100.0
                return ConversionResult(quantity, "m2", assumed_uom, quantity * factor, factor,
                                        f"Fill Material density {density} * {thickness_cm}cm", thickness_cm)
            return ConversionResult(quantity, "m2", assumed_uom, None, None,
                                    "Fill Material m2 requires thickness", thickness_cm)

        if category == "Paving":
            factor = safe_float(cfg.get("kg_per_m2"))
            if factor is not None:
                return ConversionResult(quantity, "m2", assumed_uom, quantity * factor, factor,
                                        "Paving default kg/m2", thickness_cm)

        # Generic m2 handler for categories with kg_per_m2 in config
        # Covers: Structural Concrete, Precast Concrete, Galvanized Steel, Steel Rebar, etc.
        kg_m2 = safe_float(cfg.get("kg_per_m2"))
        if kg_m2 is not None:
            if thickness_cm is not None:
                # If thickness is known, use density instead for precision
                density = safe_float(cfg.get("density_kg_m3"))
                if density is not None:
                    factor = density * thickness_cm / 100.0
                    return ConversionResult(quantity, "m2", assumed_uom, quantity * factor, factor,
                                            f"{category} m2: density {density} × {thickness_cm}cm", thickness_cm)
            # No thickness: use the kg_per_m2 default directly
            return ConversionResult(quantity, "m2", assumed_uom, quantity * kg_m2, kg_m2,
                                    f"{category} m2 default: {kg_m2} kg/m2", thickness_cm)

        # Last resort for m2: use density with a 10cm default thickness
        density = safe_float(cfg.get("density_kg_m3"))
        if density is not None:
            default_thickness = thickness_cm if thickness_cm is not None else 10.0
            factor = density * default_thickness / 100.0
            return ConversionResult(quantity, "m2", assumed_uom, quantity * factor, factor,
                                    f"{category} m2 fallback: density {density} × {default_thickness}cm assumed",
                                    default_thickness)

    if assumed_uom == "m":
        if category == "PVC Pipe":
            inch = extract_inch_diameter(text)
            if inch is not None:
                closest = min(PVC_DEFAULTS.keys(), key=lambda x: abs(x - inch))
                factor = PVC_DEFAULTS[closest]
                return ConversionResult(quantity, "m", assumed_uom, quantity * factor, factor,
                                        f"PVC default by nominal inch {closest}", thickness_cm)

            # Corrugated/perforated drainage pipe in mm text (e.g. 160 מ"מ)
            mm_match = re.search(r'(\d+(?:\.\d+)?)\s*מ(?:["״׳\']?)מ', text, flags=re.IGNORECASE)
            if mm_match:
                diameter_mm = float(mm_match.group(1))
                factor = max(0.35, round(0.0065 * diameter_mm, 3))  # pragmatic proxy from review workbook
                return ConversionResult(quantity, "m", assumed_uom, quantity * factor, factor,
                                        f"PVC corrugated pipe proxy by diameter {diameter_mm:.0f}mm", thickness_cm)

        # For concrete piles/columns — extract diameter from text for accurate kg/m
        if category in {"Structural Concrete", "Lean Concrete"} and quantity and quantity > 0:
            import re as _re, math as _math
            _dm = _re.search(r"קוטר\s*(\d+(?:\.\d+)?)", text, _re.IGNORECASE)
            if _dm:
                d_cm = float(_dm.group(1))
                # Sanity check: diameter must be realistic (20-200cm for piles)
                if 20 <= d_cm <= 200:
                    r_m = d_cm / 200.0
                    factor = _math.pi * r_m ** 2 * float(cfg.get("density_kg_m3", 2400))
                    return ConversionResult(quantity, "m", assumed_uom, quantity * factor, factor,
                                            f"Pile ø{d_cm:.0f}cm: π×{r_m:.3f}²×{cfg.get('density_kg_m3',2400)}", thickness_cm)

        factor = safe_float(cfg.get("kg_per_meter"))
        if factor is not None:
            return ConversionResult(quantity, "m", assumed_uom, quantity * factor, factor,
                                    f"Default kg/m for {category}", thickness_cm)

    if assumed_uom == "unit":
        if category == "Galvanized Steel" and re.search(r"שלט|תמרור", text, flags=re.IGNORECASE):
            factor = 25.0
            return ConversionResult(quantity, "unit", assumed_uom, quantity * factor, factor,
                                    "Traffic sign/sign-support default kg/unit", thickness_cm)

        if category == "PVC Pipe":
            # Wall drains / short outlet drains often come as unit rows but include length in text
            range_match = re.search(r"(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)\s*מ", text, flags=re.IGNORECASE)
            single_match = re.search(r"אורך\s*(?:עד\s*)?(\d+(?:\.\d+)?)\s*מ", text, flags=re.IGNORECASE)
            length_m = None
            if range_match:
                length_m = (float(range_match.group(1)) + float(range_match.group(2))) / 2.0
            elif single_match:
                length_m = float(single_match.group(1))
            if length_m is not None:
                inch = extract_inch_diameter(text)
                factor_per_m = PVC_DEFAULTS[min(PVC_DEFAULTS.keys(), key=lambda x: abs(x - inch))] if inch is not None else safe_float(cfg.get("kg_per_meter")) or 1.95
                factor = length_m * factor_per_m
                return ConversionResult(quantity, "unit", assumed_uom, quantity * factor, factor,
                                        f"PVC unit row converted from embedded length {length_m:.2f}m", thickness_cm)

        factor = safe_float(cfg.get("kg_per_unit"))
        if factor is not None:
            return ConversionResult(quantity, "unit", assumed_uom, quantity * factor, factor,
                                    f"Default kg/unit for {category}", thickness_cm)

    return ConversionResult(quantity, assumed_uom, assumed_uom, None, None, "Could not infer conversion", thickness_cm)


# ==========================================================
# CLIMATIQ
# ==========================================================
def climatiq_headers() -> Dict[str, str]:
    api_key = os.environ.get("CLIMATIQ_API_KEY")
    if not api_key:
        raise RuntimeError("Missing CLIMATIQ_API_KEY environment variable")
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


@lru_cache(maxsize=256)
def get_emission_factor_with_meta(category: str) -> Dict[str, Any]:
    cache_query = f"""
    SELECT *
    FROM `{BQ_FACTOR_CACHE_TABLE}`
    WHERE is_active = TRUE
      AND category = @category
      AND data_version = @data_version
      AND (@region IS NULL OR region = @region OR region IS NULL)
      AND (@source IS NULL OR source = @source OR source IS NULL)
    ORDER BY updated_at DESC
    LIMIT 1
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("category", "STRING", category),
            bigquery.ScalarQueryParameter("data_version", "STRING", CLIMATIQ_DATA_VERSION),
            bigquery.ScalarQueryParameter("region", "STRING", CLIMATIQ_REGION),
            bigquery.ScalarQueryParameter("source", "STRING", CLIMATIQ_SOURCE),
        ]
    )
    rows = list(bq_client.query(cache_query, job_config=job_config).result())
    if rows:
        row = dict(rows[0].items())
        return {
            "selected": {
                "id": row.get("emission_factor_id"),
                "activity_id": row.get("activity_id"),
                "unit_type": row.get("unit_type"),
                "unit": row.get("unit"),
                "name": row.get("factor_name"),
                "source": row.get("source"),
            },
            "candidate_count": 1,
            "factor_min": None,
            "factor_max": None,
            "factor_spread_pct": 0.0,
            "from_cache": True,
            "query": row.get("query"),
        }

    cfg = DEFAULT_CATEGORY_CONFIG[category]
    params: Dict[str, Any] = {
        "query": cfg["climatiq_search"],
        "data_version": CLIMATIQ_DATA_VERSION,
        "page": 1,
    }
    if CLIMATIQ_REGION:
        params["region"] = CLIMATIQ_REGION
    if CLIMATIQ_SOURCE:
        params["source"] = CLIMATIQ_SOURCE

    response = requests.get(
        f"{CLIMATIQ_BASE_URL}/search",
        headers=climatiq_headers(),
        params=params,
        timeout=HTTP_TIMEOUT,
    )
    response.raise_for_status()
    data = response.json()
    results = data.get("results", [])
    if not results:
        raise RuntimeError(
            f"No Climatiq search results for category '{category}' with query '{cfg['climatiq_search']}'")

    weight_results = []
    factor_values = []
    for item in results:
        unit_type = str(item.get("unit_type", "")).lower()
        unit = str(item.get("unit", "")).lower()
        if "weight" in unit_type or unit in {"kg", "t", "g", "lb", "ton"}:
            weight_results.append(item)
            value = safe_float(item.get("factor") or item.get("co2e"))
            if value is not None:
                factor_values.append(value)

    if not weight_results:
        raise RuntimeError(f"No weight-based Climatiq factor found for category '{category}'")

    selected = weight_results[0]
    if factor_values:
        fmin, fmax = min(factor_values), max(factor_values)
        spread = ((fmax - fmin) / fmin * 100.0) if fmin else 0.0
    else:
        fmin = fmax = None
        spread = None

    cache_row = {
        "cache_key": f"{category}|{CLIMATIQ_DATA_VERSION}|{CLIMATIQ_REGION or ''}|{CLIMATIQ_SOURCE or ''}",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "is_active": True,
        "category": category,
        "query": cfg["climatiq_search"],
        "region": CLIMATIQ_REGION,
        "source": CLIMATIQ_SOURCE,
        "data_version": CLIMATIQ_DATA_VERSION,
        "emission_factor_id": selected.get("id"),
        "activity_id": selected.get("activity_id"),
        "unit_type": str(selected.get("unit_type")),
        "unit": selected.get("unit"),
        "factor_name": selected.get("name"),
        "raw_result_json": json.dumps(
            {"selected": selected, "candidate_count": len(weight_results), "factor_min": fmin, "factor_max": fmax,
             "factor_spread_pct": spread}, ensure_ascii=False),
    }
    try:
        bq_client.insert_rows_json(BQ_FACTOR_CACHE_TABLE, [cache_row])
    except Exception:
        logger.exception("Failed writing climatiq cache row")

    return {
        "selected": selected,
        "candidate_count": len(weight_results),
        "factor_min": fmin,
        "factor_max": fmax,
        "factor_spread_pct": spread,
        "from_cache": False,
        "query": cfg["climatiq_search"],
    }


def estimate_weight_kg(category: str, weight_kg: float) -> Tuple[
    float, str, Optional[str], Optional[str], Dict[str, Any]]:
    factor_meta = get_emission_factor_with_meta(category)
    factor = factor_meta["selected"]
    factor_id = factor.get("id")
    activity_id = factor.get("activity_id")
    factor_source = factor.get("source")

    payload = {
        "emission_factor": {"id": factor_id},
        "parameters": {"weight": weight_kg, "weight_unit": "kg"},
    }

    try:
        response = requests.post(
            f"{CLIMATIQ_BASE_URL}/estimate",
            headers=climatiq_headers(),
            json=payload,
            timeout=HTTP_TIMEOUT,
        )
    except requests.exceptions.ConnectionError as _ce:
        raise RuntimeError(f"Climatiq API unavailable (network error): {_ce}") from _ce
    except requests.exceptions.Timeout as _te:
        raise RuntimeError(f"Climatiq API timeout after {HTTP_TIMEOUT}s") from _te
    if not response.ok:
        raise RuntimeError(f"Climatiq estimate failed: {response.status_code} {response.text}")

    data = response.json()
    co2e = data.get("co2e")
    if co2e is None:
        raise RuntimeError(f"Climatiq response missing co2e: {data}")

    return float(co2e), factor_id, activity_id, factor_source, factor_meta


# ==========================================================
# DATAFRAME PIPELINE
# ==========================================================
# DATAFRAME PIPELINE
# ==========================================================
def aggregate_dataframe(df: pd.DataFrame, requested_source_mode: Optional[str] = None) -> Tuple[pd.DataFrame, str]:
    work_df, source_mode = build_work_dataframe(df, requested_source_mode=requested_source_mode)

    work_df["material"] = work_df["material"].map(normalize_text)
    work_df["material"] = work_df["material"].replace({"": None, "nan": None, "None": None})
    work_df["quantity"] = (
        work_df["quantity"]
        .astype(str)
        .str.replace(",", "", regex=False)
        .str.strip()
        .replace({"": None, "nan": None, "None": None})
    )
    work_df["quantity"] = pd.to_numeric(work_df["quantity"], errors="coerce")
    work_df["unit"] = work_df["unit"].map(lambda x: normalize_text(x) if pd.notna(x) else None)
    work_df["boq_code"] = work_df["boq_code"].map(lambda x: normalize_text(x) if pd.notna(x) else None)
    work_df = work_df.dropna(subset=["material", "quantity"])
    work_df = work_df[work_df["material"].astype(str).str.strip() != ""]
    work_df = work_df[work_df["quantity"] != 0]

    grouped = work_df.groupby(["material", "unit", "boq_code", "source_mode"], dropna=False, as_index=False)[
        "quantity"].sum()
    return grouped, source_mode


def persist_annual_paid_items_2025_raw(df: pd.DataFrame, metadata: Dict[str, Any],
                                       requested_source_mode: Optional[str] = None) -> None:
    source_mode = detect_input_layout(df, requested_source_mode)
    if source_mode != SOURCE_MODE_ANNUAL:
        return
    try:
        work_df, _ = build_work_dataframe(df, requested_source_mode=SOURCE_MODE_ANNUAL)
        rows: List[Dict[str, Any]] = []
        ts = datetime.now(timezone.utc).isoformat()
        for rec in work_df.to_dict(orient="records"):
            rows.append({
                "ingested_at": ts,
                "run_id": metadata.get("run_id"),
                "source_file": metadata.get("source_file"),
                "project_name": metadata.get("project_name"),
                "project_type": metadata.get("project_type"),
                "contractor": metadata.get("contractor"),
                "region": metadata.get("region"),
                "measurement_year": 2025,
                "item_code": rec.get("boq_code"),
                "item_description": rec.get("material"),
                "contract_uom": rec.get("unit"),
                "goods_receipts_quantity": safe_float(rec.get("quantity")),
                "source_mode": SOURCE_MODE_ANNUAL,
            })
        append_rows_json(BQ_ANNUAL_PAID_ITEMS_2025_RAW_TABLE, rows)
        load_annual_paid_items_reference_rows.cache_clear()
    except Exception:
        logger.exception("Failed persisting annual paid-items raw rows to %s", BQ_ANNUAL_PAID_ITEMS_2025_RAW_TABLE)


def insert_review_row(**kwargs) -> None:
    row = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "review_status": kwargs.get("review_status", "pending"),
        **kwargs,
    }
    append_rows_json(BQ_REVIEW_QUEUE_TABLE, [row])


def _prepare_auto_mapping_row(material: str, boq_code: Optional[str], category: str, assumed_uom: str,
                              conversion: ConversionResult, matched_by: str, reliability_score: float, source: str) -> \
Dict[str, Any]:
    row = {
        "mapping_id": f"AUTO-{abs(hash((material, category, assumed_uom)))}",
        "exact_material": material,
        "material_regex": None,
        "boq_code": boq_code,
        "category": category,
        "forced_uom": assumed_uom,
        "kg_per_unit": conversion.factor_used if assumed_uom == "unit" else None,
        "kg_per_meter": conversion.factor_used if assumed_uom == "m" else None,
        "density_kg_m3": conversion.factor_used if assumed_uom == "m3" else None,
        "confidence": reliability_score,
        "notes": f"Auto approved from {source}",
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    return row


def maybe_write_learning_rows(material: str, boq_code: Optional[str], category: str, assumed_uom: str,
                              conversion: ConversionResult, matched_by: str, reliability_score: float,
                              source: str, emission_factor: Optional[float] = None, emission_factor_source: Optional[str] = None) -> None:
    if not AUTO_WRITE_MAPPINGS or category in {"Unknown", "EXCLUDE"}:
        return
    if reliability_score < AUTO_APPROVE_CONFIDENCE:
        return

    try:
        append_rows_json(BQ_MAPPING_TABLE, [
            _prepare_auto_mapping_row(material, boq_code, category, assumed_uom, conversion, matched_by,
                                      reliability_score, source)])
    except Exception:
        logger.exception("Failed auto-writing catalog mapping")

    try:
        rule_row = {
            "rule_id": f"AUTO-UCR-{abs(hash((category, assumed_uom, conversion.factor_used)))}",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "is_active": True,
            "category": category,
            "material_regex": re.escape(material[:100]) if material else None,
            "input_uom": assumed_uom,
            "output_uom": "kg",
            "kg_per_unit": conversion.factor_used if assumed_uom == "unit" else None,
            "kg_per_meter": conversion.factor_used if assumed_uom == "m" else None,
            "density_kg_m3": conversion.factor_used if assumed_uom == "m3" else None,
            "kg_per_m2": conversion.factor_used if assumed_uom == "m2" and conversion.thickness_cm is None else None,
            "kg_per_m2_per_cm": (
                        conversion.factor_used / conversion.thickness_cm) if assumed_uom == "m2" and conversion.thickness_cm else None,
            "notes": f"Auto approved from {source}",
            "source": source,
            "created_by": "system_auto_learning",
        }
        append_rows_json(BQ_UNIT_RULES_TABLE, [rule_row])
    except Exception:
        logger.exception("Failed auto-writing unit rule")

    if boq_code:
        # Validate before writing: never auto-learn bad/service categories
        _prefix2 = boq_code.split(".")[0] if "." in boq_code else boq_code
        _prefix5 = ".".join(boq_code.split(".")[:2]) if boq_code.count(".") >= 1 else boq_code
        _is_safe_to_learn = (
            category not in {None, "EXCLUDE", "Unknown"}
            and _prefix2 not in BOQ_PREFIX_EXCLUDE
            and _prefix5 not in BOQ_SUBPREFIX_EXCLUDE
            and reliability_score >= 0.90  # higher threshold for auto-write
        )
        if _is_safe_to_learn:
            try:
                boq_row = {
                    "boq_map_id": f"AUTO-BQ-{abs(hash((boq_code, category, assumed_uom)))}",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "is_active": True,
                    "boq_code": boq_code,
                    "boq_code_prefix": boq_code.split('.')[0] if '.' in boq_code else boq_code,
                    "category": category,
                    "forced_uom": assumed_uom,
                    "notes": f"Auto approved from {source}",
                    "source": source,
                    "created_by": "system_auto_learning",
                    "emission_factor": emission_factor,
                    "emission_factor_source": emission_factor_source,
                }
                append_rows_json(BQ_BOQ_MAPPING_TABLE, [boq_row])
            except Exception:
                logger.exception("Failed auto-writing BOQ mapping")


def compute_reliability_score(material: str, category: Optional[str], assumed_uom: Optional[str],
                              conversion: Optional[ConversionResult], cls_meta: Dict[str, Any],
                              factor_meta: Optional[Dict[str, Any]], threshold: float,
                              max_candidates: int = DEFAULT_MAX_CLIMATIQ_CANDIDATES,
                              max_factor_spread_pct: float = DEFAULT_MAX_FACTOR_SPREAD_PCT) -> Tuple[
    float, str, List[str]]:
    score = 1.0
    reasons: List[str] = []
    status = "auto_approved"

    conf = float(cls_meta.get("confidence", 0) or 0)
    method = cls_meta.get("method")
    has_catalog = bool(cls_meta.get("catalog_mapping"))
    has_boq = bool(cls_meta.get("boq_mapping"))

    if method == "vertex_ai":
        if conf < 0.85:
            score -= 0.20
            reasons.append("AI/classification confidence below 0.85")
        e1 = cls_meta.get("ai_engineer_1") or {}
        e2 = cls_meta.get("ai_engineer_2") or {}
        if e1.get("category") != e2.get("category"):
            score -= 0.35
            reasons.append("Dual engineers disagree on category")
    elif conf < 0.50 and not (has_catalog or has_boq):
        score -= 0.15
        reasons.append("Classification confidence below 0.50")

    if contains_suspect_non_material_text(material) and not (has_catalog or has_boq):
        score -= 0.30
        reasons.append("Text contains suspect non-material terms")
    if not category or category == "Unknown":
        score -= 0.40
        reasons.append("Unknown category")
    if not assumed_uom or assumed_uom == "unknown":
        score -= 0.25
        reasons.append("Unknown unit")
    if conversion is None or conversion.weight_kg is None:
        score -= 0.35
        reasons.append("Could not convert quantity to kg")
    if factor_meta:
        cnt = int(factor_meta.get("candidate_count") or 0)
        spread = factor_meta.get("factor_spread_pct")
        if cnt == 0:
            score -= 0.35
            reasons.append("No Climatiq candidates found")
        if cnt > max_candidates:
            score -= 0.20
            reasons.append(f"More than {max_candidates} Climatiq candidates")
        if spread is not None and spread > max_factor_spread_pct:
            score -= 0.20
            reasons.append(f"Climatiq factor spread above {max_factor_spread_pct}%")

    if (has_catalog or has_boq) and category and assumed_uom and assumed_uom != "unknown" and conversion and conversion.weight_kg not in (None, 0):
        score = max(score, threshold + 0.05)
        reasons = [r for r in reasons if r not in {"Classification confidence below 0.50", "AI/classification confidence below 0.85"}]

    score = max(0.0, min(1.0, round(score, 4)))
    if score < 0.60:
        status = "rejected"
    elif score < threshold:
        status = "review_required"
    return score, status, reasons


def _process_single_row_task(row_tuple, metadata, regulator_catalog, threshold, max_candidates, max_factor_spread_pct,
                             auto_write_ai_approved, run_id, current_time):
    # פונקציית העזר: מטפלת בשורה אחת בלבד, ורצה באחד מ-15 הערוצים המקבילים
    row = pd.Series(row_tuple._asdict())
    material = normalize_text(row.get("material"))
    boq_code = normalize_text(row.get("boq_code")) if pd.notna(row.get("boq_code")) else None
    quantity = safe_float(row.get("quantity"))
    if quantity is None or quantity == 0.0:
        # qty=NaN can happen when Excel cell is empty — try to recover from weight_kg column
        existing_weight = safe_float(row.get("weight_kg"))
        if existing_weight and existing_weight > 0:
            # weight already computed in a prior field — use it directly by setting qty=weight and uom=kg
            quantity = existing_weight
            # Safe conversion: named tuple → dict without breaking downstream
            if hasattr(row, '_asdict'):
                row = dict(row._asdict())
            elif not isinstance(row, dict):
                row = dict(row)
            row["unit"] = "kg"
        else:
            quantity = 0.0
    provided_uom = row.get("unit")
    source_mode = row.get("source_mode") or metadata.get("source_mode") or SOURCE_MODE_BOQ

    annual_reference = match_annual_paid_item_reference(material, boq_code, provided_uom)
    annual_reference_material = normalize_text(
        (annual_reference or {}).get("item_description")) if annual_reference else None
    annual_reference_uom = normalize_text((annual_reference or {}).get("contract_uom")) if annual_reference else None
    annual_reference_match_type = (annual_reference or {}).get("_match_type")
    classification_material = annual_reference_material or material
    effective_provided_uom = annual_reference_uom or provided_uom

    stats = {
        "emission": 0.0, "matched": 0, "estimated": 0, "excluded": 0,
        "unmapped": 0, "conversion_failed": 0, "estimate_failed": 0,
        "needs_review": 0, "auto_learned": 0
    }

    category, cls_meta, mapping = classify_category_smart(classification_material, boq_code)
    catalog_mapping = cls_meta.get("catalog_mapping") or (mapping if cls_meta.get("method") in {"catalog_mapping", "merged_mapping"} else None)
    boq_mapping = cls_meta.get("boq_mapping") or (mapping if cls_meta.get("method") == "boq_code_mapping" else None)
    if annual_reference_match_type:
        cls_meta["annual_reference_match_type"] = annual_reference_match_type
        cls_meta["annual_reference_material"] = annual_reference_material
        cls_meta["annual_reference_uom"] = annual_reference_uom
    classification_method = cls_meta.get("method", "none")
    classification_confidence = float(cls_meta.get("confidence", 0) or 0)
    matched_by = cls_meta.get("matched_by", classification_method)
    if annual_reference_match_type:
        matched_by = f"{annual_reference_match_type}+{matched_by}"
    category_rule = cls_meta.get("reason")
    ai_uom = cls_meta.get("inferred_uom")

    if cls_meta.get("excluded"):
        stats["excluded"] = 1
        detail_row = {
            **metadata, "calculation_date": current_time, "material": material,
            "short_text": material, "boq_code": boq_code, "category": "EXCLUDE",
            "classification_method": classification_method, "classification_confidence": classification_confidence,
            "matched_by": matched_by, "review_required": False, "status": "excluded",
            "conversion_assumption": category_rule, "error_reason": category_rule,
            "excluded": True, "source_mode": source_mode,
            "normalized_material": classification_material,
            "annual_reference_material": annual_reference_material,
            "annual_reference_uom": annual_reference_uom,
            "annual_reference_match_type": annual_reference_match_type,
            "reliability_score": 1.0, "reliability_status": "auto_approved",
        }
        return complete_emissions_detail_row(detail_row, metadata), stats

    if not category:
        stats["unmapped"] = 1
        stats["needs_review"] = 1
        insert_review_row(
            review_id=f"review-{run_id}-{abs(hash((material, boq_code, 'unmapped')))}",
            run_id=run_id, source_file=metadata.get("source_file", ""),
            material=material, short_text=material, boq_code=boq_code,
            project_type=metadata.get("project_type", "לא מוגדר"),
            project_name=metadata.get("project_name", metadata.get("source_file", "")),
            suggested_category="Unknown", suggested_uom=None, suggested_weight_kg=None,
            classification_method=classification_method, classification_confidence=classification_confidence,
            reliability_score=0.0, reliability_status="review_required",
            review_reason=category_rule or "No category mapping rule matched",
            ai_engineer_1_json=json.dumps(cls_meta.get("ai_engineer_1"), ensure_ascii=False) if cls_meta.get(
                "ai_engineer_1") else None,
            ai_engineer_2_json=json.dumps(cls_meta.get("ai_engineer_2"), ensure_ascii=False) if cls_meta.get(
                "ai_engineer_2") else None,
        )
        detail_row = {
            **metadata, "calculation_date": current_time, "material": material,
            "short_text": material, "boq_code": boq_code, "category": "Unknown",
            "classification_method": classification_method, "classification_confidence": classification_confidence,
            "matched_by": matched_by, "review_required": True, "status": "unmapped",
            "conversion_assumption": category_rule, "error_reason": "No category mapping rule matched",
            "source_mode": source_mode,
            "normalized_material": classification_material,
            "annual_reference_material": annual_reference_material,
            "annual_reference_uom": annual_reference_uom,
            "annual_reference_match_type": annual_reference_match_type,
        }
        return complete_emissions_detail_row(detail_row, metadata), stats

    stats["matched"] = 1
    assumed_uom, thickness_cm, uom_reason = infer_uom(classification_material, category, ai_uom, effective_provided_uom,
                                                      mapping, cls_meta)
    conversion = convert_quantity_to_kg(category, quantity, classification_material, assumed_uom, thickness_cm, mapping,
                                        cls_meta)
    if conversion.weight_kg is None:
        stats["conversion_failed"] = 1

    # ── Composite Material Split ──────────────────────────────────────────
    # If this material is a known composite (e.g. בטון מזוין), split its
    # weight across constituent categories and compute a blended emission.
    if conversion.weight_kg is not None and conversion.weight_kg >= MIN_WEIGHT_FOR_COMPOSITE_SPLIT_KG:
        composite_components = detect_composite_split(classification_material, conversion.weight_kg)
        if composite_components:
            composite_emission = 0.0
            composite_breakdown = []
            for comp in composite_components:
                comp_cat   = comp["category"]
                comp_wt    = comp["weight_kg"]
                comp_ef    = CATEGORY_EMISSION_OVERRIDES.get(comp_cat)
                comp_co2e  = round(comp_wt * comp_ef, 3) if comp_ef is not None else 0.0
                composite_emission += comp_co2e
                composite_breakdown.append({
                    "category":    comp_cat,
                    "fraction":    comp["fraction"],
                    "weight_kg":   comp_wt,
                    "ef_kgco2e_kg": comp_ef,
                    "emission_co2e": comp_co2e,
                    "description": comp["description"],
                })
            stats["emission"] = composite_emission
            stats["estimated"] = 1
            recipe_name = composite_components[0]["recipe_name"]
            detail_row = {
                **metadata, "calculation_date": current_time, "material": material,
                "short_text": material, "normalized_material": classification_material, "boq_code": boq_code,
                "category": category,
                "category_rule": f"Composite split: {recipe_name}",
                "classification_method": classification_method,
                "classification_confidence": classification_confidence,
                "review_required": False,
                "original_quantity": quantity,
                "original_uom": provided_uom, "effective_input_uom": effective_provided_uom,
                "assumed_uom": assumed_uom,
                "weight_kg": conversion.weight_kg,
                "conversion_factor_used": conversion.factor_used,
                "conversion_assumption": f"{uom_reason}; {conversion.assumption}",
                "quantity_unit": assumed_uom,
                "quantity_kg": conversion.weight_kg,
                "data_source": "ICE_DB_composite",
                "ef_id": f"composite:{recipe_name}",
                "emission_co2e": composite_emission,
                "reliability_score": 0.92,
                "reliability_status": "auto_approved",
                "matched_by": matched_by,
                "excluded": False,
                "status": "estimated",
                "thickness_cm_extracted": thickness_cm,
                "matched": True,
                "source_mode": source_mode,
                "annual_reference_material": annual_reference_material,
                "annual_reference_uom": annual_reference_uom,
                "annual_reference_match_type": annual_reference_match_type,
                "error_reason": None,
                # Store breakdown as JSON in the notes field for traceability
                "conversion_assumption": (
                    f"{uom_reason}; {conversion.assumption} | "
                    f"COMPOSITE {recipe_name}: "
                    + " + ".join(
                        f"{c['description']} {c['weight_kg']:,.0f}kg×{c['ef_kgco2e_kg']}={c['emission_co2e']:,.0f}kgCO2e"
                        for c in composite_breakdown
                    )
                ),
            }
            logger.info(
                "Composite split [%s] material=%s weight=%.0f kg → %d components, total CO2e=%.1f",
                recipe_name, material, conversion.weight_kg, len(composite_components), composite_emission
            )
            return complete_emissions_detail_row(detail_row, metadata), stats
    # ─────────────────────────────────────────────────────────────────────

    factor_meta = None
    manual_factor = None
    current_data_source = "Climatiq API"
    material_norm = normalize_for_compare(classification_material)

    # ── Granular BOQ/Category-level overrides ──
    # ICE DB 2019 values in kgCO2e/kg
    boq_ef = safe_float((boq_mapping or {}).get("emission_factor"))
    if boq_ef is not None:
        manual_factor = boq_ef
        ef_src = str((boq_mapping or {}).get("emission_factor_source") or "BOQ_mapping").strip()
        current_data_source = f"BOQ_specific:{ef_src}"
    elif category in CATEGORY_EMISSION_OVERRIDES:
        manual_factor = CATEGORY_EMISSION_OVERRIDES[category]
        current_data_source = "ICE_DB_override"

    # Material-level regulator override takes priority over category override
    if material_norm in regulator_catalog:
        reg_entry = regulator_catalog[material_norm]
        if reg_entry["preferred_source"] == "נתון ידני שלי":
            manual_factor = reg_entry["emission_factor"]
            current_data_source = "Regulator Manual"

    emission = None
    factor_id = None
    activity_id = None
    factor_source = None

    if conversion.weight_kg is not None:
        try:
            if manual_factor is not None:
                emission = float(manual_factor) * float(conversion.weight_kg)
                factor_id, activity_id, factor_source = "MANUAL", "MANUAL", "Regulator"
                factor_meta = {"candidate_count": 1, "factor_spread_pct": 0.0, "factor_min": manual_factor,
                               "factor_max": manual_factor, "from_cache": False}
            else:
                emission, factor_id, activity_id, factor_source, factor_meta = estimate_weight_kg(category, float(
                    conversion.weight_kg))
            stats["emission"] = emission
            stats["estimated"] = 1
        except Exception as exc:
            stats["estimate_failed"] = 1
            factor_meta = None
            emission = None
            # Last resort: if category has ICE DB override, use it even after Climatiq failure
            if category in CATEGORY_EMISSION_OVERRIDES:
                fallback_factor = CATEGORY_EMISSION_OVERRIDES[category]
                # Try conversion.weight_kg first
                _fallback_weight = float(conversion.weight_kg) if (conversion.weight_kg and float(conversion.weight_kg) > 0) else None
                # If no weight from conversion, estimate from quantity + UOM defaults
                if _fallback_weight is None and quantity and quantity > 0:
                    if category == "Asphalt":
                        # m2 × default 5cm thickness × 2300 kg/m3 density
                        if assumed_uom == "m2":
                            _fallback_weight = float(quantity) * 0.05 * 2300
                        elif assumed_uom in ("ton", "kg"):
                            _fallback_weight = float(quantity) * (1000 if assumed_uom == "ton" else 1)
                        elif assumed_uom == "m3":
                            _fallback_weight = float(quantity) * 2300
                    else:
                        cfg = DEFAULT_CATEGORY_CONFIG.get(category, {})
                        density = float(cfg.get("density_kg_m3") or 0)
                        if assumed_uom == "m3" and density:
                            _fallback_weight = float(quantity) * density
                if _fallback_weight and _fallback_weight > 0:
                    emission = fallback_factor * _fallback_weight
                    factor_id, activity_id, factor_source = "ICE_DB_fallback", "ICE_DB_fallback", "ICE_DB_fallback"
                    current_data_source = "ICE_DB_fallback"
                    factor_meta = {"candidate_count": 1, "factor_spread_pct": 0.0,
                                   "factor_min": fallback_factor, "factor_max": fallback_factor,
                                   "from_cache": False}
                    stats["estimate_failed"] = 0
                    stats["estimated"] = 1
                    stats["emission"] = emission
                    logger.warning("Used ICE_DB_fallback for %s category=%s weight=%s uom=%s",
                                   material, category, _fallback_weight, assumed_uom)

    reliability_score, reliability_status, reliability_reasons = compute_reliability_score(classification_material,
                                                                                           category, assumed_uom,
                                                                                           conversion if conversion.weight_kg is not None else None,
                                                                                           cls_meta, factor_meta,
                                                                                           threshold, max_candidates,
                                                                                           max_factor_spread_pct)
    review_required = reliability_status != "auto_approved"
    if category and category != "Unknown" and assumed_uom not in {None, "unknown"} and conversion.weight_kg not in {None, 0} and emission is not None and (catalog_mapping or boq_mapping):
        review_required = False
        reliability_status = "auto_approved"
        reliability_reasons = []

    if review_required:
        stats["needs_review"] = 1
        insert_review_row(
            review_id=f"review-{run_id}-{abs(hash((material, boq_code, category, assumed_uom)))}",
            run_id=run_id, source_file=metadata.get("source_file", ""),
            material=material, short_text=material, boq_code=boq_code,
            project_type=metadata.get("project_type", "לא מוגדר"),
            project_name=metadata.get("project_name", metadata.get("source_file", "")),
            suggested_category=category, suggested_uom=assumed_uom,
            suggested_weight_kg=conversion.weight_kg, suggested_emission_factor_id=factor_id,
            classification_method=classification_method, classification_confidence=classification_confidence,
            ai_engineer_1_json=json.dumps(cls_meta.get("ai_engineer_1"), ensure_ascii=False) if cls_meta.get(
                "ai_engineer_1") else None,
            ai_engineer_2_json=json.dumps(cls_meta.get("ai_engineer_2"), ensure_ascii=False) if cls_meta.get(
                "ai_engineer_2") else None,
            reliability_score=reliability_score, reliability_status=reliability_status,
            review_reason='; '.join(reliability_reasons) or category_rule,
            climatiq_candidate_count=(factor_meta or {}).get("candidate_count"),
            climatiq_factor_min=(factor_meta or {}).get("factor_min"),
            climatiq_factor_max=(factor_meta or {}).get("factor_max"),
            factor_spread_pct=(factor_meta or {}).get("factor_spread_pct"),
            conversion_assumption=f"{uom_reason}; {conversion.assumption}",
        )
    else:
        if auto_write_ai_approved:
            maybe_write_learning_rows(material, boq_code, category, assumed_uom, conversion, matched_by,
                                      reliability_score,
                                      "vertex_auto_approved" if classification_method == "vertex_ai" else "system_auto_approved",
                                      locals().get('factor', manual_factor), current_data_source)
        if classification_method == "vertex_ai":
            stats["auto_learned"] = 1

    detail_row = {
        **metadata, "calculation_date": current_time, "material": material,
        "short_text": material, "normalized_material": classification_material, "boq_code": boq_code,
        "category": category, "category_rule": category_rule,
        "classification_method": classification_method, "classification_confidence": classification_confidence,
        "review_required": review_required, "original_quantity": quantity,
        "original_uom": provided_uom, "effective_input_uom": effective_provided_uom, "assumed_uom": assumed_uom,
        "weight_kg": conversion.weight_kg,
        "conversion_factor_used": conversion.factor_used if conversion else None,
        "conversion_assumption": f"{uom_reason}; {conversion.assumption}",
        "quantity_unit": assumed_uom,
        "quantity_kg": conversion.weight_kg,
        "data_source": current_data_source if emission is not None else None,
        "ef_id": factor_id,
        "error_msg": "; ".join(reliability_reasons) if review_required else None,
        "thickness_cm_extracted": thickness_cm, "matched": category not in {None, 'Unknown'},
        "matched_by": matched_by, "excluded": False,
        "annual_reference_material": annual_reference_material,
        "annual_reference_uom": annual_reference_uom,
        "annual_reference_match_type": annual_reference_match_type,
        "status": "estimated" if emission is not None else (
            "conversion_failed" if conversion.weight_kg is None else "estimate_failed"),
        "emission_factor_id": factor_id, "climatiq_activity_id": activity_id,
        "emission_factor_source": current_data_source if emission is not None else "Error",
        "emission_co2e": emission, "error_reason": '; '.join(reliability_reasons) if review_required else None,
        "reliability_score": reliability_score, "reliability_status": reliability_status,
        "climatiq_candidate_count": (factor_meta or {}).get("candidate_count"),
        "climatiq_factor_min": (factor_meta or {}).get("factor_min"),
        "climatiq_factor_max": (factor_meta or {}).get("factor_max"),
        "factor_spread_pct": (factor_meta or {}).get("factor_spread_pct"),
        "ai_engineer_1_json": json.dumps(cls_meta.get("ai_engineer_1"), ensure_ascii=False) if cls_meta.get(
            "ai_engineer_1") else None,
        "ai_engineer_2_json": json.dumps(cls_meta.get("ai_engineer_2"), ensure_ascii=False) if cls_meta.get(
            "ai_engineer_2") else None,
        "source_mode": source_mode,
    }
    return detail_row, stats


def process_dataframe(df: pd.DataFrame, metadata: Dict[str, str], reliability_threshold: Optional[float] = None,
                      settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    grouped, detected_source_mode = aggregate_dataframe(df, requested_source_mode=metadata.get("source_mode"))
    metadata["source_mode"] = detected_source_mode
    regulator_catalog = fetch_regulator_catalog()
    settings = settings or {}

    run_id = metadata["run_id"]
    current_time = datetime.now(timezone.utc).isoformat()
    threshold = reliability_threshold if reliability_threshold is not None else float(
        settings.get("reliability_threshold") or DEFAULT_RELIABILITY_THRESHOLD)
    max_candidates = int(settings.get("max_climatiq_candidates") or DEFAULT_MAX_CLIMATIQ_CANDIDATES)
    max_factor_spread_pct = float(settings.get("max_factor_spread_pct") or DEFAULT_MAX_FACTOR_SPREAD_PCT)
    auto_write_ai_approved = bool(settings.get("auto_write_ai_approved", DEFAULT_AUTO_WRITE_AI_APPROVED))

    detail_rows: List[Dict[str, Any]] = []
    details_already_written = 0
    detail_batch_size = int(os.environ.get("BQ_DETAILS_BATCH_SIZE", "500"))

    def _flush_detail_rows(force: bool = False) -> None:
        nonlocal detail_rows, details_already_written
        if not detail_rows:
            return
        if not force and len(detail_rows) < detail_batch_size:
            return
        append_rows_json(BQ_DETAILS_TABLE, [complete_emissions_detail_row(r, metadata) for r in detail_rows])
        details_already_written += len(detail_rows)
        detail_rows = []
    total_emission = 0.0
    matched_rows = 0
    estimated_rows = 0
    excluded_rows = 0
    unmapped_rows = 0
    conversion_failed_rows = 0
    estimate_failed_rows = 0
    needs_review_rows = 0
    auto_learned_rows = 0
    task_error_rows = 0

    rows_total = int(len(grouped))
    rows_processed_state = {"value": 0, "stage": "Processing source rows in Parallel"}
    max_workers = int(os.environ.get("MAX_WORKERS", "8"))
    heartbeat_seconds = int(os.environ.get("PROGRESS_HEARTBEAT_SECONDS", "60"))
    overall_timeout_seconds = int(os.environ.get("OVERALL_PROCESS_TIMEOUT_SECONDS", "5400"))
    update_interval = get_progress_update_interval(rows_total)
    stop_event = threading.Event()

    def _heartbeat() -> None:
        while not stop_event.wait(heartbeat_seconds):
            try:
                update_processing_run(
                    run_id=run_id,
                    metadata=metadata,
                    rows_processed=rows_processed_state["value"],
                    rows_total=rows_total,
                    current_stage=rows_processed_state["stage"],
                    status="running",
                    finished=False,
                )
            except Exception:
                logger.exception("Heartbeat update failed for run %s", run_id)

    heartbeat_thread = threading.Thread(target=_heartbeat, daemon=True)
    heartbeat_thread.start()

    try:
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(
                    _process_single_row_task,
                    row_tuple, metadata, regulator_catalog, threshold,
                    max_candidates, max_factor_spread_pct, auto_write_ai_approved,
                    run_id, current_time
                )
                for row_tuple in grouped.itertuples(index=False)
            ]

            try:
                for future in as_completed(futures, timeout=overall_timeout_seconds):
                    try:
                        detail_row, stats = future.result()
                        detail_rows.append(detail_row)

                        total_emission += stats["emission"]
                        matched_rows += stats["matched"]
                        estimated_rows += stats["estimated"]
                        excluded_rows += stats["excluded"]
                        unmapped_rows += stats["unmapped"]
                        conversion_failed_rows += stats["conversion_failed"]
                        estimate_failed_rows += stats["estimate_failed"]
                        needs_review_rows += stats["needs_review"]
                        auto_learned_rows += stats["auto_learned"]

                    except Exception as exc:
                        task_error_rows += 1
                        detail_rows.append(complete_emissions_detail_row({
                            **metadata,
                            "calculation_date": current_time,
                            "material": None,
                            "short_text": None,
                            "boq_code": None,
                            "category": "Unknown",
                            "classification_method": "task_exception",
                            "classification_confidence": 0.0,
                            "matched_by": "task_exception",
                            "review_required": True,
                            "status": "task_failed",
                            "error_reason": str(exc)[:2000],
                            "source_mode": metadata.get("source_mode"),
                        }, metadata))
                        logger.exception("Error processing a row in thread pool")

                    _flush_detail_rows(force=False)
                    rows_processed_state["value"] += 1
                    rows_processed = rows_processed_state["value"]
                    if rows_processed % update_interval == 0 or rows_processed == rows_total:
                        rows_processed_state["stage"] = "Processing source rows in Parallel"
                        update_processing_run(
                            run_id=run_id,
                            metadata=metadata,
                            rows_processed=rows_processed,
                            rows_total=rows_total,
                            current_stage=rows_processed_state["stage"],
                            status="running",
                            finished=False,
                        )

            except FuturesTimeoutError:
                logger.exception("Overall processing timeout for run %s", run_id)
                for f in futures:
                    f.cancel()
                raise TimeoutError(f"Processing timed out after {overall_timeout_seconds} seconds")

    finally:
        stop_event.set()
        heartbeat_thread.join(timeout=2)

    _flush_detail_rows(force=True)

    summary_row = {
        "run_id": run_id, "calculation_date": current_time,
        "source_file": metadata.get("source_file"), "source_bucket": metadata.get("source_bucket"),
        "uploader_email": metadata.get("uploader_email", "unknown@netivei.co.il"),
        "project_type": metadata.get("project_type", "לא מוגדר"),
        "project_name": metadata.get("project_name"), "total_rows": rows_total,
        "matched_rows": matched_rows, "estimated_rows": estimated_rows,
        "excluded_rows": excluded_rows, "unmapped_rows": unmapped_rows,
        "conversion_failed_rows": conversion_failed_rows, "estimate_failed_rows": estimate_failed_rows,
        "needs_review_rows": needs_review_rows, "auto_learned_rows": auto_learned_rows,
        "task_error_rows": task_error_rows,
        "total_emission_co2e": total_emission, "reliability_threshold": threshold,
        "max_climatiq_candidates": max_candidates, "max_factor_spread_pct": max_factor_spread_pct,
        "auto_write_ai_approved": auto_write_ai_approved,
        "source_mode": metadata.get("source_mode"),
        "measurement_basis": metadata.get("measurement_basis"),
    }

    return {
        "summary": summary_row,
        "details": detail_rows,
        "details_already_written": details_already_written,
        "response": {
            "run_id": run_id,
            "total_emission": total_emission,
            "total_rows": rows_total,
            "needs_review_rows": needs_review_rows,
            "auto_learned_rows": auto_learned_rows,
            "task_error_rows": task_error_rows,
            "details_rows_written": details_already_written + len(detail_rows),
        },
    }


# ==========================================================
# BIGQUERY WRITES
# ==========================================================
# BIGQUERY WRITES
# ==========================================================
def filter_rows_to_table_schema(table_id: str, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    allowed_columns = get_table_columns(table_id)
    return [{k: sanitize_for_json(v) for k, v in row.items() if k in allowed_columns} for row in rows]


def append_rows_json(table_id: str, rows: List[Dict[str, Any]], max_retries: int = 3) -> None:
    if not rows:
        return
    import time as _time
    filtered_rows = filter_rows_to_table_schema(table_id, rows)
    last_exc = None
    for attempt in range(1, max_retries + 1):
        try:
            errors = bq_client.insert_rows_json(table_id, filtered_rows)
            if not errors:
                return  # success
            logger.error("BQ insert errors attempt %d/%d for %s: %s", attempt, max_retries, table_id, errors)
        except Exception as exc:
            last_exc = exc
            logger.warning("BQ insert attempt %d/%d failed for %s: %s", attempt, max_retries, table_id, exc)
        if attempt < max_retries:
            _time.sleep(2 ** attempt)  # exponential backoff: 2s, 4s
    raise RuntimeError(f"BigQuery insert failed after {max_retries} attempts for {table_id}: {last_exc or errors}")


def upsert_processing_run_started(metadata: Dict[str, Any], rows_total: int = 0) -> None:
    update_processing_run(
        run_id=metadata["run_id"],
        metadata=metadata,
        rows_processed=0,
        rows_total=int(rows_total or 0),
        progress_pct=0.0,
        current_stage="Starting",
        status="running",
        finished=False,
    )


def insert_processing_run_finished(summary: Dict[str, Any], status: str, error_message: Optional[str] = None) -> None:
    row = {**summary, "status": status, "error_message": error_message,
           "created_at": datetime.now(timezone.utc).isoformat()}
    append_rows_json(BQ_PROCESSING_RUNS_TABLE, [row])


def update_processing_progress(
    run_id: str,
    rows_processed: int,
    rows_total: int,
    current_stage: str = "Processing BOQ rows",
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    progress_pct = round((rows_processed / rows_total) * 100, 2) if rows_total else 0.0

    update_processing_run(
        run_id=run_id,
        metadata=metadata,
        rows_processed=int(rows_processed),
        rows_total=int(rows_total),
        progress_pct=float(progress_pct),
        current_stage=current_stage,
        status="running",
        finished=False,
    )


def finalize_processing_run(
    run_id: str,
    status: str = "completed",
    current_stage: str = "Finished",
    error_message: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    update_processing_run(
        run_id=run_id,
        metadata=metadata,
        current_stage=current_stage,
        status=status,
        error_message=error_message,
        finished=True,
        finished_at=datetime.now(timezone.utc),
    )

# ==========================================================
# ROUTES
# ==========================================================
# @app.route('/manage-db', methods=['POST'])
# def manage_db():
#     from flask import request, jsonify
#     from google.cloud import bigquery
#     import logging
#     
# try:
#     data = request.json or {}
#     action = data.get('action') 
#     project_name = data.get('project_name')
#         
#     client = bigquery.Client()
#     dataset = "argon-ace-483810-n9.netivei_emissions_db"
#     tables = ["emissions_details", "emissions_summary", "review_queue", "processing_runs"]
# 
#     if action == 'delete_project' and project_name:
#         logging.info(f"Deleting project: {project_name} using WRITE_TRUNCATE workaround")
#             
#         # הטריק: בוחרים את כל מה *שלא* שייך לפרויקט, ודורסים את הטבלה כדי לעקוף את חדר ההמתנה
#         for table in tables:
#             query = f"SELECT * FROM `{dataset}.{table}` WHERE project_name != @pid OR project_name IS NULL"
#             job_config = bigquery.QueryJobConfig(
#                 query_parameters=[bigquery.ScalarQueryParameter("pid", "STRING", project_name)],
#                 destination=f"{dataset}.{table}",
#                 write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE
#             )
#             client.query(query, job_config=job_config).result()
#                 
#         return jsonify({"status": "success", "message": f"הפרויקט '{project_name}' נמחק"}), 200
#         
#     return jsonify({"status": "error", "message": "פעולה לא חוקית"}), 400
# 
# except Exception as e:
#     return jsonify({"status": "error", "message": f"שגיאת שרת: {str(e)}"}), 500

@app.get("/health")
def health() -> Any:
    return jsonify({"status": "ok"}), 200


@app.route("/", methods=["POST"])
def process_excel_route() -> Any:
    run_id = f"run-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
    body: Dict[str, Any] = {}
    metadata: Dict[str, Any] = {"run_id": run_id}
    try:
        body = request.get_json(force=True) or {}
        bucket_name = body.get("bucket")
        file_name = body.get("file")

        if not bucket_name or not file_name:
            return jsonify({"error": "bucket/file required"}), 400

        requested_source_mode = body.get("source_mode", SOURCE_MODE_AUTO)
        requested_mode_norm = normalize_for_compare(requested_source_mode)
        annual_aliases = {normalize_for_compare(x) for x in
                          [SOURCE_MODE_ANNUAL, 'annual', 'paid_2025', 'yearly', 'כתב שנתי']}
        measurement_basis = body.get("measurement_basis") or (
            "paid_2025" if requested_mode_norm in annual_aliases else "boq")
        metadata = {
            "run_id": run_id,
            "source_file": file_name,
            "source_bucket": bucket_name,
            "uploader_email": body.get("uploader_email", "unknown@netivei.co.il"),
            "project_name": body.get("project_name", file_name),
            "project_type": body.get("project_type", "לא מוגדר"),
            "contractor": body.get("contractor", "לא מוגדר"),
            "region": body.get("region", "לא מוגדר"),
            "source_mode": requested_source_mode,
            "measurement_basis": measurement_basis,
        }

        ensure_dataset_exists()

        # ── Duplicate check: warn if same file+project already processed ──
        try:
            _dup_sql = f"""
                SELECT COUNT(*) as cnt
                FROM `{BQ_DETAILS_TABLE}`
                WHERE source_file = @fname
                  AND project_name = @proj
                LIMIT 1
            """
            _dup_result = bq_client.query(
                _dup_sql,
                job_config=bigquery.QueryJobConfig(query_parameters=[
                    bigquery.ScalarQueryParameter("fname", "STRING", file_name),
                    bigquery.ScalarQueryParameter("proj",  "STRING", metadata.get("project_name","")),
                ])
            ).result()
            _dup_rows = list(_dup_result)
            if _dup_rows and int(_dup_rows[0].cnt) > 0:
                logger.warning(
                    "DUPLICATE WARNING: file=%s project=%s already has %d rows in DB",
                    file_name, metadata.get("project_name"), int(_dup_rows[0].cnt)
                )
                # Return error to caller — they must explicitly pass force=true to override
                if not body.get("force_reprocess", False):
                    return jsonify({
                        "error": "duplicate_file",
                        "message": f"הקובץ '{file_name}' כבר עובד עבור פרויקט '{metadata.get('project_name')}'. "
                                   f"העבר force_reprocess=true כדי לעבד שוב.",
                        "existing_rows": int(_dup_rows[0].cnt),
                    }), 409
        except Exception as _dup_exc:
            logger.warning("Duplicate check failed (non-blocking): %s", _dup_exc)
            # Non-blocking — continue processing even if check fails

        # Warm caches once per run.
        load_boq_code_mapping_rows.cache_clear()
        load_catalog_mapping_rows.cache_clear()
        load_boq_code_mapping_rows()
        load_catalog_mapping_rows()
        load_unit_conversion_rules()
        load_materials_catalog()
        load_concrete_pipe_catalog()
        load_cable_cross_section_catalog()

        df = read_input_from_gcs(bucket_name, file_name, run_id)
        persist_annual_paid_items_2025_raw(df, metadata, requested_source_mode=requested_source_mode)

        update_processing_run(
            run_id=run_id,
            metadata=metadata,
            rows_processed=0,
            rows_total=len(df),
            progress_pct=20,
            current_stage='File loaded and normalized',
            status="running",
            finished=False,
            extra_fields={"rows_in_file": len(df)},
        )

        runtime_settings = {
            "reliability_threshold": body.get("reliability_threshold"),
            "max_climatiq_candidates": body.get("max_climatiq_candidates"),
            "max_factor_spread_pct": body.get("max_factor_spread_pct"),
            "auto_write_ai_approved": body.get("auto_write_ai_approved"),
        }
        result = process_dataframe(df, metadata, reliability_threshold=body.get("reliability_threshold"),
                                   settings=runtime_settings)

        update_processing_run(
            run_id=run_id,
            metadata=metadata,
            rows_processed=len(df),
            rows_total=len(df),
            progress_pct=96,
            current_stage='Writing results',
            status="running",
            finished=False,
            extra_fields={"rows_in_file": len(df)},
        )

        append_rows_json(BQ_SUMMARY_TABLE, [result["summary"]])
        if result.get("details"):
            append_rows_json(BQ_DETAILS_TABLE, result["details"])

        update_processing_run(
            run_id=run_id,
            metadata=metadata,
            rows_processed=len(df),
            rows_total=len(df),
            progress_pct=100,
            current_stage='Finished successfully',
            status='completed',
            error_message=None,
            finished=True,
            finished_at=datetime.now(timezone.utc),
            extra_fields={
                "rows_in_file": len(df),
                "grouped_rows": result["summary"].get("total_rows"),
                "estimated_rows": result["summary"].get("estimated_rows"),
                "excluded_rows": result["summary"].get("excluded_rows"),
                "unmapped_rows": result["summary"].get("unmapped_rows"),
                "conversion_failed_rows": result["summary"].get("conversion_failed_rows"),
                "estimate_failed_rows": result["summary"].get("estimate_failed_rows"),
                "needs_review_rows": result["summary"].get("needs_review_rows"),
                "total_emission_co2e": result["summary"].get("total_emission_co2e"),
            },
        )

        return jsonify(result["response"]), 200

    except Exception as exc:
        logger.exception("Unhandled error in process_excel_route")
        update_processing_run(
            run_id=run_id,
            metadata=metadata,
            current_stage='Failed',
            status='failed',
            error_message=str(exc),
            finished=True,
            finished_at=datetime.now(timezone.utc),
        )
        return jsonify({"error": str(exc), "trace": traceback.format_exc(), "run_id": run_id}), 500


@app.get("/review-items")
def review_items() -> Any:
    try:
        status = request.args.get("status", "pending")
        query = f"SELECT * FROM `{BQ_REVIEW_QUEUE_TABLE}` WHERE review_status = @status ORDER BY updated_at DESC LIMIT 500"
        job = bq_client.query(query, job_config=bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("status", "STRING", status)]))
        rows = [sanitize_for_json(dict(r.items())) for r in job.result()]
        return jsonify({"items": rows}), 200
    except Exception as exc:
        logger.exception("Failed loading review items")
        return jsonify({"error": str(exc)}), 500  # <--- יישרתי אותה שמאלה ב-4 רווחים

def _approve_to_learning_tables(item: Dict[str, Any], approver: str, mode: str = "manual_review") -> None:
    category = item.get("approved_category") or item.get("suggested_category")
    assumed_uom = item.get("approved_uom") or item.get("suggested_uom")
    material = item.get("material") or item.get("short_text")
    boq_code = item.get("boq_code")
    conversion_value = safe_float(item.get("approved_conversion_value") or item.get("suggested_conversion_value"))
    conversion_basis = item.get("approved_conversion_basis") or item.get("suggested_conversion_basis")
    if category and assumed_uom and material:
        mapping_row = {
            "mapping_id": f"REV-{abs(hash((material, category, assumed_uom)))}",
            "exact_material": material,
            "material_regex": None,
            "boq_code": boq_code,
            "category": category,
            "forced_uom": assumed_uom,
            "confidence": 1.0,
            "notes": f"Approved by {approver} via {mode}",
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        append_rows_json(BQ_MAPPING_TABLE, [mapping_row])
        if boq_code:
            append_rows_json(BQ_BOQ_MAPPING_TABLE, [{
                "boq_map_id": f"REV-BQ-{abs(hash((boq_code, category, assumed_uom)))}",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "is_active": True,
                "boq_code": boq_code,
                "boq_code_prefix": boq_code.split('.')[0] if '.' in boq_code else boq_code,
                "category": category,
                "forced_uom": assumed_uom,
                "notes": f"Approved by {approver} via {mode}",
                "source": mode,
                "created_by": approver,
            }])
        if conversion_value is not None:
            append_rows_json(BQ_UNIT_RULES_TABLE, [{
                "rule_id": f"REV-UCR-{abs(hash((category, assumed_uom, conversion_value)))}",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "is_active": True,
                "category": category,
                "material_regex": re.escape(str(material)[:100]),
                "input_uom": assumed_uom,
                "output_uom": "kg",
                "density_kg_m3": conversion_value if conversion_basis == "density_kg_m3" else None,
                "kg_per_meter": conversion_value if conversion_basis == "kg_per_meter" else None,
                "kg_per_unit": conversion_value if conversion_basis == "kg_per_unit" else None,
                "kg_per_m2": conversion_value if conversion_basis == "kg_per_m2" else None,
                "kg_per_m2_per_cm": conversion_value if conversion_basis == "kg_per_m2_per_cm" else None,
                "notes": f"Approved by {approver} via {mode}",
                "source": mode,
                "created_by": approver,
            }])


@app.post("/review/approve")
def review_approve() -> Any:
    try:
        body = request.get_json(force=True) or {}
        review_id = body.get("review_id")
        approver = body.get("reviewed_by", "regulator")
        if not review_id:
            return jsonify({"error": "review_id required"}), 400
        _approve_to_learning_tables(body, approver)
        query = f"UPDATE `{BQ_REVIEW_QUEUE_TABLE}` SET review_status = 'approved', reviewed_by = @reviewed_by, reviewed_at = CURRENT_TIMESTAMP(), approved_category = @approved_category, approved_uom = @approved_uom, approved_conversion_basis = @approved_conversion_basis, approved_conversion_value = @approved_conversion_value WHERE review_id = @review_id"
        job_config = bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("reviewed_by", "STRING", approver),
            bigquery.ScalarQueryParameter("approved_category", "STRING",
                                          body.get("approved_category") or body.get("suggested_category")),
            bigquery.ScalarQueryParameter("approved_uom", "STRING",
                                          body.get("approved_uom") or body.get("suggested_uom")),
            bigquery.ScalarQueryParameter("approved_conversion_basis", "STRING",
                                          body.get("approved_conversion_basis") or body.get(
                                              "suggested_conversion_basis")),
            bigquery.ScalarQueryParameter("approved_conversion_value", "FLOAT64", safe_float(
                body.get("approved_conversion_value") or body.get("suggested_conversion_value"))),
            bigquery.ScalarQueryParameter("review_id", "STRING", review_id),
        ])
        bq_client.query(query, job_config=job_config).result()
        return jsonify({"status": "approved", "review_id": review_id}), 200
    except Exception as exc:
        logger.exception("Failed approving review item")
        return jsonify({"error": str(exc)}), 500


@app.post("/review/reject")
@app.post("/review/reject")
def review_reject() -> Any:
    try:
        body = request.get_json(force=True) or {}
        review_id = body.get("review_id")
        if not review_id:
            return jsonify({"error": "review_id required"}), 400
        query = f"UPDATE `{BQ_REVIEW_QUEUE_TABLE}` SET review_status = 'rejected', reviewed_by = @reviewed_by, reviewed_at = CURRENT_TIMESTAMP(), review_notes = @review_notes WHERE review_id = @review_id"
        job_config = bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("reviewed_by", "STRING", body.get("reviewed_by", "regulator")),
            bigquery.ScalarQueryParameter("review_notes", "STRING", body.get("review_notes")),
            bigquery.ScalarQueryParameter("review_id", "STRING", review_id),
        ])
        bq_client.query(query, job_config=job_config).result()
        return jsonify({"status": "rejected", "review_id": review_id}), 200
    except Exception as exc:
        logger.exception("Failed rejecting review item")
        return jsonify({"error": str(exc)}), 500


# ====================================================================
# הבלוק שהיה חסר: הפונקציה למחיקת פרויקט (עם עקיפת ה-Streaming Buffer)
# ====================================================================
# --- סוף הקובץ הקיים שלך ---
@app.route('/manage-db', methods=['POST'])
def manage_db():
    from flask import request, jsonify
    from google.cloud import bigquery
    import logging
    import traceback

    logger = logging.getLogger(__name__)

    try:
        data = request.get_json(force=True) or {}
        action = data.get('action')
        project_name = data.get('project_name')

        if action == 'delete_project' and project_name:
            client = bigquery.Client()
            dataset = "argon-ace-483810-n9.netivei_emissions_db"
            tables = ["emissions_details", "emissions_summary", "review_queue", "processing_runs"]

            for table in tables:
                query = f"DELETE FROM `{dataset}.{table}` WHERE project_name = @pid"
                job_config = bigquery.QueryJobConfig(
                    query_parameters=[bigquery.ScalarQueryParameter("pid", "STRING", project_name)]
                )
                client.query(query, job_config=job_config).result()
                
            return jsonify({"status": "success", "message": f"הפרויקט '{project_name}' נמחק בהצלחה"}), 200
        
        return jsonify({"status": "error", "message": "פעולה לא חוקית או חסר שם פרויקט"}), 400

    except Exception as e:
        logger.error(traceback.format_exc())
        return jsonify({"status": "error", "message": str(e)}), 500

# ====================================================================
# AUTH ENDPOINT
# ====================================================================
_BQ_USERS_TABLE = f"{BQ_PROJECT_ID}.{DATASET_ID}.users"
_BQ_DETAILS_TABLE_FULL = f"{BQ_PROJECT_ID}.{DATASET_ID}.emissions_details"
_BQ_DETAILS_VIEW_FULL = f"{BQ_PROJECT_ID}.{DATASET_ID}.emissions_details_view"
_BQ_PROCESSING_RUNS_FULL = f"{BQ_PROJECT_ID}.{DATASET_ID}.processing_runs"


@app.post("/auth/login")
def auth_login():
    try:
        body = request.get_json(force=True) or {}
        email = (body.get("email") or "").strip().lower()
        password = body.get("password") or ""
        if not email or not password:
            return jsonify({"error": "חסר אימייל או סיסמה"}), 400
        query = f"SELECT email, name, role, password, is_first_login FROM `{_BQ_USERS_TABLE}` WHERE LOWER(email)=@e LIMIT 1"
        job = bq_client.query(query, job_config=bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("e", "STRING", email)]))
        rows = list(job.result())
        if not rows:
            return jsonify({"error": "משתמש לא נמצא"}), 401
        user = dict(rows[0].items())
        if user.get("password") != password:
            return jsonify({"error": "סיסמה שגויה"}), 401
        return jsonify({
            "email": user.get("email"),
            "name": user.get("name"),
            "role": user.get("role"),
            "is_first_login": bool(user.get("is_first_login")),
        }), 200
    except Exception as exc:
        logger.exception("auth/login failed")
        return jsonify({"error": str(exc)}), 500


@app.post("/auth/change-password")
def auth_change_password():
    try:
        body = request.get_json(force=True) or {}
        email = (body.get("email") or "").strip().lower()
        new_password = body.get("new_password") or ""
        if not email or len(new_password) < 4:
            return jsonify({"error": "סיסמה חייבת להיות לפחות 4 תווים"}), 400
        bq_client.query(
            f"UPDATE `{_BQ_USERS_TABLE}` SET password=@p, is_first_login=FALSE WHERE LOWER(email)=@e",
            job_config=bigquery.QueryJobConfig(query_parameters=[
                bigquery.ScalarQueryParameter("p", "STRING", new_password),
                bigquery.ScalarQueryParameter("e", "STRING", email),
            ])
        ).result()
        return jsonify({"ok": True}), 200
    except Exception as exc:
        logger.exception("auth/change-password failed")
        return jsonify({"error": str(exc)}), 500


# ====================================================================
# EMISSIONS ENDPOINT
# ====================================================================
@app.get("/emissions")
def emissions():
    try:
        try:
            query = f"SELECT * FROM `{_BQ_DETAILS_VIEW_FULL}` ORDER BY calculation_date DESC LIMIT 2000"
            job = bq_client.query(query)
            rows = [sanitize_for_json(dict(r.items())) for r in job.result()]
        except Exception:
            query = f"SELECT * FROM `{_BQ_DETAILS_TABLE_FULL}` ORDER BY calculation_date DESC LIMIT 2000"
            job = bq_client.query(query)
            rows = [sanitize_for_json(dict(r.items())) for r in job.result()]
        return jsonify({"items": rows}), 200
    except Exception as exc:
        logger.exception("emissions failed")
        return jsonify({"error": str(exc)}), 500


# ====================================================================
# PROCESSING STATUS ENDPOINT
# ====================================================================
@app.get("/processing/status")
def processing_status():
    try:
        active_q = f"""
            SELECT * FROM `{_BQ_PROCESSING_RUNS_FULL}`
            WHERE status IN ('running','processing','in_progress','started')
              AND created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 12 HOUR)
            ORDER BY created_at DESC LIMIT 1
        """
        job = bq_client.query(active_q)
        rows = list(job.result())
        if not rows:
            job2 = bq_client.query(
                f"SELECT * FROM `{_BQ_PROCESSING_RUNS_FULL}` ORDER BY created_at DESC LIMIT 1")
            rows = list(job2.result())
        if not rows:
            return jsonify({"run": None}), 200
        run = sanitize_for_json(dict(rows[0].items()))
        return jsonify({"run": run}), 200
    except Exception as exc:
        logger.exception("processing/status failed")
        return jsonify({"error": str(exc)}), 500


# ====================================================================
# AI CHAT ENDPOINT
# ====================================================================
@app.post("/ai/chat")
def ai_chat():
    try:
        body = request.get_json(force=True) or {}
        messages = body.get("messages", [])
        context = body.get("context", "")
        if not messages:
            return jsonify({"error": "חסרות הודעות"}), 400

        contents = [
            {"role": ("user" if m["role"] == "user" else "model"), "parts": [{"text": m["content"]}]}
            for m in messages
        ]
        cfg = types.GenerateContentConfig(system_instruction=context or "אתה עוזר AI מומחה לניתוח פליטות פחמן. ענה בעברית.")

        locations = ["global", "us-central1", "europe-west1"]
        last_err = None
        for loc in locations:
            for attempt in range(3):
                try:
                    client = genai.Client(vertexai=True, project=VERTEX_PROJECT, location=loc)
                    text = client.models.generate_content(
                        model=VERTEX_MODEL, contents=contents, config=cfg
                    ).text
                    return jsonify({"reply": text}), 200
                except Exception as e:
                    last_err = e
                    if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                        import time as _time
                        _time.sleep(2 ** attempt)
                        continue
                    break
        return jsonify({"error": f"AI לא זמין: {last_err}"}), 503
    except Exception as exc:
        logger.exception("ai/chat failed")
        return jsonify({"error": str(exc)}), 500


# ====================================================================
# PROJECTS LIST ENDPOINT
# ====================================================================
@app.get("/projects")
def projects_list():
    try:
        query = f"SELECT DISTINCT project_name FROM `{_BQ_DETAILS_TABLE_FULL}` WHERE project_name IS NOT NULL ORDER BY project_name"
        job = bq_client.query(query)
        names = [r["project_name"] for r in job.result()]
        return jsonify({"projects": names}), 200
    except Exception as exc:
        logger.exception("projects failed")
        return jsonify({"error": str(exc)}), 500


# ====================================================================
# FILE UPLOAD ENDPOINT — uploads file to GCS, then triggers processing
# ====================================================================
@app.route("/upload", methods=["POST"])
def upload_file_endpoint():
    try:
        if "file" not in request.files:
            return jsonify({"error": "no file provided"}), 400

        f = request.files["file"]
        if not f.filename:
            return jsonify({"error": "empty filename"}), 400

        bucket_name = request.form.get("bucket", "green_excal")
        dest_name = f.filename

        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(dest_name)
        blob.upload_from_file(f.stream, content_type=f.content_type or "application/octet-stream")

        logger.info(f"Uploaded {dest_name} to gs://{bucket_name}/{dest_name}")
        return jsonify({"ok": True, "bucket": bucket_name, "file": dest_name}), 200
    except Exception as exc:
        logger.exception("upload failed")
        return jsonify({"error": str(exc)}), 500


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)