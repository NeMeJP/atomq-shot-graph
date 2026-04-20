"""Tests for adapted QCoDeS-style ParameterCache."""
from __future__ import annotations

import time

import pytest

from yaqumo_shot_graph.ir.parameter import ParameterCache


def test_cache_invalid_by_default() -> None:
    c: ParameterCache[float] = ParameterCache()
    assert not c.valid
    with pytest.raises(RuntimeError, match="invalid"):
        c.get()


def test_cache_valid_after_set() -> None:
    c: ParameterCache[float] = ParameterCache()
    c.set(3.14)
    assert c.valid
    assert c.get() == 3.14


def test_cache_initial_value_is_valid() -> None:
    c = ParameterCache[int](initial=42)
    assert c.valid
    assert c.get() == 42


def test_cache_age_increases_over_time() -> None:
    c: ParameterCache[int] = ParameterCache()
    c.set(1)
    time.sleep(0.01)
    assert c.age_s >= 0.01


def test_cache_ttl_expired_raises() -> None:
    c: ParameterCache[int] = ParameterCache()
    c.set(1)
    time.sleep(0.02)
    with pytest.raises(RuntimeError, match="stale"):
        c.get(max_val_age_s=0.005)


def test_cache_fresh_within_ttl_returns() -> None:
    c: ParameterCache[int] = ParameterCache()
    c.set(99)
    assert c.get(max_val_age_s=10.0) == 99


def test_cache_invalidate_drops_validity() -> None:
    c: ParameterCache[int] = ParameterCache()
    c.set(1)
    c.invalidate()
    assert not c.valid


def test_cache_get_or_falls_back() -> None:
    c: ParameterCache[int] = ParameterCache()
    assert c.get_or(default=-1) == -1
    c.set(5)
    assert c.get_or(default=-1) == 5
