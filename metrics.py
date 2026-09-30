"""Plan metrics — single source of truth for dashboard and exports."""

from __future__ import annotations

from typing import Dict, List, Optional

from constraints import final_validate_plan
from distance import DistanceContext
from models import Customer, PlanResult, RunMetrics


def compute_metrics(
    plan: PlanResult,
    customers: List[Customer],
    dist_ctx: DistanceContext,
    lambda_value: float = 2.0,
) -> RunMetrics:
    customers_by_id = {c.customer_id: c for c in customers}
    all_ids = {c.customer_id for c in customers}

    total_priority_all = sum(c.priority_score for c in customers)
    ptp_total = sum(1 for c in customers if c.ptp_today)

    scheduled_ids: List[str] = []
    total_km = 0.0
    total_priority_scheduled = 0.0
    ptp_scheduled = 0

    for route in plan.routes:
        if route.valid:
            total_km += route.total_km
        for cid in route.customer_ids:
            scheduled_ids.append(cid)
            cu = customers_by_id[cid]
            total_priority_scheduled += cu.priority_score
            if cu.ptp_today:
                ptp_scheduled += 1

    score = total_priority_scheduled - lambda_value * total_km

    if total_priority_all > 0:
        priority_coverage = 100.0 * total_priority_scheduled / total_priority_all
    else:
        priority_coverage = None

    if ptp_total > 0:
        ptp_hit = 100.0 * ptp_scheduled / ptp_total
    else:
        ptp_hit = None

    violations = final_validate_plan(plan, all_ids, customers_by_id, dist_ctx)

    return RunMetrics(
        score=score,
        total_km=total_km,
        scheduled_count=len(scheduled_ids),
        unvisited_count=len(plan.unvisited),
        priority_coverage_pct=priority_coverage,
        ptp_hit_rate_pct=ptp_hit,
        constraint_violations=violations,
        total_priority_scheduled=total_priority_scheduled,
        total_priority_all=total_priority_all,
        ptp_scheduled=ptp_scheduled,
        ptp_total=ptp_total,
    )
