"""UNSEEN PROXY backend package (Phase 4A foundation).

Stdlib-only (sqlite3 / urllib / unittest) so it runs on the control-plane Master with
no extra dependencies. No business values are hardcoded here — plans/regions/protocols/
nodes live in the DB (see backend.seed); secrets come from the environment by handle
(see backend.config), never from source.
"""
__all__ = ["config", "db", "migrate", "seed", "units", "customer_code"]
