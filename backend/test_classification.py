"""
test_classification.py
----------------------
Compares manual corrections from the Google Sheets QA file against the
classification logic inside main.py (pure-Python layer only — no BigQuery/AI).

Tested layers, in pipeline order:
  1. should_exclude()          — EXCLUDE_PATTERNS + MATERIAL_INDICATOR_PATTERNS
  2. hard_classification_override()  — deterministic rule overrides
  3. CATEGORY_RULES            — regex fallback

The BigQuery catalog lookup and Vertex AI are NOT tested here (they require
live credentials), so rows that depend on those will be reported as
"no_local_match" — not as errors.

Usage:
    python backend/test_classification.py
    python backend/test_classification.py --verbose   # show every mismatch
    python backend/test_classification.py --csv path/to/local.csv
"""

import csv
import io
import re
import sys
import unicodedata
import urllib.request
import urllib.error
from typing import Any, Optional, Tuple, List

# Force UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# ── Google Sheets CSV export URL ───────────────────────────────────────────────
SHEET_ID = "1HPUnWBwuiew3Lnw_BV6IUGFZRCp12R1fxCveIplants"
SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"

# ── Column name candidates (try each until one is found) ────────────────────────
COL_CORRECT   = ["קטגוריה נכונה", "correct_category", "correct", "נכונה"]
COL_DETECTED  = ["קטגוריה שזוהתה", "detected_category", "detected", "שזוהתה"]
COL_DESC      = ["תיאור", "description", "material", "תאור", "טקסט קצר"]
COL_BOQ       = ["קוד", "boq_code", "סעיף", "code", "item_code"]

# ── Replicated constants from main.py ─────────────────────────────────────────
HEBREW_QUOTES = str.maketrans({"׳": "'", "״": '"'})


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    text = text.replace("\xa0", " ").replace("‏", " ").replace("‎", " ")
    text = unicodedata.normalize("NFC", text)
    text = text.strip().translate(HEBREW_QUOTES)
    text = re.sub(r"\s+", " ", text)
    if text.lower() in {"nan", "none", "null", "nat", ""}:
        return ""
    return text


FINANCIAL_ADJUSTMENT_PATTERNS = [
    r"ניכוי(?:ים)?", r"קנס(?:ות)?", r"קיזוז(?:ים)?", r"זיכוי(?:ים)?",
    r"חיוב(?:ים)?", r'לו[\"׳\']?ז', r"ליקויי\s*בטיחות",
    r"ליקויי\s*הבטחת\s*איכות", r"מנהל\s*פרויקט",
]

MATERIAL_INDICATOR_PATTERNS = [
    r"בטון", r"בטקל", r"CLSM", r"אספלט", r"מצע", r"סומסום", r"שומשום",
    r"חול", r"אגרגט", r"חצץ", r"יריע[התו]?\s+ביטומני", r"אמולסי",
    r"תחליב\s*ביטומני", r"ברזל\s*זיון", r"פלדה", r"PVC", r"HDPE",
    r"פוליאתילן", r"PE100", r"N2XY", r"XLPE", r"כבל", r"נחושת", r"צינור",
]

EXCLUDE_PATTERNS = [
    r"\bפ[י]?רוק\b", r"\bפוליסטר[ין]\b", r"\bEPS\b", r"\bXPS\b",
    r"תוספת\s+מחיר", r"תוספת\s+למחיר", r"תוספת\s+לסעיפי\s+צינור",
    r"תוספת\s+לביצוע\s+מחיר", r"\bצביעה\b", r"\bקרצוף\b",
    r"\bתוספת\s*מחיר\b", r"\bגמר\s*פני\b", r"\bעבודה\b", r"\bהשכרה\b",
    r"\bחפירה\b", r"\bבדיק[הת]\b", r"\bמדיד[הות]\b", r"\bתכנון\b",
    r"\bאחזק[הת]\b", r"\bסילוק\b", r"\bקידוח\b", r"\bחציבה\b",
    r"\bשאיבה\b", r"\bגיזום\b", r"\bטיפול\b", r"\bתשלום\b", r"\bפועל\b",
    r"\bמנהל\s*עבודה\b", r"\bיעה\s*אופני\b", r"\bמחפרון\b", r"\bמנוף\b",
    r"\bהעתק[הת]\b", r"\bחישוף\b", r"\bריסוס\b", r"\bעקירת\b",
    r"\bצוות\b", r"\bמשאית\b", r"\bביובית\b", r"\bהסרה\b", r"\bהסרת\b",
    r"\bעבודות\s*עפר\b", r"\bהוצאת\s*עפר\b", r"\bפינוי\s*עפר\b",
    r"\bעפר\s*עודף\b", r"\bגריפה\b", r"\bעיבוד\s*תשתית\b",
    r"\bחפירת\s*מצעים\b", r"\bדחיסת?\s*(?:קרקע|עפר|מצע)\b",
    r"\bהכנת\s*(?:תשתית|קרקע)\b", r"\bפיזור\b",
    r"\bאספקה\s*ופיזור\b",
    r"\bניקוי\s*(?:תעלות?|מערכות?|צינורות?)\b",
]

_excl_compiled = [re.compile(p, re.IGNORECASE) for p in EXCLUDE_PATTERNS]
_mat_compiled  = [re.compile(p, re.IGNORECASE) for p in MATERIAL_INDICATOR_PATTERNS]
_fin_compiled  = [re.compile(p, re.IGNORECASE) for p in FINANCIAL_ADJUSTMENT_PATTERNS]


def should_exclude(text: str) -> bool:
    text = normalize_text(text)
    if not text:
        return True
    for p in _fin_compiled:
        if p.search(text):
            return True
    has_material = any(p.search(text) for p in _mat_compiled)
    if has_material:
        return False
    return any(p.search(text) for p in _excl_compiled)


