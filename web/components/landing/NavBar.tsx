import React from "react";
import Link from "next/link";

export function NavBar() {
  return (
    <header className="nav">
      <div className="wrap">
        <a className="logo" href="#top">
          <i />
          TinyTravel
        </a>
        <nav aria-label="Sections">
          <a href="#how">How it works</a>
          <a href="#proof">Proof</a>
          <a href="#safety">Safety</a>
          <a href="#faq">FAQ</a>
        </nav>
        <Link className="btn sm" href="/book">
          Book now
        </Link>
      </div>
    </header>
  );
}