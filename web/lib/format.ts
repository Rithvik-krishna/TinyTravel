export function inr(n: number | null | undefined): string {
  if (n == null || isNaN(n)) return "N/A";
  return `₹${n.toLocaleString("en-IN")}`;
}

export function shortTime(isoString: string | null | undefined): string {
  if (!isoString) return "";
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return "";
    return d.toLocaleTimeString("en-US", {
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
      timeZone: "Asia/Kolkata",
    });
  } catch {
    return "";
  }
}

export function relativeTime(isoString: string | null | undefined): string {
  if (!isoString) return "";
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return "";
    const now = Date.now();
    const diffMs = now - d.getTime();
    const diffSec = Math.round(diffMs / 1000);
    const diffMin = Math.round(diffSec / 60);
    const diffHours = Math.round(diffMin / 60);

    if (Math.abs(diffSec) < 60) return "just now";
    if (Math.abs(diffMin) < 60) {
      return diffMin > 0 ? `${diffMin} min ago` : `in ${Math.abs(diffMin)} min`;
    }
    if (Math.abs(diffHours) < 24) {
      return diffHours > 0 ? `${diffHours} hr ago` : `in ${Math.abs(diffHours)} hr`;
    }
    const diffDays = Math.round(diffHours / 24);
    return diffDays > 0 ? `${diffDays} days ago` : `in ${Math.abs(diffDays)} days`;
  } catch {
    return "";
  }
}

/** Absolute amount with explicit sign, e.g. "+₹3,066" / "−₹4,692". Null-safe. */
export function signedInr(n: number | null | undefined): string {
  if (n == null || isNaN(n)) return "N/A";
  return `${n < 0 ? "−" : "+"}${inr(Math.abs(n))}`;
}

/** payable - listing, or null when either side is unknown. */
export function gapAmount(listing: number | null | undefined, payable: number | null | undefined): number | null {
  if (listing == null || payable == null) return null;
  return payable - listing;
}

/** (payable - listing) / listing as a percentage with one decimal, or null. */
export function gapPct(listing: number | null | undefined, payable: number | null | undefined): number | null {
  const d = gapAmount(listing, payable);
  if (d == null || !listing) return null;
  return Math.round((d / listing) * 1000) / 10;
}

/** "30 Oct 2026, 10:10 PM" in IST, or "" when unknown. */
export function longDateTime(isoString: string | null | undefined): string {
  if (!isoString) return "";
  const d = new Date(isoString);
  if (isNaN(d.getTime())) return "";
  const date = d.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "Asia/Kolkata" });
  return `${date}, ${shortTime(isoString)}`;
}