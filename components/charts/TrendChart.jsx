import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer,
} from "recharts";

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: "#0d1120", borderRadius: 10, padding: "10px 14px",
      boxShadow: "0 4px 24px rgba(0,0,0,0.6)", border: "1px solid rgba(255,255,255,0.08)",
      fontSize: 13,
    }}>
      <p style={{ fontWeight: 700, marginBottom: 4, color: "#f0f4ff" }}>{label}</p>
      {payload.map(p => (
        <p key={p.name} style={{ color: "#f4a261", margin: 0 }}>
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
        <CartesianGrid vertical={false} stroke="rgba(255,255,255,0.05)" />
        <XAxis dataKey="name" tick={{ fill: "#6b7280", fontSize: 11 }} axisLine={false} tickLine={false} />
        <YAxis tick={{ fill: "#6b7280", fontSize: 11 }} axisLine={false} tickLine={false} allowDecimals={false} />
        <Tooltip content={<ChartTooltip />} cursor={{ fill: "rgba(232,97,44,0.06)" }} />
        <Bar dataKey="tickets" fill="#E8612C" radius={[6, 6, 0, 0]} maxBarSize={48} />
      </BarChart>
    </ResponsiveContainer>
  );
}
