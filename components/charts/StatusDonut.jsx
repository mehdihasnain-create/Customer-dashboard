import {
  PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer,
} from "recharts";

const STATUS_COLORS = {
  open:    "#E8612C",
  pending: "#f4a261",
  solved:  "#2a9d8f",
  closed:  "#818cf8",
};

function ChartTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const d = payload[0];
  return (
    <div style={{
      background: "#0d1120", borderRadius: 10, padding: "10px 14px",
      boxShadow: "0 4px 24px rgba(0,0,0,0.6)", border: "1px solid rgba(255,255,255,0.08)",
      fontSize: 13,
    }}>
      <p style={{ fontWeight: 700, color: d.payload.fill, margin: 0 }}>
        {d.name}: <strong>{d.value}</strong>
      </p>
    </div>
  );
}

export default function StatusDonut({ data }) {
  return (
    <ResponsiveContainer width="100%" height={260}>
      <PieChart>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          innerRadius={70}
          outerRadius={105}
          paddingAngle={3}
          dataKey="value"
          label={({ name, value }) => `${name}: ${value}`}
          labelLine={false}
        >
          {data.map((entry) => (
            <Cell
              key={entry.name}
              fill={STATUS_COLORS[entry.name.toLowerCase()] || "#6b7280"}
              stroke="#0f1623"
              strokeWidth={2}
            />
          ))}
        </Pie>
        <Tooltip content={<ChartTooltip />} />
        <Legend wrapperStyle={{ fontSize: 12, color: "#8b96aa" }} />
      </PieChart>
    </ResponsiveContainer>
  );
}
