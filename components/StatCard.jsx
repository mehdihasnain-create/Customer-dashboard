const PALETTE = {
  orange: { grad: "linear-gradient(135deg,#E8612C,#f4a261)", accent: "#E8612C",  glow: "rgba(232,97,44,0.18)",   border: "rgba(232,97,44,0.18)" },
  green:  { grad: "linear-gradient(135deg,#059669,#34D399)",  accent: "#059669",  glow: "rgba(5,150,105,0.15)",   border: "rgba(5,150,105,0.15)" },
  red:    { grad: "linear-gradient(135deg,#DC2626,#F87171)",  accent: "#DC2626",  glow: "rgba(220,38,38,0.15)",   border: "rgba(220,38,38,0.15)" },
  blue:   { grad: "linear-gradient(135deg,#2563EB,#60A5FA)",  accent: "#2563EB",  glow: "rgba(37,99,235,0.15)",   border: "rgba(37,99,235,0.15)" },
  amber:  { grad: "linear-gradient(135deg,#D97706,#FBBF24)",  accent: "#D97706",  glow: "rgba(217,119,6,0.15)",   border: "rgba(217,119,6,0.15)" },
  purple: { grad: "linear-gradient(135deg,#7C3AED,#A78BFA)",  accent: "#7C3AED",  glow: "rgba(124,58,237,0.15)",  border: "rgba(124,58,237,0.15)" },
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
        border: `1px solid var(--border)`,
        borderTop: `3px solid ${c.accent}`,
      }}
    >
      {/* Icon */}
      <div
        className="w-10 h-10 rounded-xl flex items-center justify-center text-lg mb-4"
        style={{ background: c.grad, boxShadow: `0 4px 14px ${c.glow}` }}
      >
        {icon}
      </div>
      {/* Label */}
      <div className="text-[10px] font-bold tracking-[0.09em] uppercase mb-1.5" style={{ color: "var(--text-secondary)" }}>
        {label}
      </div>
      {/* Value */}
      <div
        className="text-[2.15rem] font-black leading-none tracking-tight mb-3"
        style={{ color: accent ? c.accent : "var(--text-primary)" }}
      >
        {value}
      </div>
      {/* Sub */}
      <div className="flex items-center gap-1.5 text-[11px] font-medium" style={{ color: "var(--text-muted)" }}>
        <span style={{ color: c.accent }} className="text-[10px] font-black">↗</span>
        {sub}
      </div>
    </a>
  );
}
