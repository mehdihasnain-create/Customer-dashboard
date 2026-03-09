"""
Klarity Support Report - Streamlit Dashboard v9
================================================
Run: python3 -m streamlit run klarity_dashboard.py
Requires: pip3 install requests streamlit plotly pandas

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

v8 changes:
  - Removed Automate Requests and Tech Tickets channels
  - Architect view split into 3 sub-buckets:
      Customer / Internal (on behalf of customer) / Failure notifications
  - Customer name extraction: 5-signal waterfall (subject, org_name, tags, keywords)
  - Expanded known customers list
  - Fixed Plotly axis text visibility (explicit tickfont per axis, not just global font)
  - Fixed sidebar dropdown text via [data-baseweb="popover"] CSS
  - Fixed fetch_view() pagination: check raw batch size BEFORE since-filtering
  - Fixed since_4_weeks(): true 4 complete Mon-Sun weeks (weeks=4, not weeks=3)
  - Added metric_sets + organizations sideloads for accurate resolved_at & org_name
  - Weekly Metrics channels now filtered to selected week range
  - Cache invalidates when subdomain, email, or date range changes
  - All metric numbers link to corresponding Zendesk search/filter
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
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;600;700;800&display=swap');
  html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }

  /* ── Force light theme everywhere ── */
  .stApp, .main, .block-container { background-color: #f7f5f2 !important; }
  p, span, div, li, td, th, label, caption, small,
  h1, h2, h3, h4, h5, h6,
  .stMarkdown, .stCaption, .element-container,
  [data-testid="stText"], [data-testid="stMarkdownContainer"] {
    color: #1a1a1a !important;
  }

  /* ── Sidebar stays dark ── */
  section[data-testid="stSidebar"] { background: #1a1a1a !important; }
  section[data-testid="stSidebar"] *,
  section[data-testid="stSidebar"] label { color: #fff !important; }
  section[data-testid="stSidebar"] label { font-size: 12px !important; }

  /* ── Sidebar input fields: white background, dark text ── */
  section[data-testid="stSidebar"] input,
  section[data-testid="stSidebar"] textarea,
  section[data-testid="stSidebar"] [data-baseweb="input"] input,
  section[data-testid="stSidebar"] [data-baseweb="textarea"] textarea {
    background-color: #ffffff !important;
    color: #1a1a1a !important;
    -webkit-text-fill-color: #1a1a1a !important;
  }
  section[data-testid="stSidebar"] [data-baseweb="input"],
  section[data-testid="stSidebar"] [data-baseweb="base-input"] {
    background-color: #ffffff !important;
  }
  section[data-testid="stSidebar"] input::placeholder {
    color: #999 !important;
    -webkit-text-fill-color: #999 !important;
  }

  /* ── Sidebar selectbox: white background, dark text ── */
  section[data-testid="stSidebar"] [data-baseweb="select"] div,
  section[data-testid="stSidebar"] [data-baseweb="select"] span {
    background-color: #ffffff !important;
    color: #1a1a1a !important;
  }

  /* ── Fix BaseUI popover (selectbox dropdown) text - portal is outside sidebar ── */
  [data-baseweb="popover"],
  [data-baseweb="popover"] * { color: #1a1a1a !important; background-color: #fff; }
  [data-baseweb="menu"] { background-color: #fff !important; }
  [data-baseweb="menu"] li,
  [data-baseweb="menu"] [role="option"] { color: #1a1a1a !important; }
  [data-baseweb="menu"] [aria-selected="true"],
  [data-baseweb="menu"] li:hover { background-color: #FDF0EA !important; }

  /* ── Stat cards ── */
  .stat-card a {
    display: block; text-decoration: none; background: #fff;
    border: 1.5px solid #eee; border-radius: 10px;
    padding: 16px 20px; transition: all 0.2s;
  }
  .stat-card a:hover { border-color: #E8612C; box-shadow: 0 4px 16px rgba(232,97,44,0.15); }
  .stat-card .label { color: #888 !important; font-size: 12px; margin-bottom: 4px; }
  .stat-card .value { color: #E8612C !important; font-size: 2rem; font-weight: 800; line-height: 1.1; }
  .stat-card .sub   { color: #aaa !important; font-size: 11px; margin-top: 2px; }

  /* ── Tables ── */
  .styled-table { width: 100%; border-collapse: collapse; font-size: 13px; }
  .styled-table thead tr th {
    background: #E8612C !important; color: #fff !important;
    padding: 10px 14px; font-weight: 700; text-align: center;
  }
  .styled-table thead tr th:first-child { text-align: left; }
  .styled-table tbody tr:nth-child(even) { background: #fafafa !important; }
  .styled-table tbody tr:nth-child(odd)  { background: #fff !important; }
  .styled-table tbody td {
    padding: 9px 14px; border-bottom: 1px solid #eee;
    text-align: center; color: #1a1a1a !important;
  }
  .styled-table tbody td:first-child { text-align: left; }
  .styled-table .total-row td { font-weight: 700; background: #f2f0ed !important; color: #1a1a1a !important; }
  .styled-table a { color: #E8612C !important; text-decoration: none; font-weight: 700; border-bottom: 1px dashed #E8612C; }
  .excl-row td { color: #999 !important; font-style: italic; background: #FDF0EA !important; }

  /* ── Section titles ── */
  .section-title {
    font-weight: 800; font-size: 17px; margin: 24px 0 12px;
    border-left: 4px solid #E8612C; padding-left: 12px; color: #1a1a1a !important;
  }
  .week-pill {
    background: #1a1a1a; color: #fff !important; font-size: 11px; font-weight: 700;
    padding: 4px 10px; border-radius: 12px; display: inline-block; margin-bottom: 8px;
  }

  /* ── Mini stat boxes (breakdown section) ── */
  .mini-stat {
    background: #fff; border: 1.5px solid #eee; border-radius: 8px;
    padding: 12px 16px; text-align: center;
  }
  .mini-stat .ms-val { color: #E8612C !important; font-size: 1.6rem; font-weight: 800; }
  .mini-stat .ms-lbl { color: #888 !important; font-size: 11px; margin-top: 2px; }

  #MainMenu, footer, header { visibility: hidden; }
  .block-container { padding-top: 1.5rem; }
</style>
""", unsafe_allow_html=True)

