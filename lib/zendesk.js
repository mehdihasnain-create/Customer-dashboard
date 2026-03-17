/**
 * Klarity Zendesk data library — JavaScript port of klarity_dashboard.py
 * All logic: exclusions, categories, customer extraction, resolution times.
 */

// ── CONSTANTS ──────────────────────────────────────────────────────────────
export const FILTERS = {
  "AI Bot":              "25251640968348",
  "Messaging/Live Chat": "23607369574812",
  "Failed Operations":   "17237919534108",
  "Architect Requests":  "24101684048412",
  "High Priority":       "23645136614684",
  "All Open":            "25994134990364",
};

export const KLARITY_DOMAINS  = ["@klaritylaw.com", "@klarity.ai"];
export const ARCHITECT_EMAIL  = "architect@klarity.ai";

export const KNOWN_CUSTOMERS = [
  "zuora","mongodb","stripe","doordash","sentinelone","miro",
  "linkedin","aven","quench","kimball","ipw","uhg","ramp",
  "cloudflare","brex","rippling","workday","salesforce","hubspot",
];

export const CUSTOMER_DISPLAY = {
  aven: "Aven Hospitality", doordash: "DoorDash", sentinelone: "SentinelOne",
  linkedin: "LinkedIn", mongodb: "MongoDB", hubspot: "HubSpot",
  cloudflare: "Cloudflare", ipw: "IPW", uhg: "UHG", ramp: "Ramp",
  miro: "Miro", zuora: "Zuora", stripe: "Stripe", quench: "Quench",
  kimball: "Kimball", brex: "Brex", rippling: "Rippling",
  workday: "Workday", salesforce: "Salesforce",
};

export const CATEGORIES = [
  { label: "Architect Run Failure / Error running operation",
    rx: /error running|error while running|run fail|architect run|flow run|operation.*fail/i,
    tags: ["architect_run_failure","operation___workflow_fail","bugs/issues"] },
  { label: "Unable to login / Access issues",
    rx: /unable.*(login|log in|sign in)|login issue|access|password|temp.*pass|sso|new.*workspace|workspace.*modif/i,
    tags: ["login","access","workspace"] },
  { label: "Table matching / Data issues",
    rx: /mismatch|match|table|missing.*line|incorrect|revenue|duplicate|deal|renewal|discrepan/i,
    tags: ["matching","table_matching","revenue","integration_issue"] },
  { label: "AI / Transcript / Hallucination issues",
    rx: /hallucin|transcript|ai interviewer|coach|indexing|insight|pilot/i,
    tags: ["transcript_processing/hallucinations","indexing/insights_errors","coach"] },
  { label: "Screenshot / Image / SOP issues",
    rx: /screenshot|image placement|sop|screen share/i,
    tags: [] },
  { label: "Token / Time limits",
    rx: /token|time limit|update with ai|anthropic token/i,
    tags: [] },
  { label: "Timeouts / Performance",
    rx: /timeout|concurrent|performance|slow/i,
    tags: [] },
  { label: "Feedback / Feature Request",
    rx: /feedback|feature request/i,
    tags: ["feedback"] },
  { label: "Others", rx: null, tags: [] },
];

export const CAT_SEARCH_QUERY = {
  "Architect Run Failure / Error running operation": "tags:architect_run_failure",
  "Unable to login / Access issues":                 "tags:login",
  "Table matching / Data issues":                    "tags:matching",
  "AI / Transcript / Hallucination issues":          "tags:transcript_processing",
  "Screenshot / Image / SOP issues":                 "subject:screenshot",
  "Token / Time limits":                             "subject:token",
  "Timeouts / Performance":                          "subject:timeout",
  "Feedback / Feature Request":                      "tags:feedback",
  "Others":                                          "",
};

export const TOP_ISSUES = [
  { label: "Run Failure / Architect errors",  rx: /error running|error while running|run fail|flow run/i },
  { label: "Login / Access / Workspace",      rx: /login|access|password|workspace|temp.*pass/i },
  { label: "Table matching / Data issues",    rx: /mismatch|match|table|missing|duplicate|deal|revenue|discrepan/i },
  { label: "AI / Transcript / Hallucination", rx: /hallucin|transcript|ai interviewer|coach|pilot/i },
];

