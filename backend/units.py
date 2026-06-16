"""Explicit GiB <-> GB conversion.

UNSEEN stores data caps in **GiB** (binary, 1024^3 bytes). Hiddify's API uses **GB**
(decimal, 1000^3 bytes) in `usage_limit_GB` / `current_usage_GB`. These differ by ~7.4%,
so we convert deliberately at the Hiddify boundary (never pass a GiB number as GB).

  1 GiB = 1024^3 bytes ;  1 GB = 1000^3 bytes  ;  1 GiB = 1.073741824 GB
"""
from __future__ import annotations

_GIB = 1024 ** 3
_GB = 1000 ** 3
GIB_PER_GB = _GB / _GIB          # ~0.931
GB_PER_GIB = _GIB / _GB          # ~1.073741824


def gib_to_gb(gib: float) -> float:
    """Convert UNSEEN GiB cap to the GB value Hiddify expects (rounded to 0.01 GB)."""
    return round(gib * GB_PER_GIB, 2)


def gb_to_gib(gb: float) -> float:
    """Convert a Hiddify GB usage value back to GiB for UNSEEN-side display/accounting."""
    return round(gb * GIB_PER_GB, 4)
