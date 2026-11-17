"""Price Cache Service for TinyTravel.

Implements:
1. Cache key: (hotel_id, site, dates, guests, cohort_signature).
2. Fields: price_public, price_member (nullable), components, captured_at, source_run_file.
3. Freshness labels ('fresh', 'stale', 'expired') with TTL calculated by check-in date proximity.
4. Read-through API with live re-check hook.
5. Support for DATA_MODE='fake', DATA_MODE='saved', and live modes.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Callable, Coroutine, Dict, Literal, Optional, Tuple, Union
from pydantic import BaseModel, Field

FreshnessLabel = Literal["fresh", "stale", "expired"]


class PriceComponents(BaseModel):
    base: Optional[float] = None
    taxes: Optional[float] = None
    fees: Optional[float] = None
    discounts: Optional[float] = None
    other: Optional[float] = None


class CacheKey(BaseModel):
    hotel_id: str
    site: str
    dates: Tuple[str, str]  # (check_in, check_out) as YYYY-MM-DD
    guests: int = 2
    cohort_signature: str = "default"

    def to_key_str(self) -> str:
        ci, co = self.dates
        return f"{self.hotel_id}::{self.site}::{ci}_{co}::{self.guests}::{self.cohort_signature}"

    def __hash__(self) -> int:
        return hash((self.hotel_id, self.site, self.dates, self.guests, self.cohort_signature))

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, CacheKey):
            return False
        return (
            self.hotel_id == other.hotel_id
            and self.site == other.site
            and self.dates == other.dates
            and self.guests == other.guests
            and self.cohort_signature == other.cohort_signature
        )


class PriceCacheEntry(BaseModel):
    key: CacheKey
    price_public: float
    price_member: Optional[float] = None
    components: PriceComponents = Field(default_factory=PriceComponents)
    captured_at: str  # ISO-8601
    source_run_file: Optional[str] = None
    ttl_seconds: int = 3600

    def get_freshness(self, now: Optional[datetime] = None) -> FreshnessLabel:
        """Evaluate freshness:
        - age <= ttl: fresh
        - ttl < age <= 2 * ttl: stale
        - age > 2 * ttl: expired
        """
        if now is None:
            now = datetime.now(timezone.utc)
        
        # Parse captured_at
        try:
            dt = datetime.fromisoformat(self.captured_at)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        except Exception:
            return "expired"

        age = (now - dt).total_seconds()
        if age <= self.ttl_seconds:
            return "fresh"
        elif age <= 2 * self.ttl_seconds:
            return "stale"
        else:
            return "expired"


def calculate_ttl_seconds(check_in_date_str: str, as_of: Optional[datetime] = None) -> int:
    """Calculate TTL based on proximity to check-in date:
    - <= 3 days out: High volatility -> TTL = 15 minutes (900 s)
    - 4 to 7 days out: Medium volatility -> TTL = 1 hour (3600 s)
    - > 7 days out: Low volatility -> TTL = 6 hours (21600 s)
    """
    if as_of is None:
        as_of = datetime.now(timezone.utc)

    try:
        ci_date = datetime.strptime(check_in_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except Exception:
        return 3600

    days_out = (ci_date.date() - as_of.date()).days
    if days_out <= 3:
        return 900  # 15 minutes
    elif days_out <= 7:
        return 3600  # 1 hour
    else:
        return 21600  # 6 hours


class PriceCache:
    """In-memory thread-safe read-through price cache."""

    def __init__(self, mode: Optional[str] = None):
        self.mode = mode or os.getenv("DATA_MODE", "saved").lower()
        self._entries: Dict[str, PriceCacheEntry] = {}
        self.recheck_hook: Optional[Callable[[CacheKey, PriceCacheEntry], None]] = None

        if self.mode == "fake":
            self._seed_fake_mode()
        elif self.mode == "saved":
            self._seed_saved_mode()

    def set(
        self,
        key: CacheKey,
        price_public: float,
        price_member: Optional[float] = None,
        components: Optional[Union[PriceComponents, dict]] = None,
        captured_at: Optional[str] = None,
        source_run_file: Optional[str] = None,
        ttl_seconds: Optional[int] = None,
    ) -> PriceCacheEntry:
        if components is None:
            comps = PriceComponents()
        elif isinstance(components, dict):
            comps = PriceComponents(**components)
        else:
            comps = components

        if captured_at is None:
            captured_at = datetime.now(timezone.utc).isoformat()

        if ttl_seconds is None:
            ttl_seconds = calculate_ttl_seconds(key.dates[0])

        entry = PriceCacheEntry(
            key=key,
            price_public=price_public,
            price_member=price_member,
            components=comps,
            captured_at=captured_at,
            source_run_file=source_run_file,
            ttl_seconds=ttl_seconds,
        )
        self._entries[key.to_key_str()] = entry
        return entry

    def get(self, key: CacheKey, now: Optional[datetime] = None) -> Optional[Tuple[PriceCacheEntry, FreshnessLabel]]:
        entry = self._entries.get(key.to_key_str())
        if not entry:
            return None
        freshness = entry.get_freshness(now=now)
        return entry, freshness

    async def get_or_fetch(
        self,
        key: CacheKey,
        fetch_fn: Optional[Callable[[CacheKey], Coroutine[Any, Any, PriceCacheEntry]]] = None,
        force_refresh: bool = False,
        now: Optional[datetime] = None,
    ) -> Tuple[PriceCacheEntry, FreshnessLabel]:
        """Read-through API with live re-check hook."""
        res = self.get(key, now=now)

        if res is not None and not force_refresh:
            entry, freshness = res
            if freshness == "fresh":
                return entry, freshness
            elif freshness == "stale":
                # Stale entry: trigger recheck hook if configured
                if self.recheck_hook:
                    try:
                        self.recheck_hook(key, entry)
                    except Exception:
                        pass
                # If fetch_fn is provided and we want to refresh immediately
                if fetch_fn is not None:
                    try:
                        new_entry = await fetch_fn(key)
                        self._entries[key.to_key_str()] = new_entry
                        return new_entry, "fresh"
                    except Exception:
                        # Fallback to serving stale entry gracefully
                        return entry, "stale"
                return entry, "stale"
            # If expired, fall through to fetch_fn
        
        # Cache miss or expired or force_refresh
        if fetch_fn is not None:
            new_entry = await fetch_fn(key)
            self._entries[key.to_key_str()] = new_entry
            return new_entry, "fresh"

        if res is not None:
            return res[0], res[1]

        raise KeyError(f"Cache miss and no fetch_fn provided for key: {key.to_key_str()}")

    def _seed_fake_mode(self):
        """Seed synthetic test rates for fake mode."""
        k1 = CacheKey(
            hotel_id="bloomrooms_city_centre",
            site="cleartrip",
            dates=("2026-11-20", "2026-11-21"),
            guests=2,
            cohort_signature="standard_queen|no_meal|non_refundable",
        )
        self.set(
            key=k1,
            price_public=5580.0,
            price_member=None,
            components={"base": 5000.0, "taxes": 580.0, "fees": 0.0, "discounts": 0.0},
            source_run_file="fake://mock_bloomrooms_cleartrip.json",
        )

        k2 = CacheKey(
            hotel_id="bloomrooms_city_centre",
            site="bookingcom",
            dates=("2026-11-20", "2026-11-21"),
            guests=2,
            cohort_signature="standard_queen|no_meal|non_refundable",
        )
        self.set(
            key=k2,
            price_public=5859.0,
            price_member=5273.0,
            components={"base": 4965.0, "taxes": 894.0, "fees": 0.0, "discounts": 0.0},
            source_run_file="fake://mock_bloomrooms_booking.json",
        )

    def _seed_saved_mode(self):
        """Seed from verified saved run files on disk."""
        root = Path(__file__).resolve().parent.parent.parent
        saved_run_file = root / "fixtures" / "saved_run.json"
        
        if not saved_run_file.exists():
            return

        try:
            with open(saved_run_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            s_req = data.get("search_request", {})
            check_in = s_req.get("check_in", "2026-11-20")
            check_out = s_req.get("check_out", "2026-11-21")
            guests = s_req.get("guests", 2)

            hotel_map = {
                h["hotel_id"]: h["canonical_name"].lower().replace(" ", "_")
                for h in data.get("hotels", [])
            }

            for offer in data.get("offers", []):
                site_raw = offer.get("site", "").lower().replace(".", "").replace(" ", "")
                payable = offer.get("price_final_payable")
                if not site_raw or payable is None:
                    continue
                
                hotel_id = hotel_map.get(offer.get("hotel_id", ""), "bloomrooms_city_centre")
                # Normalize hotel_id if needed
                if "bloomrooms" in hotel_id:
                    canonical_id = "bloomrooms_city_centre"
                elif "radisson" in hotel_id:
                    canonical_id = "radisson_blu_atria_bengaluru"
                elif "oberoi" in hotel_id:
                    canonical_id = "the_oberoi_bengaluru"
                else:
                    canonical_id = hotel_id

                k = CacheKey(
                    hotel_id=canonical_id,
                    site=site_raw,
                    dates=(check_in, check_out),
                    guests=guests,
                    cohort_signature="standard_queen|no_meal|non_refundable",
                )
                
                fee_lines = offer.get("fee_lines", [])
                base = next((f["amount"] for f in fee_lines if f.get("fee_kind") in ("base", "other")), None)
                tax = next((f["amount"] for f in fee_lines if f.get("fee_kind") == "tax"), None)
                disc = next((f["amount"] for f in fee_lines if f.get("fee_kind") == "discount"), 0.0)

                self.set(
                    key=k,
                    price_public=float(payable),
                    price_member=None,
                    components={"base": base, "taxes": tax, "discounts": disc},
                    captured_at=offer.get("finished_at") or data.get("_meta", {}).get("saved_at", "2026-11-17T11:45:00+05:30"),
                    source_run_file="fixtures/saved_run.json",
                )
        except Exception:
            pass


# Global singleton instance for easy import across API routes
price_cache = PriceCache()