def hard_classification_override(material_text: str) -> Optional[str]:
    text = normalize_text(material_text)

    if re.search(r"זכוכית|טריפלקס", text, re.IGNORECASE):
        return "Glass"
    # ארגז הסתעפות ואבטחה = metal security/junction box → Galvanized Steel
    if re.search(r"ארגז\s*הסתעפות\s*ואבטחה", text, re.IGNORECASE):
        return "Galvanized Steel"
    # ארגז הסתעפות = simple junction box = service item
    if re.search(r"ארגז\s*הסתעפות|פרט\s*השקית", text, re.IGNORECASE):
        return "EXCLUDE"
    # Transport+install of manhole covers / signs = labor = EXCLUDE
    if re.search(r"הובלה\s*ו?התקנ[הת]?\s*(?:של\s*)?(?:מכסה\s*(?:לתא)?|תמרור|שלט\s*(?:הוריה|עצור|מגביל)?)", text, re.IGNORECASE):
        return "EXCLUDE"
    # יחידת מעבר בין מעקות = transition unit = service/installation = EXCLUDE
    if re.search(r"יחידת?\s*מעבר\s*(?:ממעקה|בין\s*מעקות?)", text, re.IGNORECASE):
        return "EXCLUDE"
    # Warning signs, sign cover work = service = EXCLUDE
    if re.search(r"שלט\s*אזהרה|הורדת?\s*כיסוי\s*(?:מה)?שלט|מכלול\s*צביעת?", text, re.IGNORECASE):
        return "EXCLUDE"
    # Electrical cabinet with main switch = service item = EXCLUDE
    if re.search(r"ארון.*מפסק\s*ראשי|ארון.*חלוקה.*למעבר", text, re.IGNORECASE):
        return "EXCLUDE"
    # תומך לעץ = tree prop (landscaping service); כריתה/גיזום עץ = tree work service
    if re.search(r"תומך\s*(?:לעץ|ל?עצים)|כריתת?\s*(?:עץ|עצים)|גיזום\s*עץ", text, re.IGNORECASE):
        return "EXCLUDE"
    # ערוגות אבן = stone garden edging → Paving (before Wood check fires on ערוגות עץ)
    if re.search(r"ערוגות\s*(?:עץ\s*)?אבן|אבן\s*(?:גן|ערוגה|מעוגלת)", text, re.IGNORECASE):
        return "Paving"
    # תוספת מחיר with material indicator bypasses should_exclude, catch here before Wood
    # Exception: "תוספת מחיר לבטון/לאספלט" = material quality surcharge → let it fall through
    if re.search(r"תוספת\s+מחיר|תוספת\s+למחיר", text, re.IGNORECASE):
        if not re.search(r"תוספת\s+מחיר\s+ל(?:בטון|אספלט|מצע)", text, re.IGNORECASE):
            return "EXCLUDE"
    if re.search(r"\bעץ\b|אורן|קורות\s*עץ|לביד|סנדוויץ", text, re.IGNORECASE):
        # עץ as secondary reference (wooden pole hardware, mixed materials, wooden pole ops) → skip Wood
        if not re.search(r"(?:ל|מ|על|עם)\s*עמוד[י]?\s*עץ|עמוד[י]?\s*(?:תאורה\s*)?(?:פלדה\s*(?:או\s*)?)?עץ|פלדה\s*(?:או\s*)?עץ|\bועץ\b", text, re.IGNORECASE):
            return "Wood"
    # תכנון וביצוע (design+build service contract) → EXCLUDE
    if re.search(r"תכנון\s*ו?ביצוע|ביצוע\s*ו?תכנון", text, re.IGNORECASE):
        return "EXCLUDE"
    # מתקן הארקת יסוד = foundation grounding bracket = service, not material
    if re.search(r"מתקן\s*הארקת?\s*(?:יסוד|מעקה|גדר)", text, re.IGNORECASE):
        return "EXCLUDE"
    # Service operations that must fire even with material indicator present
    if re.search(r"\bקרצוף\b|\bחספוס\b", text, re.IGNORECASE):
        return "EXCLUDE"
    if re.search(r"פתיחת\s*(?:כביש|מדרכה|אספלט)", text, re.IGNORECASE):
        return "EXCLUDE"
    if re.search(r"ניסור\s*(?:אספלט|כביש|בטון)", text, re.IGNORECASE):
        return "EXCLUDE"
    if re.search(r"תוספת\s+לכל\s+\d|תוספת\s+ל?(?:כל|יחידת?)\s+(?:\d|ס.?מ)", text, re.IGNORECASE):
        return "EXCLUDE"
    if re.search(r"תיקון\s*(?:משטח\s*)?(?:אספלט|בטונ|ריצוף)", text, re.IGNORECASE):
        return "EXCLUDE"
    # תכנון וביצוע / ת.וביצוע = design+build contract → EXCLUDE (service)
    if re.search(r"תכנון\s*ו?ביצוע|ת\.?\s*ו?ביצוע\s+יסוד", text, re.IGNORECASE):
        return "EXCLUDE"
    if re.search(r"סלעים?\s*מקומיים?\s*(?:מה)?שטח|אבנ[יות]+\s*מקומיות?\s*(?:מה)?שטח", text, re.IGNORECASE):
        return "EXCLUDE"
    if re.search(r"\bתכנות\b|\bתוכנה\b|נקודה\s*דינמית|תוכנת\s*HMI|תוכנת\s*SCADA", text, re.IGNORECASE):
        return "EXCLUDE"
    # חיבור סיב אופטי = fiber optic splicing = service (labeled EXCLUDE in sheet, more rows than Copper Wire)
    if re.search(r"חיבור\s*סיב\s*אופטי|קצות?\s*סיב\s*אופטי", text, re.IGNORECASE):
        return "EXCLUDE"
    if re.search(r"\bמילוי\s*חוזר\b", text, re.IGNORECASE):
        return "EXCLUDE"
    # Foundation grounding exit/work = service (electrical grounding in concrete structure)
    if re.search(r"יציאה\s*חיצונית.*הארקת?\s*יסוד|ביצוע\s*הארקת?\s*יסוד", text, re.IGNORECASE):
        return "EXCLUDE"
    # יחידת כוורת = honeycomb unit embedded in concrete = prefab item → EXCLUDE
    if re.search(r"יחידת?\s*כוורת", text, re.IGNORECASE):
        return "EXCLUDE"
    # יחידת דיזל foundation = service item; also diesel unit itself
    if re.search(r"יחידת?\s*דיזל", text, re.IGNORECASE):
        return "EXCLUDE"
    # יסוד/גומחת בטון למרכזיה (switchboard) = electrical service item = EXCLUDE
    if re.search(r"(?:יסוד|גומחת?)\s*בטון.*מרכזיה|מרכזיה.*(?:יסוד|גומחת?)\s*בטון", text, re.IGNORECASE):
        return "EXCLUDE"
    # שרוול מצינור בטון\פלדה = supply-only concrete/steel pipe sleeve = EXCLUDE (not PE/PVC sleeves)
    if re.search(r"שרוול\s*מצינור\s*(?:בטון|פלדה)|שרוול\s*(?:בטון|פלדה)", text, re.IGNORECASE):
        return "EXCLUDE"
    # תיקון קו מים = repairing water/utility line = service = EXCLUDE
    if re.search(r"תיקון\s*(?:קו\s*(?:מים|ביוב|גז)|צינור\s*(?:מים|ביוב))", text, re.IGNORECASE):
        return "EXCLUDE"
    # Service connections (to existing unit = labor, NOT new pipe installation)
    if re.search(r"התחברות\s*(?:צינור|קו)\s*(?:ניקוז|ביוב)|חבור\s*קו\s*(?:ביוב|מים)", text, re.IGNORECASE):
        return "EXCLUDE"
    # שוחת מגוף = valve access pit = service/civil structure = EXCLUDE
    if re.search(r"שוחת?\s*מגוף(?!\s*(?:ביקורת|בקרה))", text, re.IGNORECASE):
        return "EXCLUDE"
    # הכנת (קירות/פני) לאיטום = wall/surface preparation service = EXCLUDE
    if re.search(r"הכנת\s*(?:פני\s*)?(?:קירות?|הבטון|משטח)\s*ל?(?:איטום|צביעה|ריצוף)", text, re.IGNORECASE):
        return "EXCLUDE"
    # IP ingress protection rating = transport/handling of cabinet = EXCLUDE (not the material box)
    if re.search(r"(?:הובלת?|העברת?|הזזת?)\s*(?:תא|ארון|קופסה).*(?:דרגת?\s*(?:איטום|הגנה)\s*IP|IP\d+)", text, re.IGNORECASE):
        return "EXCLUDE"
    # גילוי/חשיפת מתקנים קיימים = uncovering existing utilities = service
    if re.search(r"גילוי\s*(?:תאי?|קווי?|מסלול|מתקן)", text, re.IGNORECASE):
        return "EXCLUDE"
    # Agricultural/landscaping supplies = organic, not construction material → EXCLUDE
    if re.search(
        r"קרקע\s*חקלאית|פקעות?\s+ובצלים?|בצלים?\s+ופקעות?|מרבדי?\s*דשא|"
        r"הטמנת?\s*(?:פקעות?|בצלים?)|ערוגות?\s*(?:כלואות?|פרחים?)|"
        r"שתיל(?:ה|ים|ות)\s+(?:עצים|שיחים|זרעים|פרחים)|"
        r"זריעת?\s*דשא|דשא\s*(?:מכל\s*סוג|טבעי|מלאכותי)|קומפוסט",
        text, re.IGNORECASE,
    ):
        return "EXCLUDE"
    # צילום קו ביוב/מים/ניקוז = CCTV pipe inspection = service
    if re.search(r"צילום\s*קו\s*(?:ביוב|מים|ניקוז)|צילום.*מצלמת\s*(?:וידאו|CCTV)", text, re.IGNORECASE):
        return "EXCLUDE"
    # ניקוז תת אספלטי = collectors for drainage under asphalt = PVC pipe
    if re.search(r"ניקוז\s*תת\s*אספלטי|קולטנים?\s*(?:ל|ו?)?ניקוז", text, re.IGNORECASE):
        return "PVC Pipe"
    # השלמת תשתית בתעלות = completing infrastructure in conduits = service = EXCLUDE
    if re.search(r"השלמת\s*תשתית\s*ב?תעלות?", text, re.IGNORECASE):
        return "EXCLUDE"

    # Precast pits built from blocks (cable marker pits, inspection pits)
    if re.search(r"שוח[הות]{1,2}.*בלוקים|בלוקים.*שוח[הות]{1,2}", text, re.IGNORECASE):
        return "Precast Concrete"
    # Concrete niche/foundation for meter box or utility pillar = precast structure
    if re.search(r"(?:גומחת?|יסוד)\s*בטון.*(?:תא\s*מנייה|פילר\s*מונים)", text, re.IGNORECASE):
        return "Precast Concrete"
    # Concrete bench = precast street furniture
    if re.search(r"ספסל\s*(?:מבטון|בטון)", text, re.IGNORECASE):
        return "Precast Concrete"
    # Concrete ceiling panel for existing junction box = precast element
    if re.search(r"תקרת\s*בטון\s*לתא\s*מעבר", text, re.IGNORECASE):
        return "Precast Concrete"
    # שוחת ביקורת rule: concrete pad FOR the pit is Structural, the pit itself is Precast
    # PE/HDPE pits (פוליאתילן) are HDPE, not Precast
    if re.search(r"שוח[הות]{1,2}\s*(?:בקרה|ביקורת)|חוליות?\s*טרומיות?|מנהול\s*טרומי", text, re.IGNORECASE):
        if not re.search(r"משטח\s*(?:מ|ב)?בטון\s*לשוחת?", text, re.IGNORECASE):
            if not re.search(r"פולי[אא]?[תט]ילן|פולי.?א[תט]ילן|\bHDPE\b|\bPE\d", text, re.IGNORECASE):
                return "Precast Concrete"
    if re.search(r"חפירת?\s*מצעים?\b", text, re.IGNORECASE):
        return "EXCLUDE"
    if (re.search(r"(?:מסילה|פסי?\s*רכבת)", text, re.IGNORECASE) and
            re.search(r"(?:הרכבה|הנחה|התקנה|הובלה)", text, re.IGNORECASE)):
        return "EXCLUDE"
    if re.search(r"וויסות\s*לחץ\s*(?:עבור|ל)\s*מסילה", text, re.IGNORECASE):
        return "EXCLUDE"
    if re.search(r"ארגז[יות]*\s*פוליסטירן|פוליסטירן\s*(?:ברוחב|בגובה|בעובי|מוקצף\s*ב)", text, re.IGNORECASE):
        return "HDPE Granulate"
    if re.search(r"לוחות?\s*פוליסטירן\s*מוקצף\s*ב|פוליסטירן\s*מוקצף.*באלמנ", text, re.IGNORECASE):
        return "HDPE Granulate"
    if re.search(r"קופינג|חיפוי\s*(?:קיר|קירות?|חוץ)?\s*(?:ב)?לוחות?\s*אבן\s*כורכרית?", text, re.IGNORECASE):
        return "Paving"
    if re.search(r"אבן\s*גן\s*ב(?:גוון|מידות)|נדבכי?\s*ראש.*כורכרית?", text, re.IGNORECASE):
        return "Paving"

    if re.search(r"קופסת?\s*(?:פלסטיק|הסתעפות)|קופסת?\s*חיבורים?\s*(?:מפלסטיק|IP\d+)", text, re.IGNORECASE):
        return "EXCLUDE"
    if re.search(r"גיאו.?תא|geocell|כוורות?\s*גיאוטכניות?", text, re.IGNORECASE):
        return "HDPE Granulate"
    # פוליגל as primary material in description start = PVC (not when listed among acrylic options)
    if re.search(r"^לוחות?\s*פוליגל|פוליגל\s*בעובי", text, re.IGNORECASE):
        return "PVC Pipe"
    # תוספת לצינורות/לביצוע הנחת = unit supplement for pipe work = EXCLUDE (before HDPE/PE rule)
    if re.search(r"תוספת\s+ל(?:צינורות?|ביצוע\s*הנחת?|כל\s*מד)", text, re.IGNORECASE):
        return "EXCLUDE"
    if re.search(r"\bHDPE\b|H\.D\.P\.E|פוליאתילן|פולי.?אתילן|\bPE100\b|\bPE-100\b", text, re.IGNORECASE):
        return "HDPE Granulate"
    # מריכף = corrugated PVC conduit pipe (must precede "צינור פלסטי" → HDPE)
    if re.search(r"מריכף", text, re.IGNORECASE):
        return "PVC Pipe"
    if re.search(r"(?:צינור|קורגל)\s*(?:פלסטי|גמיש)\s*(?:דו.?שכבתי|שרשורי)?|פלסטי\s*שרשורי", text, re.IGNORECASE):
        return "HDPE Granulate"
    # חול מיוצב = stabilized sand = aggregate material = Crushed Stone (not Fill)
    if re.search(r"חול\s*מיוצב", text, re.IGNORECASE):
        return "Crushed Stone"
    # מילוי מובא לגשרים/מבנים = brought fill for structures (aggregate A/B/C type) = Crushed Stone
    if re.search(r"מילוי\s*מובא\s*ל(?:מבנ|גשר)", text, re.IGNORECASE):
        return "Crushed Stone"
    if re.search(r"מיוצב\s*ב?[צס]מנט|אדמה\s*מיוצבת|תשחיף\s*מיוצב|מיוצב\s*ב?סיד", text, re.IGNORECASE):
        return "Fill Material"
    if re.search(r"פייבר\s*צמנט|fiber\s*cement|צמנטבורד|לוחות?\s*(?:פייבר|fiber)", text, re.IGNORECASE):
        return "Precast Concrete"
    if re.search(r"\bגראוט\b|\bgrout\b|חומר\s*גרוט|סיקה\s*גראוט", text, re.IGNORECASE):
        return "Cementitious Mortar"
    if re.search(r"בטון\s*(?:צמנטי|להטלאה|לאיטום|מחוזק|מהיר)|יציקת\s*(?:הטלאה|תיקון)", text, re.IGNORECASE):
        return "Structural Concrete"
    if re.search(r"טיח\s*הידראולי|סיקה\s*טופ\s*\d", text, re.IGNORECASE):
        return "Cementitious Mortar"
    if re.search(r"מלט|מלת|טיט|מרגמה|רובה|דייס|צמנט", text, re.IGNORECASE):
        return "Cementitious Mortar"
    # concrete trash cans = prefab non-structural items = EXCLUDE; metal ones → AI
    if re.search(r"אשפתון.*(?:מבטון|בטון\s*אדריכלי)|פח\s*אשפות?\s*מבטון", text, re.IGNORECASE):
        return "EXCLUDE"
    if re.search(r"אלומיניום|אלומניום|פרופיל\s*אלומ", text, re.IGNORECASE):
        return "Aluminum"
    # Service operations on lighting/traffic poles = EXCLUDE (bypass material indicator)
    if re.search(r"צביע[את]?\s.*(?:עמוד|פנס)|(?:פרוק|פירוק|ניתוק|התקנ)\s.*(?:עמוד|פנס)\s*תאור[הת]?|החלפת?\s*נורה.*עמוד|העמדת?\s*עמוד.*(?:קיים|שפורק)\b", text, re.IGNORECASE):
        return "EXCLUDE"
    if re.search(r"עמוד\s*(?:פלד|תאורה|מפלד)|עמוד\s*קוני|עמוד\s*בגובה", text, re.IGNORECASE):
        # Don't fire for rectangular concrete foundations (יסוד בטון without עגול)
        if not re.search(r"יסוד\s*(?:מ)?בטון(?!\s*(?:עגול|מעוגל))", text, re.IGNORECASE):
            return "Galvanized Steel"
    # משטח יצוק מבטון = cast concrete slab (primary material is concrete, not rebar)
    if re.search(r"משטח\s*(?:יצוק|בטון)\s*(?:מ)?בטון|משטח\s*מבטון\s*(?:מזויין|ל)", text, re.IGNORECASE):
        return "Structural Concrete"
    # מייתד כימי = chemical dowel rod used in concrete assembly → Structural Concrete
    if re.search(r"מייתד|מוט\s*מייתד|אינסרט\s*להארכת\s*זיון", text, re.IGNORECASE):
        return "Structural Concrete"
    if re.search(r"דיפון\s*קשיח", text, re.IGNORECASE):
        return "Crushed Stone"
    if re.search(r"\bCLSM\b|בטון\s*זורם|בטון\s*נוזלי", text, re.IGNORECASE):
        return "Lean Concrete"
    if re.search(r"הידוק\s*(?:מבוקר|קרקע|יסוד)|גריסה\s*וניפוי|ניפוי\s*וגריסה", text, re.IGNORECASE):
        return "EXCLUDE"
    if re.search(r"\bזריע[הת]?\b|\bזיבול\b|הכשרת\s*קרקע\s*לגינון", text, re.IGNORECASE):
        return "EXCLUDE"
    # Polystyrene in a thermal-insulation context for roofing = Waterproofing (per manual labels)
    if re.search(r"(?:פוליסטירן|EPS|XPS).*בידוד\s*תרמי|בידוד\s*תרמי.*(?:פוליסטירן|EPS|XPS)", text, re.IGNORECASE):
        return "Waterproofing"
    if re.search(r"פוליסטר[ין]|פוליסטי|\bEPS\b|\bXPS\b|סנדוויץ.*בידוד|בידוד.*תרמי", text, re.IGNORECASE):
        return "EXCLUDE"
    # הכנת פני = surface preparation service = EXCLUDE (with or without material indicators)
    if re.search(r"הכנת\s*פני\s*(?:הבטון|קירות?|משטח|המשטח|מיסעת)", text, re.IGNORECASE):
        return "EXCLUDE"
    # בטון ב-20 = lean concrete; must precede CATEGORY_RULES Waterproofing (via "איטום")
    if re.search(r"\bבטון\s*ב.?20\b", text, re.IGNORECASE):
        return "Lean Concrete"
    # גיאוגריד = geogrid reinforcement mesh → HDPE
    if re.search(r"גיאוגריד|geogrids?", text, re.IGNORECASE):
        return "HDPE Granulate"
    # ארג גיאוטכני = woven geotextile = HDPE material; generic geotextile → Waterproofing
    if re.search(r"ארג\s*גיאוטכני|גיאוטקסטיל", text, re.IGNORECASE):
        return "HDPE Granulate"
    # הנחה של יריעות גיאוטכניות = laying geotextile = service (not the material) = EXCLUDE
    if re.search(r"(?:הנחה|אספקה\s*והנחה)\s*(?:של\s*)?(?:יריעות?|בד)\s*גיאוטכניות?", text, re.IGNORECASE):
        return "EXCLUDE"
    # איטום קירות עם לוחות = waterproofing walls with board cladding = service = EXCLUDE
    if re.search(r"איטום\s*קירות?.*מ?לוחות|לוחות.*איטום\s*קירות?", text, re.IGNORECASE):
        return "EXCLUDE"
    if re.search(r"יריע[ות]+\s*ניקוז|גיאוקומפוזיט|geo.?composite", text, re.IGNORECASE):
        return "Waterproofing"
    # Purchased natural boulders with a specified size → Crushed Stone (before local-site check)
    if re.search(r"בולדרים?\s*טבעיים?\s*(?:בקוטר|בגובה|בגודל|במשקל)", text, re.IGNORECASE):
        return "Crushed Stone"
    # Local/natural boulders must come BEFORE generic "בולדר → Crushed Stone" check
    if re.search(r"בולדרים?\s*מאבנים\s*מקומיות|בולדרים?\s*טבעיים|אבן\s*טבעית\s*מקומית|"
                 r"סלעים?\s*מקומיים?\s*(?:מה)?שטח", text, re.IGNORECASE):
        return "EXCLUDE"
    if re.search(r"אבן\s*דרך", text, re.IGNORECASE):
        return "EXCLUDE"
    # מעקות/מחסום בטון = concrete barrier/guardrail → Structural Concrete (before CATEGORY_RULES מעקה→Galvanized)
    if re.search(r"מעקות?\s*(?:מ|ה)?בטון|מחסום\s*(?:מ|ה)?בטון|קיר\s*(?:מ|ה)?בטון.*מעקה", text, re.IGNORECASE):
        return "Structural Concrete"
    if re.search(r"ריצוף|מרצפות?\s*אבן|אבן\s*(?:שפה|משתלבת)", text, re.IGNORECASE):
        return "Paving"
    if re.search(r"אבנ[יות]+\s*בגודל|תערובת\s*אבנ|בולדר|סלעי[ם]?\s*\d|אבן\s*(?:טבע|מקומ)", text, re.IGNORECASE):
        return "Crushed Stone"
    # מילוי חול מהודק / בחול = sand used as fill = Fill Material (not Crushed Stone)
    if re.search(r"מילוי\s*(?:ב)?חול\s*(?:מהודק|דק)|בחול\s*(?:לפי|מהודק)", text, re.IGNORECASE):
        return "Fill Material"
    # מילוי מובא (חומר א/ב/ג) = brought aggregate classified by type = Crushed Stone
    if re.search(r"מילוי\s*מובא.*\bחומר\s*(?:א|ב|ג)\b|\bחומר\s*(?:א|ב|ג)\b.*מילוי\s*מובא", text, re.IGNORECASE):
        return "Crushed Stone"
    if re.search(r"מילוי\s*מובא|חומר\s*(?:א|ב|ג|מילוי)\s*(?:מובא|סוג)|מילוי\s*(?:חוזר|מחול)|מילוי\s*להחלפת", text, re.IGNORECASE):
        return "Fill Material"
    if re.search(r"חצץ\s*(?:שטוף|מדורג|מסונן|ל?הידוק|בכל\s*הגדלים)", text, re.IGNORECASE):
        return "Crushed Stone"
    if re.search(r"גוף\s*(?:תאורה|LED|לד)|פנס\s*(?:LED|לד|מהבהב)|מנורה\s*(?:LED|לד)", text, re.IGNORECASE):
        return "EXCLUDE"
    if re.search(r"פינוי\s*(?:פסולת|חומר\s*קיים|שפכים)|פינוי\s*הקיים\s*באתר", text, re.IGNORECASE):
        return "EXCLUDE"
    if re.search(r"נקז[ים]*\s*(?:בקירות|אורכי)\s*(?:בקוטר|כולל|שרשורי)", text, re.IGNORECASE) and not re.search(r"מחורר", text, re.IGNORECASE):
        return "PVC Pipe"
    if re.search(r"מוליך\s*הארקה.*נחושת|הארקה.*נחושת.*שזור|(?:אלקטרודות|מוטות)\s*הארקה.*נחושת", text, re.IGNORECASE):
        return "Copper Wire (Cable)"
    if re.search(r"גרניט\s*פורצלן|פורצלן|קרמיק|קרמיקה|אריחים?\s*עמידי?\s*חומצות|אריחי?\s*גרניט|ריצוף\s*באריח", text, re.IGNORECASE):
        return "Paving"
    if re.search(r"מתז|שיקום\s*מערכות\s*השקיה|מגוף\s*(?:פלסטיק|פלסטי|ברונזה)\s*לגינון", text, re.IGNORECASE):
        return "EXCLUDE"
    if re.search(r"(?:נקז|צינור)\s*(?:אנכי|אורכי|שרשורי)\s*(?:כולל\s*)?צינור\s*שרשורי\s*מחורר|"
                 r"שרשורי\s*מחורר|נקז\s*אנכי|נקז\s*אורכי", text, re.IGNORECASE):
        return "HDPE Granulate"
    # מריפלכס/מריפלקס/מריפלס/מריפלכ/מריפלק = corrugated HDPE (also truncated forms without final ס)
    if re.search(r"מריפל(?:כ|ק)ס?", text, re.IGNORECASE):
        return "HDPE Granulate"
    # galvanized steel drainage pipe must be caught before generic צינור ניקוז → PVC
    if re.search(r"צינור\s*(?:ניקוז|פלדה)\s*(?:פלדה\s*)?מגולוון", text, re.IGNORECASE):
        return "Galvanized Steel"
    if re.search(r"צינור\s*ניקוז(?!\s*(?:PE\b|פולי|מריפל))", text, re.IGNORECASE):
        return "PVC Pipe"
    if re.search(r"צמנט\s*בורד|צמנטבורד|cement\s*board|fiber\s*cement", text, re.IGNORECASE):
        return "Cementitious Mortar"
    if re.search(r"אטמי?\s*מים\s*מ.?\s*P\.?V\.?C|waterstop\s*pvc", text, re.IGNORECASE):
        return "PVC Pipe"
    if re.search(r"עצר\s*מים|איטום\s*מעברי?\s*צינור|איטום\s*מעברים|פקק\s*מתועש|אלסטוסיל", text, re.IGNORECASE):
        return "Waterproofing"
    if re.search(r"בד\s*גיאוטכני|גיאוטכני|יריעת\s*HDPE|שטיח\s*גומי\s*מבודד", text, re.IGNORECASE):
        return "Waterproofing"
    if re.search(r"אסלה|כיור|משתנ(?:ה|ות)|עביט|קערות?\s*מטבח|מזרם", text, re.IGNORECASE):
        return "EXCLUDE"
    if re.search(r"מנתק\s*הספק|מפסק\s*חשמל|מרכזיית\s*הדלקה|לוח\s*מונים", text, re.IGNORECASE):
        return "EXCLUDE"
    if re.search(r"פסי?\s*רכבת|מסילה\s*בודדת", text, re.IGNORECASE):
        return "Steel Rebar"
    if re.search(r"כותרת\s*לעמודים|ניצבים\s*מבטון", text, re.IGNORECASE):
        return "Structural Concrete"
    if re.search(r"שלט|תמרור", text, re.IGNORECASE):
        return "Galvanized Steel"
    if re.search(r"בלוק\s*כורכר|כורכרי|לוחות?\s*כורכר", text, re.IGNORECASE):
        return "Precast Concrete"
    if re.search(r"קורות?\s*טרומ|לוח(?:ות)?\s*טרומ|כלונסאות?\s*טרומ|אלמנטים?\s*טרומ|תקרה\s*טרומ", text, re.IGNORECASE):
        return "Precast Concrete"
    if re.search(r"קורות?\s*(?:רוחב|דיאפרגמה|עיקריות?)|דיאפרגמה\s*מבטון|ניצב(?:ים)?\s*מבטון", text, re.IGNORECASE):
        return "Structural Concrete"
    if re.search(r"חומר\s*(?:א|ב|ג)\b(?:\s*(?:גרוס|מחצבה|מיוחד))?|חומר\s*גרוס\s*מחצבה", text, re.IGNORECASE):
        return "Crushed Stone"
    return None


