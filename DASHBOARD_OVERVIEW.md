# Klarity Support Report Dashboard — Overview

> **File:** `klarity_dashboard.py`
> **Version:** v8
> **Stack:** Python · Streamlit · Plotly · Pandas · Zendesk REST API

---

## What It Does

A self-serve internal reporting dashboard that connects to **Klarity's Zendesk account** and generates a live Support Performance Report. Anyone on the team can enter their Zendesk credentials, pick a week range, and get a fully rendered report — no code changes needed.

---

## How to Run

```bash
# One-off (no PATH setup needed)
python3 -m streamlit run klarity_dashboard.py

# After adding Python bin to PATH (see setup note below)
streamlit run klarity_dashboard.py
```

**Dependencies** (install once):
```bash
pip3 install requests streamlit plotly pandas
```

**PATH fix for macOS** (if `streamlit` command is not found):
```bash
echo 'export PATH="$HOME/Library/Python/3.13/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

---

## Sidebar — Credentials & Controls

| Field | Purpose |
|---|---|
| **Subdomain** | Your Zendesk subdomain (e.g. `klarity6695`) |
| **Email** | Your Zendesk agent email |
| **API Token** | Zendesk API token (stored as password field, never shown) |
| **From week / To week** | ISO week range selector — defaults to the last 4 weeks |
| **Generate Report** | Fetches data and renders the full report |

The cache is automatically invalidated whenever the subdomain, email, or date range changes.

---

## Zendesk Views Used

| View Name | View ID | Role |
|---|---|---|
| AI Bot | `25251640968348` | Customer tickets via AI bot channel |
| Messaging / Live Chat | `23607369574812` | Live chat tickets |
| Architect Requests | `24101684048412` | Architect-routed tickets (split into 3 sub-buckets) |
| High Priority | `23645136614684` | Escalated / urgent tickets |
| All Open | `15018924382748` | Full open queue snapshot |
| Failed Operations | `17237919534108` | **Global exclusion** — these tickets are never counted |

---

## Data Pipeline (Step by Step)

```
1. Fetch "Failed Operations" view (all time) → build exclusion ID set
2. Fetch each active view with a since-date filter
   └─ Each ticket enriched with: requester email, org name, solved_at (metric_sets sideload)
3. Broad Zendesk search for ALL tickets since the since-date
   └─ Enrichment data from step 2 is merged in (deduplication)
4. Apply global exclusions:
   - In "Failed Operations" view
   - Status = "new"
   - Subject matches [BACKEND ALERT]
   - Tagged "internal_teams"
   - Internal run failure (unless tagged "customer" or from architect@klarity.ai)
