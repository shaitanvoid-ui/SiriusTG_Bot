"""Explainable weighted rules; no trained model or Telegram account-age inference."""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from collections.abc import Mapping, Sequence


STRONG_SIGNALS = frozenset({"honeypot_promo", "honeypot_task"})


@dataclass(frozen=True)
class RiskResult:
    score: int
    reasons: tuple[tuple[str, int], ...]
    strong_signals: tuple[str, ...]
    should_shadow: bool


def regular_click_pattern(times_ms: Sequence[int], *, minimum: int, variation_permille: int) -> bool:
    """Low variation is weak evidence only; human timers/accessibility can look regular."""
    if len(times_ms) < minimum:
        return False
    intervals = [b - a for a, b in zip(times_ms, times_ms[1:])]
    if not intervals or any(value <= 0 for value in intervals):
        return False
    mean = sum(intervals) / len(intervals)
    deviation = sqrt(sum((value - mean) ** 2 for value in intervals) / len(intervals))
    return deviation * 1000 <= mean * variation_permille


def score_rules(signals: Mapping[str, bool], weights: Mapping[str, int], *, threshold: int) -> RiskResult:
    reasons = tuple(sorted(
        (name, max(0, min(100, int(weights.get(name, 0)))))
        for name, present in signals.items() if present
    ))
    score = max(0, min(100, sum(weight for _, weight in reasons)))
    strong = tuple(name for name, weight in reasons if name in STRONG_SIGNALS and weight > 0)
    return RiskResult(score, reasons, strong, score > threshold and bool(strong))
