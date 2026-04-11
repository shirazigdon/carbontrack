import os
import io
import base64
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st
import streamlit.components.v1 as components
from textwrap import dedent
try:
    from google.cloud import bigquery, storage  # type: ignore
except Exception:
    bigquery = None
    storage = None

# ── Load GCP credentials from Streamlit Secrets ──────────────────────────────
try:
    if "gcp_service_account" in st.secrets:
        from google.oauth2 import service_account as _sa
        _GCP_CREDENTIALS = _sa.Credentials.from_service_account_info(
            dict(st.secrets["gcp_service_account"]),
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        os.environ["GOOGLE_CLOUD_PROJECT"] = st.secrets["gcp_service_account"]["project_id"]
    else:
        _GCP_CREDENTIALS = None
except Exception:
    _GCP_CREDENTIALS = None

# ── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CarbonTrack360",
    page_icon="https://storage.googleapis.com/green_excal/carbontrack-logo.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Design tokens (matching index.css exactly) ───────────────────────────────
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Heebo:wght@300;400;500;600;700;800;900&display=swap');

:root {
    --bg:             hsl(140, 10%, 97%);
    --card:           hsl(0, 0%, 100%);
    --foreground:     hsl(150, 25%, 10%);
    --muted:          hsl(140, 12%, 93%);
    --muted-fg:       hsl(150, 10%, 45%);
    --border:         hsl(140, 15%, 89%);
    --primary:        hsl(142, 55%, 35%);
    --primary2:       hsl(152, 45%, 42%);
    --accent:         hsl(85, 50%, 45%);
    --success:        hsl(152, 60%, 40%);
    --warning:        hsl(38, 92%, 50%);
    --destructive:    hsl(0, 72%, 51%);
    --sidebar-bg:     hsl(150, 30%, 10%);
    --sidebar-fg:     hsl(140, 15%, 85%);
    --sidebar-border: hsl(150, 18%, 18%);
    --sidebar-accent: hsl(150, 22%, 16%);
    --shadow-card:    0 1px 3px 0 hsl(150 25% 10% / 0.04), 0 1px 2px -1px hsl(150 25% 10% / 0.04);
    --shadow-elevated:0 10px 25px -5px hsl(150 25% 10% / 0.08), 0 8px 10px -6px hsl(150 25% 10% / 0.04);
    --radius:         0.75rem;
    --grad-primary:   linear-gradient(135deg, hsl(142,55%,35%), hsl(152,45%,42%));
    --grad-accent:    linear-gradient(135deg, hsl(85,50%,45%), hsl(142,55%,35%));
    --grad-hero:      linear-gradient(135deg, hsl(150,30%,10%), hsl(150,25%,16%));
}

html, body, [data-testid="stAppViewContainer"], .stApp {
    background: var(--bg);
    font-family: 'Heebo', sans-serif;
    overflow-x: hidden !important;
}

[data-testid="stAppViewContainer"],
.main .block-container,
[data-testid="stSidebar"],
[data-testid="stSidebar"] * {
    direction: rtl;
}
body {
    margin: 0 !important;
}
.block-container {
    max-width: 1400px;
    padding-top: 0 !important;
    padding-bottom: 2rem;
    padding-left: 1rem !important;
    padding-right: 1rem !important;
}
/* Remove Streamlit's default top white bar */
header[data-testid="stHeader"] {
    display: none !important;
    height: 0 !important;
}
#MainMenu { visibility: hidden !important; }
footer { visibility: hidden !important; }
/* Kill any top padding on the app shell */
.stApp > header { display: none !important; }
[data-testid="stAppViewContainer"] > section:first-child {
    padding-top: 0 !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #fff !important;
    border: none !important;
    box-shadow: none !important;
}
[data-testid="stSidebar"] > div {
    background: #fff !important;
    border: none !important;
    border-left: 1px solid hsl(140,15%,89%) !important;
    box-shadow: none !important;
    padding-top: 0 !important;
}
/* Text colors inside sidebar – override to dark */
[data-testid="stSidebar"] * { color: var(--foreground) !important; }
[data-testid="stSidebar"] label {
    color: var(--muted-fg) !important;
    font-size: .72rem;
    text-transform: uppercase;
    letter-spacing: .05em;
}
/* ── Sidebar always open – hide collapse/expand controls ── */
[data-testid="stSidebarCollapseButton"] { display: none !important; }
[data-testid="stSidebarCollapsedControl"] { display: none !important; }
[data-testid="stSidebarNav"],
[data-testid="stSidebarUserContent"] { border: none !important; }
[data-testid="stSidebar"] > div:first-child,
[data-testid="stSidebar"] > div:first-child > div:first-child {
    box-shadow: none !important;
}
/* Expanders on white sidebar */
[data-testid="stSidebar"] .stExpander {
    border: 1px solid var(--border) !important;
    background: var(--muted) !important;
    border-radius: .75rem !important;
    margin-bottom: .4rem !important;
}
[data-testid="stSidebar"] .stExpander details summary {
    font-size: .85rem !important;
    font-weight: 600 !important;
    color: var(--foreground) !important;
}
/* Multiselect tags */
[data-testid="stSidebar"] .stMultiSelect [data-baseweb="tag"] {
    background: hsl(142,55%,35%,.12) !important;
    color: hsl(142,55%,28%) !important;
}
/* Buttons */
[data-testid="stSidebar"] .stButton > button {
    background: var(--muted) !important;
    border: 1px solid var(--border) !important;
    color: var(--foreground) !important;
    border-radius: .6rem !important;
    font-size: .82rem !important;
    font-weight: 600 !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: hsl(142,55%,35%) !important;
    color: #fff !important;
    border-color: transparent !important;
}
section.main > div {
    max-width: 100%;
}

/* ── RTL fixes ── */
label, .stSelectbox label, .stTextInput label,
.stMultiselect label, .stSlider label, .stCheckbox label,
.stNumberInput label { direction: rtl; text-align: right; }
.stButton > button { direction: rtl; }
[data-baseweb="tab"] { direction: rtl; }
input[type="number"], input[dir="ltr"], code, pre { direction: ltr; unicode-bidi: embed; }

/* ── Cards ── */
.card-surface {
    background: var(--card);
    border-radius: var(--radius);
    border: 1px solid var(--border);
    padding: 1.25rem;
    box-shadow: var(--shadow-card);
}
.card-elevated {
    background: var(--card);
    border-radius: var(--radius);
    border: 1px solid var(--border);
    padding: 2rem;
    box-shadow: var(--shadow-elevated);
}

/* ── Hero header ── */
.hero-header {
    background: var(--grad-hero);
    border-radius: 1rem;
    padding: 1.5rem 2rem;
    margin-bottom: 1.5rem;
    position: relative;
    overflow: hidden;
}
.hero-header::before {
    content: '';
    position: absolute; inset: 0;
    background: radial-gradient(circle at 80% 50%, hsl(142,55%,35%,.15) 0%, transparent 60%);
}
.hero-brand { display: flex; align-items: center; gap: 1rem; }
.hero-title {
    color: #fff;
    font-size: 1.25rem;
    font-weight: 700;
    margin: 0;
    line-height: 1.2;
}
.hero-subtitle { color: rgba(255,255,255,.5); font-size: .75rem; margin: .2rem 0 0; }
.hero-stats { display: flex; gap: 1rem; margin-right: auto; }
.hero-stat {
    display: flex; align-items: center; gap: .625rem;
    background: rgba(255,255,255,.05);
    border: 1px solid rgba(255,255,255,.10);
    border-radius: .5rem;
    padding: .5rem 1rem;
    backdrop-filter: blur(4px);
}
.hero-stat-label { color: rgba(255,255,255,.45); font-size: .65rem; text-transform: uppercase; letter-spacing: .06em; }
.hero-stat-value { color: #fff; font-size: .875rem; font-weight: 700; direction: ltr; }

/* ── KPI cards ── */
.kpi-card {
    border-radius: var(--radius);
    padding: 1.25rem;
    transition: transform .2s;
}
.kpi-card:hover { transform: scale(1.02); }
.kpi-default  { background: var(--card); border: 1px solid var(--border); box-shadow: var(--shadow-card); }
.kpi-primary  { background: var(--grad-primary); }
.kpi-accent   { background: var(--grad-accent); }
.kpi-title    { font-size: .875rem; font-weight: 500; margin-bottom: .75rem; }
.kpi-default .kpi-title  { color: var(--muted-fg); }
.kpi-primary .kpi-title,
.kpi-accent  .kpi-title  { color: rgba(255,255,255,.8); }
.kpi-value   { font-size: 1.875rem; font-weight: 700; line-height: 1.1; direction: ltr; }
.kpi-default .kpi-value  { color: var(--foreground); }
.kpi-primary .kpi-value,
.kpi-accent  .kpi-value  { color: #fff; }
.kpi-foot    { display: flex; align-items: center; gap: .5rem; margin-top: .5rem; }
.kpi-sub     { font-size: .75rem; }
.kpi-default .kpi-sub    { color: var(--muted-fg); }
.kpi-primary .kpi-sub,
.kpi-accent  .kpi-sub    { color: rgba(255,255,255,.7); }
.badge-down  { background: hsl(152,60%,40%,.15); color: hsl(152,60%,40%); font-size: .7rem; font-weight: 700; padding: .15rem .5rem; border-radius: 999px; }
.badge-up    { background: hsl(0,72%,51%,.15); color: hsl(0,72%,51%);   font-size: .7rem; font-weight: 700; padding: .15rem .5rem; border-radius: 999px; }
.badge-warn  { background: hsl(38,92%,50%,.15); color: hsl(38,92%,50%); font-size: .7rem; font-weight: 700; padding: .15rem .5rem; border-radius: 999px; }

/* ── Section title ── */
.section-title { font-size: 1rem; font-weight: 600; color: var(--foreground); margin-bottom: .75rem; display: flex; align-items: center; gap: .5rem; }

/* ── Review item ── */
.review-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1.25rem;
    margin-bottom: .75rem;
    box-shadow: var(--shadow-card);
}
.review-meta  { font-size: .75rem; color: var(--muted-fg); margin: .25rem 0 1rem; }
.review-grid  { display: grid; grid-template-columns: repeat(4,1fr); gap: .75rem; margin-bottom: 1rem; }
.review-field-label { font-size: .7rem; color: var(--muted-fg); margin-bottom: .25rem; }
.review-field-value { font-size: .875rem; font-weight: 500; color: var(--foreground); }
.score-low   { color: hsl(0,72%,51%); font-weight: 700; }
.score-mid   { color: hsl(38,92%,50%); font-weight: 700; }
.score-high  { color: hsl(152,60%,40%); font-weight: 700; }

/* ── Login page ── */
.login-page {
    background: var(--grad-hero);
    min-height: 100vh;
    display: flex; align-items: center; justify-content: center;
}
.login-card {
    background: var(--card);
    border-radius: 1rem;
    padding: 2.5rem;
    box-shadow: var(--shadow-elevated);
    max-width: 440px;
    width: 100%;
    text-align: center;
}
.login-subtitle { color: var(--muted-fg); font-size: .875rem; margin-top: .25rem; }
.login-footer   { color: var(--muted-fg); font-size: .75rem; margin-top: 1.5rem; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: hsl(140,12%,93%,.6);
    border: 1px solid var(--border);
    border-radius: .75rem;
    padding: .4rem;
    gap: .25rem;
    margin-bottom: 1.5rem;
    flex-wrap: wrap;
}
.stTabs [data-baseweb="tab"] {
    border-radius: .5rem;
    padding: .5rem .875rem;
    font-weight: 600;
    font-size: .875rem;
    color: var(--muted-fg);
}
.stTabs [aria-selected="true"] {
    background: var(--card) !important;
    color: var(--foreground) !important;
    box-shadow: var(--shadow-card);
}

/* ── Upload drop zone ── */
[data-testid="stFileUploader"] {
    border: 2px dashed var(--border);
    border-radius: var(--radius);
    padding: 1.5rem;
    background: var(--muted);
    transition: border-color .2s, background .2s;
}
[data-testid="stFileUploader"]:hover {
    border-color: var(--primary);
    background: hsl(142,55%,35%,.05);
}

/* ── Buttons ── */
.stButton > button[kind="primary"] {
    background: var(--grad-primary);
    border: none;
    font-weight: 600;
    height: 2.75rem;
}
.stButton > button[kind="primary"]:hover { opacity: .9; }

/* ── Progress bar ── */
.stProgress > div > div { background: var(--grad-primary); }

/* ── Info/Warning boxes ── */
.stAlert { border-radius: var(--radius); }



/* ── Custom sidebar content blocks ── */
.sidebar-panel {
    background: transparent;
    padding: 0 0 .75rem;
}
/* Dark header card at top of sidebar */
.sidebar-header-card {
    background: hsl(150,30%,10%);
    border-radius: 0 0 1rem 1rem;
    padding: 1rem 1rem .875rem;
    margin: -1rem -1rem .875rem;
}
.sidebar-brand-row {
    display:flex;align-items:center;gap:.75rem;
    padding-bottom:.75rem;
    border-bottom:1px solid rgba(255,255,255,.1);
    margin-bottom:.75rem;
}
.sidebar-brand-row * { color: #fff !important; }
.sidebar-user-row {
    display:flex;align-items:center;gap:.75rem;
}
.sidebar-user-row * { color: rgba(255,255,255,.85) !important; }
.sidebar-avatar {
    width:2rem;height:2rem;border-radius:999px;
    background:rgba(255,255,255,.12);
    display:flex;align-items:center;justify-content:center;
    font-size:.875rem;
    flex-shrink: 0;
}
/* Section labels on white background */
.sidebar-section-title {
    display:flex;align-items:center;gap:.5rem;
    font-size:.72rem;font-weight:700;
    letter-spacing:.06em;text-transform:uppercase;
    color: var(--muted-fg);
    margin:.75rem 0 .4rem;
}
.sidebar-count-badge {
    display:inline-flex;align-items:center;justify-content:center;
    min-width:1rem;height:1rem;padding:0 .3rem;
    border-radius:999px;background:hsl(142,55%,35%,.12);
    color:hsl(142,55%,28%);font-size:.68rem;font-weight:700;
}
[data-testid="stSidebar"] .stMultiSelect > div > div,
[data-testid="stSidebar"] .stSelectbox > div > div,
[data-testid="stSidebar"] .stSlider {
    background: var(--muted) !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar       { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 99px; }
</style>
<script>
(function() {
  function labelCollapsedBtn() {
    var el = document.querySelector('[data-testid="stSidebarCollapsedControl"] button');
    if (el && !el.dataset.labeled) {
      el.textContent = 'C\u2082T';
      el.dataset.labeled = '1';
    }
    var wrap = document.querySelector('[data-testid="stSidebarCollapsedControl"]');
    if (wrap && !wrap.dataset.labeled) {
      var inner = document.createElement('span');
      inner.textContent = 'C\u2082T';
      inner.style.cssText = 'font-family:Heebo,sans-serif;font-size:.7rem;font-weight:800;color:#fff;pointer-events:none;position:absolute;';
      wrap.appendChild(inner);
      wrap.dataset.labeled = '1';
    }
  }
  var mo = new MutationObserver(labelCollapsedBtn);
  mo.observe(document.body, {childList:true, subtree:true});
  labelCollapsedBtn();
})();
</script>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ── PWA / iOS meta tags ──────────────────────────────────────────────────────
st.markdown("""
<link rel="manifest" href="/manifest.json">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="C₂Track">
<meta name="mobile-web-app-capable" content="yes">
<meta name="theme-color" content="#1a3d2b">
<link rel="apple-touch-icon" href="https://storage.googleapis.com/green_excal/carbontrack-logo.png">
<link rel="apple-touch-startup-image" href="https://storage.googleapis.com/green_excal/carbontrack-logo.png">
""", unsafe_allow_html=True)


# ── Logo loader (GCS) ────────────────────────────────────────────────────────

LOGO_PUBLIC_URL = "https://storage.googleapis.com/green_excal/carbontrack-logo.png"

def load_logo_b64() -> Optional[str]:
    return None  # Not needed - using public URL directly

def render_logo(width: int = 48) -> str:
    return f'<img src="{LOGO_PUBLIC_URL}" style="width:{width}px;height:auto;object-fit:contain;" alt="CarbonTrack" onerror="this.style.display=\'none\'">'



ROLE_DISPLAY = {
    "management": "הנהלה",
    "support": "תומכי הלחימה",
    "project_manager": "מנהל פרויקט",
    "sustainability": "קיימות (ESG)",
    "regulator": "רגולטור",
}

# ── Mock data (same as mockData.ts) ─────────────────────────────────────────
def build_mock_emissions() -> pd.DataFrame:
    return pd.DataFrame([
        {"id":"1","project_name":"כביש 6 - מקטע צפון","contractor":"שפיר הנדסה","region":"צפון","category":"Steel Rebar","boq_code":"ST-001","short_text":"פלדת זיון B500","weight_kg":125000,"emission_co2e":231250,"reliability_score":0.92,"matched_by":"exact_match","assumed_uom":"kg","review_required":False,"year":2026},
        {"id":"2","project_name":"כביש 6 - מקטע צפון","contractor":"שפיר הנדסה","region":"צפון","category":"Structural Concrete","boq_code":"CO-001","short_text":"בטון B30","weight_kg":450000,"emission_co2e":148500,"reliability_score":0.88,"matched_by":"ai_match","assumed_uom":"m3","review_required":False,"year":2026},
        {"id":"3","project_name":"מחלף גלילות","contractor":"דניה סיבוס","region":"מרכז","category":"Asphalt","boq_code":"AS-001","short_text":"אספלט חם","weight_kg":320000,"emission_co2e":89600,"reliability_score":0.95,"matched_by":"exact_match","assumed_uom":"ton","review_required":False,"year":2026},
        {"id":"4","project_name":"מחלף גלילות","contractor":"דניה סיבוס","region":"מרכז","category":"Galvanized Steel","boq_code":"ST-002","short_text":"פלדת מבנה S355","weight_kg":85000,"emission_co2e":178500,"reliability_score":0.78,"matched_by":"ai_match","assumed_uom":"kg","review_required":True,"year":2026},
        {"id":"5","project_name":"כביש 1 - מעלה אדומים","contractor":"סולל בונה","region":"מרכז","category":"Structural Concrete","boq_code":"CO-002","short_text":"בטון B40 מזוין","weight_kg":680000,"emission_co2e":258400,"reliability_score":0.91,"matched_by":"exact_match","assumed_uom":"m3","review_required":False,"year":2025},
        {"id":"6","project_name":"גשר נחל הבשור","contractor":"אלקטרה בנייה","region":"דרום","category":"Galvanized Steel","boq_code":"ST-003","short_text":"כבלי פלדה","weight_kg":42000,"emission_co2e":92400,"reliability_score":0.85,"matched_by":"ai_match","assumed_uom":"kg","review_required":False,"year":2026},
        {"id":"7","project_name":"גשר נחל הבשור","contractor":"אלקטרה בנייה","region":"דרום","category":"Wood","boq_code":"WD-001","short_text":"עץ תבניות","weight_kg":18000,"emission_co2e":5400,"reliability_score":0.72,"matched_by":"fuzzy_match","assumed_uom":"m3","review_required":True,"year":2026},
        {"id":"8","project_name":"כביש 90 - ים המלח","contractor":"מנרב","region":"דרום","category":"Asphalt","boq_code":"AS-002","short_text":"אספלט קר","weight_kg":210000,"emission_co2e":50400,"reliability_score":0.89,"matched_by":"exact_match","assumed_uom":"ton","review_required":False,"year":2026},
        {"id":"9","project_name":"כביש 90 - ים המלח","contractor":"מנרב","region":"דרום","category":"Structural Concrete","boq_code":"CO-003","short_text":"בטון מובא B25","weight_kg":520000,"emission_co2e":161200,"reliability_score":0.93,"matched_by":"exact_match","assumed_uom":"m3","review_required":False,"year":2025},
        {"id":"10","project_name":"מנהרות הכרמל","contractor":"שפיר הנדסה","region":"צפון","category":"Steel Rebar","boq_code":"ST-004","short_text":"פלדת אנקרים","weight_kg":65000,"emission_co2e":143000,"reliability_score":0.87,"matched_by":"ai_match","assumed_uom":"kg","review_required":False,"year":2026},
        {"id":"11","project_name":"מנהרות הכרמל","contractor":"שפיר הנדסה","region":"צפון","category":"Structural Concrete","boq_code":"CO-004","short_text":"בטון מזויין B45","weight_kg":890000,"emission_co2e":356000,"reliability_score":0.96,"matched_by":"exact_match","assumed_uom":"m3","review_required":False,"year":2026},
        {"id":"12","project_name":"כביש 1 - מעלה אדומים","contractor":"סולל בונה","region":"מרכז","category":"Aluminum","boq_code":"AL-001","short_text":"מעקות אלומיניום","weight_kg":12000,"emission_co2e":108000,"reliability_score":0.81,"matched_by":"ai_match","assumed_uom":"kg","review_required":True,"year":2026},
    ])

def build_mock_review() -> pd.DataFrame:
    return pd.DataFrame([
        {"review_id":"r1","short_text":"פלדת מבנה S355","project_name":"מחלף גלילות","boq_code":"ST-002","suggested_category":"Galvanized Steel","suggested_uom":"kg","review_reason":"ציון אמינות נמוך","reliability_score":0.78,"factor_spread_pct":22.5,"climatiq_candidate_count":8},
        {"review_id":"r2","short_text":"עץ תבניות","project_name":"גשר נחל הבשור","boq_code":"WD-001","suggested_category":"Wood","suggested_uom":"m3","review_reason":"התאמה לא מדויקת","reliability_score":0.72,"factor_spread_pct":35.1,"climatiq_candidate_count":12},
        {"review_id":"r3","short_text":"מעקות אלומיניום","project_name":"כביש 1 - מעלה אדומים","boq_code":"AL-001","suggested_category":"Aluminum","suggested_uom":"kg","review_reason":"סטיית פקטור גבוהה","reliability_score":0.81,"factor_spread_pct":18.3,"climatiq_candidate_count":6},
    ])


# ── BigQuery loader ──────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_bigquery_data() -> Tuple[pd.DataFrame, pd.DataFrame, str]:
    if bigquery is None:
        raise RuntimeError("google-cloud-bigquery not installed")
    project = os.getenv("BQ_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")
    dataset = os.getenv("BQ_DATASET_ID", "netivei_emissions_db")
    e_table = os.getenv("BQ_SUMMARY_TABLE", "emissions_summary")
    r_table = os.getenv("BQ_REVIEW_TABLE", "review_queue")
    if not project:
        raise RuntimeError("Missing BQ_PROJECT_ID")
    client = bigquery.Client(project=project)

    e_sql = f"""
    SELECT
      CAST(COALESCE(project_name,'Unknown') AS STRING) AS project_name,
      CAST(COALESCE(contractor,'Unknown') AS STRING) AS contractor,
      CAST(COALESCE(region,'Unknown') AS STRING) AS region,
      CAST(COALESCE(category,'Unknown') AS STRING) AS category,
      EXTRACT(YEAR FROM COALESCE(CAST(created_at AS TIMESTAMP), CURRENT_TIMESTAMP())) AS year,
      CAST(COALESCE(weight_kg,0) AS FLOAT64) AS weight_kg,
      CAST(COALESCE(emission_co2e,0) AS FLOAT64) AS emission_co2e,
      CAST(COALESCE(reliability_score,0) AS FLOAT64) AS reliability_score
    FROM `{project}.{dataset}.{e_table}`
    """
    r_sql = f"""
    SELECT
      CAST(COALESCE(review_id,'') AS STRING) AS review_id,
      CAST(COALESCE(material, short_text, '') AS STRING) AS short_text,
      CAST(COALESCE(project_name,'') AS STRING) AS project_name,
      CAST(COALESCE(boq_code,'') AS STRING) AS boq_code,
      CAST(COALESCE(suggested_category,'') AS STRING) AS suggested_category,
      CAST(COALESCE(suggested_uom,'') AS STRING) AS suggested_uom,
      CAST(COALESCE(reason,'') AS STRING) AS review_reason,
      CAST(COALESCE(reliability_score,0) AS FLOAT64) AS reliability_score,
      CAST(COALESCE(factor_spread_pct,0) AS FLOAT64) AS factor_spread_pct,
      CAST(COALESCE(climatiq_candidate_count,0) AS INT64) AS climatiq_candidate_count
    FROM `{project}.{dataset}.{r_table}`
    WHERE review_status = 'pending'
    LIMIT 200
    """
    return (
        client.query(e_sql).result().to_dataframe(),
        client.query(r_sql).result().to_dataframe(),
        f"BigQuery · {project}.{dataset}",
    )


def load_data():
    if os.getenv("USE_BIGQUERY", "true").lower() == "true":
        try:
            return load_bigquery_data()
        except Exception as exc:
            st.sidebar.warning(f"BigQuery: {exc}")
    e, r = build_mock_emissions(), build_mock_review()
    return e, r, "Mock data"


# ── Chart helpers ─────────────────────────────────────────────────────────────
COLORS = ["hsl(142,55%,35%)","hsl(152,45%,42%)","hsl(85,50%,45%)","hsl(38,92%,50%)","hsl(170,50%,40%)","hsl(120,40%,50%)"]

def _base_layout(fig, height=300):
    fig.update_layout(
        height=height, margin=dict(l=10,r=10,t=32,b=10),
        paper_bgcolor="white", plot_bgcolor="white",
        font=dict(family="Heebo", size=12, color="hsl(150,10%,45%)"),
        legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=.5),
    )
    return fig


# ── KPI card ──────────────────────────────────────────────────────────────────
def kpi(title, value, subtitle="", trend=None, trend_val=None, variant="default"):
    badge = ""
    if trend_val:
        cls = "badge-down" if trend=="down" else "badge-up" if trend=="up" else "badge-warn"
        badge = f'<span class="{cls}">{trend_val}</span>'
    st.markdown(f"""
    <div class="kpi-card kpi-{variant}">
        <div class="kpi-title">{title}</div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-foot">{badge}<span class="kpi-sub">{subtitle}</span></div>
    </div>""", unsafe_allow_html=True)


# ── API helpers ───────────────────────────────────────────────────────────────
@st.cache_data(ttl=120)
def fetch_status() -> Optional[pd.DataFrame]:
    base = os.getenv("API_BASE_URL","").rstrip("/")
    ep   = os.getenv("API_STATUS_ENDPOINT","/processing/status")
    if not base: return None
    try:
        r = requests.get(f"{base}{ep}", timeout=15)
        r.raise_for_status()
        data = r.json()
        items = data.get("items", data) if isinstance(data, dict) else data
        if isinstance(items, list):
            df = pd.DataFrame(items)
            return df if not df.empty else None
    except Exception:
        return None

def upload_to_backend(f) -> Tuple[bool, str]:
    base = os.getenv("API_BASE_URL","").rstrip("/")
    ep   = os.getenv("API_UPLOAD_ENDPOINT","/upload")
    if not base: return False, "חסר API_BASE_URL"
    files = {"file": (f.name, f.getvalue(), f.type or "application/octet-stream")}
    data  = {
        "project_name": st.session_state.get("up_proj",""),
        "project_type": st.session_state.get("up_type",""),
        "contractor":   st.session_state.get("up_cont",""),
        "region":       st.session_state.get("up_region","מרכז"),
        "source_mode":  st.session_state.get("up_mode","auto"),
    }
    try:
        resp = requests.post(f"{base}{ep}", files=files, data=data, timeout=120)
        if resp.ok:
            rid = (resp.json() or {}).get("run_id","uploaded")
            return True, f"הקובץ נשלח בהצלחה · run_id: {rid}"
        return False, f"שגיאה {resp.status_code}: {resp.text[:200]}"
    except Exception as e:
        return False, str(e)


# ════════════════════════════════════════════════════════════════════════════
# BIGQUERY HELPERS
# ════════════════════════════════════════════════════════════════════════════
_PROJECT  = "argon-ace-483810-n9"
_DATASET  = "netivei_emissions_db"
_USERS    = f"{_PROJECT}.{_DATASET}.users"
_DETAILS_V= f"{_PROJECT}.{_DATASET}.emissions_details_view"
_DETAILS_T= f"{_PROJECT}.{_DATASET}.emissions_details"
_REVIEW   = f"{_PROJECT}.{_DATASET}.review_queue"

@st.cache_resource
def _bq_client():
    try:
        from google.cloud import bigquery as _bq
        if _GCP_CREDENTIALS is not None:
            return _bq.Client(project=_PROJECT, credentials=_GCP_CREDENTIALS)
        return _bq.Client(project=_PROJECT)
    except Exception:
        return None

def _run_bq(sql, params=None):
    try:
        from google.cloud import bigquery as _bq
        client = _bq_client()
        if client is None: return pd.DataFrame()
        cfg = _bq.QueryJobConfig(query_parameters=params) if params else None
        return client.query(sql, job_config=cfg).to_dataframe()
    except Exception:
        return pd.DataFrame()

def _get_user(email):
    try:
        from google.cloud import bigquery as _bq
        df = _run_bq(
            f"SELECT email,name,role,password,is_first_login FROM `{_USERS}` WHERE LOWER(email)=LOWER(@e) LIMIT 1",
            [_bq.ScalarQueryParameter("e","STRING",email)],
        )
        return df.iloc[0].to_dict() if not df.empty else None
    except Exception:
        return None

def _update_password(email, new_pass):
    try:
        from google.cloud import bigquery as _bq
        _bq_client().query(
            f"UPDATE `{_USERS}` SET password=@p,is_first_login=FALSE WHERE email=@e",
            job_config=_bq.QueryJobConfig(query_parameters=[
                _bq.ScalarQueryParameter("p","STRING",new_pass),
                _bq.ScalarQueryParameter("e","STRING",email),
            ])
        ).result()
        return True
    except Exception:
        return False

@st.cache_data(ttl=60)
def _load_bq_emissions():
    df = _run_bq(f"SELECT * FROM `{_DETAILS_V}` ORDER BY calculation_date DESC")
    if df.empty:
        df = _run_bq(f"SELECT * FROM `{_DETAILS_T}` ORDER BY calculation_date DESC")
    if not df.empty:
        for c in ["project_name","contractor","region","category","matched_by","assumed_uom"]:
            if c not in df.columns: df[c] = None
        if "short_text" not in df.columns and "material" in df.columns:
            df["short_text"] = df["material"]
        if "review_required" not in df.columns: df["review_required"] = False
        for c in ["emission_co2e","weight_kg","reliability_score","factor_spread_pct"]:
            if c in df.columns: df[c] = pd.to_numeric(df[c], errors="coerce")
        if "calculation_date" in df.columns:
            df["calculation_date"] = pd.to_datetime(df["calculation_date"], errors="coerce")
            df["year"] = df["calculation_date"].dt.year
    return df

@st.cache_data(ttl=60)
def _load_bq_review():
    return _run_bq(f"SELECT * FROM `{_REVIEW}` WHERE review_status='pending' ORDER BY created_at DESC LIMIT 300")


# ════════════════════════════════════════════════════════════════════════════
# PROCESSING PROGRESS BAR
# ════════════════════════════════════════════════════════════════════════════
_PROCESSING = f"{_PROJECT}.{_DATASET}.processing_runs"

@st.cache_data(ttl=8)   # short TTL so it refreshes automatically while running
def _load_latest_run() -> pd.DataFrame:
    active = _run_bq(f"""
        SELECT * FROM `{_PROCESSING}`
        WHERE status IN ('running','processing','in_progress','started')
          AND created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 12 HOUR)
        ORDER BY created_at DESC LIMIT 1""")
    if not active.empty:
        return active
    return _run_bq(f"SELECT * FROM `{_PROCESSING}` ORDER BY created_at DESC LIMIT 1")


def _normalize_ts(val):
    if pd.isna(val): return None
    if hasattr(val, "to_pydatetime"): val = val.to_pydatetime()
    if isinstance(val, datetime):
        if val.tzinfo is None: return val.replace(tzinfo=timezone.utc)
        return val.astimezone(timezone.utc)
    return None


def render_processing_progress(key_suffix: str = "default") -> None:
    pr_df = _load_latest_run()
    if pr_df is None or pr_df.empty:
        return

    run = pr_df.iloc[0]

    status = "" if pd.isna(run.get("status")) else str(run.get("status", "")).strip()
    stage = "" if pd.isna(run.get("current_stage")) else str(run.get("current_stage", "")).strip()
    rows_p = 0 if pd.isna(run.get("rows_processed")) else int(run.get("rows_processed", 0))
    rows_t = 0 if pd.isna(run.get("rows_total")) else int(run.get("rows_total", 0))
    run_id = "run" if pd.isna(run.get("run_id")) else str(run.get("run_id", "run"))

    _fname_raw = (
        run.get("source_file")
        or run.get("file_name")
        or run.get("filename")
        or run.get("input_file")
        or ""
    )
    file_name = "" if pd.isna(_fname_raw) else str(_fname_raw).split("/")[-1]

    raw_pct = run.get("progress_pct")
    if pd.isna(raw_pct):
        pct = (rows_p / rows_t * 100.0) if rows_t > 0 else 0.0
    else:
        pct = float(raw_pct)
    pct = max(0.0, min(pct, 100.0))

    updated_dt = _normalize_ts(run.get("updated_at")) or _normalize_ts(run.get("created_at"))
    eff_status = status.lower()

    if eff_status in ("running", "processing", "in_progress", "started") and updated_dt:
        if datetime.now(timezone.utc) - updated_dt > timedelta(minutes=10):
            eff_status = "stale"

    is_active = eff_status in ("running", "processing", "in_progress", "started")

    if eff_status in ("completed", "done", "success"):
        label = "הושלם"; icon = "✅"
    elif eff_status in ("failed", "error"):
        label = "נכשל"; icon = "❌"
    elif eff_status == "stale":
        label = "לא מתעדכן"; icon = "⚠️"
    else:
        label = "בריצה"; icon = "⏳"

    rows_text = f"{rows_p:,} / {rows_t:,} שורות" if rows_t > 0 else f"{rows_p:,} שורות"

    with st.container():
        st.markdown("""
        <div style="background:var(--card);border:1px solid var(--border);border-radius:var(--radius);
                    padding:1rem 1.25rem;margin-bottom:1rem;box-shadow:var(--shadow-card);">
        """, unsafe_allow_html=True)

        top_l, top_r = st.columns([5, 2])
        with top_l:
            title_line = f"{icon} **{label}**"
            if stage:
                title_line += f" · {stage}"
            if is_active:
                title_line += " · מתרענן אוטומטית"
            st.markdown(title_line)
            if file_name:
                st.caption(f"📄 {file_name}")
        with top_r:
            st.markdown(
                f"<div style='text-align:left;direction:ltr;color:var(--muted-fg);font-size:.9rem;'>"
                f"{rows_text} &nbsp;·&nbsp; <b>{pct:.1f}%</b></div>",
                unsafe_allow_html=True,
            )

        st.progress(pct / 100.0)

        btn_col1, btn_col2 = st.columns([6, 1])
        with btn_col2:
            if st.button("רענן", key=f"refresh_prog_{key_suffix}_{run_id}", use_container_width=True):
                _load_latest_run.clear()
                st.session_state["_stay_on_upload"] = True
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

    if is_active:
        components.html(
            """
            <script>
                setTimeout(function() {
                    const parentDoc = window.parent.document;
                    const buttons = Array.from(parentDoc.querySelectorAll('button'));
                    const btn = buttons.find(b => b.innerText.trim() === "רענן");
                    if (btn) { btn.click(); }
                }, 12000);
            </script>
            """,
            height=0,
            width=0,
        )

# ════════════════════════════════════════════════════════════════════════════
# LOGIN PAGE
# ════════════════════════════════════════════════════════════════════════════
# ── Normal login ──
# ════════════════════════════════════════════════════════════════════════════
# LOGIN PAGE
# ════════════════════════════════════════════════════════════════════════════
def render_login():
    # ── Change-password mode ──
    if st.session_state.get("change_password_mode"):
        _, col, _ = st.columns([1, 2, 1])
        with col:
            st.markdown(f"<div style='text-align:center;margin:2rem 0 1.5rem;'>{render_logo(140)}</div>", unsafe_allow_html=True)
            st.markdown("### 🔒 החלפת סיסמה ראשונית")
            new_p = st.text_input("הזן סיסמה חדשה", type="password")
            if st.button("עדכן סיסמה וכנס", type="primary", use_container_width=True):
                if len(new_p) >= 4 and new_p != "1234":
                    if _update_password(st.session_state["temp_email"], new_p):
                        st.session_state.update({
                            "logged_in": True,
                            "display_name": st.session_state["temp_name"],
                            "user_role": st.session_state["temp_role"],
                            "user_email": st.session_state["temp_email"],
                            "change_password_mode": False,
                        })
                        st.rerun()
                else:
                    st.error("סיסמה חייבת להיות לפחות 4 תווים ושונה מ-1234")
        st.stop()
        return

    # ── Normal login ──
    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown(f"<div style='text-align:center;margin:2rem 0 1.5rem;'>{render_logo(140)}</div>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center;color:var(--muted-fg);margin-bottom:1.5rem;'>נתיבי ישראל — מעקב פליטות פחמן</p>", unsafe_allow_html=True)
        
        # === טופס התחברות מסודר שפותר את בעיית הלחיצה הכפולה ===
        with st.form("login_form"):
            email    = st.text_input("כתובת אימייל", placeholder="your@email.com")
            password = st.text_input("סיסמה", type="password", placeholder="••••••••")
            submitted = st.form_submit_button("היכנס למערכת", type="primary", use_container_width=True)

        if submitted:
            if email and password:
                user = _get_user(email)
                if user and password == user.get("password"):
                    if user.get("is_first_login"):
                        st.session_state.update({
                            "temp_email": email, "temp_name": user.get("name"),
                            "temp_role": user.get("role"), "change_password_mode": True,
                        })
                        st.rerun()
                    else:
                        st.session_state.update({
                            "logged_in": True,
                            "display_name": user.get("name", email.split("@")[0]),
                            "user_role": user.get("role","management"),
                            "user_email": email, "change_password_mode": False,
                        })
                        st.rerun()
                else:
                    st.error("אימייל או סיסמה שגויים")
            else:
                st.error("יש להזין אימייל וסיסמה")

        st.markdown('<p style="text-align:center;color:var(--muted-fg);font-size:.75rem;margin-top:1.5rem;">🛣️ מערכת ניהול פליטות פחמן — נתיבי ישראל</p>', unsafe_allow_html=True)
# ════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ════════════════════════════════════════════════════════════════════════════
def render_dashboard():
    # ── Load data – cached in session_state to avoid repeated BQ calls ──
    if "_emissions_df" not in st.session_state or "_review_df" not in st.session_state:
        try:
            emissions_df = _load_bq_emissions()
            review_df    = _load_bq_review()
            data_source  = f"BigQuery · {_PROJECT}"
            if emissions_df.empty: raise ValueError("empty")
        except Exception:
            emissions_df, review_df, data_source = load_data()
        st.session_state["_emissions_df"]  = emissions_df
        st.session_state["_review_df"]     = review_df
        st.session_state["_data_source"]   = data_source
    else:
        emissions_df = st.session_state["_emissions_df"]
        review_df    = st.session_state["_review_df"]
        data_source  = st.session_state.get("_data_source", f"BigQuery · {_PROJECT}")

    for c in ["project_name","contractor","region","category"]:
        if c not in emissions_df.columns: emissions_df[c] = "Unknown"
    for c in ["weight_kg","emission_co2e","reliability_score","year"]:
        if c not in emissions_df.columns: emissions_df[c] = 0
    if emissions_df.empty:
        emissions_df, review_df = build_mock_emissions(), build_mock_review()

    emissions_df["year"]         = pd.to_numeric(emissions_df["year"],         errors="coerce").fillna(2026).astype(int)
    emissions_df["weight_kg"]    = pd.to_numeric(emissions_df["weight_kg"],    errors="coerce").fillna(0)
    emissions_df["emission_co2e"]= pd.to_numeric(emissions_df["emission_co2e"],errors="coerce").fillna(0)

    # ── Sidebar ──
    with st.sidebar:
        display_name = st.session_state.get("display_name", "Admin")
        user_role_key = st.session_state.get("user_role", "management")
        user_role_label = ROLE_DISPLAY.get(user_role_key, user_role_key)

        projects    = sorted(emissions_df["project_name"].dropna().unique())
        contractors = sorted(emissions_df["contractor"].dropna().unique())
        regions     = sorted(emissions_df["region"].dropna().unique())
        categories  = sorted(emissions_df["category"].dropna().unique())
        years       = sorted(emissions_df["year"].unique().tolist())

        st.markdown(f"""
        <div class="sidebar-panel">
          <div class="sidebar-header-card">
            <div class="sidebar-brand-row">
              {render_logo(40)}
              <div>
                <div style="font-weight:700;font-size:.95rem;color:#fff;">CarbonTrack</div>
                <div style="font-size:.72rem;color:rgba(255,255,255,.5);">נתיבי ישראל</div>
              </div>
            </div>
            <div class="sidebar-user-row">
              <div class="sidebar-avatar">👤</div>
              <div>
                <div style="font-size:.875rem;font-weight:600;color:#fff;">{display_name}</div>
                <div style="font-size:.72rem;color:rgba(255,255,255,.5);">{user_role_label}</div>
              </div>
            </div>
          </div>
        </div>""", unsafe_allow_html=True)

        total_active_filters = sum([
            len(st.session_state.get("sb_projects", [])),
            len(st.session_state.get("sb_contractors", [])),
            len(st.session_state.get("sb_regions", [])),
            len(st.session_state.get("sb_categories", [])),
        ])
        st.markdown(
            f'<div class="sidebar-section-title">🔎 מסננים <span class="sidebar-count-badge">{total_active_filters}</span></div>',
            unsafe_allow_html=True,
        )

        with st.expander("פרויקט", expanded=False):
            sel_proj = st.multiselect("פרויקט", projects, key="sb_projects", label_visibility="collapsed")
        with st.expander("קבלן", expanded=False):
            sel_cont = st.multiselect("קבלן", contractors, key="sb_contractors", label_visibility="collapsed")
        with st.expander("אזור", expanded=False):
            sel_reg = st.multiselect("אזור", regions, key="sb_regions", label_visibility="collapsed")
        with st.expander("קטגוריה", expanded=False):
            sel_cat = st.multiselect("קטגוריה", categories, key="sb_categories", label_visibility="collapsed")
        with st.expander("שנה וספי בקרה", expanded=True):
            sel_years = st.multiselect("שנה", years, default=years, key="sb_years")
            reliability_thr = st.slider("סף אמינות", 0.50, 1.00, 0.85, 0.01, key="sb_reliability")

        c1, c2 = st.columns(2)
        with c1:
            if st.button("נקה מסננים", use_container_width=True, key="clear_sidebar_filters"):
                for k, default in {
                    "sb_projects": [],
                    "sb_contractors": [],
                    "sb_regions": [],
                    "sb_categories": [],
                    "sb_years": years,
                    "sb_reliability": 0.85,
                }.items():
                    st.session_state[k] = default
                st.rerun()
        with c2:
            if st.button("התנתק", use_container_width=True, key="logout_sidebar"):
                st.session_state["logged_in"] = False
                st.rerun()

        st.caption(f"מקור נתונים: {data_source}")

    # ── Filter ──
    df = emissions_df.copy()
    if sel_proj:  df = df[df["project_name"].isin(sel_proj)]
    if sel_cont:  df = df[df["contractor"].isin(sel_cont)]
    if sel_reg:   df = df[df["region"].isin(sel_reg)]
    if sel_cat:   df = df[df["category"].isin(sel_cat)]
    if sel_years: df = df[df["year"].isin(sel_years)]

    cur_year = datetime.now().year
    yearly   = df[df["year"]==cur_year]["emission_co2e"].sum()
    total_e  = df["emission_co2e"].sum()
    total_w  = df["weight_kg"].sum()
    rev_n    = len(review_df)

    # ── Hero header ──
    api_url = os.getenv("API_BASE_URL","")
    st.markdown(f"""
    <div class="hero-header">
      <div class="hero-brand" dir="rtl">
        {render_logo(72)}
        <div>
          <div class="hero-title">Carbon₂Track <span style="font-size:.65rem;font-weight:400;background:hsl(142,55%,35%,.3);padding:.1rem .5rem;border-radius:999px;">BI</span></div>
          <div class="hero-subtitle">מערכת ניתוח פליטות פחמן • נתיבי ישראל</div>
        </div>
        <div class="hero-stats">
          <div class="hero-stat">
            <span style="color:hsl(152,60%,50%)">↓</span>
            <div>
              <div class="hero-stat-label">סה״כ פליטות</div>
              <div class="hero-stat-value">{total_e/1000:,.0f}t CO₂e</div>
            </div>
          </div>
          <div class="hero-stat">
            <span style="color:hsl(152,60%,50%)">◎</span>
            <div>
              <div class="hero-stat-label">רשומות</div>
              <div class="hero-stat-value">{len(df):,}</div>
            </div>
          </div>
          <div class="hero-stat">
            <span style="color:hsl(152,60%,50%)">↓</span>
            <div>
              <div class="hero-stat-label">מגמה</div>
              <div class="hero-stat-value" style="color:hsl(152,60%,50%)">↓ 8.3%</div>
            </div>
          </div>
        </div>
      </div>
    </div>""", unsafe_allow_html=True)

    # ── Tabs ──
    # After refresh on upload tab, jump back to it via JS
    if st.session_state.pop("_stay_on_upload", False):
        st.markdown("""
        <script>
        setTimeout(function() {
            var tabs = window.parent.document.querySelectorAll('[data-baseweb="tab"]');
            for (var i = 0; i < tabs.length; i++) {
                if (tabs[i].innerText.indexOf('\u2601') > -1) { tabs[i].click(); break; }
            }
        }, 100);
        </script>""", unsafe_allow_html=True)

    tab_dash, tab_review, tab_whatif, tab_upload, tab_data, tab_settings = st.tabs([
        "📊 דאשבורד", f"✅ Review ({rev_n})", "⇄ What-If", "☁️ קליטת קבצים", "📋 נתונים", "⚙️ הגדרות"
    ])

    # ════ TAB: DASHBOARD ════
    with tab_dash:
        k1, k2, k3, k4 = st.columns(4)
        with k1: kpi(f"פליטות {cur_year}", f"{yearly/1000:,.0f}t", "kg CO₂e", variant="primary")
        with k2: kpi('סה"כ פליטות', f"{total_e/1000:,.0f}t", "מתחילת הפרויקט", trend="down", trend_val="↓ 8.3%")
        with k3: kpi("משקל חומרים", f"{total_w/1000:,.0f}t", 'ק"ג')
        with k4: kpi("שורות Review", f"{rev_n:,}", "ממתינות לאישור", variant="accent" if rev_n==0 else "default")

        st.markdown("<div style='height:.75rem'></div>", unsafe_allow_html=True)

        c1, c2 = st.columns([3, 2])
        with c1:
            st.markdown('<div class="card-surface"><div class="section-title">📊 פליטות לפי פרויקט</div>', unsafe_allow_html=True)

            proj_agg = df.groupby("project_name", as_index=False).agg(
                emission_co2e=("emission_co2e", "sum"),
                weight_kg=("weight_kg", "sum"),
            ).reset_index(drop=True)
            proj_agg["emission_per_ton"] = proj_agg.apply(
                lambda r: r["emission_co2e"] / (r["weight_kg"] / 1000) if r["weight_kg"] > 0 else 0,
                axis=1,
            )

            view_mode = st.radio(
                "תצוגה",
                ["סה״כ פליטות (t CO₂e)", "נורמלי לטון חומר (kg CO₂e / t)"],
                horizontal=True, key="proj_view_mode",
                help="נורמלי לטון: כמה פחמן נפלט לכל טון חומר — השוואה הוגנת בין גשר קטן לכביש ארוך",
            )

            if view_mode.startswith("סה"):
                plot_df = proj_agg.sort_values("emission_co2e", ascending=True).reset_index(drop=True)
                x_vals  = (plot_df["emission_co2e"] / 1000).tolist()
                x_text  = [f"{v:.1f}t" for v in x_vals]
                bar_col = "hsl(142,55%,35%)"
                x_sfx   = "t CO₂e"
            else:
                plot_df = proj_agg.sort_values("emission_per_ton", ascending=True).reset_index(drop=True)
                x_vals  = plot_df["emission_per_ton"].tolist()
                x_text  = [f"{v:.0f}" for v in x_vals]
                bar_col = "hsl(85,50%,45%)"
                x_sfx   = "kg CO₂e / t"

            if not plot_df.empty:
                y_labels = plot_df["project_name"].tolist()
                # dynamic height: min 200px, 52px per project
                chart_h  = max(200, len(y_labels) * 52)
                fig = go.Figure(go.Bar(
                    x=x_vals,
                    y=y_labels,
                    orientation="h",
                    marker_color=bar_col,
                    text=x_text,
                    textposition="outside",
                ))
                _base_layout(fig, chart_h)
                fig.update_yaxes(type="category", automargin=True)
                fig.update_xaxes(title=x_sfx, rangemode="tozero")
                # add padding on right so text labels don't get clipped
                fig.update_layout(margin=dict(l=10, r=80, t=20, b=40))
                st.plotly_chart(fig, use_container_width=True)

            if not view_mode.startswith("סה"):
                st.caption("💡 נורמלי לטון: מאפשר להשוות פרויקטים בגדלים שונים — ק״ג CO₂e לכל טון חומר.")

            st.markdown('</div>', unsafe_allow_html=True)

        with c2:
            st.markdown('<div class="card-surface"><div class="section-title">🧱 פילוח חומרים</div>', unsafe_allow_html=True)
            cat = df.groupby("category", as_index=False)["emission_co2e"].sum()
            if not cat.empty:
                fig = go.Figure(go.Pie(
                    labels=cat["category"], values=cat["emission_co2e"],
                    hole=.45, marker_colors=COLORS,
                    textfont=dict(size=11),
                ))
                _base_layout(fig, 320)
                st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("<div style='height:.75rem'></div>", unsafe_allow_html=True)
        d1, d2 = st.columns([2, 1])
        with d1:
            st.markdown('<div class="card-surface"><div class="section-title">🗺️ פליטות לפי אזור</div>',
                        unsafe_allow_html=True)
            reg = df.groupby("region", as_index=False)["emission_co2e"].sum()
            reg_dict = {str(r["region"]): float(r["emission_co2e"]) for _, r in reg.iterrows()}
            max_e = max(reg_dict.values()) if reg_dict else 1

            def _map_color(val, mx):
                if mx == 0: return "#d4edda"
                t = val / mx
                r = int(200 - t * 155)
                g = int(230 - t * 100)
                b = int(200 - t * 165)
                return f"rgb({r},{g},{b})"

            nc = _map_color(reg_dict.get("צפון", 0), max_e)
            cc = _map_color(reg_dict.get("מרכז", 0), max_e)
            sc = _map_color(reg_dict.get("דרום", 0), max_e)
            ne = reg_dict.get("צפון", 0)
            ce = reg_dict.get("מרכז", 0)
            se = reg_dict.get("דרום", 0)

            israel_svg = dedent(f"""
            <div style="display:flex;justify-content:center;align-items:center;height:100%;padding:.25rem 0;">
            <svg viewBox="0 0 220 520" xmlns="http://www.w3.org/2000/svg"
                 style="width:100%;max-width:220px;display:block;margin:0 auto;filter:drop-shadow(0 2px 6px rgba(0,0,0,.12));">
              <defs>
                <style>
                  .reg {{ cursor:default; stroke:#ffffff; stroke-width:3; stroke-linejoin:round; }}
                  .reg-label {{ font-family:Heebo, sans-serif; font-size:18px; font-weight:800; fill:#1f2937; text-anchor:middle; }}
                  .reg-sub {{ font-family:Heebo, sans-serif; font-size:14px; fill:#4b5563; text-anchor:middle; }}
                  .legend {{ font-family:Heebo, sans-serif; font-size:12px; fill:#4b5563; }}
                </style>
                <linearGradient id="lgnd" x1="0" x2="1" y1="0" y2="0">
                  <stop offset="0%" stop-color="rgb(226,243,229)"/>
                  <stop offset="100%" stop-color="rgb(27,94,32)"/>
                </linearGradient>
              </defs>

              <path class="reg" fill="{nc}" d="M 90,10 L 115,8  L 140,12  L 160,22  L 170,40  L 168,58 L 155,70  L 148,80  L 138,88 L 125,95  L 112,100 L 100,103 L 88,100 L 78,92  L 68,82 L 60,70  L 55,58  L 55,45 L 58,30  L 70,18  Z"/>
              <text class="reg-label" x="112" y="48">צפון</text>
              <text class="reg-sub" x="112" y="68">{ne / 1000:,.0f}t CO₂e</text>

              <path class="reg" fill="{cc}" d="M 88,100 L 100,103 L 112,100 L 125,95 L 138,88  L 148,80 L 152,100 L 155,118 L 150,135 L 145,150 L 140,165 L 136,178 L 125,185 L 112,188 L 100,186 L 88,183 L 78,175 L 72,162 L 68,148 L 65,132 L 65,115 L 68,105 Z"/>
              <text class="reg-label" x="110" y="138">מרכז</text>
              <text class="reg-sub" x="110" y="158">{ce / 1000:,.0f}t CO₂e</text>

              <path class="reg" fill="{sc}" d="M 78,175 L 88,183 L 100,186 L 112,188 L 125,185 L 136,178 L 140,195 L 142,212 L 140,230 L 138,250 L 134,270 L 130,290 L 125,310 L 118,330 L 112,355 L 108,380 L 105,405 L 102,425 L 99,445 L 97,465 L 95,490 L 92,510 L 88,490 L 85,468 L 82,445 L 78,420 L 74,395 L 70,370 L 65,348 L 60,325 L 55,302 L 52,278 L 50,255 L 50,230 L 52,208 L 55,192 L 62,182 L 72,178 Z"/>
              <text class="reg-label" x="96" y="340">דרום</text>
              <text class="reg-sub" x="96" y="360">{se / 1000:,.0f}t CO₂e</text>

              <rect x="18" y="18" width="72" height="12" rx="6" fill="url(#lgnd)"/>
              <text class="legend" x="18" y="42">פחות</text>
              <text class="legend" x="64" y="42">יותר</text>
            </svg>
            </div>
            """)

            mc1, mc2 = st.columns([1, 1])
            with mc1:
                components.html(israel_svg, height=560, scrolling=False)
            with mc2:
                if not reg.empty:
                    reg_sorted = reg.sort_values("emission_co2e", ascending=False).reset_index(drop=True)
                    fig2 = px.bar(reg_sorted, x="region", y="emission_co2e",
                                  color="region", color_discrete_sequence=COLORS, text_auto=".2s")
                    fig2.update_traces(marker_line_width=0, width=0.6)
                    _base_layout(fig2, 260)
                    fig2.update_xaxes(title="")
                    fig2.update_yaxes(title="")
                    fig2.update_layout(showlegend=False, margin=dict(l=5, r=5, t=10, b=30))
                    st.plotly_chart(fig2, use_container_width=True)

            st.markdown('</div>', unsafe_allow_html=True)
    # ════ bottom: delete project rows in the table ════
    st.sidebar.title("🛠️ ניהול בסיס נתונים")

    # 1. שליפת פרויקטים (כמו קודם)
    try:
        client = bigquery.Client()
        query = "SELECT DISTINCT project_name FROM `argon-ace-483810-n9.netivei_emissions_db.emissions_details`"
        results = client.query(query).result()
        projects_list = [row.project_name for row in results]
        
        # בדיקה ויזואלית זמנית - תמחקי אחרי שזה עובד
        if not projects_list:
            st.sidebar.warning("השאילתה חזרה ריקה - האם הטבלה emissions_details באמת מכילה שורות?")
        else:
            st.sidebar.success(f"נמצאו {len(projects_list)} פרויקטים")

    except Exception as e:
        # זה יציג לך את השגיאה המדויקת (למשל: Access Denied או Not Found)
        st.sidebar.error(f"שגיאת BigQuery: {e}")
        projects_list = []
        
    # התיקון: שורה אחת בלבד עם key ייחודי
    selected_project = st.sidebar.selectbox("בחר פרויקט למחיקה:", options=[""] + projects_list, key="unique_del_box")
# ברגע שנבחר פרויקט (ולא נבחרה השורה הריקה)
    if selected_project:
        # מציג את כפתור המחיקה הראשי
        if st.sidebar.button(f"מחק את {selected_project}", type="primary", use_container_width=True):
            st.session_state["show_confirm"] = True

        # אם לחצו על הכפתור, נפתח אזור אישור קטן
        if st.session_state.get("show_confirm", False):
            st.sidebar.warning(f"⚠️ האם למחוק את כל הנתונים של {selected_project}?")
            
            # כפתורי אישור וביטול
            c1, c2 = st.sidebar.columns(2)
            if c1.button("✅ כן, מחק", type="primary", use_container_width=True):
                url = "https://calc-carbon-140293665526.me-west1.run.app/manage-db"
                payload = {"action": "delete_project", "project_name": selected_project}
                
                with st.spinner("שולח פקודת מחיקה לשרת..."):
                    try:
                        # שליחת הבקשה לשרת
                        res = requests.post(url, json=payload)
                        
                        # עכשיו נבדוק מה השרת ענה באמת
                        if res.status_code == 200:
                            st.sidebar.success("✅ השרת אישר: נמחק בהצלחה!")
                            st.session_state["show_confirm"] = False
                            _load_bq_emissions.clear(); st.session_state.pop("_emissions_df", None); st.session_state.pop("_review_df", None) # מרענן
                            st.rerun()
                        else:
                            # אם השרת החזיר שגיאה (כמו 400, 404, 500)
                            st.sidebar.error(f"❌ שגיאה מהשרת! קוד סטטוס: {res.status_code}")
                            st.sidebar.write(f"תוכן השגיאה: {res.text}")
                            
                    except Exception as e:
                        # אם אין בכלל תקשורת עם השרת (כתובת שגויה, שרת למטה)
                        st.sidebar.error("❌ אין תקשורת עם השרת (Cloud Run)!")
                        st.sidebar.write(f"פרטי השגיאה: {e}")
    # ════ TAB: REVIEW ════
    with tab_review:
        if review_df.empty:
            st.markdown("""
            <div class="card-surface" style="text-align:center;padding:3rem;">
              <div style="font-size:3rem;margin-bottom:1rem;">✅</div>
              <div style="font-weight:600;font-size:1rem;">אין שורות שמחכות ל-Review</div>
              <div style="color:var(--muted-fg);font-size:.875rem;margin-top:.5rem;">כל הנתונים אושרו</div>
            </div>""", unsafe_allow_html=True)
        else:
            # ── Summary charts ──
            rc1, rc2 = st.columns([2, 1])
            with rc1:
                if "review_reason" in review_df.columns:
                    reason_counts = review_df["review_reason"].value_counts().reset_index()
                    reason_counts.columns = ["reason","count"]
                    fig = px.bar(reason_counts, x="reason", y="count", text_auto=True, color_discrete_sequence=[COLORS[0]])
                    _base_layout(fig, 280)
                    st.plotly_chart(fig, use_container_width=True)
            with rc2:
                _scores = pd.to_numeric(review_df["reliability_score"], errors="coerce") if "reliability_score" in review_df.columns else pd.Series([0.0]*len(review_df), index=review_df.index)
                low = review_df[_scores.fillna(0) < reliability_thr]
                st.markdown(f"""
                <div class="card-surface">
                  <div><b>ממתינים לאישור:</b> {len(review_df):,}</div>
                  <div style="margin-top:.5rem;"><b>מתחת לסף ({reliability_thr:.2f}):</b> {len(low):,}</div>
                </div>""", unsafe_allow_html=True)

            # ── Filters ──
            st.markdown("---")
            f1, f2, f3, f4 = st.columns([2, 1, 1, 1])
            with f1:
                rev_search = st.text_input("🔍 חיפוש חופשי", placeholder="שם חומר, קוד בוק...", key="rev_search", label_visibility="collapsed")
            with f2:
                rev_proj_opts = ["הכל"] + sorted(review_df["project_name"].dropna().unique().tolist()) if "project_name" in review_df.columns else ["הכל"]
                rev_proj = st.selectbox("פרויקט", rev_proj_opts, key="rev_proj")
            with f3:
                rev_cat_opts = ["הכל"] + sorted(review_df["suggested_category"].dropna().unique().tolist()) if "suggested_category" in review_df.columns else ["הכל"]
                rev_cat = st.selectbox("קטגוריה", rev_cat_opts, key="rev_cat")
            with f4:
                rev_score_filter = st.selectbox("ציון אמינות", ["הכל", "נמוך (<80%)", "בינוני (80-90%)", "גבוה (>90%)"], key="rev_score_f")

            # Apply filters
            filtered_review = review_df.copy()
            if rev_search:
                _mask = pd.Series([False]*len(filtered_review), index=filtered_review.index)
                for col in ["material","short_text","boq_code","suggested_category","project_name"]:
                    if col in filtered_review.columns:
                        _mask |= filtered_review[col].astype(str).str.contains(rev_search, case=False, na=False)
                filtered_review = filtered_review[_mask]
            if rev_proj != "הכל" and "project_name" in filtered_review.columns:
                filtered_review = filtered_review[filtered_review["project_name"] == rev_proj]
            if rev_cat != "הכל" and "suggested_category" in filtered_review.columns:
                filtered_review = filtered_review[filtered_review["suggested_category"] == rev_cat]
            if rev_score_filter != "הכל" and "reliability_score" in filtered_review.columns:
                _sc = pd.to_numeric(filtered_review["reliability_score"], errors="coerce").fillna(0)
                if rev_score_filter == "נמוך (<80%)":
                    filtered_review = filtered_review[_sc < 0.80]
                elif rev_score_filter == "בינוני (80-90%)":
                    filtered_review = filtered_review[(_sc >= 0.80) & (_sc < 0.90)]
                else:
                    filtered_review = filtered_review[_sc >= 0.90]

            st.markdown(f"<p style='color:var(--muted-fg);font-size:.875rem;margin:.75rem 0;'>מוצגות {len(filtered_review):,} מתוך {len(review_df):,} שורות</p>", unsafe_allow_html=True)

            for _, row in filtered_review.iterrows():
                score = float(row.get("reliability_score", 0))
                score_cls = "score-low" if score < 0.8 else "score-mid" if score < 0.9 else "score-high"
                spread = row.get("factor_spread_pct", "—")
                cands  = row.get("climatiq_candidate_count", "—")
                st.markdown(f"""
                <div class="review-card">
                  <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                    <div>
                      <div style="font-weight:600;font-size:.9375rem;">{row.get('short_text','')}</div>
                      <div class="review-meta">{row.get('project_name','')} • {row.get('boq_code','')}</div>
                    </div>
                    <span class="badge-warn">⚠ דורש בדיקה</span>
                  </div>
                  <div class="review-grid">
                    <div><div class="review-field-label">קטגוריה מוצעת</div><div class="review-field-value">{row.get('suggested_category','')}</div></div>
                    <div><div class="review-field-label">יחידה מוצעת</div><div class="review-field-value">{row.get('suggested_uom','')}</div></div>
                    <div><div class="review-field-label">ציון אמינות</div><div class="review-field-value {score_cls}" dir="ltr">{score*100:.0f}%</div></div>
                    <div><div class="review-field-label">סיבת Review</div><div class="review-field-value">{row.get('review_reason','')}</div></div>
                  </div>
                  <div style="display:flex;gap:1rem;font-size:.75rem;color:var(--muted-fg);padding-top:.75rem;border-top:1px solid var(--border);">
                    <span>פיזור פקטור: <b dir="ltr">{spread}%</b></span>
                    <span>מועמדים Climatiq: <b>{cands}</b></span>
                  </div>
                </div>""", unsafe_allow_html=True)
                bc1, bc2, _ = st.columns([1, 1, 4])
                with bc1: st.button("✓ אשר", key=f"ap_{row.get('review_id','')}", type="primary")
                with bc2: st.button("✗ דחה", key=f"rj_{row.get('review_id','')}")

    # ════ TAB: WHAT-IF ════
    with tab_whatif:
        st.markdown('<div class="section-title">⇄ סימולטור חלופות חומרים (What-If)</div>', unsafe_allow_html=True)
        st.caption("השוואת פליטה נוכחית מול חומר חלופי על בסיס פקטור היסטורי ממאגר הנתונים")

        all_cats = sorted(emissions_df["category"].unique())
        cur_cats = sorted(df["category"].unique()) if not df.empty else all_cats

        w1, w2, w3 = st.columns(3)
        with w1:
            st.markdown("**1. מצב נוכחי**")
            src = st.selectbox("חומר קיים", cur_cats, key="wi_src")
            src_sub  = df[df["category"]==src]
            curr_e   = src_sub["emission_co2e"].sum()
            curr_w   = src_sub["weight_kg"].sum()
            kpi("פליטה נוכחית", f"{curr_e:,.0f} kg", src, variant="primary")
            st.caption(f"משקל נוכחי: {curr_w:,.0f} ק״ג")

        with w2:
            st.markdown("**2. חלופה מוצעת**")
            alt = st.selectbox("חומר חלופי", all_cats, key="wi_alt")
            alt_sub    = emissions_df[emissions_df["category"]==alt]
            alt_w_tot  = alt_sub["weight_kg"].sum()
            alt_e_tot  = alt_sub["emission_co2e"].sum()
            alt_factor = alt_e_tot / alt_w_tot if alt_w_tot > 0 else 0
            eff_qty    = st.number_input("כמות חלופית (ק״ג)", value=float(curr_w), min_value=0.0, step=1000.0, key="wi_qty")
            proj_e     = eff_qty * alt_factor
            kpi("פליטה חלופית צפויה", f"{proj_e:,.0f} kg", f"פקטור: {alt_factor:.4f}")
            st.caption(f"פקטור: {alt_factor:.4f} kg CO₂e / kg")

        with w3:
            st.markdown("**3. שורת הרווח הסביבתי**")
            diff = curr_e - proj_e
            if diff > 0:
                st.success(f"✅ חיסכון: {diff:,.0f} kg")
                pct = abs(diff/curr_e*100) if curr_e else 0
                st.caption(f"ירידה של {pct:.1f}% מהפליטה הנוכחית")
            elif diff < 0:
                st.error(f"⚠️ תוספת: {abs(diff):,.0f} kg")
                pct = abs(diff/curr_e*100) if curr_e else 0
                st.caption(f"עלייה של {pct:.1f}% מהפליטה הנוכחית")
            else:
                st.info("אין שינוי בפליטות")

    # ════ TAB: UPLOAD ════
    with tab_upload:
        st.markdown('<div class="section-title">☁️ קליטת קובץ חדש</div>', unsafe_allow_html=True)
        st.caption("העלאת קובץ אקסל/CSV לחישוב פליטות פחמן אוטומטי")

        render_processing_progress("upload")

        up1, up2 = st.columns(2)
        with up1:
            input_project    = st.text_input("שם הפרויקט *", placeholder="לדוגמה: כביש 6 - מקטע צפון", key="up_proj")
            input_contractor = st.text_input("קבלן מבצע", placeholder="שם הקבלן", key="up_cont")
        with up2:
            input_region = st.selectbox("אזור", ["צפון","מרכז","דרום",'יו"ש'], key="up_region")
            source_mode_label = st.selectbox(
                "סוג קובץ",
                ["אוטומטי","כתב כמויות","כתב שנתי 2025 / שולם בפועל"],
                key="up_mode_label",
            )
            st.caption('במצב כתב כמויות, אם קיימים מק"ט/תיאור/יחידה תואמים מהאקסל השנתי, המערכת תעדיף אותם כ-reference.')
            uploaded_file = st.file_uploader("בחר קובץ אקסל/CSV", type=["xlsx","xls","csv"], key="up_file")

        if st.button("🚀 חשב פליטות ושמור", type="primary", key="upload_calculate_button"):
            if not input_project:
                st.warning("יש להזין שם פרויקט")
            elif uploaded_file is None:
                st.warning("יש לבחור קובץ")
            else:
                _mode_map = {"אוטומטי":"auto","כתב כמויות":"boq","כתב שנתי 2025 / שולם בפועל":"annual_paid_2025"}
                sel_mode = _mode_map.get(source_mode_label, "auto")
                try:
                    from google.cloud import storage as _gcs
                    _gcs.Client(project=_PROJECT).bucket("green_excal").blob(uploaded_file.name).upload_from_file(uploaded_file, rewind=True)
                    payload = {
                        "bucket": "green_excal", "file": uploaded_file.name,
                        "uploader_email": st.session_state.get("user_email",""),
                        "project_name": input_project, "contractor": input_contractor,
                        "region": input_region, "source_mode": sel_mode,
                        "measurement_basis": "paid_2025" if sel_mode=="annual_paid_2025" else "boq",
                        "reliability_threshold": float(st.session_state.get("reliability_threshold",0.85)),
                        "max_climatiq_candidates": int(st.session_state.get("max_climatiq_candidates",5)),
                        "max_factor_spread_pct": float(st.session_state.get("max_factor_spread_pct",15.0)),
                        "auto_write_ai_approved": bool(st.session_state.get("auto_write_ai_approved",True)),
                    }
                    with st.spinner("מנתח קובץ מול מנוע החומרים וה-AI..."):
                        resp = requests.post("https://calc-carbon-140293665526.me-west1.run.app", json=payload, timeout=900)
                        res  = resp.json() if resp.headers.get("content-type","").startswith("application/json") else {"error":resp.text}
                        if not resp.ok: raise RuntimeError(res.get("error", resp.text or "שגיאה לא ידועה"))
                    st.success(f"✅ עובדו {res.get('total_rows',0):,} שורות · {res.get('needs_review_rows',0)} דורשות review")
                    if res.get("auto_learned_rows"):
                        st.info(f"נכתבו אוטומטית {res['auto_learned_rows']} מיפויים אמינים")
                    _load_bq_emissions.clear(); _load_bq_review.clear(); st.session_state.pop("_emissions_df", None); st.session_state.pop("_review_df", None)
                    st.rerun()
                except Exception as e:
                    st.error(f"שגיאה: {e}")

        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
        ic1, ic2, ic3 = st.columns(3)
        for col, icon, title, desc in [
            (ic1,"🤖","זיהוי AI","המערכת מזהה חומרים אוטומטית ומתאימה מקדמי פליטה מ-Climatiq"),
            (ic2,"🔍","Review חכם","שורות עם ציון אמינות נמוך מועברות לבדיקה ידנית"),
            (ic3,"📊","למידה מתמשכת","כל אישור ידני מעשיר את מאגר הלמידה"),
        ]:
            with col:
                st.markdown(f"""
                <div class="card-surface">
                  <div style="display:flex;align-items:center;gap:.625rem;margin-bottom:.625rem;">
                    <div style="width:2rem;height:2rem;border-radius:.5rem;background:hsl(142,55%,35%,.1);display:flex;align-items:center;justify-content:center;">{icon}</div>
                    <b style="font-size:.875rem;">{title}</b>
                  </div>
                  <p style="font-size:.75rem;color:var(--muted-fg);line-height:1.6;margin:0;">{desc}</p>
                </div>""", unsafe_allow_html=True)

    # ════ TAB: DATA ════
    with tab_data:
        st.markdown('<div class="section-title">📋 נתונים מסוננים</div>', unsafe_allow_html=True)
        st.dataframe(df, use_container_width=True, hide_index=True)

    # ════ TAB: SETTINGS ════
    with tab_settings:
        s1, s2 = st.columns(2)
        with s1:
            st.markdown('<div class="card-surface">', unsafe_allow_html=True)
            st.markdown('<div class="section-title">⚙️ ספים ופרמטרים</div>', unsafe_allow_html=True)
            st.number_input("סף אמינות לאישור אוטומטי", 0.50, 0.99, 0.85, 0.01)
            st.number_input("מקסימום תוצאות Climatiq", 1, 20, 5, 1)
            st.number_input("סטיית פקטור מותרת (%)", 1, 100, 15, 1)
            st.toggle("כתיבה אוטומטית לטבלאות", True)
            if st.button("💾 שמור הגדרות", type="primary"): st.success("נשמר")
            st.markdown('</div>', unsafe_allow_html=True)

        with s2:
            st.markdown('<div class="card-surface">', unsafe_allow_html=True)
            st.markdown('<div class="section-title">📖 קטלוג חברה / רגולטור</div>', unsafe_allow_html=True)
            st.text_input("שם חומר/סעיף", placeholder="לדוגמה: בטון B30", key="cat_mat")
            st.number_input("מקדם פליטה", 0.0, step=0.0001, format="%.4f", key="cat_fac")
            st.selectbox("מקור מועדף", ["נתון חברה (ידני)","Climatiq (אוטומטי)"], key="cat_src")
            if st.button("💾 שמור לקטלוג"): st.success("נשמר לקטלוג")

            st.markdown('<div class="section-title" style="margin-top:1.5rem;">👥 הוספת משתמש</div>', unsafe_allow_html=True)
            st.text_input("אימייל", placeholder="user@company.com", key="u_email")
            st.text_input("שם מלא", placeholder="ישראל ישראלי", key="u_name")
            st.selectbox("תפקיד", ["הנהלה","מנהל פרויקט","קיימות (ESG)","רגולטור"], key="u_role")
            if st.button("💾 שמור משתמש"): st.success("משתמש נשמר")
            st.markdown('</div>', unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════════
for _k, _v in {
    "logged_in": False, "change_password_mode": False,
    "display_name": "Admin", "user_role": "management", "user_email": "",
    "reliability_threshold": 0.85, "max_climatiq_candidates": 5,
    "max_factor_spread_pct": 15.0, "auto_write_ai_approved": True,
    "_stay_on_upload": False,
}.items():
    if _k not in st.session_state: st.session_state[_k] = _v

if st.session_state["logged_in"]:
    render_dashboard()
else:
    render_login()