# ── CONSTANTS ─────────────────────────────────────────────────────────────────
FILTERS = {
    "AI Bot":              "25251640968348",
    "Messaging/Live Chat": "23607369574812",
    "Failed Operations":   "17237919534108",   # global exclusion — never displayed
    "Architect Requests":  "24101684048412",   # split into 3 sub-buckets
    "High Priority":       "23645136614684",
    "All Open":            "15018924382748",
}

KLARITY_DOMAINS   = ("@klaritylaw.com", "@klarity.ai")
ARCHITECT_EMAIL   = "architect@klarity.ai"

KNOWN_CUSTOMERS = [
    "zuora", "mongodb", "stripe", "doordash", "sentinelone", "miro",
    "linkedin", "aven", "quench", "kimball", "ipw", "uhg", "ramp",
    "cloudflare", "brex", "rippling", "workday", "salesforce", "hubspot",
]
# Proper display names for known customers
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

# Zendesk search fragments used to build per-category drill-down links
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
            "display":  f"{start.strftime('%b %d')} - {end.strftime('%b %d')}",
        })
    return weeks

def since_4_weeks():
    """Start of the 4th-most-recent complete Mon-Sun week (excludes current partial week)."""
    today       = date.today()
    this_monday = monday_of(today)
    # Go back 4 full weeks from the most recent complete week start
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
    """Exclude non-actionable internal run failure alerts.
    Tag automated_architect = non-actionable internal alert → exclude.
    architect@klarity.ai tickets = failure notifications → keep (shown as sub-bucket).
    All external requesters → keep regardless of subject.
    """
    subj = t.get("subject", "") or ""
    if not re.search(r"error running operation|error while running", subj, re.I):
        return False
    # architect@ sends legitimate failure notifications — never exclude
    req_email = (t.get("_requester_email") or "").lower()
    if req_email == ARCHITECT_EMAIL:
        return False
    # Only exclude if explicitly tagged as non-actionable internal alert
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
        # Only use solved_at from metric_sets sideload — updated_at changes on any
        # edit (tags, notes, etc.) and must not be used as a resolution timestamp.
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
def fh(v):  return f"{v}h" if v is not None else "-"

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
    """5-signal waterfall: subject pattern → org_name → tags → subject keywords → Other."""
    subj = t.get("subject", "") or ""
    tgs  = tags_of(t)

    # 1. Klarity<>CustomerName || in subject
    m = re.search(r"<>([^|<>]+)\s*\|\|", subj)
    if m:
        return m.group(1).strip()

    # 2. [TAG] CustomerName || or CustomerName || prefix in subject
    if "||" in subj:
        part = subj.split("||")[0].strip()
        # Strip leading [tag] brackets
        part = re.sub(r"^\[[^\]]*\]\s*", "", part).strip()
        if 1 < len(part) < 50 and part.lower() not in ("klarity", "klarity ai", ""):
            return part

    # 3. organization_name from Zendesk ticket (sideloaded via metric_sets/orgs)
    org = (t.get("_org_name") or "").strip()
    if org and org.lower() not in ("klarity", "klarity ai", "klarity law", ""):
        return org

    # 4. Known customer keywords in tags
    for k in KNOWN_CUSTOMERS:
        if any(k.lower() in tg.lower() for tg in tgs):
            return CUSTOMER_DISPLAY.get(k, k.title())

    # 5. Known customer keywords in subject
    subj_lower = subj.lower()
    for k in KNOWN_CUSTOMERS:
        if k.lower() in subj_lower:
            return CUSTOMER_DISPLAY.get(k, k.title())

    return "Other"

