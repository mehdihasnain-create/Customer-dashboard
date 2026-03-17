export default function StatCard({ icon, label, value, sub, href, accent }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className="stat-card block bg-white rounded-2xl p-5 border border-black/[0.07] shadow-sm no-underline"
    >
      <span className="text-2xl mb-3 block">{icon}</span>
      <span className="block text-[11px] font-semibold tracking-wide uppercase text-gray-400 mb-1.5">
        {label}
      </span>
      <span
        className="block text-4xl font-black leading-none tracking-tight mb-2"
        style={{ color: accent ? "var(--brand)" : "var(--ink)" }}
      >
        {value}
      </span>
      <span className="flex items-center gap-1 text-[11px] text-gray-400">
        <span style={{ color: "var(--brand)" }} className="text-sm">↗</span>
        {sub}
      </span>
    </a>
  );
}