5. Split into open / closed
6. Split Architect tickets into 3 sub-buckets (see below)
7. Compute category performance over the last 4 complete Mon–Sun weeks
8. Build per-ISO-week ticket counts for the trend chart
```

---

## Architect Requests — 3 Sub-Buckets

| Sub-Bucket | Logic |
|---|---|
| **Customer tickets** | Requester is NOT a Klarity email and NOT `architect@klarity.ai` |
| **Internal — on behalf of** | Requester has a `@klaritylaw.com` or `@klarity.ai` email |
| **Failure notifications** | Requester is exactly `architect@klarity.ai` |

---

## Ticket Exclusion Rules

A ticket is excluded from all metrics if **any** of the following are true:

- Its ID is in the Failed Operations view
- Its status is `new`
- Its subject contains `[BACKEND ALERT]`
- It is tagged `internal_teams`
- Its subject matches *"error running operation"* or *"error while running"*, the requester is a Klarity staff email, and it is **not** tagged `customer` (internal run failures) — unless sent by `architect@klarity.ai`

---

## Customer Name Extraction — 5-Signal Waterfall

For each ticket, the customer name is resolved in this priority order:

1. **Subject pattern** — `Klarity<>CustomerName ||` format
2. **Subject prefix** — `CustomerName ||` at the start (strips leading `[tag]` brackets)
3. **Zendesk org name** — sideloaded `organization_name` field (excluding Klarity entities)
4. **Tags** — known customer keywords matched against ticket tags
5. **Subject keywords** — known customer keywords searched in the subject text
6. Falls back to **"Other"**

Known customers tracked: Zuora, MongoDB, Stripe, DoorDash, SentinelOne, Miro, LinkedIn, Aven, Quench, Kimball, IPW, UHG, Ramp, Cloudflare, Brex, Rippling, Workday, Salesforce, HubSpot.

---

## Issue Categories

Tickets are auto-classified into these buckets (matched against subject text and tags):

| Category | How It Matches |
|---|---|
| Architect Run Failure / Error running operation | Subject: `error running`, `run fail`, `flow run`, etc. or tags: `architect_run_failure`, `bugs/issues` |
| Unable to login / Access issues | Subject: `login`, `access`, `password`, `sso`, `workspace` etc. |
| Table matching / Data issues | Subject: `mismatch`, `match`, `table`, `duplicate`, `revenue`, etc. |
| AI / Transcript / Hallucination issues | Subject: `hallucin`, `transcript`, `ai interviewer`, `coach`, etc. |
| Screenshot / Image / SOP issues | Subject: `screenshot`, `image placement`, `sop` |
| Token / Time limits | Subject: `token`, `time limit`, `anthropic token` |
| Timeouts / Performance | Subject: `timeout`, `concurrent`, `performance`, `slow` |
| Feedback / Feature Request | Subject: `feedback`, `feature request` |
| Others | Everything that doesn't match above |

---

## Resolution Time Metrics

For closed tickets, resolution time is calculated as:

```
resolved_at (from metric_sets sideload, fallback: updated_at) − created_at
```

Three statistics are reported per category:

- **Median** — middle value (robust to outliers)
- **Average** — mean across all closed tickets
- **P90** — 90th percentile (worst-case excluding extreme outliers)

---

## Dashboard Sections

### 1. Stat Cards (top row — 6 cards)
Each card is **clickable** and links directly to the corresponding Zendesk search or filter.

| Card | What It Shows |
|---|---|
| Tickets Received | Total non-excluded tickets in selected week range |
| Open | Open + pending tickets in range |
| Solved / Closed | Resolved tickets in range |
| Resolution Rate | % of tickets resolved |
| Unsolved in Group | Count from "All Open" view (excl. Failed Ops) |
| High Priority | Tickets in the High Priority view |

### 2. Weekly Metrics Tables
Two side-by-side tables:
- **Customer Raised Tickets** — AI Bot + Messaging/Live Chat + Architect Customer sub-bucket
- **Architect Breakdown** — all 3 Architect sub-buckets with open/closed/total counts

### 3. Support Performance by Category — Last 4 Weeks
Fixed 4-week window (last 4 complete Mon–Sun weeks, independent of the week selector). Shows ticket count + median / average / P90 resolution times per category.

### 4. Week by Week Trend Chart
Bar chart of ticket volume per ISO week for the selected range, with a **Top Issues** table alongside it showing the 4 most recent weeks broken down by issue type.

### 5. Resolution Time by Category (grouped bar chart)
Median, Average, and P90 resolution hours visualised side-by-side per category.

### 6. Ticket Breakdown
- **Status Donut Chart** — Open / Pending / Solved / Closed distribution
- **Top Customers by Volume** — up to 15 customers ranked by total tickets, with open/solved split
- **Daily Ticket Volume** — bar chart coloured by weekday (orange) vs weekend (light)
- **Volume by Category** — horizontal bar chart

---

## Caching

- Data is cached for **5 minutes** (`@st.cache_data(ttl=300)`)
- Cache is **cleared immediately** when subdomain, email, or since-date changes
- Cache is **cleared** on 401 authentication errors

---

## Theming & Styling

Configured via `.streamlit/config.toml`:

| Setting | Value |
|---|---|
| Base theme | Light |
| Primary colour | `#E8612C` (Klarity orange) |
| Background | `#f7f5f2` (warm off-white) |
| Text | `#1a1a1a` (near-black) |
| Font | DM Sans (loaded from Google Fonts) |

The sidebar is forced **dark** (`#1a1a1a`) via inline CSS overrides for contrast. All Plotly charts have explicit `tickfont` settings per axis to ensure text remains visible regardless of Streamlit's theme injection.

---

## Key Technical Decisions

| Decision | Why |
|---|---|
| Pagination checks raw batch size before since-filtering | Prevents premature loop exit when a full 100-ticket page is filtered down to 0 |
| `metric_sets` sideload on view fetches | Gets accurate `solved_at` timestamps (Zendesk's ticket `updated_at` is not reliable for resolution time) |
| `organizations` sideload | Provides org name for customer extraction without extra API calls |
| 4-week window is always complete Mon–Sun weeks | Avoids partial-week skew in performance averages |
| Failed Ops fetched without date filter | Ensures old failed-op ticket IDs are still excluded even if created before the since-date |