# ── ARCHITECT SUB-BUCKET CLASSIFIER ──────────────────────────────────────────
def arch_bucket(t):
    """Classify an Architect Requests ticket into one of three sub-buckets."""
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
    """Broad ticket search with cursor pagination. Returns only ticket-type results."""
    tickets, page = [], 1
    while True:
        data  = zd_get(sub, email, token, "/search.json",
                       {"query": query, "per_page": 100, "page": page})
        # Filter to ticket type only (safety — query already contains type:ticket)
        batch = [r for r in data.get("results", []) if r.get("result_type") == "ticket"]
        tickets.extend(batch)
        if not data.get("next_page") or len(data.get("results", [])) < 100:
            break
        page += 1
    return tickets

def fetch_view(sub, email, token, view_id, since=None):
    """Fetch all tickets from a Zendesk view.
    Includes users (for emails), organizations (for org_name), and metric_sets (for solved_at).
    Paginates correctly: checks raw batch size BEFORE the since-date filter.
    """
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

            # Attach enriched fields before any filtering
            for t in batch:
                t["_requester_email"] = users.get(t.get("requester_id"), "")
                t["_org_name"]        = orgs.get(t.get("organization_id"), "")
                ms = metrics.get(t["id"])
                if ms:
                    t["solved_at"] = ms.get("solved_at")  # accurate solve timestamp

            # Record raw page size BEFORE date-filtering (critical for correct pagination)
            raw_count = len(batch)

            if since:
                batch = [t for t in batch if (t.get("created_at") or "")[:10] >= since]

            tickets.extend(batch)

            # Stop when API signals no more pages OR the raw page was not full
            if not data.get("next_page") or raw_count < 100:
                break
            page += 1
        except Exception:
            break
    return tickets