// ── WEEK HELPERS ─────────────────────────────────────────────────────────────
export function mondayOf(d) {
  const day = new Date(d);
  const dow = day.getDay(); // 0=Sun, 1=Mon...
  const diff = (dow === 0) ? -6 : 1 - dow;
  day.setDate(day.getDate() + diff);
  return day;
}

export function isoWeekBounds(year, weekNum) {
  const jan4 = new Date(year, 0, 4);
  const week1Mon = mondayOf(jan4);
  const start = new Date(week1Mon);
  start.setDate(start.getDate() + (weekNum - 1) * 7);
  const end = new Date(start);
  end.setDate(end.getDate() + 6);
  return { start, end };
}

export function toIso(d) {
  return d.toISOString().slice(0, 10);
}

export function since4Weeks() {
  const today     = new Date();
  const thisMonday = mondayOf(today);
  const result    = new Date(thisMonday);
  result.setDate(result.getDate() - 28);
  return toIso(result);
}

export function zdAfter(isoStr) {
  const d = new Date(isoStr);
  d.setDate(d.getDate() - 1);
  return toIso(d);
}

export function getYearWeeks(year) {
  const today   = new Date();
  const curYear = today.getFullYear();
  // Rough ISO week calc
  const startOfYear = new Date(year, 0, 1);
  const curWeek     = getIsoWeek(today);
  const maxWeek     = (year === curYear) ? curWeek : 52;

  const weeks = [];
  for (let wn = 1; wn <= maxWeek; wn++) {
    const { start, end } = isoWeekBounds(year, wn);
    const isCur = (year === curYear && wn === curWeek);
    weeks.push({
      label:    `Wk ${wn}${isCur ? " (cur)" : ""}`,
      weekNum:  wn,
      start:    toIso(start),
      end:      toIso(new Date(end.getTime() + 86400000)), // exclusive end (day after Sunday)
      display:  `${fmtDate(start)} – ${fmtDate(end)}`,
    });
  }
  return weeks;
}

export function getIsoWeek(d) {
  const date = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
  date.setUTCDate(date.getUTCDate() + 4 - (date.getUTCDay() || 7));
  const yearStart = new Date(Date.UTC(date.getUTCFullYear(), 0, 1));
  return Math.ceil((((date - yearStart) / 86400000) + 1) / 7);
}

