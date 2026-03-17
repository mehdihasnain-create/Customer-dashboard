import {
  BarChart, Bar, Cell, XAxis, YAxis, CartesianGrid,
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

export default function DailyVolumeChart({ data }) {
  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data} margin={{ top: 10, right: 10, bottom: 50, left: 0 }}>
        <CartesianGrid vertical={false} stroke="rgba(255,255,255,0.05)" />
        <XAxis
          dataKey="short"
          tick={{ fill: "#6b7280", fontSize: 10 }}
          angle={-45} textAnchor="end"
          axisLine={false} tickLine={false}
        />
        <YAxis tick={{ fill: "#6b7280", fontSize: 10 }} axisLine={false} tickLine={false} allowDecimals={false} />
        <Tooltip content={<ChartTooltip />} cursor={{ fill: "rgba(232,97,44,0.06)" }} />
        <Bar dataKey="count" radius={[4, 4, 0, 0]} maxBarSize={22}>
          {data.map((entry, i) => (
            <Cell key={i} fill={entry.weekend ? "rgba(232,97,44,0.25)" : "#E8612C"} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