# ── LOAD DATA ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def load_data(sub, email, token, since):
    # Step 1: Failed Ops view → global exclusion set (no date filter — fetch all)
    fo_view = fetch_view(sub, email, token, FILTERS["Failed Operations"])
    fo_ids  = {t["id"] for t in fo_view}

    # Step 2: Fetch each active view (with date filter)
    active_views = ["AI Bot", "Messaging/Live Chat", "Architect Requests", "High Priority"]
    view_tickets = {"Failed Operations": fo_view}
    for name in active_views:
        view_tickets[name] = fetch_view(sub, email, token, FILTERS[name], since=since)
    # All Open fetched WITHOUT a since-date so the "Unsolved in Group" card reflects
    # the full live queue including tickets older than the selected week range.
    view_tickets["All Open"] = fetch_view(sub, email, token, FILTERS["All Open"])

    # Step 3: Broad search to catch any tickets not in a specific view.
    # Use the earlier of (since, since_4_weeks) so the fixed category-performance
    # window always has the full 4 complete weeks of data regardless of what the
    # week selector is set to.
    broad_since = min(since, since_4_weeks())
    all_tickets = fetch_search(sub, email, token, f"type:ticket created>{zd_after(broad_since)}")

    # Attach requester emails/org names from view data to search results (dedup enrichment)
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

    # Step 4: Global exclusion + status split
    real     = [t for t in all_tickets if not is_excluded(t, fo_ids)]
    open_t   = [t for t in real if is_open(t)]
    closed_t = [t for t in real if is_closed(t)]

    # Step 5: Per-channel data (all filtered to since, exclusion applied)
    def view_ch(name):
        t = [x for x in view_tickets[name] if not is_excluded(x, fo_ids)]
        return {"tickets": t,
                "open":    [x for x in t if is_open(x)],
                "closed":  [x for x in t if is_closed(x)]}

    channels = {k: view_ch(k) for k in ["AI Bot", "Messaging/Live Chat",
                                          "Architect Requests", "High Priority"]}

    # Step 6: Architect sub-bucket split
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

    # Step 7: Category performance — last 4 COMPLETE Mon-Sun weeks (fixed window)
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

    # Step 8: Year weeks (for trend chart)
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
    """Zendesk created> is strictly greater-than. Subtract one day so that
    tickets created ON the target date are included in the results."""
    return (date.fromisoformat(d) - timedelta(days=1)).isoformat()

def stat_card(col, label, value, sub_text, url):
    with col:
        st.markdown(f"""<div class="stat-card"><a href="{url}" target="_blank">
          <div class="label">{label}</div>
          <div class="value">{value}</div>
          <div class="sub">{sub_text} &#8599;</div>
        </a></div>""", unsafe_allow_html=True)

def ch_table(rows, show_total=True):
    html = """<table class="styled-table"><thead><tr>
        <th>Source</th><th>Open</th><th>Closed</th><th>Total</th>
    </tr></thead><tbody>"""
    tot = [0, 0, 0]
    for label, ch, url, excl in rows:
        o = len(ch["open"]); c = len(ch["closed"]); t = len(ch["tickets"])
        if not excl: tot[0]+=o; tot[1]+=c; tot[2]+=t
        mk  = lambda v, u=url: f'<a href="{u}" target="_blank">{v}</a>' if v > 0 else '<span style="color:#bbb">0</span>'
        cls = ' class="excl-row"' if excl else ""
        html += (f'<tr{cls}><td><a href="{url}" target="_blank">{label}</a></td>'
                 f'<td>{mk(o)}</td><td>{mk(c)}</td><td>{mk(t)}</td></tr>')
    if show_total:
        html += (f'<tr class="total-row"><td><strong>TOTAL</strong></td>'
                 f'<td><strong>{tot[0]}</strong></td><td><strong>{tot[1]}</strong></td>'
                 f'<td><strong style="color:#E8612C">{tot[2]}</strong></td></tr>')
    html += "</tbody></table>"
    return html

def filter_ch_to_weeks(ch, weeks):
    """Return a channel dict filtered to the given display weeks."""
    t = [x for x in ch["tickets"] if any(in_week(x, w) for w in weeks)]
    return {"tickets": t, "open": [x for x in t if is_open(x)], "closed": [x for x in t if is_closed(x)]}

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
today  = date.today()
cur_wk = today.isocalendar()[1]
year   = today.year

