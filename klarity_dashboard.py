"""
Klarity Support Report - Streamlit Dashboard v10
================================================
Run: python3 -m streamlit run klarity_dashboard.py
Requires: pip3 install requests streamlit plotly pandas

v10 changes (UI overhaul):
  - Full visual redesign: glassmorphism stat cards, gradient hero header,
    modern section headers, polished Plotly charts, elevated typography
  - Status badges as colored pills
  - Gradient top-border stat cards with icons and hover lift
  - Chart color palette upgraded: multi-tone gradient bars, softer grids
  - Tables: hover state rows, pill-style status cells, better spacing
  - All data logic, exclusion rules, and API calls unchanged from v9

v9 changes (data accuracy audit):
  - is_internal_run_failure: now uses automated_architect tag as the sole exclusion
    signal; removed subject+email heuristic that silently dropped external-customer
    run-failure tickets not yet tagged "customer"
  - res_hours: removed updated_at fallback — updated_at fires on any edit (notes,
    tags) not just resolution; only solved_at from metric_sets is used now
  - load_data broad search: uses min(since, since_4_weeks()) so the Category
    Performance section always has a full 4-week data window regardless of the
    week selector setting
  - All Open view: fetched WITHOUT a since-date so "Unsolved in Group" reflects
    the full live queue, not just tickets created since the selected week start
  - Category performance table: each row now links to a category-specific Zendesk
    search (via CAT_SEARCH_QUERY map) instead of the same generic tags:customer URL
"""

import streamlit as st
import requests
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta, date
from collections import defaultdict, Counter
import re
import urllib.parse

