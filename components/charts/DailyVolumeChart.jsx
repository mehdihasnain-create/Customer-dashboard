import {
  BarChart, Bar, Cell, XAxis, YAxis, CartesianGrid,
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

export default function DailyVolumeChart({ data }) {
  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data} margin={{ top: 10, right: 10, bottom: 50, left: 0 }}>
        <CartesianGrid vertical={false} stroke="#f0f2f6" />
        <XAxis
          dataKey="short"
          tick={{ fill: "#9ca3af", fontSize: 10 }}
          angle={-45} textAnchor="end"
          axisLine={false} tickLine={false}
        />
        <YAxis tick={{ fill: "#9ca3af", fontSize: 10 }} axisLine={false} tickLine={false} allowDecimals={false} />
        <Tooltip content={<ChartTooltip />} cursor={{ fill: "rgba(232,97,44,0.05)" }} />
        <Bar dataKey="count" radius={[4, 4, 0, 0]} maxBarSize={22}>
          {data.map((entry, i) => (
            <Cell key={i} fill={entry.weekend ? "#fde8d8" : "#E8612C"} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
