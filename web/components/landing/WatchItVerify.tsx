"use client";

import React, { useState, useEffect, useCallback, useMemo } from "react";
import { Play, Pause, RotateCcw, CheckCircle2, ShieldAlert, Clock, Bot } from "lucide-react";
import sseFixture from "@fixtures/sse_script.json";

interface SiteState {
  name: string;
  runId: string;
  stepText: string;
  progress: number;
  status: "idle" | "running" | "verified" | "blocked" | "unverified";
  reachedPayment: boolean;
}

interface ScriptEvent {
  t_ms: number;
  event: string;
  data: {
    run_id?: string;
    step_text?: string;
    status?: string;
    platform?: string;
    [key: string]: unknown;
  };
}

export function WatchItVerify() {
  const [isPlaying, setIsPlaying] = useState(true);
  const [playbackTimeMs, setPlaybackTimeMs] = useState(0);

  // Focus simulation on La Marvella 3 platform agents (cleartrip, agoda, booking)
  const targetRuns = useMemo(
    () => ({
      Cleartrip: "mock_run_h1_cleartrip",
      Agoda: "mock_run_h1_agoda",
      "Booking.com": "mock_run_h1_booking",
    }),
    []
  );

  const events: ScriptEvent[] = (sseFixture.events as ScriptEvent[]) || [];
  const maxTime = sseFixture.total_ms || 27000;

  // Step advancement loop at 2x speed (interval = 50ms, adds 100ms)
  useEffect(() => {
    if (!isPlaying) return;

    const interval = setInterval(() => {
      setPlaybackTimeMs((prev) => {
        if (prev >= maxTime) {
          return 0; // loop
        }
        return prev + 120;
      });
    }, 50);

    return () => clearInterval(interval);
  }, [isPlaying, maxTime]);

  const restart = useCallback(() => {
    setPlaybackTimeMs(0);
    setIsPlaying(true);
  }, []);

  // Compute state of each platform at current playbackTimeMs
  const siteStates = useMemo(() => {
    const states: Record<string, SiteState> = {
      Cleartrip: {
        name: "Cleartrip",
        runId: targetRuns.Cleartrip,
        stepText: "Queued for probe...",
        progress: 0,
        status: "idle",
        reachedPayment: false,
      },
      Agoda: {
        name: "Agoda",
        runId: targetRuns.Agoda,
        stepText: "Queued for probe...",
        progress: 0,
        status: "idle",
        reachedPayment: false,
      },
      "Booking.com": {
        name: "Booking.com",
        runId: targetRuns["Booking.com"],
        stepText: "Queued for probe...",
        progress: 0,
        status: "idle",
        reachedPayment: false,
      },
    };

    const pastEvents = events.filter((e) => e.t_ms <= playbackTimeMs);

    for (const ev of pastEvents) {
      for (const [platform, runId] of Object.entries(targetRuns)) {
        if (ev.data.run_id === runId) {
          if (ev.event === "agent_started") {
            states[platform].status = "running";
            states[platform].stepText = "Starting browser sandbox...";
            states[platform].progress = 15;
          } else if (ev.event === "agent_progress" && ev.data.step_text) {
            states[platform].status = "running";
            states[platform].stepText = ev.data.step_text;
            if (ev.data.step_text.includes("search page")) states[platform].progress = 30;
            else if (ev.data.step_text.includes("Searching hotel")) states[platform].progress = 45;
            else if (ev.data.step_text.includes("hotel page")) states[platform].progress = 60;
            else if (ev.data.step_text.includes("Selecting room")) states[platform].progress = 75;
            else if (ev.data.step_text.includes("guest details")) states[platform].progress = 85;
            else if (ev.data.step_text.includes("payment page")) {
              states[platform].progress = 95;
              states[platform].reachedPayment = true;
            }
          } else if (ev.event === "agent_done" && ev.data.status) {
            states[platform].status = ev.data.status as SiteState["status"];
            states[platform].progress = 100;
            states[platform].stepText = "Audit complete. Payment page captured.";
          }
        }
      }
    }

    return Object.values(states);
  }, [events, playbackTimeMs, targetRuns]);

  return (
    <section id="watch-it-verify" className="w-full py-16 sm:py-24 px-4 sm:px-6">
      <div className="max-w-6xl mx-auto">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-12">
          <div className="space-y-2">
            <span className="text-xs sm:text-sm font-bold uppercase tracking-wider text-brand">
              Live Probe Telemetry
            </span>
            <h2 className="text-3xl sm:text-5xl font-extrabold tracking-tight text-text">
              Watch it verify
            </h2>
            <p className="text-sm sm:text-base text-text-muted max-w-xl">
              Simulated real-time playback of 3 guest agents navigating concurrently to checkout.
            </p>
          </div>

          {/* Controls */}
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setIsPlaying((p) => !p)}
              className="inline-flex items-center gap-2 rounded-full border border-border bg-surface px-4 py-2 text-xs sm:text-sm font-semibold text-text shadow-sm hover:bg-surface-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"
            >
              {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
              {isPlaying ? "Pause" : "Resume"}
            </button>
            <button
              type="button"
              onClick={restart}
              className="inline-flex items-center gap-2 rounded-full border border-border bg-surface px-4 py-2 text-xs sm:text-sm font-semibold text-text shadow-sm hover:bg-surface-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"
            >
              <RotateCcw className="w-4 h-4" />
              Restart
            </button>
            <span className="text-xs font-mono text-text-muted tabular-nums">
              {(playbackTimeMs / 1000).toFixed(1)}s / {(maxTime / 1000).toFixed(1)}s
            </span>
          </div>
        </div>

        {/* Aria-live announcement for screen readers */}
        <div className="sr-only" aria-live="polite">
          {siteStates.map((s) => `${s.name}: ${s.stepText} (${s.progress}%).`).join(" ")}
        </div>

        {/* 3 Site Tiles */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {siteStates.map((site) => {
            const isVerified = site.status === "verified";
            const isBlocked = site.status === "blocked";
            const isRunning = site.status === "running";

            return (
              <div
                key={site.name}
                className="flex flex-col p-6 rounded-3xl bg-surface border border-border shadow-sm space-y-5 relative overflow-hidden"
              >
                {/* Header */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <div className="flex items-center justify-center w-8 h-8 rounded-xl bg-surface-2 border border-border text-brand font-bold text-xs">
                      <Bot className="w-4 h-4" />
                    </div>
                    <div>
                      <h3 className="text-base font-bold text-text leading-tight">{site.name}</h3>
                      <span className="text-[11px] text-text-muted">Agent probe #1</span>
                    </div>
                  </div>

                  {/* Badge */}
                  {isVerified ? (
                    <span className="inline-flex items-center gap-1 rounded-full bg-success/15 border border-success/30 px-2.5 py-0.5 text-xs font-bold text-success">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      Verified
                    </span>
                  ) : isBlocked ? (
                    <span className="inline-flex items-center gap-1 rounded-full bg-danger/15 border border-danger/30 px-2.5 py-0.5 text-xs font-bold text-danger">
                      <ShieldAlert className="w-3.5 h-3.5" />
                      Blocked
                    </span>
                  ) : isRunning ? (
                    <span className="inline-flex items-center gap-1.5 rounded-full bg-brand/15 border border-brand/30 px-2.5 py-0.5 text-xs font-semibold text-brand animate-pulse">
                      <span className="w-1.5 h-1.5 rounded-full bg-brand" />
                      Navigating
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 rounded-full bg-surface-2 border border-border px-2.5 py-0.5 text-xs font-medium text-text-muted">
                      <Clock className="w-3 h-3" />
                      Queued
                    </span>
                  )}
                </div>

                {/* Step Text */}
                <div className="flex-1 min-h-[52px] rounded-2xl bg-surface-2/60 border border-border/80 p-3 flex items-center">
                  <p className="text-xs sm:text-sm font-medium text-text">
                    {site.stepText}
                  </p>
                </div>

                {/* Progress Bar */}
                <div className="space-y-1.5">
                  <div className="flex justify-between text-xs text-text-muted font-medium">
                    <span>Funnel depth</span>
                    <span className="font-mono tabular-nums">{site.progress}%</span>
                  </div>
                  <div className="w-full h-2 rounded-full bg-surface-2 overflow-hidden border border-border/40">
                    <div
                      className={`h-full transition-all duration-300 ${
                        isVerified
                          ? "bg-success"
                          : isBlocked
                          ? "bg-danger"
                          : "bg-brand"
                      }`}
                      style={{ width: `${site.progress}%` }}
                    />
                  </div>
                </div>

                {/* Footer notes */}
                <div className="pt-2 border-t border-border/60 flex items-center justify-between text-[11px] text-text-muted">
                  <span>Guest profile: Test Guest</span>
                  <span>Payment: STOPPED</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
