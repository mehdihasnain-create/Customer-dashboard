/**
 * POST /api/report
 * Body: { subdomain, email, token, since }
 * Returns the full processed dashboard data object.
 */

import { loadData } from "../../lib/zendesk";

export default async function handler(req, res) {
  if (req.method !== "POST") {
    return res.status(405).json({ error: "Method not allowed" });
  }

  const { subdomain, email, token, since } = req.body || {};

  if (!subdomain || !email || !token || !since) {
    return res.status(400).json({ error: "Missing required fields: subdomain, email, token, since" });
  }

  try {
    const data = await loadData(subdomain, email, token, since);
    // Strip raw ticket arrays from week objects to reduce payload size
    // (they're only used server-side for counting)
    const lightWeeks = data.allWeeks.map(w => ({
      label:   w.label,
      weekNum: w.weekNum,
      start:   w.start,
      end:     w.end,
      display: w.display,
      count:   w.count,
    }));

    return res.status(200).json({
      ...data,
      allWeeks: lightWeeks,
      // Keep tickets but only the fields the UI needs to minimise payload
      real:    data.real.map(slim),
      openT:   data.openT.map(slim),
      closedT: data.closedT.map(slim),
      channels: Object.fromEntries(
        Object.entries(data.channels).map(([k, v]) => [k, slimCh(v)])
      ),
      archBuckets: Object.fromEntries(
        Object.entries(data.archBuckets).map(([k, v]) => [k, slimCh(v)])
      ),
    });
  } catch (err) {
    const status = err.status || 500;
    return res.status(status).json({ error: err.message });
  }
}

function slim(t) {
  return {
    id:               t.id,
    subject:          t.subject,
    status:           t.status,
    created_at:       t.created_at,
    solved_at:        t.solved_at,
    tags:             t.tags,
    _requester_email: t._requester_email,
    _org_name:        t._org_name,
  };
}

function slimCh(ch) {
  return {
    tickets: ch.tickets.map(slim),
    open:    ch.open.map(slim),
    closed:  ch.closed.map(slim),
  };
}