with st.sidebar:
    st.markdown("### Klarity Support")
    st.markdown("---")
    subdomain = st.text_input("Subdomain", value="klarity6695")
    email     = st.text_input("Email", placeholder="you@klaritylaw.com")
    token     = st.text_input("API Token", type="password")
    st.markdown("**Week range**")
    all_wk_nums = list(range(1, cur_wk + 1))
    start_wk    = st.selectbox("From week", all_wk_nums,
                               index=max(0, len(all_wk_nums) - 4),
                               format_func=lambda w: f"Week {w}")
    end_wk      = st.selectbox("To week", all_wk_nums,
                               index=len(all_wk_nums) - 1,
                               format_func=lambda w: f"Week {w}")
    wk_start_d, _ = iso_week_bounds(year, start_wk)
    since_date    = wk_start_d.isoformat()
    run = st.button("Generate Report", use_container_width=True, type="primary")
    st.markdown("---")
    _, e_disp = iso_week_bounds(year, end_wk)
    st.markdown(
        f"<small style='color:#aaa'>Wk {start_wk} ({wk_start_d.strftime('%b %d')}) to "
        f"Wk {end_wk} ({e_disp.strftime('%b %d')})<br>"
        f"Failed Ops excluded from all counts</small>",
        unsafe_allow_html=True
    )

# ── HEADER ────────────────────────────────────────────────────────────────────
h1, h2 = st.columns([3, 1])
with h1:
    st.markdown("## Support Performance Report")
    st.markdown(
        f'<span class="week-pill">Week {start_wk} to Week {end_wk} &nbsp;|&nbsp; '
        f'{today.strftime("%d %b %Y")}</span>',
        unsafe_allow_html=True
    )
with h2:
    st.markdown(
        f"<div style='text-align:right;color:#888;font-size:12px;padding-top:16px'>"
        f"Generated {datetime.now().strftime('%d %b %Y %H:%M')}</div>",
        unsafe_allow_html=True
    )

if not run and "data" not in st.session_state:
    st.info("Enter your Zendesk credentials in the sidebar and click Generate Report.")
    st.stop()

if run:
    if not email or not token:
        st.error("Please enter your email and API token."); st.stop()
    if start_wk > end_wk:
        st.error("Start week must be before or equal to end week."); st.stop()
    # Invalidate cache whenever credentials or date range change
    cache_key = f"{subdomain}|{email}|{since_date}"
    if st.session_state.get("_cache_key") != cache_key:
        load_data.clear()
        st.session_state["_cache_key"] = cache_key
    with st.spinner("Fetching from Zendesk..."):
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

# Selected date range
display_weeks = [w for w in all_weeks if start_wk <= w["week_num"] <= end_wk]
range_real    = [t for t in real if any(in_week(t, w) for w in display_weeks)]
range_open    = [t for t in range_real if is_open(t)]
range_closed  = [t for t in range_real if is_closed(t)]
range_res     = round(len(range_closed) / len(range_real) * 100) if range_real else 0

w_since = display_weeks[0]["start"] if display_weeks else since
w_end   = display_weeks[-1]["end"]  if display_weeks else since

# Channel data filtered to the selected week range (not just since-date)
ch_ranged      = {k: filter_ch_to_weeks(v, display_weeks) for k, v in channels.items()}
arch_b_ranged  = {k: filter_ch_to_weeks(v, display_weeks) for k, v in arch_buckets.items()}

# ── STAT CARDS ────────────────────────────────────────────────────────────────
cols = st.columns(6)
_excl = '-subject:"[BACKEND ALERT]" -tags:internal_teams -tags:automated_architect'
stat_card(cols[0], "Tickets Received",  len(range_real),
          f"Wk {start_wk} – Wk {end_wk}",
          su(sub, f"type:ticket created>{zd_after(w_since)} created<{w_end} -status:new {_excl}"))
stat_card(cols[1], "Open",              len(range_open),
          f"{100 - range_res}% of total",
          su(sub, f"type:ticket status:open status:pending created>{zd_after(w_since)} created<{w_end} {_excl}"))
