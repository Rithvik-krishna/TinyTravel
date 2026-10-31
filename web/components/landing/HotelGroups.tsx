import React from "react";
import { TagItem } from "@/lib/tags";
import { KeyTagRail } from "./KeyTagRail";

interface Group {
  hotel_id?: string;
  canonical_name?: string;
  area?: string;
  match_status?: string;
  confidence?: number;
  why?: string;
  offer_ids?: string[];
}

export function HotelGroups({ groups, tags }: { groups: Group[]; tags: TagItem[] }) {
  return (
    <section id="hotels">
      <div className="wrap">
        <div className="sec-head">
          <span className="eyebrow">Every hotel we checked</span>
          <h2>Eight offers, shown honestly.</h2>
          <p className="lede">Blocked and unverified offers stay on the rail with the reason. They never get a price or a score.</p>
        </div>
        <div className="groups">
          {groups.map((g) => {
            const merged = g.match_status === "merged";
            const conf = g.confidence != null ? Math.round(g.confidence * 100) : null;
            const items = tags.filter((t) => (g.offer_ids ? g.offer_ids.includes(t.id) : t.hotelId === g.hotel_id));
            return (
              <div className={`group${merged ? "" : " suggested"}`} key={g.hotel_id ?? g.canonical_name}>
                <div className="ghead">
                  <h3>{g.canonical_name}</h3>
                  {g.area && <span className="mono" style={{ color: "var(--muted)", fontSize: 13 }}>{g.area}</span>}
                  {merged ? (
                    <span className="badge ok">Same hotel{conf != null ? ` · ${conf}%` : ""}</span>
                  ) : (
                    <span className="badge warn">Possible match, not merged in pricing{conf != null ? ` · ${conf}%` : ""}</span>
                  )}
                </div>
                <div className="gbar" />
                {g.why && <p className="gwhy">Why grouped: {g.why}</p>}
                <KeyTagRail tags={items} width="170px" variant="group" />
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}