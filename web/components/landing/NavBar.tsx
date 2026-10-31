import React from "react";
import { NavPill } from "@/components/ui/NavPill";

export function NavBar() {
  return (
    <NavPill
      links={[
        { href: "#how", label: "How it works" },
        { href: "#proof", label: "Proof" },
        { href: "#safety", label: "Safety" },
        { href: "#faq", label: "FAQ" },
      ]}
      ctaLabel="Book now"
      ctaHref="/book"
      logoHref="#top"
    />
  );
}