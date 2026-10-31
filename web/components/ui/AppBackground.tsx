import React from "react";

/**
 * Fixed sky-blue background with drifting blurred blobs and a fluted-glass rib overlay.
 * Rendered once in the root layout; every page scrolls over it. Styles live in app/glass.css.
 */
export function AppBackground() {
  return (
    <div className="appbg" aria-hidden="true">
      <span className="blob b1" />
      <span className="blob b2" />
      <span className="blob b3" />
      <span className="blob b4" />
      <span className="blob b5" />
      <span className="flutes" />
      <span className="vignette" />
      <span className="grain" />
    </div>
  );
}