function fmtDate(d) {
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export function inWeek(ticket, week) {
  const c = (ticket.created_at || "").slice(0, 10);
  return c >= week.start && c < week.end;
}

// ── TICKET CLASSIFIERS ────────────────────────────────────────────────────────
function tagsOf(t) {
  return new Set(t.tags || []);
}

function isBackendAlert(t) {
  return /\[BACKEND ALERT\]/i.test(t.subject || "");
}

function isInternalTeams(t) {
  return tagsOf(t).has("internal_teams");
}

export function isKlarityStaff(email) {
  const e = (email || "").toLowerCase();
  return KLARITY_DOMAINS.some(d => e.endsWith(d));
}

function isInternalRunFailure(t) {
  if (!/error running operation|error while running/i.test(t.subject || "")) return false;
  const req = (t._requester_email || "").toLowerCase();
  if (req === ARCHITECT_EMAIL) return false;
  return tagsOf(t).has("automated_architect");
}

export function isExcluded(t, foIds) {
  if (foIds.has(t.id))            return true;
  if (t.status === "new")         return true;
  if (isBackendAlert(t))          return true;
  if (isInternalTeams(t))         return true;
  if (isInternalRunFailure(t))    return true;
  return false;
}

export function isOpen(t)   { return t.status === "open"   || t.status === "pending"; }
export function isClosed(t) { return t.status === "solved" || t.status === "closed"; }

export function resHours(t) {
  if (!isClosed(t)) return null;
  try {
    const created  = new Date(t.created_at);
    const solvedAt = t.solved_at;
    if (!solvedAt) return null;
    const solved   = new Date(solvedAt);
    const h        = Math.round((solved - created) / 3600000);
    return h >= 0 ? h : null;
  } catch { return null; }
}

export function median(arr) {
  if (!arr.length) return null;
  const s = [...arr].sort((a, b) => a - b);
  return s[Math.floor(s.length / 2)];
}
export function mean(arr) {
  if (!arr.length) return null;
  return Math.round(arr.reduce((a, b) => a + b, 0) / arr.length);
}
export function p90(arr) {
  if (!arr.length) return null;
  const s = [...arr].sort((a, b) => a - b);
  return s[Math.floor(s.length * 0.9)];
}
export function fh(v) { return v !== null && v !== undefined ? `${v}h` : "—"; }

export function categorize(tickets) {
  const result = {};
  CATEGORIES.forEach(c => { result[c.label] = []; });
  for (const t of tickets) {
    const subj = t.subject || "";
    const tgs  = tagsOf(t);
    for (const { label, rx, tags } of CATEGORIES) {
      if (!rx || rx.test(subj) || tags.some(tg => tgs.has(tg))) {
        result[label].push(t);
        break;
      }
    }
  }
  return result;
}

export function extractCustomer(t) {
  const subj = t.subject || "";
  const tgs  = tagsOf(t);

  // 1. Klarity<>CustomerName || in subject
  const m1 = subj.match(/<>([^|<>]+)\s*\|\|/);
  if (m1) return m1[1].trim();

  // 2. CustomerName || prefix
  if (subj.includes("||")) {
    let part = subj.split("||")[0].trim();
    part = part.replace(/^\[[^\]]*\]\s*/, "").trim();
    if (part.length > 1 && part.length < 50 && !["klarity","klarity ai",""].includes(part.toLowerCase()))
      return part;
  }

  // 3. org_name
  const org = (t._org_name || "").trim();
  if (org && !["klarity","klarity ai","klarity law",""].includes(org.toLowerCase()))
    return org;

  // 4. tags
  for (const k of KNOWN_CUSTOMERS) {
    for (const tg of tgs) {
      if (tg.toLowerCase().includes(k)) return CUSTOMER_DISPLAY[k] || cap(k);
    }
  }

  // 5. subject keywords
  const subjLow = subj.toLowerCase();
  for (const k of KNOWN_CUSTOMERS) {
    if (subjLow.includes(k)) return CUSTOMER_DISPLAY[k] || cap(k);
  }

  return "Other";
}

function cap(s) { return s.charAt(0).toUpperCase() + s.slice(1); }

export function archBucket(t) {
  const req = (t._requester_email || "").toLowerCase();
  if (req === ARCHITECT_EMAIL)    return "failure_notification";
  if (isKlarityStaff(req))        return "internal";
  return "customer";
}

// ── ZENDESK API (server-side) ─────────────────────────────────────────────────
export async function zdGet(sub, email, token, path, params = {}) {
  const url    = new URL(`https://${sub}.zendesk.com/api/v2${path}`);
  Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));
  const auth   = Buffer.from(`${email}/token:${token}`).toString("base64");
  const res    = await fetch(url.toString(), {
    headers: { Authorization: `Basic ${auth}`, "Content-Type": "application/json" },
  });
  if (!res.ok) {
    const err = new Error(`Zendesk ${res.status}: ${res.statusText}`);
    err.status = res.status;
    throw err;
  }
  return res.json();
}

export async function fetchSearch(sub, email, token, query) {
  const tickets = [];
  let page = 1;
  while (true) {
    const data  = await zdGet(sub, email, token, "/search.json", { query, per_page: 100, page });
    const batch = (data.results || []).filter(r => r.result_type === "ticket");
    tickets.push(...batch);
    if (!data.next_page || (data.results || []).length < 100) break;
    page++;
  }
  return tickets;
}

export async function fetchView(sub, email, token, viewId, since = null) {
  const tickets = [];
  let page = 1;
  while (true) {
    try {
      const data = await zdGet(sub, email, token, `/views/${viewId}/tickets.json`, {
        per_page: 100, page, include: "users,organizations,metric_sets",
      });
      const users   = {};
      (data.users   || []).forEach(u => { users[u.id]   = u.email || ""; });
      const orgs    = {};
      (data.organizations || []).forEach(o => { orgs[o.id] = o.name || ""; });
      const metrics = {};
      (data.metric_sets   || []).forEach(m => { metrics[m.ticket_id] = m; });
      const batch = data.tickets || [];

      for (const t of batch) {
        t._requester_email = users[t.requester_id] || "";
        t._org_name        = orgs[t.organization_id] || "";
        const ms = metrics[t.id];
        if (ms) t.solved_at = ms.solved_at;
      }

      const rawCount = batch.length;
      const filtered = since ? batch.filter(t => (t.created_at || "").slice(0, 10) >= since) : batch;
      tickets.push(...filtered);

      if (!data.next_page || rawCount < 100) break;
      page++;
    } catch { break; }
  }
  return tickets;
}