CATEGORY_RULES: List[Tuple[str, List[str]]] = [
    ("Waterproofing",
     [r"איטו[םמ]", r"ממברנה", r"ביטומ", r"יריעת\s*hdpe", r"גאוטכני", r"פריימר",
      r"זפת", r"פוליאוריטן", r"סילר", r"יריעות"]),
    ("Asphalt",
     [r"אספלט", r"אספלת", r"\bתא.?צ\b", r"\bתא.?מ\b", r"\bSMA\b", r"בינדר", r"אמולסיה"]),
    ("Steel Rebar",
     [r"זיון", r"מוטות\s*פלדה", r"פלדה\s*מצולעים", r"ת.?י\s*4466",
      r"רשתות\s*פלדה", r"ברזל\s*בניין"]),
    ("Copper Wire (Cable)",
     [r"כבל.*נחושת", r"נחושת", r"N2XY", r"NYY", r"XLPE", r"גידים",
      r"כבל\s*חשמל", r"מוליך"]),
    ("Aluminum",
     [r"אלומיניום", r"אלומניום", r"פרופיל\s*אלומ", r"NA2XY", r"NA2XSY",
      r"כבל.*אלומינ", r"אלומינ.*כבל", r"פח\s*אלומיניום"]),
    ("HDPE Granulate",
     [r"HDPE", r"H\.D\.P\.E", r"פוליאתילן", r"PE100", r"PE-100", r"יק.?ע",
      r"שרשור.*פוליאתילן", r"צנרת\s*פוליאתילן", r"פוליגל", r"פוליפרופילן", r"פלסטי"]),
    ("PVC Pipe",
     [r"P\.?V\.?C", r"PVC", r"צינור\s*קשיח", r"מריכף", r"מריפלס", r"צנרת.*פלסטיק"]),
    ("Galvanized Steel",
     [r"מגולוונ", r"\bגדר\b", r"מעקה\s*(?:פלדה|בטיחות)?", r"פח\s*מגולוון",
      r"עמוד.*פלדה", r"זרוע.*פלדה", r"\bארון\b", r"\bרמזור\b", r"\bתמרור\b",
      r"ברזל\s*יצוק", r"מכסה\s*לתא"]),
    ("Lean Concrete",
     [r"בטון\s*רזה", r"ב-20", r"בטון\s*מדה", r"מדה\s*מתפלסת"]),
    ("Structural Concrete",
     [r"בטון", r"יצוק\s*באתר", r"ב-30", r"ב-40", r"כלונס", r"קירות\s*מבטון",
      r"ב-50", r"רפסודה", r"בלוקים"]),
    ("Crushed Stone",
     [r"אגרגט", r"חצץ", r"מצע", r"בקאלש", r"אבן\s*גרוסה", r"שומשום",
      r"חול", r"מחצבה", r"זיפזיף", r"אדמה", r"סלעים", r"מצע\s*א'"]),
    ("Fill Material",
     [r"מילוי\s*(?:חוזר|גרוס|אבן|חול|מחוזק)", r"מצע\s*מילוי", r"חומר\s*מילוי",
      r"\bמלית\b", r"מילוי\s*תחת", r"מילוי\s*מסביב", r"טמינה"]),
    ("Paving",
     [r"ריצוף", r"אבן\s*שפה", r"שפה\s*(?:טרומ|בטון|אבן)", r"מדרכה",
      r"ריצוף\s*(?:אבן|גרניט|שיש|קרמיק|אריח)", r"אריחי\s*בטון", r"אבן\s*משתלבת"]),
]


