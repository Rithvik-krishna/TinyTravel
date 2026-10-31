"use client";

import React, { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import demo from "@fixtures/demo_run.json";
import { MOCK, startSearch } from "@/lib/dataSource";
import { inr } from "@/lib/format";
import { applySentence, buildSentence, DEAL_LABEL, DealMode, loadRequest, MustHave, saveSearch, SearchRequest } from "@/lib/flow";

const MUST: Array<[keyof MustHave, string]> = [
  ["breakfast", "Breakfast"],
  ["free_cancellation", "Free cancellation"],
  ["wifi", "Wi-Fi"],
  ["parking", "Parking"],
];

function initial(): SearchRequest {
  if (MOCK) {
    const r = demo.search_request;
    return {
      destination: r.destination,
      area_hint: r.area_hint,
      check_in: r.check_in,
      check_out: r.check_out,
      guests: r.guests,
      rooms: r.rooms,
      budget_per_night: r.budget_per_night,
      must_have: { ...r.must_have },
      deal_mode: r.deal_mode as DealMode,
      currency: r.currency,
      raw_text: r.raw_text,
    };
  }
  return {
    destination: "",
    area_hint: "",
    check_in: "",
    check_out: "",
    guests: 2,
    rooms: 1,
    budget_per_night: 12000,
    must_have: { breakfast: false, free_cancellation: false, wifi: false, parking: false },
    deal_mode: "best_value",
    currency: "INR",
    raw_text: "",
  };
}

type Errors = Partial<Record<"destination" | "check_in" | "check_out" | "budget_per_night", string>>;

export function validate(r: SearchRequest, today: string): Errors {
  const e: Errors = {};
  if (!r.destination.trim()) e.destination = "Enter a city or area.";
  if (!r.check_in) e.check_in = "Pick a check-in date.";
  else if (today && r.check_in < today) e.check_in = "Check-in can't be in the past.";
  if (!r.check_out) e.check_out = "Pick a check-out date.";
  else if (r.check_in && r.check_out <= r.check_in) e.check_out = "Check-out must be after check-in.";
  if (!(r.budget_per_night > 0)) e.budget_per_night = "Enter a budget above 0.";
  return e;
}

function Counter({ label, value, min, max, onChange }: { label: string; value: number; min: number; max: number; onChange: (n: number) => void }) {
  return (
    <div className="field">
      <span className="fl" id={`l-${label}`}>{label}</span>
      <div className="stepper-num" role="group" aria-labelledby={`l-${label}`}>
        <button type="button" aria-label={`Fewer ${label.toLowerCase()}`} disabled={value <= min} onClick={() => onChange(value - 1)}>−</button>
        <output aria-live="polite">{value}</output>
        <button type="button" aria-label={`More ${label.toLowerCase()}`} disabled={value >= max} onClick={() => onChange(value + 1)}>+</button>
      </div>
    </div>
  );
}

export function SearchForm() {
  const router = useRouter();
  const [req, setReq] = useState<SearchRequest>(initial);
  const [today, setToday] = useState("");
  const [touched, setTouched] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [nl, setNl] = useState("");
  const dlg = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    setToday(new Date().toLocaleDateString("en-CA"));
    const last = loadRequest();
    if (last) setReq(last);
  }, []);

  const set = <K extends keyof SearchRequest>(k: K, v: SearchRequest[K]) => setReq((r) => ({ ...r, [k]: v }));
  const errs = validate(req, today);
  const valid = Object.keys(errs).length === 0;
  const show = (k: keyof Errors) => (touched ? errs[k] : undefined);

  const submit = async (ev: React.FormEvent) => {
    ev.preventDefault();
    setTouched(true);
    if (!valid || busy) return;
    setBusy(true);
    setError(null);
    const full = { ...req, destination: req.destination.trim(), raw_text: buildSentence(req) };
    try {
      const res: { search_id?: string } = await startSearch(full.raw_text, { ...full });
      if (!res?.search_id) throw new Error("no id");
      saveSearch(full, res.search_id);
      router.push(`/investigation?id=${encodeURIComponent(res.search_id)}`);
    } catch {
      setError("Couldn't start the search. Check your connection and try again.");
      setBusy(false);
    }
  };

  return (
    <form className="sform" onSubmit={submit} noValidate aria-label="Search hotels">
      <h2 className="sf-title">Find your stay</h2>
      <div className="nlrow">
        <input type="text" aria-label="Describe your stay" placeholder="Or type it: Bengaluru, 20-21 Nov, 2 people, under 12k" value={nl} onChange={(e) => setNl(e.target.value)} />
        <button className="btn ghost sm" type="button" onClick={() => nl.trim() && setReq((r) => applySentence(r, nl, today))}>Fill in</button>
      </div>
      <div className="fgrid">
        <div className="field f-wide">
          <label htmlFor="dest">Where to?</label>
          <input id="dest" type="text" autoComplete="off" placeholder="City or area, e.g. Bengaluru" value={req.destination} onChange={(e) => set("destination", e.target.value)} aria-invalid={!!show("destination")} aria-describedby="e-dest" />
          <span id="e-dest" className="err" role="alert">{show("destination")}</span>
        </div>
        <div className="field">
          <label htmlFor="cin">Check-in</label>
          <input id="cin" type="date" min={today || undefined} value={req.check_in} onChange={(e) => set("check_in", e.target.value)} aria-invalid={!!show("check_in")} aria-describedby="e-cin" />
          <span id="e-cin" className="err" role="alert">{show("check_in")}</span>
        </div>
        <div className="field">
          <label htmlFor="cout">Check-out</label>
          <input id="cout" type="date" min={req.check_in || today || undefined} value={req.check_out} onChange={(e) => set("check_out", e.target.value)} aria-invalid={!!show("check_out")} aria-describedby="e-cout" />
          <span id="e-cout" className="err" role="alert">{show("check_out")}</span>
        </div>
      </div>

      <div className="fgrid2">
        <Counter label="Guests" value={req.guests} min={1} max={12} onChange={(n) => set("guests", n)} />
        <Counter label="Rooms" value={req.rooms} min={1} max={6} onChange={(n) => set("rooms", n)} />
        <div className="field">
          <label htmlFor="budget">Budget per night: <span className="num" style={{ color: "var(--fg)", textTransform: "none", letterSpacing: 0 }}>{inr(req.budget_per_night)}</span></label>
          <input id="budget" type="range" min={2000} max={20000} step={500} value={Math.min(20000, Math.max(2000, req.budget_per_night || 12000))} onChange={(e) => set("budget_per_night", Number(e.target.value))} aria-describedby="e-bud" />
          <span id="e-bud" className="err" role="alert">{show("budget_per_night")}</span>
        </div>
      </div>

      <fieldset>
        <legend>Must have</legend>
        <div className="chips">
          {MUST.map(([k, label]) => (
            <button key={k} type="button" className="chip-btn" aria-pressed={req.must_have[k]} onClick={() => set("must_have", { ...req.must_have, [k]: !req.must_have[k] })}>
              {label}
            </button>
          ))}
        </div>
      </fieldset>

      <fieldset>
        <legend>What counts as a good deal?</legend>
        <div className="chips" role="radiogroup" aria-label="Deal mode">
          {(Object.keys(DEAL_LABEL) as DealMode[]).map((m) => (
            <button key={m} type="button" role="radio" className="chip-btn" aria-checked={req.deal_mode === m} onClick={() => set("deal_mode", m)}>
              {DEAL_LABEL[m]}
            </button>
          ))}
        </div>
      </fieldset>

      <details className="req">
        <summary>What we&apos;ll check</summary>
        <pre>{JSON.stringify({ ...req, raw_text: buildSentence(req) }, null, 2)}</pre>
      </details>

      {error && <div className="notice bad" role="alert">{error}</div>}

      <div className="form-foot">
        <p>
          We check 3 sites like a real buyer, as a guest, and never pay. About 3–5 minutes.{" "}
          <button type="button" className="linkish" onClick={() => dlg.current?.showModal()}>How we stay safe</button>
        </p>
        <button className="btn" type="submit" disabled={busy || (touched && !valid)}>
          {busy ? "Starting…" : "Verify prices"}
        </button>
      </div>
      {MOCK && (
        <p className="notice warn" role="note">
          Demo mode: this runs a recorded sample (Bengaluru, 20–21 Nov) whatever you enter. Results are labelled MOCK DATA.
        </p>
      )}

      <dialog ref={dlg} aria-labelledby="safe-t" onClick={(e) => e.target === dlg.current && dlg.current?.close()}>
        <div className="dlg">
          <h3 id="safe-t">How we stay safe</h3>
          <ul style={{ margin: 0, paddingLeft: 18, display: "grid", gap: 6 }}>
            <li>Agents use dummy guest details, never yours.</li>
            <li>Every run stops at the payment page. Nothing is booked.</li>
            <li>We never log in and never enter an OTP.</li>
            <li>We don&apos;t solve captchas. A blocked site is shown as blocked.</li>
          </ul>
          <button className="btn sm" type="button" onClick={() => dlg.current?.close()}>Got it</button>
        </div>
      </dialog>
    </form>
  );
}