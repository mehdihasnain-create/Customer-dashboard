const PALETTE = {
  orange: { grad: "linear-gradient(135deg,#E8612C,#f4a261)", text: "#E8612C", glow: "rgba(232,97,44,0.22)" },
  green:  { grad: "linear-gradient(135deg,#10B981,#34D399)",  text: "#10B981", glow: "rgba(16,185,129,0.20)" },
  red:    { grad: "linear-gradient(135deg,#EF4444,#F87171)",  text: "#DC2626", glow: "rgba(239,68,68,0.20)" },
  blue:   { grad: "linear-gradient(135deg,#3B82F6,#60A5FA)",  text: "#2563EB", glow: "rgba(59,130,246,0.20)" },
  amber:  { grad: "linear-gradient(135deg,#F59E0B,#FBBF24)",  text: "#D97706", glow: "rgba(245,158,11,0.20)" },
  purple: { grad: "linear-gradient(135deg,#8B5CF6,#A78BFA)",  text: "#7C3AED", glow: "rgba(139,92,246,0.20)" },
};

export default function StatCard({ icon, label, value, sub, href, accent, color = "orange" }) {
  const c = PALETTE[color] || PALETTE.orange;

  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className="stat-card block bg-white rounded-2xl p-5 border border-black/[0.06] no-underline"
    >
      {/* Colored icon pill */}
      <div
        className="w-10 h-10 rounded-xl flex items-center justify-center text-lg mb-4 flex-shrink-0"
        style={{ background: c.grad, boxShadow: `0 4px 14px ${c.glow}` }}
      >
        {icon}
      </div>

      {/* Label */}
      <div className="text-[10.5px] font-bold tracking-widest uppercase text-gray-400 mb-1.5">
        {label}
      </div>

      {/* Value */}
      <div
        className="text-[2.4rem] font-black leading-none tracking-tight mb-2.5"
        style={{ color: accent ? c.text : "#111827" }}
      >
        {value}
      </div>

      {/* Sub */}
      <div className="flex items-center gap-1 text-[11px] font-medium text-gray-400">
        <span style={{ color: c.text }} className="text-xs font-black">↗</span>
        {sub}
      </div>
    </a>
  );
}
