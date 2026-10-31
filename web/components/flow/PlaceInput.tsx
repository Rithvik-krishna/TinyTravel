"use client";

import React, { useId, useState } from "react";
import { Place, placeLabel, searchPlaces } from "@/lib/places";

interface Props {
  value: string;
  onChange: (text: string) => void;
  onPick: (place: Place) => void;
  id?: string;
  placeholder?: string;
  ariaLabel?: string;
  invalid?: boolean;
  describedBy?: string;
  /** The box also accepts a whole sentence: suggest only while the text still looks like a place name. */
  freeText?: boolean;
  onKeyDown?: (e: React.KeyboardEvent<HTMLInputElement>) => void;
}

/** Text input with a place suggestion list (combobox pattern: arrows move, Enter picks, Escape closes). */
export function PlaceInput({ value, onChange, onPick, id, placeholder, ariaLabel, invalid, describedBy, freeText, onKeyDown }: Props) {
  const listId = useId();
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);

  const looksLikePlace = !freeText || !/[,\d]/.test(value);
  const options = open && looksLikePlace ? searchPlaces(value) : [];
  // Nothing to suggest once the text exactly matches the only option.
  const shown = options.length === 1 && placeLabel(options[0]).toLowerCase() === value.trim().toLowerCase() ? [] : options;

  const pick = (p: Place) => {
    onPick(p);
    setOpen(false);
    setActive(-1);
  };

  return (
    <div className="place">
      <input
        id={id}
        type="text"
        role="combobox"
        aria-expanded={shown.length > 0}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={active >= 0 ? `${listId}-${active}` : undefined}
        aria-label={ariaLabel}
        aria-invalid={invalid}
        aria-describedby={describedBy}
        autoComplete="off"
        placeholder={placeholder}
        value={value}
        onChange={(e) => {
          onChange(e.target.value);
          setOpen(true);
          setActive(-1);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onKeyDown={(e) => {
          if (shown.length > 0) {
            if (e.key === "ArrowDown") {
              e.preventDefault();
              setActive((i) => (i + 1) % shown.length);
              return;
            }
            if (e.key === "ArrowUp") {
              e.preventDefault();
              setActive((i) => (i <= 0 ? shown.length - 1 : i - 1));
              return;
            }
            if (e.key === "Enter" && active >= 0) {
              e.preventDefault();
              pick(shown[active]);
              return;
            }
          }
          if (e.key === "Escape") setOpen(false);
          onKeyDown?.(e);
        }}
      />
      {shown.length > 0 && (
        <ul className="place-list" role="listbox" id={listId}>
          {shown.map((p, i) => (
            <li
              key={placeLabel(p)}
              id={`${listId}-${i}`}
              role="option"
              aria-selected={i === active}
              // mousedown, not click: the input's blur would close the list before a click lands
              onMouseDown={(e) => {
                e.preventDefault();
                pick(p);
              }}
              onMouseEnter={() => setActive(i)}
            >
              <span>{placeLabel(p)}</span>
              <small>{p.region}</small>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}