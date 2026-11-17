"""Tests for Price Cache Service."""
import pytest
from datetime import datetime, timezone, timedelta
from api.services.cache import (
    CacheKey,
    PriceCache,
    PriceCacheEntry,
    PriceComponents,
    calculate_ttl_seconds,
)


def test_cache_key_equality_and_hashing():
    k1 = CacheKey(
        hotel_id="bloomrooms_city_centre",
        site="bookingcom",
        dates=("2026-11-20", "2026-11-21"),
        guests=2,
        cohort_signature="standard_queen",
    )
    k2 = CacheKey(
        hotel_id="bloomrooms_city_centre",
        site="bookingcom",
        dates=("2026-11-20", "2026-11-21"),
        guests=2,
        cohort_signature="standard_queen",
    )
    k3 = CacheKey(
        hotel_id="bloomrooms_city_centre",
        site="cleartrip",
        dates=("2026-11-20", "2026-11-21"),
        guests=2,
        cohort_signature="standard_queen",
    )
    assert k1 == k2
    assert hash(k1) == hash(k2)
    assert k1 != k3


def test_ttl_calculation_by_date_proximity():
    as_of = datetime(2026, 11, 17, 12, 0, 0, tzinfo=timezone.utc)

    # 1. <= 3 days out (e.g. 2026-11-20 is 3 days out): TTL = 15 min (900s)
    ttl_close = calculate_ttl_seconds("2026-11-20", as_of=as_of)
    assert ttl_close == 900

    # 2. 4 to 7 days out (e.g. 2026-11-23 is 6 days out): TTL = 1 hour (3600s)
    ttl_medium = calculate_ttl_seconds("2026-11-23", as_of=as_of)
    assert ttl_medium == 3600

    # 3. > 7 days out (e.g. 2026-11-27 is 10 days out): TTL = 6 hours (21600s)
    ttl_far = calculate_ttl_seconds("2026-11-27", as_of=as_of)
    assert ttl_far == 21600


def test_freshness_lifecycle():
    key = CacheKey(
        hotel_id="test_hotel",
        site="test_site",
        dates=("2026-11-20", "2026-11-21"),
    )
    capture_time = datetime(2026, 11, 17, 12, 0, 0, tzinfo=timezone.utc)
    entry = PriceCacheEntry(
        key=key,
        price_public=1000.0,
        price_member=900.0,
        captured_at=capture_time.isoformat(),
        ttl_seconds=900,  # 15 minutes
    )

    # Within 15 minutes -> fresh
    t_fresh = capture_time + timedelta(minutes=10)
    assert entry.get_freshness(now=t_fresh) == "fresh"

    # Between 15 and 30 minutes -> stale
    t_stale = capture_time + timedelta(minutes=20)
    assert entry.get_freshness(now=t_stale) == "stale"

    # After 30 minutes -> expired
    t_expired = capture_time + timedelta(minutes=35)
    assert entry.get_freshness(now=t_expired) == "expired"


import asyncio

def test_price_cache_read_through_and_recheck_hook():
    async def _run_test():
        cache = PriceCache(mode="none")
        key = CacheKey(
            hotel_id="radisson_blu_atria_bengaluru",
            site="bookingcom",
            dates=("2026-11-20", "2026-11-21"),
            guests=2,
            cohort_signature="superior_room",
        )

        fetch_call_count = 0

        async def mock_fetch(k: CacheKey) -> PriceCacheEntry:
            nonlocal fetch_call_count
            fetch_call_count += 1
            return PriceCacheEntry(
                key=k,
                price_public=10620.0,
                price_member=9558.0,
                components=PriceComponents(base=9000.0, taxes=1620.0, fees=0.0, discounts=0.0),
                captured_at=datetime.now(timezone.utc).isoformat(),
                source_run_file="test_run.json",
                ttl_seconds=900,
            )

        # 1. Cache miss -> calls fetch_fn
        entry, freshness = await cache.get_or_fetch(key, fetch_fn=mock_fetch)
        assert fetch_call_count == 1
        assert freshness == "fresh"
        assert entry.price_public == 10620.0
        assert entry.price_member == 9558.0

        # 2. Cache hit (fresh) -> does not call fetch_fn
        entry2, freshness2 = await cache.get_or_fetch(key, fetch_fn=mock_fetch)
        assert fetch_call_count == 1
        assert freshness2 == "fresh"
        assert entry2.price_public == 10620.0

        # 3. Cache entry becomes stale -> recheck hook is triggered
        stale_time = datetime.now(timezone.utc) + timedelta(minutes=20)
        hook_called = False

        def on_stale(k, e):
            nonlocal hook_called
            hook_called = True

        cache.recheck_hook = on_stale
        entry3, freshness3 = await cache.get_or_fetch(key, now=stale_time)
        assert freshness3 == "stale"
        assert hook_called is True

    asyncio.run(_run_test())


def test_price_cache_fake_mode():
    cache = PriceCache(mode="fake")
    k = CacheKey(
        hotel_id="bloomrooms_city_centre",
        site="bookingcom",
        dates=("2026-11-20", "2026-11-21"),
        guests=2,
        cohort_signature="standard_queen|no_meal|non_refundable",
    )
    res = cache.get(k)
    assert res is not None
    entry, freshness = res
    assert entry.price_public == 5859.0
    assert entry.price_member == 5273.0


def test_price_cache_saved_mode():
    cache = PriceCache(mode="saved")
    k = CacheKey(
        hotel_id="bloomrooms_city_centre",
        site="bookingcom",
        dates=("2026-11-20", "2026-11-21"),
        guests=2,
        cohort_signature="standard_queen|no_meal|non_refundable",
    )
    res = cache.get(k)
    assert res is not None
    entry, _ = res
    assert entry.price_public == 5859.0
