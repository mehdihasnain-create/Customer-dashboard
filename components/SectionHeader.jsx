export default function SectionHeader({ icon, title, sub }) {
  return (
    <div className="flex items-center gap-3 mt-10 mb-5">
      <div
        className="w-8 h-8 rounded-lg flex items-center justify-center text-sm flex-shrink-0"
        style={{
          background: "linear-gradient(135deg, #E8612C, #f4a261)",
          boxShadow: "0 3px 10px rgba(232,97,44,0.28)",
        }}
      >
        {icon}
      </div>
      <div className="flex items-baseline gap-2 min-w-0">
        <h2 className="text-[15px] font-extrabold tracking-tight text-gray-900 leading-none whitespace-nowrap">
          {title}
        </h2>
        {sub && (
          <span className="text-xs font-medium text-gray-400 tracking-normal">— {sub}</span>
        )}
      </div>
      <div
        className="flex-1 h-px ml-1"
        style={{ background: "linear-gradient(90deg, rgba(232,97,44,0.25), transparent)" }}
      />
    </div>
  );
}
