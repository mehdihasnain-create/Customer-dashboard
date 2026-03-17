export default function ChannelTable({ rows, showTotal = true }) {
  let totO = 0, totC = 0, totT = 0;
  rows.filter(r => !r.excl).forEach(r => {
    totO += r.ch.open.length;
    totC += r.ch.closed.length;
    totT += r.ch.tickets.length;
  });

  function cell(v, href) {
    if (v === 0) return <span className="text-gray-200">—</span>;
    return (
      <a href={href} target="_blank" rel="noreferrer" className="font-semibold" style={{ color: "var(--brand)" }}>
        {v}
      </a>
    );
  }

  return (
    <table className="klarity-table">
      <thead>
        <tr>
          <th>Source</th>
          <th className="text-center">Open</th>
          <th className="text-center">Closed</th>
          <th className="text-center">Total</th>
        </tr>
      </thead>
      <tbody>
        {rows.map(({ label, ch, href, excl }) => (
          <tr key={label} className={excl ? "excl-row" : ""}>
            <td><a href={href} target="_blank" rel="noreferrer">{label}</a></td>
            <td className="text-center">{cell(ch.open.length, href)}</td>
            <td className="text-center">{cell(ch.closed.length, href)}</td>
            <td className="text-center">{cell(ch.tickets.length, href)}</td>
          </tr>
        ))}
        {showTotal && (
          <tr className="total-row">
            <td>TOTAL</td>
            <td className="text-center font-extrabold">{totO}</td>
            <td className="text-center font-extrabold">{totC}</td>
            <td className="text-center font-extrabold" style={{ color: "var(--brand)" }}>{totT}</td>
          </tr>
        )}
      </tbody>
    </table>
  );
}
