import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer,
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
        <p key={p.name} style={{ color: p.fill || "#E8612C", margin: 0 }}>
          Tickets: <strong>{p.value}</strong>
        </p>
      ))}
    </div>
  );
}

export default function TrendChart({ data }) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={data} margin={{ top: 16, right: 16, bottom: 16, left: 0 }}>
        <CartesianGrid vertical={false} stroke="#f0ede9" />
        <XAxis dataKey="name" tick={{ fill: "#999", fontSize: 11 }} axisLine={false} tickLine={false} />
        <YAxis tick={{ fill: "#999", fontSize: 11 }} axisLine={false} tickLine={false} allowDecimals={false} />
        <Tooltip content={<ChartTooltip />} />
        <Bar dataKey="tickets" fill="#E8612C" radius={[6, 6, 0, 0]} maxBarSize={48} />
      </BarChart>
    </ResponsiveContainer>
  );
}
