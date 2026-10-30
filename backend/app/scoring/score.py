"""Scoring formula: weighted signals → criterion scores → total.

See PLAN.md §5.5 for the formula:
    criterion_score = Σ(weight_i × value_i) / Σ(weight_i)      over signals found
    coverage        = Σ(weight_i found) / Σ(weight_i possible)
    total           = Σ(cw_c × cs_c) / Σ(cw_c)   over criteria with coverage > 0
    confidence      = weighted mean of coverage across criteria
"""

from __future__ import annotations

from app.config import AppConfig
from app.scoring import CriterionScore, ScoreResult, SignalResult

# Signals that describe the country, not the company (countries.yaml baseline).
PRIOR_KEYS = frozenset({"english_baseline"})


def compute_scores(
    signals: list[SignalResult],
    config: AppConfig,
) -> ScoreResult:
    """Compute total score from a list of signals using config weights."""
    criterion_weights = config.criterion_weights
    signal_defs = config.signals

    # Group signals by criterion
    by_criterion: dict[str, list[SignalResult]] = {}
    for s in signals:
        by_criterion.setdefault(s.criterion, []).append(s)

    criteria: dict[str, CriterionScore] = {}

    for criterion, _cw in criterion_weights.items():
        criterion_signals = by_criterion.get(criterion, [])
        possible_weight = sum(sd.weight for sd in signal_defs.get(criterion, {}).values())

        if not criterion_signals or possible_weight == 0:
            criteria[criterion] = CriterionScore(
                criterion=criterion,
                score=0.0,
                coverage=0.0,
                signals=[],
            )
            continue

        found_weight = sum(s.weight for s in criterion_signals)
        weighted_sum = sum(s.weight * s.value for s in criterion_signals)
        score = weighted_sum / found_weight if found_weight > 0 else 0.0
        coverage = found_weight / possible_weight if possible_weight > 0 else 0.0

        criteria[criterion] = CriterionScore(
            criterion=criterion,
            score=round(score, 4),
            coverage=round(min(1.0, coverage), 4),
            signals=criterion_signals,
        )

    # Total: weighted mean of criterion scores where coverage > 0
    active = [
        (cw, criteria[c])
        for c, cw in criterion_weights.items()
        if criteria.get(c) and criteria[c].coverage > 0
    ]
    # A country prior says nothing about the company itself. Without at least one
    # company-specific signal the total stays unknown instead of echoing the prior
    # (a blocked US site would otherwise rank 100% on the US English baseline alone).
    has_company_evidence = any(
        s.key not in PRIOR_KEYS for s in signals if s.criterion in criterion_weights
    )
    if active and has_company_evidence:
        total_num = sum(cw * cs.score for cw, cs in active)
        total_den = sum(cw for cw, _ in active)
        total = round(total_num / total_den, 4) if total_den > 0 else None
    else:
        total = None

    # Confidence: weighted mean of coverage across all criteria
    all_cw = [(cw, criteria.get(c)) for c, cw in criterion_weights.items()]
    conf_num = sum(cw * (cs.coverage if cs else 0.0) for cw, cs in all_cw)
    conf_den = sum(cw for cw, _ in all_cw)
    confidence = round(conf_num / conf_den, 4) if conf_den > 0 else 0.0

    return ScoreResult(
        total=total,
        confidence=confidence,
        criteria=criteria,
        signals=signals,
    )
