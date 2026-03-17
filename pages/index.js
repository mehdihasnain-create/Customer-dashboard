import { useState, useMemo } from "react";
import dynamic from "next/dynamic";
import Head from "next/head";
import StatCard from "../components/StatCard";
import SectionHeader from "../components/SectionHeader";
import StatusPill from "../components/StatusPill";
import ChannelTable from "../components/ChannelTable";
import {
  FILTERS, CAT_SEARCH_QUERY, TOP_ISSUES,
  isoWeekBounds, getYearWeeks, since4Weeks, zdAfter,
  inWeek, isOpen, isClosed, categorize, extractCustomer,
  fh, median, mean, p90, archBucket, resHours, getIsoWeek,
} from "../lib/zendesk";

// Recharts — no SSR (browser-only)
const BarChart = dynamic(() => import("recharts").then(m => m.BarChart), { ssr: false });
const Bar      = dynamic(() => import("recharts").then(m => m.Bar),      { ssr: false });
const PieChart = dynamic(() => import("recharts").then(m => m.PieChart), { ssr: false });
const Pie      = dynamic(() => import("recharts").then(m => m.Pie),      { ssr: false });
const Cell     = dynamic(() => import("recharts").then(m => m.Cell),     { ssr: false });
const XAxis    = dynamic(() => import("recharts").then(m => m.XAxis),    { ssr: false });
const YAxis    = dynamic(() => import("recharts").then(m => m.YAxis),    { ssr: false });
const CartesianGrid = dynamic(() => import("recharts").then(m => m.CartesianGrid), { ssr: false });
const Tooltip  = dynamic(() => import("recharts").then(m => m.Tooltip),  { ssr: false });
const Legend   = dynamic(() => import("recharts").then(m => m.Legend),   { ssr: false });
const ResponsiveContainer = dynamic(() => import("recharts").then(m => m.ResponsiveContainer), { ssr: false });

const ZD_EXCL = '-status:new -tags:internal_teams -tags:automated_architect -subject:"BACKEND ALERT"';

function fu(sub, fid) { return `https://${sub}.zendesk.com/agent/filters/${fid}`; }
function su(sub, q)   {
  return `https://${sub}.zendesk.com/agent/search?q=${encodeURIComponent(q)}`;
}
function tu(sub, tid) { return `https://${sub}.zendesk.com/agent/tickets/${tid}`; }

function Divider() {
  return <hr className="fancy-divider" />;
}

function MiniStat({ value, label }) {
  return (
    <div className="mini-stat">
      <div className="text-4xl font-black leading-none tracking-tight mb-1" style={{ color: "var(--brand)" }}>
        {value}
      </div>
      <div className="text-[11px] font-semibold uppercase tracking-wide text-gray-400 mt-1.5">{label}</div>
    </div>
  );
}

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white rounded-xl shadow-xl border border-black/[0.08] px-4 py-3 text-sm">
      <p className="font-bold mb-1" style={{ color: "var(--ink)" }}>{label}</p>
      {payload.map(p => (
        <p key={p.name} style={{ color: p.color || "var(--brand)" }}>
          {p.name}: <strong>{p.value}</strong>
        </p>
      ))}
    </div>
  );
}