stat_card(cols[2], "Solved / Closed",   len(range_closed),
          f"{range_res}% resolution",
          su(sub, f"type:ticket status:solved status:closed created>{zd_after(w_since)} created<{w_end} {_excl}"))
stat_card(cols[3], "Resolution Rate",   f"{range_res}%",
          f"{len(range_closed)} of {len(range_real)} resolved",
          su(sub, f"type:ticket status:solved created>{zd_after(w_since)} created<{w_end} {_excl}"))
stat_card(cols[4], "Unsolved in Group", unsolved,
          "Failed Ops excluded",
          fu(sub, FILTERS["All Open"]))
stat_card(cols[5], "High Priority",     len(ch_ranged["High Priority"]["tickets"]),
          "View filter",
          fu(sub, FILTERS["High Priority"]))

st.caption(
    f"Failed Operations view ({fo_count} tickets) excluded from every metric. "
    f"[View bucket ↗](https://{sub}.zendesk.com/agent/filters/{FILTERS['Failed Operations']})"
)
st.markdown("---")

# ── WEEKLY METRICS ────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">Weekly Metrics</div>', unsafe_allow_html=True)
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
        ("Customer tickets",          arch_b_ranged["customer"],
         su(sub, f"type:ticket created>{zd_after(w_since)} created<{w_end} group:architect"), False),
        ("Internal — on behalf of",   arch_b_ranged["internal"],
         su(sub, f"type:ticket created>{zd_after(w_since)} created<{w_end} group:architect requester:{ARCHITECT_EMAIL}"), False),
        ("Failure notifications",     arch_b_ranged["failure_notification"],
         su(sub, f"type:ticket created>{zd_after(w_since)} created<{w_end} requester:{ARCHITECT_EMAIL}"), False),
    ], show_total=True), unsafe_allow_html=True)

st.markdown("---")

# ── CATEGORY PERFORMANCE ──────────────────────────────────────────────────────
s4 = since_4_weeks()
st.markdown('<div class="section-title">Support Performance by Category — Last 4 Weeks</div>',
            unsafe_allow_html=True)
st.caption(f"Fixed window: last 4 complete Mon–Sun weeks from {s4} (independent of week selector).")
if cat_perf:
    cat_html = """<table class="styled-table"><thead><tr>
        <th>Sub Issue type</th><th>Ticket count</th>
        <th>Median (hrs)</th><th>Average (hrs)</th><th>P90 (hrs)</th>
    </tr></thead><tbody>"""
    for cat in cat_perf:
        cat_q   = CAT_SEARCH_QUERY.get(cat["label"], "")
        url     = su(sub, f"type:ticket created>{zd_after(s4)} {cat_q}".strip())
        cat_html += (f'<tr><td><a href="{url}" target="_blank">{cat["label"]}</a></td>'
                     f'<td><a href="{url}" target="_blank">{cat["count"]}</a></td>'
                     f'<td>{fh(cat["median"])}</td><td>{fh(cat["average"])}</td><td>{fh(cat["p90"])}</td></tr>')
    cat_html += "</tbody></table>"
    st.markdown(cat_html, unsafe_allow_html=True)
else:
    st.info("No categorized tickets found in the last 4 weeks.")

st.markdown("---")

# ── WOW TREND ────────────────────────────────────────────────────────────────
st.markdown(
    f'<div class="section-title">Week by Week Trend — Wk {start_wk} to Wk {end_wk} ({year})</div>',
    unsafe_allow_html=True
)
cc, ct = st.columns([3, 2])
with cc:
    fig = go.Figure(go.Bar(
        x=[w["label"] for w in display_weeks],
        y=[w["count"] for w in display_weeks],
        marker_color="#E8612C",
        text=[w["count"] for w in display_weeks],
        textposition="outside",
        textfont=dict(color="#1a1a1a"),
        hovertemplate="<b>%{x}</b><br>%{customdata}<br>Tickets: %{y}<extra></extra>",
        customdata=[w["display"] for w in display_weeks],
    ))
    fig.update_layout(
        plot_bgcolor="white", paper_bgcolor="white",
        font=dict(family="DM Sans", size=12, color="#1a1a1a"),
        margin=dict(t=30, b=40, l=20, r=20),
        yaxis=dict(showgrid=True, gridcolor="#eee", zeroline=False, color="#1a1a1a",
                   tickfont=dict(color="#1a1a1a")),
        xaxis=dict(showgrid=False, tickangle=-45 if len(display_weeks) > 8 else 0,
                   color="#1a1a1a", tickfont=dict(color="#1a1a1a")),
        showlegend=False, height=300,
    )
    st.plotly_chart(fig, use_container_width=True)
