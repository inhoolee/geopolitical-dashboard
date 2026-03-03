"""Deterministic UUID generation for idempotent pipeline runs."""

import hashlib
import uuid


def make_uuid(*parts: str) -> str:
    """Generate a stable UUID5-style string from concatenated parts."""
    key = "|".join(str(p) for p in parts if p is not None)
    hex_digest = hashlib.sha256(key.encode()).hexdigest()
    # Format as UUID (8-4-4-4-12)
    return str(uuid.UUID(hex=hex_digest[:32]))