export default function Dashboard() {
  const today     = new Date();
  const curYear   = today.getFullYear();
  const curIsoWk  = getIsoWeek(today);

  const allWkNums = Array.from({ length: curIsoWk }, (_, i) => i + 1);
  const [subdomain, setSubdomain] = useState("klarity6695");
  const [email,     setEmail]     = useState("");
  const [token,     setToken]     = useState("");
  const [startWk,   setStartWk]   = useState(Math.max(1, curIsoWk - 3));
  const [endWk,     setEndWk]     = useState(curIsoWk);
  const [loading,   setLoading]   = useState(false);
  const [error,     setError]     = useState(null);
  const [data,      setData]      = useState(null);

  // Sidebar collapsed state
  const [sideOpen, setSideOpen] = useState(true);

  const { start: wkStartD } = isoWeekBounds(curYear, startWk);
  const { end:   wkEndD }   = isoWeekBounds(curYear, endWk);
  const sinceDate = wkStartD.toISOString().slice(0, 10);

  async function generate(e) {
    e.preventDefault();
    if (!email || !token) { setError("Enter your email and API token."); return; }
    if (startWk > endWk)  { setError("Start week must be ≤ end week."); return; }
    setError(null);
    setLoading(true);
    try {
      const res = await fetch("/api/report", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ subdomain, email, token, since: sinceDate }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.error || `HTTP ${res.status}`);
      setData(json);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  // ── Derived data ────────────────────────────────────────────────────────
  const derived = useMemo(() => {
    if (!data) return null;

    const allWeeks     = data.allWeeks || [];
    const displayWeeks = allWeeks.filter(w => w.weekNum >= startWk && w.weekNum <= endWk);
    const wSince       = displayWeeks[0]?.start ?? sinceDate;
    const wEnd         = displayWeeks[displayWeeks.length - 1]?.end ?? sinceDate;

    const rangeReal   = (data.real || []).filter(t => displayWeeks.some(w => inWeek(t, w)));
    const rangeOpen   = rangeReal.filter(isOpen);
    const rangeClosed = rangeReal.filter(isClosed);
    const rangeRes    = rangeReal.length ? Math.round(rangeClosed.length / rangeReal.length * 100) : 0;

    // Channel data filtered to display weeks
    function filterCh(ch) {
      const t = (ch?.tickets || []).filter(t => displayWeeks.some(w => inWeek(t, w)));
      return { tickets: t, open: t.filter(isOpen), closed: t.filter(isClosed) };
    }
    const chRanged     = Object.fromEntries(Object.entries(data.channels || {}).map(([k, v]) => [k, filterCh(v)]));
    const archRanged   = Object.fromEntries(Object.entries(data.archBuckets || {}).map(([k, v]) => [k, filterCh(v)]));

    // Category perf (last 4 weeks) — already computed server-side
    const catPerf = data.catPerf || [];

    // Trend data for chart (counts already computed server-side in allWeeks)
    const trendData = displayWeeks.map(w => ({
      name:    w.label,
      tickets: w.count,
      display: w.display,
    }));

    // Status distribution
    const statusCounts = {};
    rangeReal.forEach(t => {
      const s = (t.status || "unknown");
      statusCounts[s] = (statusCounts[s] || 0) + 1;
    });
    const statusData = Object.entries(statusCounts).map(([name, value]) => ({ name, value }));

    // Daily volume
    const dailyCounts = {};
    rangeReal.forEach(t => {
      const d = (t.created_at || "").slice(0, 10);
      if (d) dailyCounts[d] = (dailyCounts[d] || 0) + 1;
    });
    const dailyData = Object.keys(dailyCounts).sort().map(d => ({
      date:    d,
      short:   d.slice(5), // MM-DD
      count:   dailyCounts[d],
      weekend: new Date(d).getDay() === 0 || new Date(d).getDay() === 6,
    }));

    // Volume by category
    const catMapRange = categorize(rangeReal);
    const catVolData  = Object.entries(catMapRange)
      .map(([label, tix]) => ({ label: label.split("/")[0].trim().slice(0, 28), count: tix.length }))
      .filter(r => r.count > 0)
      .sort((a, b) => b.count - a.count);

    // Top customers
    const custMap = {};
    rangeReal.forEach(t => {
      const c = extractCustomer(t);
      if (!custMap[c]) custMap[c] = { open: 0, solved: 0 };
      if (isOpen(t)) custMap[c].open++;
      else custMap[c].solved++;
    });
    const topCustomers = Object.entries(custMap)
      .sort((a, b) => (b[1].open + b[1].solved) - (a[1].open + a[1].solved))
      .slice(0, 15);

    // Resolution time by category chart
    const resData = catPerf
      .filter(c => c.median !== null)
      .map(c => ({
        name:    c.label.split("/")[0].trim().slice(0, 28),
        Median:  c.median,
        Average: c.average,
        P90:     c.p90,
      }));

    // Top issues per last-4-weeks of selection (compute counts from real tickets)
    const top4Weeks = displayWeeks.slice(-4).map(w => ({
      ...w,
      // Re-attach tickets from data.real for top-issues counting
      tickets: (data.real || []).filter(t => inWeek(t, w)),
    }));

    return {
      displayWeeks, wSince, wEnd,
      rangeReal, rangeOpen, rangeClosed, rangeRes,
      chRanged, archRanged, catPerf,
      trendData, statusData, dailyData, catVolData, topCustomers, resData,
      top4Weeks,
      unsolvedCount: data.unsolvedCount,
      foCount: data.foCount,
      since4w: data.since4w,
    };
  }, [data, startWk, endWk]);

  const s4 = since4Weeks();

  // ── Status pie colours ──────────────────────────────────────────────────
  const STATUS_COLORS = { open: "#E8612C", pending: "#f4a261", solved: "#2a9d8f", closed: "#457b9d" };

  return (
    <>
      <Head>
        <title>Klarity Support Report</title>
        <meta name="description" content="Klarity Support Performance Dashboard" />
        <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🟠</text></svg>" />
      </Head>

      <div className="flex min-h-screen">
        {/* ── SIDEBAR ─────────────────────────────────────────────────── */}
        <aside
          className="flex-shrink-0 flex flex-col transition-all duration-300"
          style={{
            width: sideOpen ? 260 : 0,
            background: "linear-gradient(180deg, #161616 0%, #1e1e1e 100%)",
            borderRight: "1px solid rgba(255,255,255,0.06)",
            overflow: "hidden",
          }}
        >
          <div style={{ minWidth: 260 }} className="flex flex-col h-full">
            <div className="px-6 pt-7 pb-4">
              <div className="text-xl font-black text-white tracking-tight mb-0.5">
                klarity<span style={{ color: "var(--brand)" }}>.</span>
              </div>
              <div className="text-[11px] text-white/30 font-medium mb-6">Support Performance</div>

              <form onSubmit={generate} className="space-y-4">
                <div>
                  <label className="block text-[11px] font-semibold text-white/40 uppercase tracking-wider mb-1.5">
                    Subdomain
                  </label>
                  <input
                    value={subdomain}
                    onChange={e => setSubdomain(e.target.value)}
                    className="w-full rounded-lg px-3 py-2 text-sm bg-white/10 border border-white/10 text-white placeholder-white/30 focus:outline-none focus:border-brand/50"
                    placeholder="klarity6695"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-white/40 uppercase tracking-wider mb-1.5">
                    Email
                  </label>
                  <input
                    value={email}
                    onChange={e => setEmail(e.target.value)}
                    type="email"
                    className="w-full rounded-lg px-3 py-2 text-sm bg-white/10 border border-white/10 text-white placeholder-white/30 focus:outline-none focus:border-brand/50"
                    placeholder="you@klaritylaw.com"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-white/40 uppercase tracking-wider mb-1.5">
                    API Token
                  </label>
                  <input
                    value={token}
                    onChange={e => setToken(e.target.value)}
                    type="password"
                    className="w-full rounded-lg px-3 py-2 text-sm bg-white/10 border border-white/10 text-white placeholder-white/30 focus:outline-none focus:border-brand/50"
                    placeholder="••••••••••••"
                  />
                </div>

                <div className="pt-1">
                  <label className="block text-[11px] font-semibold text-white/40 uppercase tracking-wider mb-1.5">
                    Week Range
                  </label>
                  <div className="flex gap-2">
                    <select
                      value={startWk}
                      onChange={e => setStartWk(Number(e.target.value))}
                      className="flex-1 rounded-lg px-2 py-2 text-sm bg-white/10 border border-white/10 text-white focus:outline-none"
                    >
                      {allWkNums.map(w => <option key={w} value={w} style={{ background: "#1e1e1e" }}>Wk {w}</option>)}
                    </select>
                    <span className="text-white/30 self-center text-xs">to</span>
                    <select
                      value={endWk}
                      onChange={e => setEndWk(Number(e.target.value))}
                      className="flex-1 rounded-lg px-2 py-2 text-sm bg-white/10 border border-white/10 text-white focus:outline-none"
                    >
                      {allWkNums.map(w => <option key={w} value={w} style={{ background: "#1e1e1e" }}>Wk {w}</option>)}
                    </select>
                  </div>
                  <div className="text-[11px] text-white/25 mt-2">
                    {wkStartD.toLocaleDateString("en-US", { month: "short", day: "numeric" })} →{" "}
                    {wkEndD.toLocaleDateString("en-US", { month: "short", day: "numeric" })}
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full py-2.5 rounded-xl font-bold text-sm text-white transition-all"
                  style={{
                    background: "linear-gradient(135deg, #E8612C, #c0392b)",
                    boxShadow: "0 4px 14px rgba(232,97,44,0.35)",
                    opacity: loading ? 0.7 : 1,
                  }}
                >
                  {loading ? (
                    <span className="flex items-center justify-center gap-2">
                      <svg className="spinner w-4 h-4" viewBox="0 0 24 24" fill="none">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="white" strokeWidth="4"/>
                        <path className="opacity-75" fill="white" d="M4 12a8 8 0 018-8v8z"/>
                      </svg>
                      Fetching…
                    </span>
                  ) : "Generate Report"}
                </button>
              </form>

              {error && (
                <div className="mt-3 rounded-lg px-3 py-2 text-[12px] text-red-300 bg-red-900/30 border border-red-500/20">
                  {error}
                </div>
              )}
            </div>

            <div className="mt-auto px-6 pb-6 text-[11px] text-white/20">
              Failed Ops excluded from all counts
            </div>
          </div>
        </aside>

        {/* ── MAIN CONTENT ─────────────────────────────────────────────── */}
        <main className="flex-1 min-w-0 overflow-x-hidden">
          {/* ── HERO ── */}
          <div
            className="relative overflow-hidden px-8 py-7"
            style={{ background: "linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%)" }}
          >
            {/* orange top line */}
            <div
              className="absolute top-0 left-0 right-0 h-[3px]"
              style={{ background: "linear-gradient(90deg, #E8612C, #f4a261, #E8612C)" }}
            />
            {/* glow orb */}
            <div
              className="absolute -top-16 -right-16 w-48 h-48 rounded-full"
              style={{ background: "radial-gradient(circle, rgba(232,97,44,0.15) 0%, transparent 70%)" }}
            />
            <div className="flex items-start justify-between relative z-10">
              <div>
                <div className="flex items-center gap-3 mb-1">
                  <button
                    onClick={() => setSideOpen(!sideOpen)}
                    className="text-white/40 hover:text-white/80 transition-colors text-lg"
                    title="Toggle sidebar"
                  >
                    ☰
                  </button>
                  <h1 className="text-2xl font-black text-white tracking-tight">
                    Support Performance Report
                  </h1>
                </div>
                <p className="text-white/40 text-sm ml-9">
                  Klarity · Zendesk Analytics · {today.toLocaleDateString("en-US", { month: "long", year: "numeric" })}
                </p>
                <div
                  className="inline-flex items-center gap-2 mt-3 ml-9 px-3 py-1 rounded-full text-xs font-semibold"
                  style={{
                    background: "rgba(232,97,44,0.15)",
                    border: "1px solid rgba(232,97,44,0.3)",
                    color: "#f4a261",
                  }}
                >
                  <span className="w-1.5 h-1.5 rounded-full bg-brand inline-block" />
                  Week {startWk} – Week {endWk} &nbsp;·&nbsp; {today.toLocaleDateString("en-US", { day: "numeric", month: "short", year: "numeric" })}
                </div>
              </div>
              <div className="text-right text-white/30 text-xs">
                <div>Generated</div>
                <div className="font-semibold text-white/50">{today.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" })}</div>
              </div>
            </div>
          </div>

          <div className="px-8 pb-16">

            {/* No data yet */}
            {!data && !loading && (
              <div className="mt-10 empty-state py-16 flex flex-col items-center rounded-2xl border-2 border-dashed border-gray-200">
                <span className="text-5xl mb-4">📊</span>
                <p className="font-bold text-gray-500 text-base mb-1">Ready to generate your report</p>
                <p className="text-sm text-gray-400">Enter your Zendesk credentials and click <strong>Generate Report</strong></p>
              </div>
            )}

            {loading && (
              <div className="mt-10 flex flex-col items-center py-20">
                <svg className="spinner w-10 h-10 mb-4" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-20" cx="12" cy="12" r="10" stroke="#E8612C" strokeWidth="3"/>
                  <path fill="#E8612C" d="M4 12a8 8 0 018-8v8z"/>
                </svg>
                <p className="text-gray-400 font-medium">Fetching data from Zendesk…</p>
              </div>
            )}

            {/* ── DATA RENDERS ── */}
            {data && derived && (
              <div className="flash-in">
                {/* ── STAT CARDS ── */}
                <div className="mt-7 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
                  <StatCard icon="📥" label="Tickets Received" value={derived.rangeReal.length}
                    sub={`Wk ${startWk} – Wk ${endWk}`}
                    href={su(subdomain, `type:ticket created>${zdAfter(derived.wSince)} created<${derived.wEnd} ${ZD_EXCL}`)} />
                  <StatCard icon="🔓" label="Open" value={derived.rangeOpen.length}
                    sub={`${100 - derived.rangeRes}% of total`}
                    href={su(subdomain, `type:ticket status:open status:pending created>${zdAfter(derived.wSince)} created<${derived.wEnd} ${ZD_EXCL}`)} />
                  <StatCard icon="✅" label="Solved / Closed" value={derived.rangeClosed.length}
                    sub={`${derived.rangeRes}% resolution`}
                    href={su(subdomain, `type:ticket status:solved status:closed created>${zdAfter(derived.wSince)} created<${derived.wEnd} ${ZD_EXCL}`)} />
                  <StatCard icon="📈" label="Resolution Rate" value={`${derived.rangeRes}%`} accent
                    sub={`${derived.rangeClosed.length} of ${derived.rangeReal.length} resolved`}
                    href={su(subdomain, `type:ticket status:solved created>${zdAfter(derived.wSince)} created<${derived.wEnd} ${ZD_EXCL}`)} />
                  <StatCard icon="📋" label="Unsolved in Group" value={derived.unsolvedCount}
                    sub="Full queue · Failed Ops excluded"
                    href={fu(subdomain, FILTERS["All Open"])} />
                  <StatCard icon="🔥" label="High Priority" value={derived.chRanged["High Priority"]?.tickets?.length ?? 0}
                    sub="View filter"
                    href={fu(subdomain, FILTERS["High Priority"])} />
                </div>
                <p className="text-xs text-gray-400 mt-2">
                  Failed Operations view ({derived.foCount} tickets) excluded from every metric.{" "}
                  <a href={`https://${subdomain}.zendesk.com/agent/filters/${FILTERS["Failed Operations"]}`}
                     target="_blank" rel="noreferrer" style={{ color: "var(--brand)" }}>
                    View bucket ↗
                  </a>
                </p>

                {/* Ticket expanders */}
                <TicketExpanders
                  rangeReal={derived.rangeReal}
                  rangeOpen={derived.rangeOpen}
                  rangeClosed={derived.rangeClosed}
                  sub={subdomain}
                />

                <Divider />

                {/* ── WEEKLY METRICS ── */}
                <SectionHeader icon="📊" title="Weekly Metrics" sub={`Wk ${startWk} – Wk ${endWk}`} />
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <div>
                    <p className="font-semibold text-sm mb-3">Customer Raised Tickets</p>
                    <ChannelTable rows={[
                      { label: "AI Bot",               ch: derived.chRanged["AI Bot"],             href: fu(subdomain, FILTERS["AI Bot"]),             excl: false },
                      { label: "Messaging / Live Chat", ch: derived.chRanged["Messaging/Live Chat"], href: fu(subdomain, FILTERS["Messaging/Live Chat"]), excl: false },
                      { label: "Architect — Customer",  ch: derived.archRanged["customer"],          href: fu(subdomain, FILTERS["Architect Requests"]),  excl: false },
                    ]} />
                  </div>
                  <div>
                    <p className="font-semibold text-sm mb-3">Architect Breakdown</p>
                    <ChannelTable rows={[
                      { label: "Customer tickets",        ch: derived.archRanged["customer"],           href: su(subdomain, `type:ticket created>${zdAfter(derived.wSince)} created<${derived.wEnd} group:architect ${ZD_EXCL}`), excl: false },
                      { label: "Internal — on behalf of", ch: derived.archRanged["internal"],           href: su(subdomain, `type:ticket created>${zdAfter(derived.wSince)} created<${derived.wEnd} group:architect ${ZD_EXCL}`), excl: false },
                      { label: "Failure notifications",   ch: derived.archRanged["failure_notification"], href: su(subdomain, `type:ticket created>${zdAfter(derived.wSince)} created<${derived.wEnd} requester:architect@klarity.ai ${ZD_EXCL}`), excl: false },
                    ]} showTotal />
                  </div>
                </div>

                <Divider />

                {/* ── CATEGORY PERFORMANCE ── */}
                <SectionHeader icon="🎯" title="Support Performance by Category" sub="Last 4 complete weeks" />
                <p className="text-xs text-gray-400 -mt-2 mb-4">
                  Fixed window: last 4 complete Mon–Sun weeks from {s4} — independent of the week selector.
                </p>
                {derived.catPerf.length > 0 ? (
                  <CategoryPerfTable catPerf={derived.catPerf} sub={subdomain} s4={s4} />
                ) : (
                  <p className="text-gray-400 text-sm">No categorized tickets found in the last 4 weeks.</p>
                )}

                <Divider />

                {/* ── TREND CHART ── */}
                <SectionHeader icon="📅" title="Week by Week Trend" sub={`Wk ${startWk} – Wk ${endWk} · ${curYear}`} />
                <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
                  <div className="lg:col-span-3 chart-wrap">
                    <ResponsiveContainer width="100%" height={280}>
                      <BarChart data={derived.trendData} margin={{ top: 16, right: 16, bottom: 16, left: 0 }}>
                        <CartesianGrid vertical={false} stroke="#f0ede9" />
                        <XAxis dataKey="name" tick={{ fill: "#999", fontSize: 11 }} axisLine={false} tickLine={false} />
                        <YAxis tick={{ fill: "#999", fontSize: 11 }} axisLine={false} tickLine={false} />
                        <Tooltip content={<CustomTooltip />} />
                        <Bar dataKey="tickets" fill="#E8612C" radius={[6, 6, 0, 0]} maxBarSize={40} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                  <div className="lg:col-span-2">
                    <p className="font-semibold text-sm mb-3">Top Issues — last 4 weeks</p>
                    <TopIssuesTable weeks={derived.top4Weeks} sub={subdomain} wSince={derived.wSince} wEnd={derived.wEnd} />
                  </div>
                </div>

                <Divider />

                {/* ── RESOLUTION TIME ── */}
                <SectionHeader icon="⏱️" title="Resolution Time by Category" sub="Median · Average · P90 (hours)" />
                {derived.resData.length > 0 ? (
                  <div className="chart-wrap">
                    <ResponsiveContainer width="100%" height={320}>
                      <BarChart data={derived.resData} margin={{ top: 16, right: 24, bottom: 80, left: 0 }}>
                        <CartesianGrid vertical={false} stroke="#f0ede9" />
                        <XAxis dataKey="name" tick={{ fill: "#999", fontSize: 11 }} angle={-30} textAnchor="end" interval={0} axisLine={false} tickLine={false} />
                        <YAxis tick={{ fill: "#999", fontSize: 11 }} axisLine={false} tickLine={false} />
                        <Tooltip content={<CustomTooltip />} />
                        <Legend wrapperStyle={{ fontSize: 12, color: "#888", paddingTop: 8 }} />
                        <Bar dataKey="Median"  fill="#E8612C" radius={[4, 4, 0, 0]} maxBarSize={22} />
                        <Bar dataKey="Average" fill="#f4a261" radius={[4, 4, 0, 0]} maxBarSize={22} />
                        <Bar dataKey="P90"     fill="#fde8d8" radius={[4, 4, 0, 0]} maxBarSize={22} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                ) : (
                  <p className="text-gray-400 text-sm">No closed tickets yet — resolution times will appear once tickets are solved.</p>
                )}

                <Divider />

                {/* ── BREAKDOWN ── */}
                <SectionHeader
                  icon="🔍"
                  title="Ticket Breakdown"
                  sub={`Wk ${startWk}–${endWk} · ${derived.rangeReal.length} received · ${derived.rangeOpen.length} open · ${derived.rangeClosed.length} solved`}
                />

                {/* Mini stats row */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
                  <MiniStat value={derived.rangeReal.length}   label="Total Received" />
                  <MiniStat value={derived.rangeOpen.length}   label="Still Open" />
                  <MiniStat value={derived.rangeClosed.length} label="Resolved" />
                  <MiniStat value={`${derived.rangeRes}%`}     label="Resolution Rate" />
                </div>

                {/* Row 1: Donut + Top customers */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
                  {/* Status donut */}
                  <div>
                    <p className="font-semibold text-sm mb-3">Status Distribution</p>
                    <div className="chart-wrap flex items-center justify-center" style={{ minHeight: 280 }}>
                      <ResponsiveContainer width="100%" height={260}>
                        <PieChart>
                          <Pie
                            data={derived.statusData}
                            cx="50%"
                            cy="50%"
                            innerRadius={70}
                            outerRadius={100}
                            paddingAngle={3}
                            dataKey="value"
                            label={({ name, value }) => `${name}: ${value}`}
                            labelLine={false}
                          >
                            {derived.statusData.map((entry) => (
                              <Cell key={entry.name} fill={STATUS_COLORS[entry.name.toLowerCase()] || "#ccc"} stroke="white" strokeWidth={2} />
                            ))}
                          </Pie>
                          <Tooltip content={<CustomTooltip />} />
                          <Legend wrapperStyle={{ fontSize: 12, color: "#888" }} />
                        </PieChart>
                      </ResponsiveContainer>
                    </div>
                  </div>

                  {/* Top customers */}
                  <div>
                    <p className="font-semibold text-sm mb-3">Top Customers by Volume</p>
                    <table className="klarity-table">
                      <thead>
                        <tr>
                          <th>Customer</th>
                          <th className="text-center">Open</th>
                          <th className="text-center">Solved</th>
                          <th className="text-center">Total</th>
                        </tr>
                      </thead>
                      <tbody>
                        {derived.topCustomers.map(([cust, cnts]) => {
                          const tot = cnts.open + cnts.solved;
                          const href = su(subdomain, `type:ticket created>${zdAfter(derived.wSince)} created<${derived.wEnd} "${cust}" ${ZD_EXCL}`);
                          return (
                            <tr key={cust}>
                              <td>{cust}</td>
                              <td className="text-center">
                                {cnts.open > 0 ? <a href={href} target="_blank" rel="noreferrer">{cnts.open}</a> : <span className="text-gray-200">—</span>}
                              </td>
                              <td className="text-center">
                                {cnts.solved > 0 ? <a href={href} target="_blank" rel="noreferrer">{cnts.solved}</a> : <span className="text-gray-200">—</span>}
                              </td>
                              <td className="text-center">
                                <a href={href} target="_blank" rel="noreferrer" className="font-extrabold">{tot}</a>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Row 2: Daily + Category */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <div>
                    <p className="font-semibold text-sm mb-3">Daily Ticket Volume</p>
                    <div className="chart-wrap">
                      <ResponsiveContainer width="100%" height={240}>
                        <BarChart data={derived.dailyData} margin={{ top: 10, right: 10, bottom: 50, left: 0 }}>
                          <CartesianGrid vertical={false} stroke="#f0ede9" />
                          <XAxis dataKey="short" tick={{ fill: "#999", fontSize: 10 }} angle={-45} textAnchor="end" axisLine={false} tickLine={false} />
                          <YAxis tick={{ fill: "#999", fontSize: 10 }} axisLine={false} tickLine={false} />
                          <Tooltip content={<CustomTooltip />} />
                          <Bar dataKey="count" radius={[4, 4, 0, 0]} maxBarSize={22}>
                            {derived.dailyData.map((entry, i) => (
                              <Cell key={i} fill={entry.weekend ? "#fde8d8" : "#E8612C"} />
                            ))}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                      <p className="text-xs text-gray-400 mt-1 text-center">Orange = weekday · Pale = weekend</p>
                    </div>
                  </div>
                  <div>
                    <p className="font-semibold text-sm mb-3">Volume by Category</p>
                    <div className="chart-wrap">
                      <ResponsiveContainer width="100%" height={270}>
                        <BarChart data={derived.catVolData} layout="vertical" margin={{ top: 10, right: 40, bottom: 10, left: 4 }}>
                          <CartesianGrid horizontal={false} stroke="#f0ede9" />
                          <XAxis type="number" tick={{ fill: "#999", fontSize: 10 }} axisLine={false} tickLine={false} />
                          <YAxis type="category" dataKey="label" tick={{ fill: "#555", fontSize: 11 }} width={140} axisLine={false} tickLine={false} />
                          <Tooltip content={<CustomTooltip />} />
                          <Bar dataKey="count" fill="#E8612C" radius={[0, 4, 4, 0]} maxBarSize={18} />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                </div>

              </div>
            )}

            {/* ── FOOTER ── */}
            <div className="mt-16 pt-5 border-t border-black/[0.07] text-center text-xs text-gray-300">
              <span className="font-semibold text-gray-400">Klarity Support Report</span>
              {" "}·{" "}Week {startWk} – Week {endWk} ({curYear})
              {" "}·{" "}
              <a href={`https://${subdomain}.zendesk.com/agent`} target="_blank" rel="noreferrer"
                 style={{ color: "var(--brand)", fontWeight: 600, textDecoration: "none" }}>
                Open Zendesk ↗
              </a>
            </div>
          </div>
        </main>
      </div>
    </>
  );
}

// ── SUB-COMPONENTS ─────────────────────────────────────────────────────────
function TicketExpanders({ rangeReal, rangeOpen, rangeClosed, sub }) {
  const [openExpander, setOpenExpander] = useState(null);
  function toggle(key) { setOpenExpander(prev => prev === key ? null : key); }
  const sets = [
    { key: "all",    label: `📄 ${rangeReal.length} Tickets Received`,     tickets: rangeReal },
    { key: "open",   label: `🔓 ${rangeOpen.length} Open`,                 tickets: rangeOpen },
    { key: "closed", label: `✅ ${rangeClosed.length} Solved / Closed`,    tickets: rangeClosed },
  ];
  return (
    <div className="mt-4 space-y-2">
      {sets.map(({ key, label, tickets }) => (
        <div key={key} className="rounded-xl overflow-hidden border border-black/[0.07] bg-white shadow-sm">
          <button
            onClick={() => toggle(key)}
            className="w-full text-left px-5 py-3 text-sm font-semibold flex items-center justify-between hover:bg-gray-50 transition-colors"
            style={{ color: "var(--ink)" }}
          >
            <span>{label}</span>
            <span className="text-gray-300">{openExpander === key ? "▲" : "▼"}</span>
          </button>
          {openExpander === key && (
            <div className="overflow-x-auto border-t border-gray-100">
              <table className="klarity-table rounded-none">
                <thead>
                  <tr>
                    <th className="rounded-none">ID</th>
                    <th className="text-left rounded-none">Subject</th>
                    <th className="rounded-none">Status</th>
                    <th className="text-left rounded-none">Requester</th>
                    <th className="rounded-none">Created</th>
                  </tr>
                </thead>
                <tbody>
                  {[...tickets]
                    .sort((a, b) => (b.created_at || "") > (a.created_at || "") ? 1 : -1)
                    .map(t => (
                      <tr key={t.id}>
                        <td><a href={`https://${sub}.zendesk.com/agent/tickets/${t.id}`} target="_blank" rel="noreferrer">#{t.id}</a></td>
                        <td className="text-left text-xs max-w-xs truncate">{(t.subject || "").replace(/\[BACKEND ALERT\]\s*/i, "").slice(0, 80)}</td>
                        <td><StatusPill status={t.status} /></td>
                        <td className="text-left text-xs text-gray-400">{t._requester_email || "—"}</td>
                        <td>{(t.created_at || "").slice(0, 10)}</td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function CategoryPerfTable({ catPerf, sub, s4 }) {
  const maxCount = catPerf[0]?.count || 1;
  return (
    <table className="klarity-table">
      <thead>
        <tr>
          <th>Issue Type</th>
          <th>Tickets</th>
          <th className="text-center">Median</th>
          <th className="text-center">Average</th>
          <th className="text-center">P90</th>
        </tr>
      </thead>
      <tbody>
        {catPerf.map(cat => {
          const catQ  = CAT_SEARCH_QUERY[cat.label] || "";
          const excl  = `-status:new -tags:internal_teams -tags:automated_architect -subject:"BACKEND ALERT"`;
          const href  = `https://${sub}.zendesk.com/agent/search?q=${encodeURIComponent(`type:ticket created>${zdAfter(s4)} ${catQ} ${excl}`.trim())}`;
          const barPct = Math.round((cat.count / maxCount) * 100);
          return (
            <tr key={cat.label}>
              <td><a href={href} target="_blank" rel="noreferrer">{cat.label}</a></td>
              <td>
                <div className="flex items-center gap-2">
                  <a href={href} target="_blank" rel="noreferrer" className="font-bold">{cat.count}</a>
                  <div className="cat-bar-bg">
                    <div className="cat-bar-fill" style={{ width: `${barPct}%` }} />
                  </div>
                </div>
              </td>
              <td className="text-center">{fh(cat.median)}</td>
              <td className="text-center">{fh(cat.average)}</td>
              <td className="text-center">{fh(cat.p90)}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

function TopIssuesTable({ weeks, sub, wSince, wEnd }) {
  return (
    <table className="klarity-table">
      <thead>
        <tr>
          <th>Issue</th>
          {weeks.map(w => <th key={w.weekNum} className="text-center">{w.label}</th>)}
        </tr>
      </thead>
      <tbody>
        {TOP_ISSUES.map(({ label, rx }) => (
          <tr key={label}>
            <td className="text-xs">{label}</td>
            {weeks.map(w => {
              const wTickets = (w.tickets || []);
              const count = wTickets.filter(t => rx.test(t.subject || "")).length;
              const href  = `https://${sub}.zendesk.com/agent/search?q=${encodeURIComponent(`type:ticket created>${zdAfter(w.start)} created<${w.end} -status:new -tags:internal_teams`)}`;
              return (
                <td key={w.weekNum} className="text-center">
                  {count > 0
                    ? <a href={href} target="_blank" rel="noreferrer" className="font-bold">{count}</a>
                    : <span className="text-gray-200">—</span>}
                </td>
              );
            })}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
