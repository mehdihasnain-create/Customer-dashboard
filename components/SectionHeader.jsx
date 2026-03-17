export default function SectionHeader({ icon, title, sub }) {
  return (
    <div className="flex items-center gap-3 mt-10 mb-4">
      <div
        className="w-9 h-9 rounded-xl flex items-center justify-center text-base flex-shrink-0 shadow-md"
        style={{ background: "linear-gradient(135deg, #E8612C, #f4a261)" }}
      >
        {icon}
      </div>
      <span className="text-[17px] font-extrabold tracking-tight" style={{ color: "var(--ink)" }}>
        {title}
        {sub && (
          <span className="text-sm font-normal text-gray-400 ml-2">— {sub}</span>
        )}
      </span>
    </div>
  );
}
