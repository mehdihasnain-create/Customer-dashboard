export default function SectionHeader({ icon, title, sub }) {
  return (
    <div className="flex items-center gap-3 mt-10 mb-5">
      <div
        className="w-7 h-7 rounded-lg flex items-center justify-center text-xs flex-shrink-0"
        style={{
          background: "rgba(232,97,44,0.12)",
          border: "1px solid rgba(232,97,44,0.22)",
          color: "#f4a261",
        }}
      >
        {icon}
      </div>
      <div className="flex items-baseline gap-2.5 min-w-0">
        <h2 className="text-sm font-bold tracking-tight leading-none whitespace-nowrap" style={{ color: "var(--text-primary)" }}>
          {title}
        </h2>
        {sub && (
          <span className="text-xs font-medium tracking-normal" style={{ color: "var(--text-muted)" }}>/ {sub}</span>
        )}
      </div>
      <div
        className="flex-1 h-px ml-1"
        style={{ background: "linear-gradient(90deg, rgba(232,97,44,0.18), transparent)" }}
      />
    </div>
  );
}
