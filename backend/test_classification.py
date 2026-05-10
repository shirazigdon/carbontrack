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
    if re.search(r"\bעץ\b|אורן|קורות\s*עץ|לביד|סנדוויץ", text, re.IGNORECASE):
        return "Wood"
    # Service operations that must fire even with material indicator present
    if re.search(r"\bקרצוף\b|\bחספוס\b", text, re.IGNORECASE):
        return "EXCLUDE"
    if re.search(r"פתיחת\s*(?:כביש|מדרכה|אספלט)", text, re.IGNORECASE):
        return "EXCLUDE"
    if re.search(r"ניסור\s*(?:אספלט|כביש|בטון)", text, re.IGNORECASE):
        return "EXCLUDE"
    if re.search(r"תוספת\s+לכל\s+\d|תוספת\s+ל?(?:כל|יחידת?)\s+(?:\d|ס.?מ)", text, re.IGNORECASE):
        return "EXCLUDE"
    if re.search(r"תיקון\s*משטח\s*(?:אספלט|בטונ|ריצוף)", text, re.IGNORECASE):
        return "EXCLUDE"
    if re.search(r"סלעים?\s*מקומיים?\s*(?:מה)?שטח|אבנ[יות]+\s*מקומיות?\s*(?:מה)?שטח", text, re.IGNORECASE):
        return "EXCLUDE"
    if re.search(r"\bתכנות\b|\bתוכנה\b|נקודה\s*דינמית|תוכנת\s*HMI|תוכנת\s*SCADA", text, re.IGNORECASE):
        return "EXCLUDE"
    if re.search(r"חיבור\s*סיב\s*אופטי|קצות?\s*סיב\s*אופטי", text, re.IGNORECASE):
        return "EXCLUDE"
    if re.search(r"\bמילוי\s*חוזר\b", text, re.IGNORECASE):
        return "EXCLUDE"

    if re.search(r"גיאו.?תא|geocell|כוורות?\s*גיאוטכניות?", text, re.IGNORECASE):
        return "HDPE Granulate"
    if re.search(r"\bHDPE\b|H\.D\.P\.E|פוליאתילן|פולי.?אתילן|\bPE100\b|\bPE-100\b", text, re.IGNORECASE):
        return "HDPE Granulate"
    if re.search(r"(?:צינור|קורגל)\s*(?:פלסטי|גמיש)\s*(?:דו.?שכבתי|שרשורי)?|פלסטי\s*שרשורי", text, re.IGNORECASE):
        return "HDPE Granulate"
    if re.search(r"מיוצב\s*ב?[צס]מנט|חול\s*מיוצב|אדמה\s*מיוצבת|תשחיף\s*מיוצב|מיוצב\s*ב?סיד", text, re.IGNORECASE):
        return "Fill Material"
    if re.search(r"פייבר\s*צמנט|fiber\s*cement|צמנטבורד|לוחות?\s*(?:פייבר|fiber)", text, re.IGNORECASE):
        return "Precast Concrete"
    if re.search(r"\bגראוט\b|\bgrout\b|חומר\s*גרוט|סיקה\s*גראוט", text, re.IGNORECASE):
        return "Cementitious Mortar"
    if re.search(r"בטון\s*(?:צמנטי|להטלאה|לאיטום|מחוזק|מהיר)|יציקת\s*(?:הטלאה|תיקון)", text, re.IGNORECASE):
        return "Structural Concrete"
    if re.search(r"מלט|מלת|טיט|מרגמה|רובה|דייס|צמנט", text, re.IGNORECASE):
        return "Cementitious Mortar"
    if re.search(r"אלומיניום|אלומניום|פרופיל\s*אלומ", text, re.IGNORECASE):
        return "Aluminum"
    if re.search(r"עמוד\s*(?:פלד|תאורה|מפלד)|עמוד\s*קוני|עמוד\s*בגובה", text, re.IGNORECASE):
        return "Galvanized Steel"
    if re.search(r"מייתד|מוט\s*מייתד|אינסרט\s*להארכת\s*זיון", text, re.IGNORECASE):
        return "Steel Rebar"
    if re.search(r"תוספת\s+מחיר|תוספת\s+למחיר", text, re.IGNORECASE):
        return "EXCLUDE"
    if re.search(r"דיפון\s*קשיח", text, re.IGNORECASE):
        return "Crushed Stone"
    if re.search(r"\bCLSM\b|בטון\s*זורם|בטון\s*נוזלי", text, re.IGNORECASE):
        return "Lean Concrete"
    if re.search(r"הידוק\s*(?:מבוקר|קרקע|יסוד)|גריסה\s*וניפוי|ניפוי\s*וגריסה", text, re.IGNORECASE):
        return "EXCLUDE"
    if re.search(r"\bזריע[הת]?\b|\bזיבול\b|הכשרת\s*קרקע\s*לגינון", text, re.IGNORECASE):
        return "EXCLUDE"
    if re.search(r"פוליסטר[ין]|פוליסטי|\bEPS\b|\bXPS\b|סנדוויץ.*בידוד|בידוד.*תרמי", text, re.IGNORECASE):
        return "EXCLUDE"
    if re.search(r"יריע[ות]+\s*ניקוז|גיאוקומפוזיט|geo.?composite", text, re.IGNORECASE):
        return "Waterproofing"
    # Local/natural boulders must come BEFORE generic "בולדר → Crushed Stone" check
    if re.search(r"בולדרים?\s*מאבנים\s*מקומיות|בולדרים?\s*טבעיים|אבן\s*טבעית\s*מקומית|"
                 r"סלעים?\s*מקומיים?\s*(?:מה)?שטח", text, re.IGNORECASE):
        return "EXCLUDE"
    if re.search(r"אבן\s*דרך", text, re.IGNORECASE):
        return "EXCLUDE"
    if re.search(r"אבנ[יות]+\s*בגודל|תערובת\s*אבנ|בולדר|סלעי[ם]?\s*\d|אבן\s*(?:טבע|מקומ)", text, re.IGNORECASE):
        return "Crushed Stone"
    if re.search(r"מילוי\s*מובא|חומר\s*(?:א|ב|ג|מילוי)\s*(?:מובא|סוג)|מילוי\s*חוזר|מילוי\s*להחלפת", text, re.IGNORECASE):
        return "Fill Material"
    if re.search(r"חצץ\s*(?:שטוף|מדורג|מסונן|ל?הידוק|בכל\s*הגדלים)", text, re.IGNORECASE):
        return "Crushed Stone"
    if re.search(r"גוף\s*(?:תאורה|LED|לד)|פנס\s*(?:LED|לד|מהבהב)|מנורה\s*(?:LED|לד)", text, re.IGNORECASE):
        return "EXCLUDE"
    if re.search(r"פינוי\s*(?:פסולת|חומר\s*קיים|שפכים)|פינוי\s*הקיים\s*באתר", text, re.IGNORECASE):
        return "EXCLUDE"
    if re.search(r"נקז[ים]*\s*(?:בקירות|אורכי)\s*(?:בקוטר|כולל|שרשורי)", text, re.IGNORECASE):
        return "PVC Pipe"
    if re.search(r"מוליך\s*הארקה.*נחושת|הארקה.*נחושת.*שזור", text, re.IGNORECASE):
        return "Copper Wire (Cable)"
    if re.search(r"גרניט\s*פורצלן|פורצלן|קרמיק|קרמיקה|אריחים?\s*עמידי?\s*חומצות|אריחי?\s*גרניט|ריצוף\s*באריח", text, re.IGNORECASE):
        return "Paving"
    if re.search(r"מתז|שיקום\s*מערכות\s*השקיה|מגוף\s*ברונזה\s*לגינון", text, re.IGNORECASE):
        return "EXCLUDE"
    if re.search(r"(?:נקז|צינור)\s*(?:אנכי|אורכי|שרשורי)\s*(?:כולל\s*)?צינור\s*שרשורי\s*מחורר|"
                 r"שרשורי\s*מחורר|נקז\s*אנכי|נקז\s*אורכי", text, re.IGNORECASE):
        return "HDPE Granulate"
    if re.search(r"צינור\s*ניקוז", text, re.IGNORECASE):
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
     [r"אספלט", r"אספלת", r"תא.?צ", r"תא.?מ", r"\bSMA\b", r"בינדר", r"אמולסיה"]),
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
      r"מלית", r"מילוי\s*תחת", r"מילוי\s*מסביב", r"טמינה"]),
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
