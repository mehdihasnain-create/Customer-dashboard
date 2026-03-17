const PALETTE = {
  orange: { grad: "linear-gradient(135deg,#E8612C,#f4a261)", accent: "#E8612C",  glow: "rgba(232,97,44,0.20)",   border: "rgba(232,97,44,0.25)" },
  green:  { grad: "linear-gradient(135deg,#059669,#34D399)",  accent: "#10B981",  glow: "rgba(16,185,129,0.18)",  border: "rgba(16,185,129,0.22)" },
  red:    { grad: "linear-gradient(135deg,#DC2626,#F87171)",  accent: "#EF4444",  glow: "rgba(239,68,68,0.18)",   border: "rgba(239,68,68,0.22)" },
  blue:   { grad: "linear-gradient(135deg,#2563EB,#60A5FA)",  accent: "#3B82F6",  glow: "rgba(59,130,246,0.18)",  border: "rgba(59,130,246,0.22)" },
  amber:  { grad: "linear-gradient(135deg,#D97706,#FBBF24)",  accent: "#F59E0B",  glow: "rgba(245,158,11,0.18)",  border: "rgba(245,158,11,0.22)" },
  purple: { grad: "linear-gradient(135deg,#7C3AED,#A78BFA)",  accent: "#8B5CF6",  glow: "rgba(139,92,246,0.18)",  border: "rgba(139,92,246,0.22)" },
};

export default function StatCard({ icon, label, value, sub, href, accent, color = "orange" }) {
  const c = PALETTE[color] || PALETTE.orange;
  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className="stat-card block rounded-2xl p-5 no-underline"
      style={{
        background: "var(--bg-card)",
        border: `1px solid ${c.border}`,
        borderTop: `2px solid ${c.accent}`,
      }}
    >
      {/* Corner glow */}
      <div
        className="absolute top-0 right-0 w-28 h-28 pointer-events-none"
        style={{ background: `radial-gradient(circle at top right, ${c.glow}, transparent 65%)` }}
      />
      {/* Icon */}
      <div
        className="w-9 h-9 rounded-xl flex items-center justify-center text-base mb-4 flex-shrink-0 relative z-10"
        style={{ background: c.grad, boxShadow: `0 4px 16px ${c.glow}` }}
      >
        {icon}
      </div>
      {/* Label */}
      <div className="text-[10px] font-bold tracking-[0.1em] uppercase mb-2 relative z-10" style={{ color: "var(--text-secondary)" }}>
        {label}
      </div>
      {/* Value */}
      <div
        className="text-[2.2rem] font-black leading-none tracking-tight mb-3 relative z-10"
        style={{ color: accent ? c.accent : "var(--text-primary)" }}
      >
        {value}
      </div>
      {/* Sub */}
      <div className="flex items-center gap-1.5 text-[11px] font-medium relative z-10" style={{ color: "var(--text-muted)" }}>
        <span style={{ color: c.accent }} className="text-[10px] font-black">↗</span>
        {sub}
      </div>
    </a>
  );
}