// ── MAIN DATA LOADER ──────────────────────────────────────────────────────────
export async function loadData(sub, email, token, since) {
  // Step 1: Failed Ops → exclusion set
  const foView = await fetchView(sub, email, token, FILTERS["Failed Operations"]);
  const foIds  = new Set(foView.map(t => t.id));

  // Step 2: Active views
  const activeViews = ["AI Bot", "Messaging/Live Chat", "Architect Requests", "High Priority"];
  const viewTickets = { "Failed Operations": foView };
  await Promise.all(activeViews.map(async name => {
    viewTickets[name] = await fetchView(sub, email, token, FILTERS[name], since);
  }));
  viewTickets["All Open"] = await fetchView(sub, email, token, FILTERS["All Open"]);

  // Step 3: Broad search
  const broadSince = since < since4Weeks() ? since : since4Weeks();
  const allTickets = await fetchSearch(sub, email, token,
    `type:ticket created>${zdAfter(broadSince)}`);

  // Enrich from view data
  const emailMap = {}; const orgMap = {}; const solveMap = {};
  for (const vl of Object.values(viewTickets)) {
    for (const t of vl) {
      if (t._requester_email) emailMap[t.id] = t._requester_email;
      if (t._org_name)        orgMap[t.id]   = t._org_name;
      if (t.solved_at)        solveMap[t.id] = t.solved_at;
    }
  }
  for (const t of allTickets) {
    if (!t._requester_email) t._requester_email = emailMap[t.id] || "";
    if (!t._org_name)        t._org_name        = orgMap[t.id]   || "";
    if (!t.solved_at)        t.solved_at        = solveMap[t.id] || null;
  }

  // Step 4: Exclusions + status split
  const real     = allTickets.filter(t => !isExcluded(t, foIds));
  const openT    = real.filter(isOpen);
  const closedT  = real.filter(isClosed);

  // Step 5: Channels
  function viewCh(name) {
    const t = viewTickets[name].filter(t => !isExcluded(t, foIds));
    return { tickets: t, open: t.filter(isOpen), closed: t.filter(isClosed) };
  }
  const channels = {};
  ["AI Bot","Messaging/Live Chat","Architect Requests","High Priority"].forEach(k => {
    channels[k] = viewCh(k);
  });

  // Step 6: Architect sub-buckets
  const archAll = channels["Architect Requests"].tickets;
  const archBuckets = {};
  ["customer","internal","failure_notification"].forEach(bk => {
    const lst = archAll.filter(t => archBucket(t) === bk);
    archBuckets[bk] = { tickets: lst, open: lst.filter(isOpen), closed: lst.filter(isClosed) };
  });

  // Step 7: Category performance (last 4 complete weeks)
  const s4     = since4Weeks();
  const real4w = real.filter(t => (t.created_at || "").slice(0, 10) >= s4);
  const catMap = categorize(real4w);
  const catPerf = CATEGORIES
    .map(({ label }) => {
      const tix   = catMap[label];
      if (!tix.length) return null;
      const times = tix.map(resHours).filter(h => h !== null);
      return { label, count: tix.length, median: median(times), average: mean(times), p90: p90(times) };
    })
    .filter(Boolean)
    .sort((a, b) => b.count - a.count);

  // Step 8: Year weeks with counts
  const year     = new Date().getFullYear();
  const allWeeks = getYearWeeks(year);
  for (const w of allWeeks) {
    w.tickets = real.filter(t => inWeek(t, w));
    w.count   = w.tickets.length;
  }

  const unsolved = viewTickets["All Open"].filter(t => !isExcluded(t, foIds));

  return {
    real, openT, closedT,
    channels, archBuckets,
    catPerf, allWeeks,
    unsolvedCount: unsolved.length,
    foCount: foView.length,
    since,
    since4w: s4,
  };
}