with ct:
    st.markdown("**Top Issues (last 4 wks of selection)**")
    top_weeks = display_weeks[-4:] if len(display_weeks) >= 4 else display_weeks
    top_html  = "<table class='styled-table'><thead><tr><th>Issue</th>"
    for w in top_weeks:
        top_html += f"<th>{w['label']}</th>"
    top_html += "</tr></thead><tbody>"
    for label, rx in TOP_ISSUES:
        top_html += f"<tr><td>{label}</td>"
        for w in top_weeks:
            count = len([t for t in w["tickets"] if rx.search(t.get("subject", "") or "")])
            url   = su(sub, f"type:ticket created>{zd_after(w['start'])} created<{w['end']}")
            cell  = (f'<a href="{url}" target="_blank">{count}</a>'
                     if count else '<span style="color:#bbb">-</span>')
            top_html += f"<td>{cell}</td>"
        top_html += "</tr>"
    top_html += "</tbody></table>"
    st.markdown(top_html, unsafe_allow_html=True)

st.markdown("---")

# ── RESOLUTION TIME CHART ─────────────────────────────────────────────────────
st.markdown('<div class="section-title">Resolution Time by Category</div>', unsafe_allow_html=True)
cats_with_data = [c for c in cat_perf if c["median"] is not None]
if cats_with_data:
    df = pd.DataFrame(cats_with_data)
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(name="Median",  x=df["label"], y=df["median"],  marker_color="#E8612C"))
    fig2.add_trace(go.Bar(name="Average", x=df["label"], y=df["average"], marker_color="#1a1a1a", opacity=0.7))
    fig2.add_trace(go.Bar(name="P90",     x=df["label"], y=df["p90"],     marker_color="#f4c5aa"))
    fig2.update_layout(
        barmode="group", plot_bgcolor="white", paper_bgcolor="white",
        font=dict(family="DM Sans", size=11, color="#1a1a1a"),
        margin=dict(t=20, b=120, l=20, r=20),
        yaxis=dict(title="Hours", showgrid=True, gridcolor="#eee", color="#1a1a1a",
                   tickfont=dict(color="#1a1a1a"), title_font=dict(color="#1a1a1a")),
        xaxis=dict(tickangle=-30, color="#1a1a1a", tickfont=dict(color="#1a1a1a")),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    font=dict(color="#1a1a1a")),
        height=360,
    )
    st.plotly_chart(fig2, use_container_width=True)
else:
    st.info("No closed tickets yet — resolution times will appear once tickets are solved.")

st.markdown("---")

# ── BREAKDOWN DASHBOARD ───────────────────────────────────────────────────────
st.markdown(
    f'<div class="section-title">Ticket Breakdown — Wk {start_wk} to Wk {end_wk} &nbsp;'
    f'<span style="font-weight:400;font-size:14px;color:#888">'
    f'{len(range_real)} received · {len(range_open)} open · {len(range_closed)} solved'
    f'</span></div>',
    unsafe_allow_html=True
)

