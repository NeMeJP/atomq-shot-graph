"""Cached parameter with TTL — for slow-varying lab state (laser locks, MOT readiness).

Adapted from QCoDeS' ``ParameterBase._Cache`` pattern (MIT License, Copyright
(c) 2015-2023 Microsoft Corporation and Københavns Universitet):
https://github.com/QCoDeS/Qcodes/blob/main/src/qcodes/parameters/cache.py

The full MIT license text is in THIRD_PARTY_NOTICES.md. We keep only the
minimal TTL-aware value cache (roughly lines 140–190 of the upstream file),
dropped of the Station/Instrument coupling that QCoDeS layers on top.

Intent: any slow-varying quantity in a neutral-atom shot cycle — fiber MZI
lock status, MOT fill probability, laser wavelength readback — is expensive
to re-query every shot. ParameterCache exposes a bounded-staleness read
(``get(max_val_age_s=0.1)`` → use cached value if fresher than 100 ms).
"""
from __future__ import annotations

import time
from typing import Generic, TypeVar

T = TypeVar("T")


class ParameterCache(Generic[T]):
    """Single-valued TTL cache with explicit invalidation.

    Attribution: adapted from QCoDeS ParameterBase._Cache (MIT).
    """

    def __init__(self, initial: T | None = None) -> None:
        self._value: T | None = initial
        self._timestamp: float = time.monotonic() if initial is not None else 0.0
        self._valid: bool = initial is not None

    def set(self, value: T) -> None:
        self._value = value
        self._timestamp = time.monotonic()
        self._valid = True

    def invalidate(self) -> None:
        self._valid = False

    @property
    def valid(self) -> bool:
        return self._valid

    @property
    def age_s(self) -> float:
        if not self._valid:
            return float("inf")
        return time.monotonic() - self._timestamp

    def get(self, max_val_age_s: float | None = None) -> T:
        """Return cached value if fresh enough; raise otherwise.

        Raises ``RuntimeError`` if the cache is invalid or exceeds max age.
        """
        if not self._valid or self._value is None:
            raise RuntimeError("ParameterCache invalid — no value set or explicitly invalidated")
        if max_val_age_s is not None and self.age_s > max_val_age_s:
            raise RuntimeError(
                f"ParameterCache stale: age {self.age_s * 1000:.1f} ms > "
                f"max_val_age {max_val_age_s * 1000:.1f} ms"
            )
        return self._value

    def get_or(self, default: T, max_val_age_s: float | None = None) -> T:
        """Return cached value if fresh, else ``default`` — never raises."""
        try:
            return self.get(max_val_age_s=max_val_age_s)
        except RuntimeError:
            return default


__all__ = ["ParameterCache"]
