import demo from "@fixtures/demo_run.json";
import script from "@fixtures/sse_script.json";

export const MOCK = process.env.NEXT_PUBLIC_DATA_MODE !== "live";
const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
export const EVENTS = ["parsed","discovery_started","listings_found","hotels_grouped","agent_started","agent_progress","agent_done","ranking_ready","error"];

export async function startSearch(text: string, request?: Record<string, unknown>) {
  if (MOCK) return { search_id: "mock_search" };
  return (await fetch(`${API}/api/search`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(request ? { text, ...request } : { text }) })).json();
}
export async function getResults(id: string): Promise<any> {
  return MOCK ? demo : (await fetch(`${API}/api/search/${id}/results`)).json();
}
export async function getHandoff(offerId: string): Promise<any> {
  return MOCK ? demo.handoff : (await fetch(`${API}/api/offers/${offerId}/handoff`)).json();
}
export async function recheck(offerId: string): Promise<any> {
  return MOCK ? demo.rechecks[0] : (await fetch(`${API}/api/offers/${offerId}/recheck`, { method: "POST" })).json();
}
export function openStream(id: string, onEvent: (e: string, d: any) => void, speed = 1) {
  if (!MOCK) {
    const es = new EventSource(`${API}/api/search/${id}/stream`);
    EVENTS.forEach(t => es.addEventListener(t, (m: MessageEvent) => onEvent(t, JSON.parse(m.data))));
    return () => es.close();
  }
  const timers = (script as any).events.map((ev: any) => setTimeout(() => onEvent(ev.event, ev.data), ev.t_ms / speed));
  return () => timers.forEach(clearTimeout);
}
export const inr = (n: number | null) => (n == null ? "N/A" : "₹" + n.toLocaleString("en-IN"));