st.set_page_config(
    page_title="Klarity Support Report",
    page_icon="🟠",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

  /* ── Base background ── */
  .stApp, .main { background: linear-gradient(135deg, #faf9f7 0%, #f2ede6 100%) !important; }
  .block-container { background: transparent !important; padding-top: 0 !important; }

  /* ── Force light text everywhere ── */
  p, span, div, li, td, th, label, caption, small,
  h1, h2, h3, h4, h5, h6,
  .stMarkdown, .stCaption, .element-container,
  [data-testid="stText"], [data-testid="stMarkdownContainer"] {
    color: #1a1a1a !important;
  }

  /* ── HERO HEADER ── */
  .hero-header {
    background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 50%, #1a1a1a 100%);
    border-radius: 18px;
    padding: 28px 36px;
    margin-bottom: 28px;
    position: relative;
    overflow: hidden;
    box-shadow: 0 8px 32px rgba(0,0,0,0.18);
  }
  .hero-header::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, #E8612C, #f4a261, #E8612C, #c0392b);
  }
  .hero-header::after {
    content: '';
    position: absolute;
    top: -60px; right: -60px;
    width: 200px; height: 200px;
    background: radial-gradient(circle, rgba(232,97,44,0.12) 0%, transparent 70%);
    border-radius: 50%;
  }
  .hero-title {
    color: #ffffff !important;
    font-size: 24px;
    font-weight: 800;
    letter-spacing: -0.5px;
    margin: 0 0 6px 0;
  }
  .hero-sub {
    color: rgba(255,255,255,0.55) !important;
    font-size: 13px;
    margin: 0;
  }
  .hero-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(232,97,44,0.18);
    border: 1px solid rgba(232,97,44,0.35);
    color: #f4a261 !important;
    font-size: 12px;
    font-weight: 600;
    padding: 4px 12px;
    border-radius: 20px;
    margin-top: 10px;
  }
  .hero-generated {
    color: rgba(255,255,255,0.4) !important;
    font-size: 12px;
    text-align: right;
    margin-top: 4px;
  }

  /* ── DARK SIDEBAR ── */
  section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #161616 0%, #1e1e1e 100%) !important;
    border-right: 1px solid rgba(255,255,255,0.06) !important;
  }
  section[data-testid="stSidebar"] *,
  section[data-testid="stSidebar"] label { color: #e0e0e0 !important; }
  section[data-testid="stSidebar"] label { font-size: 12px !important; font-weight: 500 !important; }
  section[data-testid="stSidebar"] .sidebar-logo {
    font-size: 18px; font-weight: 800; color: #fff !important;
    letter-spacing: -0.5px;
  }
  section[data-testid="stSidebar"] .sidebar-logo span { color: #E8612C !important; }

  /* Sidebar inputs */
  section[data-testid="stSidebar"] input,
  section[data-testid="stSidebar"] [data-baseweb="input"] input {
    background-color: rgba(255,255,255,0.08) !important;
    color: #fff !important;
    -webkit-text-fill-color: #fff !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    border-radius: 8px !important;
  }
  section[data-testid="stSidebar"] [data-baseweb="input"] {
    background-color: rgba(255,255,255,0.08) !important;
    border-radius: 8px !important;
  }
  section[data-testid="stSidebar"] input::placeholder {
    color: rgba(255,255,255,0.3) !important;
    -webkit-text-fill-color: rgba(255,255,255,0.3) !important;
  }

  /* Sidebar selectbox */
  section[data-testid="stSidebar"] [data-baseweb="select"] div,
  section[data-testid="stSidebar"] [data-baseweb="select"] span {
    background-color: rgba(255,255,255,0.08) !important;
    color: #fff !important;
    border-radius: 8px !important;
  }

  /* Sidebar button */
  section[data-testid="stSidebar"] .stButton button {
    background: linear-gradient(135deg, #E8612C, #c0392b) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    font-size: 14px !important;
    padding: 10px !important;
    box-shadow: 0 4px 14px rgba(232,97,44,0.35) !important;
    transition: all 0.2s !important;
  }
  section[data-testid="stSidebar"] .stButton button:hover {
    box-shadow: 0 6px 20px rgba(232,97,44,0.5) !important;
    transform: translateY(-1px) !important;
  }

  /* Dropdown portal */
  [data-baseweb="popover"],
  [data-baseweb="popover"] * { color: #1a1a1a !important; background-color: #fff; }
  [data-baseweb="menu"] { background-color: #fff !important; border-radius: 10px !important; }
  [data-baseweb="menu"] li,
  [data-baseweb="menu"] [role="option"] { color: #1a1a1a !important; }
  [data-baseweb="menu"] [aria-selected="true"],
  [data-baseweb="menu"] li:hover { background-color: #FDF0EA !important; }

  /* ── STAT CARDS ── */
  .stat-card {
    border-radius: 14px;
    overflow: hidden;
    margin-bottom: 4px;
  }
  .stat-card a {
    display: block;
    text-decoration: none;
    background: #ffffff;
    border: 1px solid rgba(0,0,0,0.07);
    border-radius: 14px;
    padding: 18px 20px 16px;
    transition: all 0.22s ease;
    position: relative;
    overflow: hidden;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  }
  .stat-card a::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, #E8612C, #f4a261);
    border-radius: 0;
    transform: scaleX(0);
    transform-origin: left;
    transition: transform 0.25s ease;
  }
  .stat-card a:hover {
    box-shadow: 0 8px 28px rgba(232,97,44,0.18);
    transform: translateY(-3px);
    border-color: rgba(232,97,44,0.25);
  }
  .stat-card a:hover::before { transform: scaleX(1); }
  .stat-card .sc-icon {
    font-size: 20px;
    margin-bottom: 8px;
    display: block;
    opacity: 0.85;
  }
  .stat-card .label {
    color: #888 !important;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.5px;
    text-transform: uppercase;
    margin-bottom: 6px;
    display: block;
  }
  .stat-card .value {
    color: #1a1a1a !important;
    font-size: 2.2rem;
    font-weight: 800;
    line-height: 1;
    letter-spacing: -1px;
    display: block;
    margin-bottom: 6px;
  }
  .stat-card .value-accent { color: #E8612C !important; }
  .stat-card .sub {
    color: #aaa !important;
    font-size: 11px;
    display: flex;
    align-items: center;
    gap: 4px;
  }
  .stat-card .sub .arrow { color: #E8612C !important; font-size: 14px; }

  /* ── SECTION TITLES ── */
  .section-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 32px 0 14px;
  }
  .section-header .sh-icon {
    width: 34px; height: 34px;
    background: linear-gradient(135deg, #E8612C, #f4a261);
    border-radius: 9px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 16px;
    flex-shrink: 0;
    box-shadow: 0 3px 8px rgba(232,97,44,0.3);
  }
  .section-header .sh-text { font-size: 17px; font-weight: 800; color: #1a1a1a !important; letter-spacing: -0.3px; }
  .section-header .sh-sub { font-size: 12px; color: #999 !important; margin-left: 4px; font-weight: 400; }

  /* ── DIVIDER ── */
  .fancy-divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(232,97,44,0.25), transparent);
    margin: 28px 0;
    border: none;
  }

  /* ── TABLES ── */
  .styled-table { width: 100%; border-collapse: separate; border-spacing: 0; font-size: 13px; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 12px rgba(0,0,0,0.07); }
  .styled-table thead tr th {
    background: linear-gradient(135deg, #1a1a1a, #2d2d2d) !important;
    color: #fff !important;
    padding: 11px 16px;
    font-weight: 700;
    font-size: 12px;
    letter-spacing: 0.3px;
    text-transform: uppercase;
    text-align: center;
  }
  .styled-table thead tr th:first-child {
    text-align: left;
    border-radius: 12px 0 0 0;
  }
  .styled-table thead tr th:last-child { border-radius: 0 12px 0 0; }
  .styled-table tbody tr { transition: background 0.15s; }
  .styled-table tbody tr:nth-child(even) { background: #fafaf9 !important; }
  .styled-table tbody tr:nth-child(odd)  { background: #ffffff !important; }
  .styled-table tbody tr:hover { background: #fff5f0 !important; }
  .styled-table tbody td {
    padding: 10px 16px;
    border-bottom: 1px solid #f0ede9;
    text-align: center;
    color: #1a1a1a !important;
    font-size: 13px;
  }
  .styled-table tbody td:first-child { text-align: left; font-weight: 500; }
  .styled-table .total-row td {
    font-weight: 800;
    background: linear-gradient(135deg, #fff5f0, #fdf0ea) !important;
    color: #1a1a1a !important;
    border-top: 2px solid #f4c5aa;
    font-size: 13px;
  }
  .styled-table a {
    color: #E8612C !important;
    text-decoration: none;
    font-weight: 600;
    transition: color 0.15s;
  }
  .styled-table a:hover { color: #c0392b !important; text-decoration: underline; }
  .excl-row td { color: #bbb !important; font-style: italic; background: #fafaf9 !important; }

  /* ── STATUS PILLS ── */
  .pill {
    display: inline-block;
    padding: 2px 9px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.2px;
  }
  .pill-open    { background: rgba(232,97,44,0.12); color: #c0392b !important; }
  .pill-pending { background: rgba(244,162,97,0.15); color: #d35400 !important; }
  .pill-solved  { background: rgba(42,157,143,0.12); color: #1a7a6e !important; }
  .pill-closed  { background: rgba(69,123,157,0.12); color: #2e6d9c !important; }

  /* ── WEEK BADGE ── */
  .week-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: linear-gradient(135deg, #1a1a1a, #2d2d2d);
    color: #fff !important;
    font-size: 12px;
    font-weight: 700;
    padding: 5px 14px;
    border-radius: 20px;
    margin-bottom: 2px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.2);
  }
  .week-badge .dot {
    width: 7px; height: 7px;
    background: #E8612C;
    border-radius: 50%;
    display: inline-block;
  }

  /* ── MINI STAT BOXES ── */
  .mini-stat {
    background: #fff;
    border: 1px solid rgba(0,0,0,0.07);
    border-radius: 12px;
    padding: 14px 18px;
    text-align: center;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    position: relative;
    overflow: hidden;
  }
  .mini-stat::after {
    content: '';
    position: absolute;
    bottom: 0; left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, #E8612C, #f4a261);
  }
  .mini-stat .ms-val { color: #E8612C !important; font-size: 1.8rem; font-weight: 800; line-height: 1; letter-spacing: -1px; }
  .mini-stat .ms-lbl { color: #888 !important; font-size: 11px; margin-top: 5px; font-weight: 500; letter-spacing: 0.3px; text-transform: uppercase; }

  /* ── INFO STATE ── */
  .empty-state {
    background: #fff;
    border: 1.5px dashed #e8e0d8;
    border-radius: 14px;
    padding: 32px;
    text-align: center;
    color: #bbb !important;
    font-size: 14px;
  }

  /* ── CHART CONTAINER ── */
  .chart-wrap {
    background: #fff;
    border-radius: 14px;
    padding: 4px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.07);
    border: 1px solid rgba(0,0,0,0.05);
  }

  /* ── CAPTION OVERRIDE ── */
  .stCaption { color: #999 !important; font-size: 12px !important; }

  /* ── EXPANDER ── */
  .streamlit-expanderHeader { font-weight: 600 !important; font-size: 13px !important; }

  /* ── HIDE DEFAULT CHROME ── */
  #MainMenu, footer, header { visibility: hidden; }
  .block-container { padding-top: 0; }
</style>
""", unsafe_allow_html=True)

# ── CONSTANTS ─────────────────────────────────────────────────────────────────
FILTERS = {
    "AI Bot":              "25251640968348",
    "Messaging/Live Chat": "23607369574812",
    "Failed Operations":   "17237919534108",
    "Architect Requests":  "24101684048412",
    "High Priority":       "23645136614684",
    "All Open":            "25994134990364",
}

KLARITY_DOMAINS   = ("@klaritylaw.com", "@klarity.ai")
ARCHITECT_EMAIL   = "architect@klarity.ai"

KNOWN_CUSTOMERS = [
    "zuora", "mongodb", "stripe", "doordash", "sentinelone", "miro",
    "linkedin", "aven", "quench", "kimball", "ipw", "uhg", "ramp",
    "cloudflare", "brex", "rippling", "workday", "salesforce", "hubspot",
]
CUSTOMER_DISPLAY = {
    "aven":        "Aven Hospitality",
    "doordash":    "DoorDash",
    "sentinelone": "SentinelOne",
    "linkedin":    "LinkedIn",
    "mongodb":     "MongoDB",
    "hubspot":     "HubSpot",
    "cloudflare":  "Cloudflare",
    "ipw":         "IPW",
    "uhg":         "UHG",
    "ramp":        "Ramp",
    "miro":        "Miro",
    "zuora":       "Zuora",
    "stripe":      "Stripe",
    "quench":      "Quench",
    "kimball":     "Kimball",
    "brex":        "Brex",
    "rippling":    "Rippling",
    "workday":     "Workday",
    "salesforce":  "Salesforce",
}

CATEGORIES = [
    ("Architect Run Failure / Error running operation",
     re.compile(r"error running|error while running|run fail|architect run|flow run|operation.*fail", re.I),
     ["architect_run_failure", "operation___workflow_fail", "bugs/issues"]),
    ("Unable to login / Access issues",
     re.compile(r"unable.*(login|log in|sign in)|login issue|access|password|temp.*pass|sso|new.*workspace|workspace.*modif", re.I),
     ["login", "access", "workspace"]),
    ("Table matching / Data issues",
     re.compile(r"mismatch|match|table|missing.*line|incorrect|revenue|duplicate|deal|renewal|discrepan", re.I),
     ["matching", "table_matching", "revenue", "integration_issue"]),
    ("AI / Transcript / Hallucination issues",
     re.compile(r"hallucin|transcript|ai interviewer|coach|indexing|insight|pilot", re.I),
     ["transcript_processing/hallucinations", "indexing/insights_errors", "coach"]),
    ("Screenshot / Image / SOP issues",
     re.compile(r"screenshot|image placement|sop|screen share", re.I), []),
    ("Token / Time limits",
     re.compile(r"token|time limit|update with ai|anthropic token", re.I), []),
    ("Timeouts / Performance",
     re.compile(r"timeout|concurrent|performance|slow", re.I), []),
    ("Feedback / Feature Request",
     re.compile(r"feedback|feature request", re.I), ["feedback"]),
    ("Others", None, []),
]

CAT_SEARCH_QUERY = {
    "Architect Run Failure / Error running operation": 'tags:architect_run_failure',
    "Unable to login / Access issues":                 'tags:login',
    "Table matching / Data issues":                    'tags:matching',
    "AI / Transcript / Hallucination issues":          'tags:transcript_processing',
    "Screenshot / Image / SOP issues":                 'subject:screenshot',
    "Token / Time limits":                             'subject:token',
    "Timeouts / Performance":                          'subject:timeout',
    "Feedback / Feature Request":                      'tags:feedback',
    "Others":                                          '',
}

TOP_ISSUES = [
    ("Run Failure / Architect errors",  re.compile(r"error running|error while running|run fail|flow run", re.I)),
    ("Login / Access / Workspace",      re.compile(r"login|access|password|workspace|temp.*pass", re.I)),
    ("Table matching / Data issues",    re.compile(r"mismatch|match|table|missing|duplicate|deal|revenue|discrepan", re.I)),
    ("AI / Transcript / Hallucination", re.compile(r"hallucin|transcript|ai interviewer|coach|pilot", re.I)),
]

# ── WEEK HELPERS ──────────────────────────────────────────────────────────────
def monday_of(d):
    return d - timedelta(days=d.weekday())

def iso_week_bounds(year, week_num):
    jan4      = date(year, 1, 4)
    week1_mon = monday_of(jan4)
    start     = week1_mon + timedelta(weeks=week_num - 1)
    end       = start + timedelta(days=6)
    return start, end

def get_year_weeks(year):
    today    = date.today()
    cur_year = today.isocalendar()[0]
    cur_week = today.isocalendar()[1]
    max_week = cur_week if year == cur_year else 52
    weeks    = []
    for wn in range(1, max_week + 1):
        start, end = iso_week_bounds(year, wn)
        is_cur = (year == cur_year and wn == cur_week)
        weeks.append({
            "label":    f"Wk {wn}" + (" (cur)" if is_cur else ""),
            "week_num": wn,
            "start":    start.isoformat(),
            "end":      (end + timedelta(days=1)).isoformat(),
            "display":  f"{start.strftime('%b %d')} – {end.strftime('%b %d')}",
        })
    return weeks

def since_4_weeks():
    today       = date.today()
    this_monday = monday_of(today)
    return (this_monday - timedelta(weeks=4)).isoformat()

def in_week(t, w):
    c = (t.get("created_at") or "")[:10]
    return w["start"] <= c < w["end"]

# ── TICKET CLASSIFIERS ────────────────────────────────────────────────────────
def tags_of(t):
    return set(t.get("tags") or [])

def is_backend_alert(t):
    return bool(re.search(r"\[BACKEND ALERT\]", t.get("subject", "") or "", re.I))

def is_internal_teams(t):
    return "internal_teams" in tags_of(t)

def is_klarity_staff(email: str) -> bool:
    return any(email.lower().endswith(d) for d in KLARITY_DOMAINS)

def is_internal_run_failure(t):
    subj = t.get("subject", "") or ""
    if not re.search(r"error running operation|error while running", subj, re.I):
        return False
    req_email = (t.get("_requester_email") or "").lower()
    if req_email == ARCHITECT_EMAIL:
        return False
    return "automated_architect" in tags_of(t)

def is_excluded(t, fo_ids):
    if t["id"] in fo_ids:          return True
    if t.get("status") == "new":   return True
    if is_backend_alert(t):        return True
    if is_internal_teams(t):       return True
    if is_internal_run_failure(t): return True
    return False

def is_open(t):   return t.get("status") in ("open", "pending")
def is_closed(t): return t.get("status") in ("solved", "closed")

def res_hours(t):
    if not is_closed(t): return None
    try:
        c  = datetime.fromisoformat(t["created_at"].replace("Z", "+00:00"))
        s  = t.get("solved_at")
        if not s:
            return None
        sd = datetime.fromisoformat(s.replace("Z", "+00:00"))
        h  = round((sd - c).total_seconds() / 3600)
        return h if h >= 0 else None
    except Exception:
        return None

def med(v): return sorted(v)[len(v) // 2] if v else None
def avg(v): return round(sum(v) / len(v)) if v else None
def p90(v): return sorted(v)[int(len(v) * 0.9)] if v else None
def fh(v):  return f"{v}h" if v is not None else "—"

def categorize(tickets):
    result = {label: [] for label, _, __ in CATEGORIES}
    for t in tickets:
        subj = t.get("subject", "") or ""
        tgs  = tags_of(t)
        for label, rx, tag_list in CATEGORIES:
            if rx is None or rx.search(subj) or any(tg in tgs for tg in tag_list):
                result[label].append(t)
                break
    return result

def extract_customer(t):
    subj = t.get("subject", "") or ""
    tgs  = tags_of(t)

    m = re.search(r"<>([^|<>]+)\s*\|\|", subj)
    if m:
        return m.group(1).strip()

    if "||" in subj:
        part = subj.split("||")[0].strip()
        part = re.sub(r"^\[[^\]]*\]\s*", "", part).strip()
        if 1 < len(part) < 50 and part.lower() not in ("klarity", "klarity ai", ""):
            return part

    org = (t.get("_org_name") or "").strip()
    if org and org.lower() not in ("klarity", "klarity ai", "klarity law", ""):
        return org

    for k in KNOWN_CUSTOMERS:
        if any(k.lower() in tg.lower() for tg in tgs):
            return CUSTOMER_DISPLAY.get(k, k.title())

    subj_lower = subj.lower()
    for k in KNOWN_CUSTOMERS:
        if k.lower() in subj_lower:
            return CUSTOMER_DISPLAY.get(k, k.title())

    return "Other"

def arch_bucket(t):
    req = (t.get("_requester_email") or "").lower()
    if req == ARCHITECT_EMAIL:
        return "failure_notification"
    if is_klarity_staff(req):
        return "internal"
    return "customer"

# ── ZENDESK API ───────────────────────────────────────────────────────────────
def zd_get(sub, email, token, path, params=None):
    r = requests.get(
        f"https://{sub}.zendesk.com/api/v2{path}",
        auth=(f"{email}/token", token), params=params, timeout=30
    )
    r.raise_for_status()
    return r.json()

def fetch_search(sub, email, token, query):
    tickets, page = [], 1
    while True:
        data  = zd_get(sub, email, token, "/search.json",
                       {"query": query, "per_page": 100, "page": page})
        batch = [r for r in data.get("results", []) if r.get("result_type") == "ticket"]
        tickets.extend(batch)
        if not data.get("next_page") or len(data.get("results", [])) < 100:
            break
        page += 1
    return tickets

def fetch_view(sub, email, token, view_id, since=None):
    tickets, page = [], 1
    while True:
        try:
            data = zd_get(
                sub, email, token,
                f"/views/{view_id}/tickets.json",
                {"per_page": 100, "page": page,
                 "include": "users,organizations,metric_sets"},
            )
            users   = {u["id"]: u.get("email", "") for u in data.get("users", [])}
            orgs    = {o["id"]: o.get("name", "")  for o in data.get("organizations", [])}
            metrics = {m["ticket_id"]: m            for m in data.get("metric_sets", [])}
            batch   = data.get("tickets", [])

            for t in batch:
                t["_requester_email"] = users.get(t.get("requester_id"), "")
                t["_org_name"]        = orgs.get(t.get("organization_id"), "")
                ms = metrics.get(t["id"])
                if ms:
                    t["solved_at"] = ms.get("solved_at")

            raw_count = len(batch)

            if since:
                batch = [t for t in batch if (t.get("created_at") or "")[:10] >= since]

            tickets.extend(batch)

            if not data.get("next_page") or raw_count < 100:
                break
            page += 1
        except Exception:
            break
    return tickets

# ── LOAD DATA ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def load_data(sub, email, token, since):
    fo_view = fetch_view(sub, email, token, FILTERS["Failed Operations"])
    fo_ids  = {t["id"] for t in fo_view}

    active_views = ["AI Bot", "Messaging/Live Chat", "Architect Requests", "High Priority"]
    view_tickets = {"Failed Operations": fo_view}
    for name in active_views:
        view_tickets[name] = fetch_view(sub, email, token, FILTERS[name], since=since)
    view_tickets["All Open"] = fetch_view(sub, email, token, FILTERS["All Open"])

    broad_since = min(since, since_4_weeks())
    all_tickets = fetch_search(sub, email, token, f"type:ticket created>{zd_after(broad_since)}")

    email_map = {t["id"]: t["_requester_email"] for vl in view_tickets.values()
                 for t in vl if t.get("_requester_email")}
    org_map   = {t["id"]: t["_org_name"]        for vl in view_tickets.values()
                 for t in vl if t.get("_org_name")}
    solve_map = {t["id"]: t.get("solved_at")    for vl in view_tickets.values()
                 for t in vl if t.get("solved_at")}
    for t in all_tickets:
        if not t.get("_requester_email"):
            t["_requester_email"] = email_map.get(t["id"], "")
        if not t.get("_org_name"):
            t["_org_name"]        = org_map.get(t["id"], "")
        if not t.get("solved_at"):
            t["solved_at"]        = solve_map.get(t["id"])

    real     = [t for t in all_tickets if not is_excluded(t, fo_ids)]
    open_t   = [t for t in real if is_open(t)]
    closed_t = [t for t in real if is_closed(t)]

    def view_ch(name):
        t = [x for x in view_tickets[name] if not is_excluded(x, fo_ids)]
        return {"tickets": t,
                "open":    [x for x in t if is_open(x)],
                "closed":  [x for x in t if is_closed(x)]}

    channels = {k: view_ch(k) for k in ["AI Bot", "Messaging/Live Chat",
                                          "Architect Requests", "High Priority"]}

    arch_all = channels["Architect Requests"]["tickets"]
    arch_buckets = {
        "customer":             [t for t in arch_all if arch_bucket(t) == "customer"],
        "internal":             [t for t in arch_all if arch_bucket(t) == "internal"],
        "failure_notification": [t for t in arch_all if arch_bucket(t) == "failure_notification"],
    }
    for k, lst in arch_buckets.items():
        arch_buckets[k] = {
            "tickets": lst,
            "open":    [t for t in lst if is_open(t)],
            "closed":  [t for t in lst if is_closed(t)],
        }

    s4      = since_4_weeks()
    real_4w = [t for t in real if (t.get("created_at") or "")[:10] >= s4]
    cat_map  = categorize(real_4w)
    cat_perf = []
    for label, _, __ in CATEGORIES:
        tix = cat_map[label]
        if not tix: continue
        times = [h for t in tix if (h := res_hours(t)) is not None]
        cat_perf.append({"label": label, "count": len(tix),
                         "median": med(times), "average": avg(times), "p90": p90(times)})
    cat_perf.sort(key=lambda x: -x["count"])

    year      = date.today().year
    all_weeks = get_year_weeks(year)
    for w in all_weeks:
        w["tickets"] = [t for t in real if in_week(t, w)]
        w["count"]   = len(w["tickets"])

    unsolved = [t for t in view_tickets["All Open"] if not is_excluded(t, fo_ids)]

    return dict(
        real=real, open_t=open_t, closed_t=closed_t,
        channels=channels, arch_buckets=arch_buckets,
        cat_perf=cat_perf, all_weeks=all_weeks,
        unsolved_count=len(unsolved),
        fo_count=len(fo_view),
        since=since,
    )

# ── URL HELPERS ───────────────────────────────────────────────────────────────
def fu(sub, fid): return f"https://{sub}.zendesk.com/agent/filters/{fid}"
def su(sub, q):   return f"https://{sub}.zendesk.com/agent/search?q={urllib.parse.quote(q)}"
def tu(sub, tid): return f"https://{sub}.zendesk.com/agent/tickets/{tid}"

def zd_after(d: str) -> str:
    return (date.fromisoformat(d) - timedelta(days=1)).isoformat()

ZD_EXCL = '-status:new -tags:internal_teams -tags:automated_architect -subject:"BACKEND ALERT"'

# ── UI HELPERS ────────────────────────────────────────────────────────────────
def stat_card(col, icon, label, value, sub_text, url, accent=False):
    val_cls = "value-accent" if accent else "value"
    with col:
        st.markdown(f"""
        <div class="stat-card">
          <a href="{url}" target="_blank">
            <span class="sc-icon">{icon}</span>
            <span class="label">{label}</span>
            <span class="{val_cls}">{value}</span>
            <span class="sub"><span class="arrow">↗</span>{sub_text}</span>
          </a>
        </div>""", unsafe_allow_html=True)

def section_header(icon, title, sub=""):
    sub_html = f'<span class="sh-sub">— {sub}</span>' if sub else ""
    st.markdown(f"""
    <div class="section-header">
      <div class="sh-icon">{icon}</div>
      <span class="sh-text">{title}{sub_html}</span>
    </div>""", unsafe_allow_html=True)

def divider():
    st.markdown('<hr class="fancy-divider">', unsafe_allow_html=True)

def status_pill(status: str) -> str:
    cls_map = {"open": "pill-open", "pending": "pill-pending",
               "solved": "pill-solved", "closed": "pill-closed"}
    cls = cls_map.get(status.lower(), "pill-open")
    return f'<span class="pill {cls}">{status.title()}</span>'

def ticket_table_html(tickets, sub):
    if not tickets:
        return "<div class='empty-state'>No tickets in this range.</div>"
    sorted_t = sorted(tickets, key=lambda t: t.get("created_at", ""), reverse=True)
    html = """<table class="styled-table"><thead><tr>
        <th>ID</th><th>Subject</th><th>Status</th><th>Requester</th><th>Created</th>
    </tr></thead><tbody>"""
    for t in sorted_t:
        tid   = t["id"]
        url   = tu(sub, tid)
        subj  = re.sub(r"\[backend alert\]\s*", "", t.get("subject") or "", flags=re.I).strip()[:80]
        stat  = t.get("status") or "unknown"
        req   = t.get("_requester_email") or "—"
        cdate = (t.get("created_at") or "")[:10]
        html += (f'<tr><td><a href="{url}" target="_blank">#{tid}</a></td>'
                 f'<td>{subj}</td><td>{status_pill(stat)}</td>'
                 f'<td style="font-size:12px;color:#888 !important">{req}</td>'
                 f'<td>{cdate}</td></tr>')
    html += "</tbody></table>"
    return html

def ch_table(rows, show_total=True):
    html = """<table class="styled-table"><thead><tr>
        <th>Source</th><th>Open</th><th>Closed</th><th>Total</th>
    </tr></thead><tbody>"""
    tot = [0, 0, 0]
    for label, ch, url, excl in rows:
        o = len(ch["open"]); c = len(ch["closed"]); t = len(ch["tickets"])
        if not excl: tot[0]+=o; tot[1]+=c; tot[2]+=t
        def mk(v, u=url):
            if v == 0:
                return '<span style="color:#ddd">—</span>'
            return f'<a href="{u}" target="_blank"><strong>{v}</strong></a>'
        cls = ' class="excl-row"' if excl else ""
        html += (f'<tr{cls}><td><a href="{url}" target="_blank">{label}</a></td>'
                 f'<td>{mk(o)}</td><td>{mk(c)}</td><td>{mk(t)}</td></tr>')
    if show_total:
        html += (f'<tr class="total-row"><td>TOTAL</td>'
                 f'<td>{tot[0]}</td><td>{tot[1]}</td>'
                 f'<td style="color:#E8612C !important">{tot[2]}</td></tr>')
    html += "</tbody></table>"
    return html

def filter_ch_to_weeks(ch, weeks):
    t = [x for x in ch["tickets"] if any(in_week(x, w) for w in weeks)]
    return {"tickets": t, "open": [x for x in t if is_open(x)], "closed": [x for x in t if is_closed(x)]}

# Shared Plotly layout defaults
PLOT_DEFAULTS = dict(
    plot_bgcolor="white",
    paper_bgcolor="white",
    font=dict(family="Inter, sans-serif", size=12, color="#1a1a1a"),
    margin=dict(t=30, b=40, l=20, r=20),
)
AXIS_STYLE = dict(showgrid=True, gridcolor="#f0ede9", zeroline=False,
                  color="#888", tickfont=dict(color="#888", size=11))
XAXIS_STYLE = dict(showgrid=False, color="#888", tickfont=dict(color="#888", size=11))

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
today  = date.today()
cur_wk = today.isocalendar()[1]
year   = today.year

with st.sidebar:
    st.markdown(
        '<div class="sidebar-logo">klarity<span>.</span></div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<p style="color:rgba(255,255,255,0.35) !important; font-size:11px; margin:-4px 0 16px">Support Performance Report</p>',
        unsafe_allow_html=True
    )
    st.markdown("---")
    subdomain = st.text_input("Subdomain", value="klarity6695")
    email     = st.text_input("Email", placeholder="you@klaritylaw.com")
    token     = st.text_input("API Token", type="password")
    st.markdown(
        '<p style="color:rgba(255,255,255,0.4) !important; font-size:11px; margin: 8px 0 4px; font-weight:600; letter-spacing:0.5px; text-transform:uppercase">Week Range</p>',
        unsafe_allow_html=True
    )
    all_wk_nums = list(range(1, cur_wk + 1))
    start_wk    = st.selectbox("From week", all_wk_nums,
                               index=max(0, len(all_wk_nums) - 4),
                               format_func=lambda w: f"Week {w}")
    end_wk      = st.selectbox("To week", all_wk_nums,
                               index=len(all_wk_nums) - 1,
                               format_func=lambda w: f"Week {w}")
    wk_start_d, _ = iso_week_bounds(year, start_wk)
    since_date    = wk_start_d.isoformat()
    st.markdown("<br>", unsafe_allow_html=True)
    run = st.button("Generate Report", use_container_width=True, type="primary")
    st.markdown("---")
    _, e_disp = iso_week_bounds(year, end_wk)
    st.markdown(
        f"<small style='color:rgba(255,255,255,0.3) !important'>Wk {start_wk} ({wk_start_d.strftime('%b %d')}) → "
        f"Wk {end_wk} ({e_disp.strftime('%b %d')})<br>"
        f"Failed Ops excluded from all counts</small>",
        unsafe_allow_html=True
    )

# ── HERO HEADER ───────────────────────────────────────────────────────────────
h1, h2 = st.columns([3, 1])
with h1:
    st.markdown(f"""
    <div class="hero-header">
      <div class="hero-title">Support Performance Report</div>
      <div class="hero-sub">Klarity · Zendesk Analytics · {today.strftime('%B %Y')}</div>
      <div class="hero-badge"><span class="dot"></span>Week {start_wk} – Week {end_wk} &nbsp;·&nbsp; {today.strftime('%d %b %Y')}</div>
    </div>""", unsafe_allow_html=True)
with h2:
    st.markdown(
        f"<div style='text-align:right;color:#bbb !important;font-size:12px;padding-top:20px'>"
        f"Generated<br><strong style='color:#888 !important'>{datetime.now().strftime('%d %b %Y %H:%M')}</strong></div>",
        unsafe_allow_html=True
    )

if not run and "data" not in st.session_state:
    st.markdown("""
    <div class="empty-state" style="margin-top:16px; padding: 48px">
      <div style="font-size:40px; margin-bottom:12px">📊</div>
      <strong style="font-size:16px; color:#555 !important">Ready to generate your report</strong><br>
      <span style="font-size:13px">Enter your Zendesk credentials in the sidebar and click <strong>Generate Report</strong></span>
    </div>""", unsafe_allow_html=True)
    st.stop()

if run:
    if not email or not token:
        st.error("Please enter your email and API token."); st.stop()
    if start_wk > end_wk:
        st.error("Start week must be before or equal to end week."); st.stop()
    cache_key = f"{subdomain}|{email}|{since_date}"
    if st.session_state.get("_cache_key") != cache_key:
        load_data.clear()
        st.session_state["_cache_key"] = cache_key
    with st.spinner("Fetching from Zendesk…"):
        try:
            st.session_state["data"]     = load_data(subdomain, email, token, since_date)
            st.session_state["sub"]      = subdomain
            st.session_state["start_wk"] = start_wk
            st.session_state["end_wk"]   = end_wk
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 401:
                load_data.clear()
                st.error("401 Unauthorized — check your email and API token.")
            else:
                st.error(f"Zendesk API error: {e}")
            st.stop()
        except Exception as e:
            st.error(f"Unexpected error: {e}"); st.stop()

data     = st.session_state["data"]
sub      = st.session_state["sub"]
start_wk = st.session_state.get("start_wk", start_wk)
end_wk   = st.session_state.get("end_wk", end_wk)

real         = data["real"]
open_t       = data["open_t"]
closed_t     = data["closed_t"]
channels     = data["channels"]
arch_buckets = data["arch_buckets"]
cat_perf     = data["cat_perf"]
all_weeks    = data["all_weeks"]
unsolved     = data["unsolved_count"]
fo_count     = data["fo_count"]
since        = data["since"]

display_weeks = [w for w in all_weeks if start_wk <= w["week_num"] <= end_wk]
range_real    = [t for t in real if any(in_week(t, w) for w in display_weeks)]
range_open    = [t for t in range_real if is_open(t)]
range_closed  = [t for t in range_real if is_closed(t)]
range_res     = round(len(range_closed) / len(range_real) * 100) if range_real else 0

w_since = display_weeks[0]["start"] if display_weeks else since
w_end   = display_weeks[-1]["end"]  if display_weeks else since

ch_ranged     = {k: filter_ch_to_weeks(v, display_weeks) for k, v in channels.items()}
arch_b_ranged = {k: filter_ch_to_weeks(v, display_weeks) for k, v in arch_buckets.items()}

# ── STAT CARDS ────────────────────────────────────────────────────────────────
cols = st.columns(6)
stat_card(cols[0], "📥", "Tickets Received", len(range_real),
          f"Wk {start_wk} – Wk {end_wk}",
          su(sub, f"type:ticket created>{zd_after(w_since)} created<{w_end} {ZD_EXCL}"))
stat_card(cols[1], "🔓", "Open", len(range_open),
          f"{100 - range_res}% of total",
          su(sub, f"type:ticket status:open status:pending created>{zd_after(w_since)} created<{w_end} {ZD_EXCL}"))
stat_card(cols[2], "✅", "Solved / Closed", len(range_closed),
          f"{range_res}% resolution",
          su(sub, f"type:ticket status:solved status:closed created>{zd_after(w_since)} created<{w_end} {ZD_EXCL}"))
stat_card(cols[3], "📈", "Resolution Rate", f"{range_res}%",
          f"{len(range_closed)} of {len(range_real)} resolved",
          su(sub, f"type:ticket status:solved created>{zd_after(w_since)} created<{w_end} {ZD_EXCL}"),
          accent=True)
stat_card(cols[4], "📋", "Unsolved in Group", unsolved,
          "Full queue · Failed Ops excluded",
          fu(sub, FILTERS["All Open"]))
stat_card(cols[5], "🔥", "High Priority", len(ch_ranged["High Priority"]["tickets"]),
          "View filter",
          fu(sub, FILTERS["High Priority"]))

st.caption(
    f"Failed Operations view ({fo_count} tickets) excluded from every metric. "
    f"[View bucket ↗](https://{sub}.zendesk.com/agent/filters/{FILTERS['Failed Operations']})"
)

with st.expander(f"📄 View {len(range_real)} Tickets Received"):
    st.markdown(ticket_table_html(range_real, sub), unsafe_allow_html=True)
tcol1, tcol2 = st.columns(2)
with tcol1:
    with st.expander(f"🔓 View {len(range_open)} Open Tickets"):
        st.markdown(ticket_table_html(range_open, sub), unsafe_allow_html=True)
with tcol2:
    with st.expander(f"✅ View {len(range_closed)} Solved / Closed Tickets"):
        st.markdown(ticket_table_html(range_closed, sub), unsafe_allow_html=True)

divider()

# ── WEEKLY METRICS ────────────────────────────────────────────────────────────
section_header("📊", "Weekly Metrics", f"Wk {start_wk} – Wk {end_wk}")
cl, cr = st.columns(2)
with cl:
    st.markdown("**Customer Raised Tickets**")
    st.markdown(ch_table([
        ("AI Bot",               ch_ranged["AI Bot"],              fu(sub, FILTERS["AI Bot"]),           False),
        ("Messaging / Live Chat", ch_ranged["Messaging/Live Chat"], fu(sub, FILTERS["Messaging/Live Chat"]), False),
        ("Architect — Customer",  arch_b_ranged["customer"],        fu(sub, FILTERS["Architect Requests"]), False),
    ]), unsafe_allow_html=True)

with cr:
    st.markdown("**Architect Breakdown**")
    st.markdown(ch_table([
        ("Customer tickets",        arch_b_ranged["customer"],
         su(sub, f"type:ticket created>{zd_after(w_since)} created<{w_end} group:architect {ZD_EXCL}"), False),
        ("Internal — on behalf of", arch_b_ranged["internal"],
         su(sub, f"type:ticket created>{zd_after(w_since)} created<{w_end} group:architect requester:{ARCHITECT_EMAIL} {ZD_EXCL}"), False),
        ("Failure notifications",   arch_b_ranged["failure_notification"],
         su(sub, f"type:ticket created>{zd_after(w_since)} created<{w_end} requester:{ARCHITECT_EMAIL} {ZD_EXCL}"), False),
    ], show_total=True), unsafe_allow_html=True)

divider()

# ── CATEGORY PERFORMANCE ──────────────────────────────────────────────────────
s4 = since_4_weeks()
section_header("🎯", "Support Performance by Category", "Last 4 complete weeks")
st.caption(f"Fixed window: last 4 complete Mon–Sun weeks from {s4} — independent of the week selector above.")

if cat_perf:
    cat_html = """<table class="styled-table"><thead><tr>
        <th>Issue Type</th><th>Tickets</th>
        <th>Median</th><th>Average</th><th>P90</th>
    </tr></thead><tbody>"""
    for i, cat in enumerate(cat_perf):
        cat_q   = CAT_SEARCH_QUERY.get(cat["label"], "")
        url     = su(sub, f"type:ticket created>{zd_after(s4)} {cat_q} {ZD_EXCL}".strip())
        bar_pct = round(cat["count"] / cat_perf[0]["count"] * 100) if cat_perf else 0
        bar_html = (f'<div style="display:inline-flex;align-items:center;gap:8px">'
                    f'<a href="{url}" target="_blank"><strong>{cat["count"]}</strong></a>'
                    f'<div style="width:60px;height:5px;background:#f0ede9;border-radius:3px;overflow:hidden">'
                    f'<div style="width:{bar_pct}%;height:100%;background:linear-gradient(90deg,#E8612C,#f4a261);border-radius:3px"></div>'
                    f'</div></div>')
        cat_html += (f'<tr><td><a href="{url}" target="_blank">{cat["label"]}</a></td>'
                     f'<td>{bar_html}</td>'
                     f'<td>{fh(cat["median"])}</td><td>{fh(cat["average"])}</td><td>{fh(cat["p90"])}</td></tr>')
    cat_html += "</tbody></table>"
    st.markdown(cat_html, unsafe_allow_html=True)
else:
    st.markdown("<div class='empty-state'>No categorized tickets found in the last 4 weeks.</div>", unsafe_allow_html=True)

divider()

# ── WOW TREND ────────────────────────────────────────────────────────────────
section_header("📅", "Week by Week Trend", f"Wk {start_wk} – Wk {end_wk} · {year}")
cc, ct = st.columns([3, 2])
with cc:
    # Gradient-effect by using a colorscale based on value
    counts = [w["count"] for w in display_weeks]
    max_c  = max(counts) if counts else 1
    colors = [f"rgba(232, {int(97 + (44-97)*(v/max_c))}, {int(44 + (0-44)*(v/max_c))}, {0.6 + 0.4*(v/max_c):.2f})"
              for v in counts]
    fig = go.Figure(go.Bar(
        x=[w["label"] for w in display_weeks],
        y=counts,
        marker_color=colors,
        marker_line_width=0,
        text=counts,
        textposition="outside",
        textfont=dict(color="#888", size=11),
        hovertemplate="<b>%{x}</b><br>%{customdata}<br><b>%{y} tickets</b><extra></extra>",
        customdata=[w["display"] for w in display_weeks],
    ))
    fig.update_layout(
        **PLOT_DEFAULTS,
        yaxis=dict(**AXIS_STYLE),
        xaxis=dict(**XAXIS_STYLE, tickangle=-45 if len(display_weeks) > 8 else 0),
        showlegend=False,
        height=300,
        bargap=0.35,
    )
    st.markdown('<div class="chart-wrap">', unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

with ct:
    st.markdown("**Top Issues — last 4 weeks**")
    top_weeks = display_weeks[-4:] if len(display_weeks) >= 4 else display_weeks
    top_html  = "<table class='styled-table'><thead><tr><th>Issue</th>"
    for w in top_weeks:
        top_html += f"<th>{w['label']}</th>"
    top_html += "</tr></thead><tbody>"
    for label, rx in TOP_ISSUES:
        top_html += f"<tr><td>{label}</td>"
        for w in top_weeks:
            count = len([t for t in w["tickets"] if rx.search(t.get("subject", "") or "")])
            url   = su(sub, f"type:ticket created>{zd_after(w['start'])} created<{w['end']} {ZD_EXCL}")
            cell  = (f'<a href="{url}" target="_blank"><strong>{count}</strong></a>'
                     if count else '<span style="color:#e0d8d0">—</span>')
            top_html += f"<td>{cell}</td>"
        top_html += "</tr>"
    top_html += "</tbody></table>"
    st.markdown(top_html, unsafe_allow_html=True)

divider()

# ── RESOLUTION TIME CHART ─────────────────────────────────────────────────────
section_header("⏱️", "Resolution Time by Category", "Median · Average · P90 (hours)")
cats_with_data = [c for c in cat_perf if c["median"] is not None]
if cats_with_data:
    df   = pd.DataFrame(cats_with_data)
    short_labels = [lbl.split("/")[0].strip()[:32] for lbl in df["label"]]
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(
        name="Median", x=short_labels, y=df["median"],
        marker_color="#E8612C", marker_line_width=0,
        hovertemplate="<b>%{x}</b><br>Median: %{y}h<extra></extra>",
    ))
    fig2.add_trace(go.Bar(
        name="Average", x=short_labels, y=df["average"],
        marker_color="#f4a261", marker_line_width=0,
        hovertemplate="<b>%{x}</b><br>Average: %{y}h<extra></extra>",
    ))
    fig2.add_trace(go.Bar(
        name="P90", x=short_labels, y=df["p90"],
        marker_color="#fde8d8", marker_line_width=0,
        hovertemplate="<b>%{x}</b><br>P90: %{y}h<extra></extra>",
    ))
    fig2.update_layout(
        **PLOT_DEFAULTS,
        barmode="group",
        bargap=0.25,
        bargroupgap=0.06,
        margin=dict(t=20, b=120, l=20, r=20),
        yaxis=dict(**AXIS_STYLE, title="Hours", title_font=dict(color="#888")),
        xaxis=dict(tickangle=-30, **XAXIS_STYLE),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    font=dict(color="#555", size=12),
                    bgcolor="rgba(0,0,0,0)", borderwidth=0),
        height=360,
    )
    st.markdown('<div class="chart-wrap">', unsafe_allow_html=True)
    st.plotly_chart(fig2, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
else:
    st.markdown("<div class='empty-state'>No closed tickets yet — resolution times will appear once tickets are solved.</div>",
                unsafe_allow_html=True)

divider()

# ── BREAKDOWN DASHBOARD ───────────────────────────────────────────────────────
section_header("🔍", "Ticket Breakdown",
               f"Wk {start_wk}–{end_wk} · {len(range_real)} received · {len(range_open)} open · {len(range_closed)} solved")

if range_real:
    # ── Summary mini-stat row ──────────────────────────────────────────────
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f'<div class="mini-stat"><div class="ms-val">{len(range_real)}</div><div class="ms-lbl">Total Received</div></div>',
                    unsafe_allow_html=True)
    with m2:
        st.markdown(f'<div class="mini-stat"><div class="ms-val">{len(range_open)}</div><div class="ms-lbl">Still Open</div></div>',
                    unsafe_allow_html=True)
    with m3:
        st.markdown(f'<div class="mini-stat"><div class="ms-val">{len(range_closed)}</div><div class="ms-lbl">Resolved</div></div>',
                    unsafe_allow_html=True)
    with m4:
        st.markdown(f'<div class="mini-stat"><div class="ms-val">{range_res}%</div><div class="ms-lbl">Resolution Rate</div></div>',
                    unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Row 1: Status donut + Customer table ──────────────────────────────
    col_donut, col_cust = st.columns(2)

    with col_donut:
        st.markdown("**Status Distribution**")
        status_counts = Counter(t.get("status", "unknown").capitalize() for t in range_real)
        status_colors = {
            "Open":    "#E8612C",
            "Pending": "#f4a261",
            "Solved":  "#2a9d8f",
            "Closed":  "#457b9d",
        }
        fig_s = go.Figure(go.Pie(
            labels=list(status_counts.keys()),
            values=list(status_counts.values()),
            hole=0.62,
            marker=dict(
                colors=[status_colors.get(k, "#ccc") for k in status_counts.keys()],
                line=dict(color="white", width=3),
            ),
            textinfo="label+value",
            textfont=dict(color="#1a1a1a", size=12, family="Inter"),
            hovertemplate="<b>%{label}</b><br>%{value} tickets · %{percent}<extra></extra>",
        ))
        fig_s.update_layout(
            showlegend=True,
            legend=dict(font=dict(color="#555", size=12), bgcolor="rgba(0,0,0,0)"),
            height=300,
            margin=dict(t=10, b=10, l=10, r=10),
            paper_bgcolor="white",
            annotations=[dict(
                text=f"<b>{len(range_real)}</b><br><span style='font-size:11px;color:#999'>tickets</span>",
                x=0.5, y=0.5, font_size=20, showarrow=False, font_color="#1a1a1a"
            )]
        )
        st.markdown('<div class="chart-wrap">', unsafe_allow_html=True)
        st.plotly_chart(fig_s, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_cust:
        st.markdown("**Top Customers by Volume**")
        cust_map = defaultdict(lambda: {"open": 0, "solved": 0})
        for t in range_real:
            cust = extract_customer(t)
            if is_open(t):
                cust_map[cust]["open"] += 1
            else:
                cust_map[cust]["solved"] += 1

        cust_html = """<table class="styled-table"><thead><tr>
            <th>Customer</th><th>Open</th><th>Solved</th><th>Total</th>
        </tr></thead><tbody>"""
        for cust, cnts in sorted(cust_map.items(), key=lambda x: -(x[1]["open"]+x[1]["solved"]))[:15]:
            o = cnts["open"]; s = cnts["solved"]; tot = o + s
            url = su(sub, f'type:ticket created>{zd_after(w_since)} created<{w_end} "{cust}" {ZD_EXCL}')
            o_cell  = f'<a href="{url}" target="_blank">{o}</a>' if o else '<span style="color:#ddd">—</span>'
            s_cell  = f'<a href="{url}" target="_blank">{s}</a>' if s else '<span style="color:#ddd">—</span>'
            cust_html += (f'<tr><td>{cust}</td><td>{o_cell}</td><td>{s_cell}</td>'
                          f'<td><a href="{url}" target="_blank"><strong>{tot}</strong></a></td></tr>')
        cust_html += "</tbody></table>"
        st.markdown(cust_html, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Row 2: Daily volume + Category horizontal bar ─────────────────────
    col_daily, col_cat = st.columns(2)

    with col_daily:
        st.markdown("**Daily Ticket Volume**")
        daily = Counter((t.get("created_at") or "")[:10] for t in range_real if t.get("created_at"))
        if daily:
            dates  = sorted(daily.keys())
            counts = [daily[d] for d in dates]
            bar_colors = []
            for d in dates:
                try:
                    wd = datetime.strptime(d, "%Y-%m-%d").weekday()
                    bar_colors.append("#fde8d8" if wd >= 5 else "#E8612C")
                except Exception:
                    bar_colors.append("#E8612C")
            fig_d = go.Figure(go.Bar(
                x=dates, y=counts,
                marker_color=bar_colors,
                marker_line_width=0,
                text=counts,
                textposition="outside",
                textfont=dict(color="#888", size=10),
                hovertemplate="<b>%{x}</b><br>%{y} tickets<extra></extra>",
            ))
            fig_d.update_layout(
                **PLOT_DEFAULTS,
                margin=dict(t=20, b=50, l=20, r=10),
                xaxis=dict(**XAXIS_STYLE, tickangle=-45),
                yaxis=dict(**AXIS_STYLE),
                height=300, showlegend=False, bargap=0.3,
            )
            st.markdown('<div class="chart-wrap">', unsafe_allow_html=True)
            st.plotly_chart(fig_d, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            st.caption("Orange = weekday  ·  Pale = weekend")

    with col_cat:
        st.markdown("**Volume by Category**")
        cat_map_range = categorize(range_real)
        cat_labels = [lbl for lbl, _, __ in CATEGORIES if cat_map_range[lbl]]
        cat_vals   = [len(cat_map_range[lbl]) for lbl in cat_labels]
        short      = [lbl.split("/")[0].strip()[:26] for lbl in cat_labels]
        max_val    = max(cat_vals) if cat_vals else 1
        bar_colors_c = [
            f"rgba(232, {int(97 + (162-97)*(1 - v/max_val))}, {int(44 + (97-44)*(1 - v/max_val))}, 0.85)"
            for v in cat_vals
        ]
        fig_c = go.Figure(go.Bar(
            x=cat_vals, y=short,
            orientation="h",
            marker_color=bar_colors_c,
            marker_line_width=0,
            text=cat_vals,
            textposition="outside",
            textfont=dict(color="#888", size=11),
            hovertemplate="<b>%{y}</b><br>%{x} tickets<extra></extra>",
        ))
        fig_c.update_layout(
            **PLOT_DEFAULTS,
            margin=dict(t=10, b=10, l=10, r=50),
            xaxis=dict(**AXIS_STYLE),
            yaxis=dict(showgrid=False, autorange="reversed", color="#555",
                       tickfont=dict(color="#555", size=11)),
            height=310, showlegend=False, bargap=0.3,
        )
        st.markdown('<div class="chart-wrap">', unsafe_allow_html=True)
        st.plotly_chart(fig_c, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

# ── FOOTER ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="text-align:center;color:#ccc !important;font-size:12px;margin-top:48px;
            padding:20px 0 32px;border-top:1px solid rgba(0,0,0,0.07)">
  <strong style="color:#888 !important">Klarity Support Report</strong>
  &nbsp;·&nbsp; Week {start_wk} – Week {end_wk} ({year})
  &nbsp;·&nbsp; Generated {datetime.now().strftime('%d %b %Y %H:%M')}
  &nbsp;·&nbsp;
  <a href="https://{subdomain}.zendesk.com/agent" target="_blank"
     style="color:#E8612C !important; text-decoration:none; font-weight:600">
    Open Zendesk ↗
  </a>
</div>
""", unsafe_allow_html=True)
