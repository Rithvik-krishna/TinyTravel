import React from "react";

/** Deterministic skyline placeholder (no photos in the data yet). Painted only with palette tokens. */
export function HotelArt({ hotelId, name }: { hotelId: string; name: string }) {
  let seed = 0;
  for (const ch of hotelId) seed = (seed * 31 + ch.charCodeAt(0)) % 100000;
  seed = seed * 7 + 3;
  const rnd = () => {
    seed = (seed * 9301 + 49297) % 233280;
    return seed / 233280;
  };
  const sunX = 60 + Math.floor(rnd() * 280);
  const shapes: React.ReactNode[] = [];
  let x = -10;
  let k = 0;
  while (x < 410) {
    const w = 34 + Math.floor(rnd() * 44);
    const h = 60 + Math.floor(rnd() * 90);
    const shade = 0.55 + rnd() * 0.45;
    shapes.push(<rect key={`b${k++}`} x={x} y={200 - h} width={w} height={h} style={{ fill: "var(--ocean)", opacity: shade }} />);
    for (let wy = 200 - h + 10; wy < 190; wy += 16)
      for (let wx = x + 6; wx < x + w - 8; wx += 12)
        if (rnd() > 0.35) shapes.push(<rect key={`w${k++}`} x={wx} y={wy} width={5} height={7} style={{ fill: "var(--clay)", opacity: 0.9 }} />);
    x += w + 4;
  }
  return (
    <svg viewBox="0 0 400 200" preserveAspectRatio="xMidYMid slice" role="img" aria-label={`Illustration of ${name}`} style={{ display: "block", width: "100%", height: "100%" }}>
      <rect width="400" height="200" style={{ fill: "var(--sand)", opacity: 0.55 }} />
      <circle cx={sunX} cy={46} r={20} style={{ fill: "var(--clay)", opacity: 0.85 }} />
      {shapes}
    </svg>
  );
}