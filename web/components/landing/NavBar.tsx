import React from "react";

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
        <a className="btn sm" href="#verdict">
          Verify prices
        </a>
      </div>
    </header>
  );
}