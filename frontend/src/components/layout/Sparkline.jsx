export default function Sparkline({ points, width = 80, height = 20, stroke = 'var(--accent)' }) {
  if (!points || points.length < 2) return null;

  const min = Math.min(...points);
  const max = Math.max(...points);
  const range = max - min || 1;

  const coords = points.map((v, i) => {
    const x = (i / (points.length - 1)) * (width - 2) + 1;
    const y = height - 1 - ((v - min) / range) * (height - 2);
    return `${x.toFixed(2)},${y.toFixed(2)}`;
  });

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} aria-hidden="true" style={{ display: 'block' }}>
      <polyline
        points={coords.join(' ')}
        fill="none"
        stroke={stroke}
        strokeWidth="1.5"
        strokeLinejoin="miter"
        strokeLinecap="square"
      />
    </svg>
  );
}