if range_real:
    # ── Row 1: Status donut + Customer breakdown ──────────────────────────────
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
            hole=0.6,
            marker_colors=[status_colors.get(k, "#ccc") for k in status_counts.keys()],
            textinfo="label+value",
            textfont=dict(color="#1a1a1a", size=13),
            hovertemplate="<b>%{label}</b><br>%{value} tickets (%{percent})<extra></extra>",
        ))
        fig_s.update_layout(
            showlegend=True,
            legend=dict(font=dict(color="#1a1a1a")),
            height=280,
            margin=dict(t=10, b=10, l=10, r=10),
            paper_bgcolor="white",
            annotations=[dict(
                text=f"<b>{len(range_real)}</b><br><span style='font-size:12px'>tickets</span>",
                x=0.5, y=0.5, font_size=18, showarrow=False, font_color="#1a1a1a"
            )]
        )
        st.plotly_chart(fig_s, use_container_width=True)

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
            url = su(sub, f"type:ticket created>{zd_after(w_since)} created<{w_end} \"{cust}\"")
            cust_html += (f'<tr><td>{cust}</td>'
                          f'<td><a href="{url}" target="_blank">{o}</a></td>'
                          f'<td><a href="{url}" target="_blank">{s}</a></td>'
                          f'<td><a href="{url}" target="_blank"><b>{tot}</b></a></td></tr>')
        cust_html += "</tbody></table>"
        st.markdown(cust_html, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Row 2: Daily volume bar + Category bar ────────────────────────────────
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
                    bar_colors.append("#f4c5aa" if wd >= 5 else "#E8612C")
                except Exception:
                    bar_colors.append("#E8612C")
            fig_d = go.Figure(go.Bar(
                x=dates, y=counts,
                marker_color=bar_colors,
                text=counts,
                textposition="outside",
                textfont=dict(color="#1a1a1a"),
                hovertemplate="<b>%{x}</b><br>%{y} tickets<extra></extra>",
            ))
            fig_d.update_layout(
                plot_bgcolor="white", paper_bgcolor="white",
                font=dict(family="DM Sans", size=11, color="#1a1a1a"),
                margin=dict(t=20, b=50, l=20, r=10),
                xaxis=dict(tickangle=-45, showgrid=False, color="#1a1a1a",
                           tickfont=dict(color="#1a1a1a")),
                yaxis=dict(showgrid=True, gridcolor="#eee", zeroline=False, color="#1a1a1a",
                           tickfont=dict(color="#1a1a1a")),
                height=300, showlegend=False,
            )
            st.plotly_chart(fig_d, use_container_width=True)
            st.caption("Orange = weekday  ·  Light = weekend")

    with col_cat:
        st.markdown("**Volume by Category**")
        cat_map_range = categorize(range_real)
        cat_labels = [lbl for lbl, _, __ in CATEGORIES if cat_map_range[lbl]]
        cat_vals   = [len(cat_map_range[lbl]) for lbl in cat_labels]
        short      = [lbl.split("/")[0].strip()[:28] for lbl in cat_labels]
        fig_c = go.Figure(go.Bar(
            x=cat_vals, y=short,
            orientation="h",
            marker_color="#E8612C",
            text=cat_vals,
            textposition="outside",
            textfont=dict(color="#1a1a1a"),
            hovertemplate="<b>%{y}</b><br>%{x} tickets<extra></extra>",
        ))
        fig_c.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            font=dict(family="DM Sans", size=11, color="#1a1a1a"),
            margin=dict(t=10, b=10, l=10, r=40),
            xaxis=dict(showgrid=True, gridcolor="#eee", color="#1a1a1a",
                       tickfont=dict(color="#1a1a1a")),
            yaxis=dict(showgrid=False, autorange="reversed", color="#1a1a1a",
                       tickfont=dict(color="#1a1a1a")),
            height=300, showlegend=False,
        )
        st.plotly_chart(fig_c, use_container_width=True)

# ── FOOTER ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="text-align:center;color:#bbb;font-size:12px;margin-top:32px;
            padding-top:16px;border-top:1px solid #eee">
  Klarity Support Report — Wk {start_wk} to Wk {end_wk} ({year}) —
  Generated {datetime.now().strftime('%d %b %Y %H:%M')} —
  <a href="https://{subdomain}.zendesk.com/agent" target="_blank"
     style="color:#E8612C">Open Zendesk</a>
</div>
""", unsafe_allow_html=True)
