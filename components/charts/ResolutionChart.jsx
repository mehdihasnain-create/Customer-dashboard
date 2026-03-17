import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from "recharts";

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: "#fff", borderRadius: 10, padding: "10px 14px",
      boxShadow: "0 4px 20px rgba(0,0,0,0.12)", border: "1px solid rgba(0,0,0,0.07)",
      fontSize: 13,
    }}>
      <p style={{ fontWeight: 700, marginBottom: 4, color: "#111827" }}>{label}</p>
      {payload.map(p => (
        <p key={p.name} style={{ color: p.fill || "#E8612C", margin: "2px 0" }}>
          {p.name}: <strong>{p.value}h</strong>
        </p>
      ))}
    </div>
  );
}

export default function ResolutionChart({ data }) {
  return (
    <ResponsiveContainer width="100%" height={320}>
      <BarChart data={data} margin={{ top: 16, right: 24, bottom: 80, left: 0 }}>
        <CartesianGrid vertical={false} stroke="#f0ede9" />
        <XAxis
          dataKey="name"
          tick={{ fill: "#999", fontSize: 11 }}
          angle={-30} textAnchor="end" interval={0}
          axisLine={false} tickLine={false}
        />
        <YAxis tick={{ fill: "#999", fontSize: 11 }} axisLine={false} tickLine={false} />
        <Tooltip content={<ChartTooltip />} />
        <Legend wrapperStyle={{ fontSize: 12, color: "#888", paddingTop: 8 }} />
        <Bar dataKey="Median"  fill="#E8612C" radius={[4, 4, 0, 0]} maxBarSize={22} />
        <Bar dataKey="Average" fill="#f4a261" radius={[4, 4, 0, 0]} maxBarSize={22} />
        <Bar dataKey="P90"     fill="#fbbf24" radius={[4, 4, 0, 0]} maxBarSize={22} />
      </BarChart>
    </ResponsiveContainer>
  );
}
