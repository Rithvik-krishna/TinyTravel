"use client";

import React, { useState } from "react";
import { TagItem } from "@/lib/tags";
import { KeyTagRail } from "@/components/ui/key-tag-rail";
import { ShieldCheck, Info } from "lucide-react";

interface HotelGroupInfo {
  hotel_id?: string;
  canonical_name?: string;
  area?: string;
  match_status?: string;
  confidence?: number;
  why?: string;
  offer_ids?: string[];
}

interface AllHotelsRailProps {
  items: TagItem[];
  hotelGroups?: HotelGroupInfo[];
}

export function AllHotelsRail({ items, hotelGroups }: AllHotelsRailProps) {
  const [selectedGroup, setSelectedGroup] = useState<string>("all");

  const groups = hotelGroups || [
    {
      hotel_id: "h1",
      canonical_name: "La Marvella",
      area: "HSR Layout",
      match_status: "merged",
      confidence: 0.96,
      why: "Name 100%, same area, phone match",
    },
    {
      hotel_id: "h2",
      canonical_name: "Lemon Leaf Suites",
      area: "Koramangala",
      match_status: "merged",
      confidence: 0.93,
      why: "Name 96%, same area",
    },
    {
      hotel_id: "h3",
      canonical_name: "Urban Nest Inn",
      area: "HSR Layout",
      match_status: "suggested",
      confidence: 0.82,
      why: "Name 82%, same area. Possible match: not merged in pricing",
    },
  ];

  const filteredItems =
    selectedGroup === "all"
      ? items
      : items.filter((item) => item.hotelId === selectedGroup);

  return (
    <section className="w-full py-16 sm:py-24 px-4 sm:px-6 bg-surface-2/30 border-t border-border">
      <div className="max-w-6xl mx-auto space-y-8">
        {/* Section Header */}
        <div className="text-center max-w-3xl mx-auto space-y-3">
          <span className="text-xs sm:text-sm font-bold uppercase tracking-wider text-brand">
            Stage 2 Full Audit
          </span>
          <h2 className="text-3xl sm:text-5xl font-extrabold tracking-tight text-text">
            All 8 offers compared across 3 platforms
          </h2>
          <p className="text-sm sm:text-base text-text-muted">
            Grouped by hotel with strict honesty rules: unverified funnels and blocked sites
            are displayed explicitly—never hidden and never fabricated.
          </p>
        </div>

        {/* Grouping Bars & Status Legend */}
        <div className="p-5 sm:p-6 rounded-3xl bg-surface border border-border shadow-sm space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-border/70">
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-brand" />
              <span className="text-xs sm:text-sm font-bold text-text">
                Hotel Entity Resolution &amp; Matching Integrity
              </span>
            </div>
            <div className="flex items-center gap-4 text-xs text-text-muted">
              <div className="flex items-center gap-1.5">
                <span className="w-6 h-1.5 rounded-full bg-gradient-to-r from-amber-400 to-amber-600 inline-block" />
                <span>Solid brass = Merged</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-6 border-t-2 border-dashed border-amber-500 inline-block" />
                <span>Dashed bar = Suggested match</span>
              </div>
            </div>
          </div>

          {/* Grouping Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {groups.map((group) => {
              const isMerged = group.match_status === "merged";
              const isSelected = selectedGroup === group.hotel_id;

              return (
                <button
                  type="button"
                  key={group.hotel_id}
                  onClick={() =>
                    setSelectedGroup((curr) =>
                      curr === group.hotel_id ? "all" : group.hotel_id || "all"
                    )
                  }
                  className={`text-left p-3.5 rounded-2xl border transition-all ${
                    isSelected
                      ? "border-brand bg-brand/5 ring-1 ring-brand"
                      : "border-border bg-surface-2/60 hover:border-brand/40"
                  }`}
                >
                  {/* Brass grouping bar */}
                  <div className="mb-2.5">
                    {isMerged ? (
                      <div className="w-full h-1.5 rounded-full bg-gradient-to-r from-amber-400 via-yellow-400 to-amber-600 shadow-sm" />
                    ) : (
                      <div className="w-full border-t-2 border-dashed border-amber-500" />
                    )}
                  </div>

                  <div className="flex items-center justify-between">
                    <span className="font-bold text-text text-sm sm:text-base">
                      {group.canonical_name}
                    </span>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider ${
                        isMerged
                          ? "bg-amber-500/15 text-amber-600 dark:text-amber-400"
                          : "bg-warning/15 text-warning"
                      }`}
                    >
                      {group.match_status}
                    </span>
                  </div>

                  <p className="text-xs text-text-muted mt-1 leading-snug">
                    {group.why}
                  </p>

                  <div className="mt-2 text-[11px] font-medium text-brand">
                    {isSelected ? "Showing this hotel only" : "Click to isolate in rail →"}
                  </div>
                </button>
              );
            })}
          </div>

          {selectedGroup !== "all" && (
            <div className="pt-1 text-center">
              <button
                type="button"
                onClick={() => setSelectedGroup("all")}
                className="text-xs font-semibold text-brand hover:underline inline-flex items-center gap-1"
              >
                Reset to show all 8 offers
              </button>
            </div>
          )}
        </div>

        {/* 8-Tag Rail Centerpiece */}
        <div className="pt-2">
          <KeyTagRail
            items={filteredItems}
            eyebrow="Physics Tag Rail"
            heading={
              selectedGroup === "all"
                ? "All 8 Offers Hanging on Rail"
                : `Filtered Offers (${filteredItems.length})`
            }
            caption="Swing, lift, drag, and flip tags to inspect listing price vs checkout payable price."
            maxUnit={220}
          />
        </div>
      </div>
    </section>
  );
}