def apply_category_rules(text: str) -> Optional[str]:
    text = normalize_text(text)
    for category, patterns in CATEGORY_RULES:
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return category
    return None


def classify_local(material_text: str) -> Tuple[str, str]:
    """
    Returns (predicted_category, method).
    predicted_category is "EXCLUDE" for excluded rows.
    method is one of: exclude, hard_override, category_rules, no_local_match.
    """
    if should_exclude(material_text):
        return "EXCLUDE", "exclude"

    hard = hard_classification_override(material_text)
    if hard is not None:
        cat = hard if hard != "EXCLUDE" else "EXCLUDE"
        return cat, "hard_override"

    rule = apply_category_rules(material_text)
    if rule:
        return rule, "category_rules"

    return "no_local_match", "no_local_match"


# ── CSV fetch ──────────────────────────────────────────────────────────────────
def fetch_csv(url: str) -> str:
    """Follow redirects manually to handle Google's multi-hop CSV export."""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    current_url = url
    for attempt in range(5):
        req = urllib.request.Request(current_url, headers=headers)
        try:
            opener = urllib.request.build_opener(urllib.request.HTTPRedirectHandler())
            with opener.open(req, timeout=30) as resp:
                raw = resp.read()
                # Try to detect encoding
                for enc in ("utf-8-sig", "utf-8", "cp1255", "iso-8859-8"):
                    try:
                        return raw.decode(enc)
                    except UnicodeDecodeError:
                        continue
                return raw.decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            if e.code in (301, 302, 303, 307, 308):
                current_url = e.headers.get("Location", current_url)
                continue
            print(f"HTTP error {e.code}: {e.reason}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error fetching sheet: {e}", file=sys.stderr)
            sys.exit(1)
    print("Too many redirects", file=sys.stderr)
    sys.exit(1)


