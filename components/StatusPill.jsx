const PILL_MAP = {
  open:    "pill pill-open",
  pending: "pill pill-pending",
  solved:  "pill pill-solved",
  closed:  "pill pill-closed",
};

export default function StatusPill({ status }) {
  const cls = PILL_MAP[(status || "").toLowerCase()] || "pill pill-open";
  return <span className={cls}>{status}</span>;
}
