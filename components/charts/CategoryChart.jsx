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

export default function CategoryChart({ data }) {
  return (
    <ResponsiveContainer width="100%" height={270}>
      <BarChart
        data={data}
        layout="vertical"
        margin={{ top: 10, right: 40, bottom: 10, left: 4 }}
      >
        <CartesianGrid horizontal={false} stroke="rgba(255,255,255,0.05)" />
        <XAxis type="number" tick={{ fill: "#6b7280", fontSize: 10 }} axisLine={false} tickLine={false} allowDecimals={false} />
        <YAxis
          type="category" dataKey="label"
          tick={{ fill: "#8b96aa", fontSize: 11 }} width={145}
          axisLine={false} tickLine={false}
        />
        <Tooltip content={<ChartTooltip />} cursor={{ fill: "rgba(232,97,44,0.06)" }} />
        <Bar dataKey="count" fill="#E8612C" radius={[0, 4, 4, 0]} maxBarSize={20} />
      </BarChart>
    </ResponsiveContainer>
  );
}
