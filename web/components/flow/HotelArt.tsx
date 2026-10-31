import React, { useId } from "react";

/** Deterministic skyline illustration so each hotel gets a stable placeholder image (no photos in the data yet). */
export function HotelArt({ hotelId, name }: { hotelId: string; name: string }) {
  const gid = `g${useId().replace(/[^a-zA-Z0-9]/g, "")}`;
  let hue = 0;
  for (const ch of hotelId) hue = (hue * 31 + ch.charCodeAt(0)) % 360;
  let seed = hue * 7 + 3;
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
    const l = 28 + Math.floor(rnd() * 10);
    shapes.push(<rect key={`b${k++}`} x={x} y={200 - h} width={w} height={h} fill={`hsl(${hue},35%,${l}%)`} />);
    for (let wy = 200 - h + 10; wy < 190; wy += 16)
      for (let wx = x + 6; wx < x + w - 8; wx += 12)
        if (rnd() > 0.35) shapes.push(<rect key={`w${k++}`} x={wx} y={wy} width={5} height={7} fill={`hsl(48,95%,${70 + Math.floor(rnd() * 20)}%)`} opacity={0.9} />);
    x += w + 4;
  }
  return (
    <svg viewBox="0 0 400 200" preserveAspectRatio="xMidYMid slice" role="img" aria-label={`Illustration of ${name}`} style={{ display: "block", width: "100%", height: "100%" }}>
      <defs>
        <linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor={`hsl(${hue},62%,70%)`} />
          <stop offset="1" stopColor={`hsl(${(hue + 25) % 360},70%,90%)`} />
        </linearGradient>
      </defs>
      <rect width="400" height="200" fill={`url(#${gid})`} />
      <circle cx={sunX} cy={46} r={20} fill={`hsl(${(hue + 40) % 360},90%,92%)`} opacity={0.85} />
      {shapes}
    </svg>
  );
}