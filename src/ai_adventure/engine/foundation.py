"""Foundation meters: stability (0–100) and legacy quality tier (1–6).

Phase 2 resolution
------------------
* ``foundation_stability`` is the authoritative play meter (0–100).
* ``foundation_quality`` is the legacy Milestone 3 / Boundless story axis (1–6).

Quality is treated as a **derived tier** of stability for display and
compatibility. Story events that historically mutated quality (Boundless path
commit) still update the stored quality column, then re-sync from stability
when needed so both remain coherent.
"""

from __future__ import annotations

from ai_adventure.engine.constants import (
    FOUNDATION_QUALITY_BANDS,
    FOUNDATION_STABILITY_MAX,
    FOUNDATION_STABILITY_MIN,
)

# Stability thresholds mapped onto legacy quality tiers 1–6.
_STABILITY_TO_QUALITY: list[tuple[int, int]] = [
    (0, 1),
    (20, 2),
    (40, 3),
    (60, 4),
    (80, 5),
    (95, 6),
]


def clamp_stability(value: int) -> int:
    """Clamp foundation stability into 0–100."""

    return max(FOUNDATION_STABILITY_MIN, min(FOUNDATION_STABILITY_MAX, value))


def quality_tier_from_stability(stability: int) -> int:
    """Derive legacy foundation_quality (1–6) from foundation_stability."""

    tier = 1
    for threshold, quality in _STABILITY_TO_QUALITY:
        if clamp_stability(stability) >= threshold:
            tier = quality
    return tier


def sync_foundation_quality(stability: int, current_quality: int) -> int:
    """Return quality that respects derived tier without dropping Boundless bumps.

    Uses ``max(derived_tier, current_quality)`` so a Boundless path commit that
    raised quality is not erased by a mid-range stability value.
    """

    derived = quality_tier_from_stability(stability)
    return max(derived, current_quality)


def foundation_quality_label(value: int) -> str:
    """Map internal foundation quality to a qualitative band."""

    label = FOUNDATION_QUALITY_BANDS[0][1]
    for threshold, band in FOUNDATION_QUALITY_BANDS:
        if value >= threshold:
            label = band
    return label
