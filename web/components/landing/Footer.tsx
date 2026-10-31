import React from "react";

function join(names: string[]): string {
  if (names.length < 2) return names.join("");
  return `${names.slice(0, -1).join(", ")} and ${names[names.length - 1]}`;
}

export function Footer({ platforms }: { platforms: string[] }) {
  return (
    <footer>
      <div className="wrap">
        <span>TinyTravel · Built at Swim with TinyFish, Bangalore</span>
        {platforms.length > 0 && <span>Checks {join(platforms)}</span>}
      </div>
    </footer>
  );
}