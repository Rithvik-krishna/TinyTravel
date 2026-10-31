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