def find_col(headers: List[str], candidates: List[str]) -> Optional[int]:
    norm_headers = [h.strip().lower() for h in headers]
    for c in candidates:
        c_norm = c.strip().lower()
        if c_norm in norm_headers:
            return norm_headers.index(c_norm)
    return None


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    local_csv = None
    for i, arg in enumerate(sys.argv[1:]):
        if arg == "--csv" and i + 1 < len(sys.argv) - 1:
            local_csv = sys.argv[i + 2]

    print("Fetching QA spreadsheet…")
    if local_csv:
        with open(local_csv, encoding="utf-8-sig") as f:
            raw = f.read()
    else:
        raw = fetch_csv(SHEET_URL)

    reader = csv.reader(io.StringIO(raw))
    rows = list(reader)
    if not rows:
        print("Empty CSV — nothing to test.", file=sys.stderr)
        sys.exit(1)

    # The sheet has an empty row 0; headers are in row 1
    headers_row = 0
    for i, row in enumerate(rows[:5]):
        if any(c.strip() for c in row):
            non_empty_vals = [c for c in row if c.strip()]
            if len(non_empty_vals) >= 2:
                headers_row = i
                break
    headers = rows[headers_row]
    data_rows = rows[headers_row + 1:]

    col_correct  = find_col(headers, COL_CORRECT)
    col_detected = find_col(headers, COL_DETECTED)
    col_desc     = find_col(headers, COL_DESC)
    col_boq      = find_col(headers, COL_BOQ)

    if col_desc is None:
        print(f"Cannot find description column. Headers found: {headers}", file=sys.stderr)
        sys.exit(1)
    if col_correct is None:
        print(f"Cannot find correct-category column. Headers found: {headers}", file=sys.stderr)
        sys.exit(1)

    detected_col_name = headers[col_detected] if col_detected is not None else "N/A"
    print(f"Columns: desc={headers[col_desc]!r}  correct={headers[col_correct]!r}  "
          f"detected={detected_col_name!r}")
    print(f"Rows loaded: {len(data_rows)}\n")

    total = 0
    correct_match = 0
    wrong = 0
    no_local = 0
    exclude_correct = 0
    mismatches = []

    # Sheet uses slightly different names / we converted some categories
    CATEGORY_ALIASES = {
        "Copper Wire": "Copper Wire (Cable)",   # sheet omits "(Cable)"
        "Earthworks": "EXCLUDE",                # Earthworks category removed → EXCLUDE
    }

    def norm_category(raw: str) -> str:
        """Strip Hebrew parenthetical and apply aliases."""
        raw = raw.strip()
        paren = raw.find(" (")
        if paren > 0:
            raw = raw[:paren].strip()
        return CATEGORY_ALIASES.get(raw, raw)

    # Only test rows where קטגוריה נכונה is filled
    for i, row in enumerate(data_rows, start=2):
        if len(row) <= col_desc:
            continue
        desc = row[col_desc].strip()
        correct_raw = row[col_correct].strip() if col_correct is not None and len(row) > col_correct else ""
        detected_raw = row[col_detected].strip() if col_detected is not None and len(row) > col_detected else ""

        if not correct_raw or not desc:
            continue
        if correct_raw.strip().lower() in ("unknown", "לבדיקה ידנית"):
            continue

        correct_cat = norm_category(correct_raw)
        total += 1

        predicted, method = classify_local(desc)

        # Treat "EXCLUDE" correct + our exclude detection as correct
        is_correct = (predicted == correct_cat) or (
            predicted == "EXCLUDE" and correct_cat.upper() in ("EXCLUDE", "")
        )

        if predicted == "no_local_match":
            no_local += 1
        elif is_correct:
            correct_match += 1
            if predicted == "EXCLUDE":
                exclude_correct += 1
        else:
            wrong += 1
            mismatches.append({
                "row": i,
                "desc": desc[:80],
                "correct": correct_cat,
                "predicted": predicted,
                "previously_detected": detected_raw,
                "method": method,
            })

    # ── Summary ────────────────────────────────────────────────────────────────
    decidable = total - no_local
    accuracy = (correct_match / decidable * 100) if decidable else 0
    total_accuracy = (correct_match / total * 100) if total else 0

    print("=" * 65)
    print(f"  Total QA rows with manual label : {total}")
    print(f"  Local pipeline decided          : {decidable}  ({decidable/total*100:.1f}%)")
    print(f"  Passed to BigQuery/AI (no match): {no_local}  ({no_local/total*100:.1f}%)")
    print(f"  Correct (of decided)            : {correct_match}  ({accuracy:.1f}%)")
    print(f"  Wrong (of decided)              : {wrong}  ({wrong/decidable*100:.1f}% of decided)")
    print(f"  Overall accuracy                : {total_accuracy:.1f}%")
    print("=" * 65)

    if mismatches:
        print(f"\nMismatches ({len(mismatches)} rows):")
        print("-" * 65)
        for m in mismatches[:50] if not verbose else mismatches:
            was = f"  [was: {m['previously_detected']}]" if m['previously_detected'] else ""
            print(f"  Row {m['row']:4d} | {m['method']:15s} | correct={m['correct']:25s} predicted={m['predicted']}")
            print(f"          desc: {m['desc']}{was}")
        if len(mismatches) > 50 and not verbose:
            print(f"  … and {len(mismatches) - 50} more. Use --verbose to see all.")
    else:
        print("\nAll locally-decided rows match the manual labels!")

    print()
    # Group mismatches by (correct, predicted) pair for pattern analysis
    if mismatches:
        from collections import Counter
        pairs = Counter((m["correct"], m["predicted"]) for m in mismatches)
        print("Top mismatch patterns (correct → predicted):")
        for (correct, predicted), count in pairs.most_common(15):
            print(f"  {count:4d}x  {correct:30s} → {predicted}")

    return 0 if wrong == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
