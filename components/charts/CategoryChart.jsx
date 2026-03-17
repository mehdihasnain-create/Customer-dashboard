import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer,
} from "recharts";

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: "#fff", borderRadius: 10, padding: "10px 14px",
      boxShadow: "0 4px 20px rgba(0,0,0,0.1)", border: "1px solid rgba(0,0,0,0.08)",
      fontSize: 13,
    }}>
      <p style={{ fontWeight: 700, marginBottom: 4, color: "#111827" }}>{label}</p>
      {payload.map(p => (
        <p key={p.name} style={{ color: "#E8612C", margin: 0 }}>
          Tickets: <strong>{p.value}</strong>
        </p>
      ))}
    </div>
  );
}

export default function CategoryChart({ data }) {
  return (
    <ResponsiveContainer width="100%" height={270}>
      <BarChart
        data={data}
        layout="vertical"
        margin={{ top: 10, right: 40, bottom: 10, left: 4 }}
      >
        <CartesianGrid horizontal={false} stroke="#f0f2f6" />
        <XAxis type="number" tick={{ fill: "#9ca3af", fontSize: 10 }} axisLine={false} tickLine={false} allowDecimals={false} />
        <YAxis
          type="category" dataKey="label"
          tick={{ fill: "#6b7280", fontSize: 11 }} width={145}
          axisLine={false} tickLine={false}
        />
        <Tooltip content={<ChartTooltip />} cursor={{ fill: "rgba(232,97,44,0.05)" }} />
        <Bar dataKey="count" fill="#E8612C" radius={[0, 4, 4, 0]} maxBarSize={20} />
      </BarChart>
    </ResponsiveContainer>
  );
}
