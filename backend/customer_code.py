"""Gap-safe public customer code generation.

Uses **max(id)+1**, not count+1, so deleting a customer never causes a future code to
collide with an existing one. Code = PREFIX + zero-padded number (e.g. UP0001).
The width is advisory: numbers beyond the width simply render with more digits.
"""
from __future__ import annotations

import sqlite3


def format_code(n: int, prefix: str = "UP", width: int = 4) -> str:
    return f"{prefix}{n:0{width}d}"


def next_public_customer_code(conn: sqlite3.Connection, prefix: str = "UP", width: int = 4) -> str:
    """Next code based on max customer id + 1 (gap-safe)."""
    row = conn.execute("SELECT COALESCE(MAX(id), 0) FROM customers").fetchone()
    return format_code(int(row[0]) + 1, prefix=prefix, width=width)


def assign_code_for_id(customer_id: int, prefix: str = "UP", width: int = 4) -> str:
    """Deterministic code for a known customer id (id IS the gap-safe sequence)."""
    return format_code(int(customer_id), prefix=prefix, width=width)
