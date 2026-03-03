"""Shared constants, color palettes, and helper functions."""

from __future__ import annotations

REGION_LABELS: dict[str, str] = {
    "EU_EUR": "Europe & Eurasia",
    "MENA":   "Middle East & N. Africa",
    "SSA":    "Sub-Saharan Africa",
    "SCA":    "South & Central Asia",
    "EAP":    "East Asia & Pacific",
    "AME":    "Americas",
    "GLO":    "Global / Multilateral",
}

REGION_COLORS: dict[str, str] = {
    "EU_EUR": "#3B82F6",
    "MENA":   "#F59E0B",
    "SSA":    "#10B981",
    "SCA":    "#8B5CF6",
    "EAP":    "#EC4899",
    "AME":    "#F97316",
    "GLO":    "#6B7280",
}

EVENT_TYPE_COLORS: dict[str, str] = {
    "Battles":                      "#EF4444",
    "Explosions/Remote violence":   "#F97316",
    "Violence against civilians":   "#DC2626",
    "Protests":                     "#3B82F6",
    "Riots":                        "#8B5CF6",
    "Strategic developments":       "#6B7280",
}

ACTION_TYPE_COLORS: dict[str, str] = {
    "sanction":          "#EF4444",
    "withdrawal":        "#F97316",
    "diplomacy":         "#3B82F6",
    "conflict_onset":    "#DC2626",
    "conflict_event":    "#B91C1C",
    "governance_shock":  "#8B5CF6",
    "alliance":          "#10B981",
    "treaty":            "#06B6D4",
    "recognition":       "#F59E0B",
    "governance_change": "#A78BFA",
    "social_unrest":     "#FB923C",
    "global_shock":      "#6B7280",
    "atrocity_warning":  "#7C3AED",
}

DRIVER_WEIGHTS: dict[str, float] = {
    "conflict_incidents":  0.225,
    "conflict_fatalities": 0.225,
    "sanctions":           0.20,
    "militarization":      0.15,
    "news_tension":        0.10,
}

DRIVER_LABELS: dict[str, str] = {
    "conflict_incidents":  "Conflict (incidents)",
    "conflict_fatalities": "Conflict (fatalities)",
    "sanctions":           "Sanctions",
    "militarization":      "Militarization",
    "news_tension":        "News tension",
}


def grs_band(score: float | None) -> tuple[str, str]:
    """Return (label, hex_color) for a GRS score."""
    if score is None:
        return "No data", "#475569"
    if score < 15:
        return "Low",      "#22C55E"
    if score < 30:
        return "Moderate", "#EAB308"
    if score < 50:
        return "Elevated", "#F97316"
    return "High",         "#EF4444"


def fmt_number(n: float | None, decimals: int = 0) -> str:
    if n is None:
        return "–"
    return f"{n:,.{decimals}f}"
