"""Baseline planner: nearest executive + ID order until max_visits."""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List

from constraints import simulate_route
from distance import DistanceContext
from models import Customer, Executive, PlanResult, RouteResult, UnvisitedCustomer


def run_baseline(
    executives: List[Executive],
    customers: List[Customer],
    dist_ctx: DistanceContext,
) -> PlanResult:
    customers_by_id = {c.customer_id: c for c in customers}
    assignments: Dict[str, List[str]] = defaultdict(list)

    for cu in customers:
        best_eid = None
        best_km = float("inf")
        for ex in executives:
            km = dist_ctx.km_exec_to_customer(ex.executive_id, cu.customer_id)
            if km < best_km:
                best_km = km
                best_eid = ex.executive_id
        if best_eid:
            assignments[best_eid].append(cu.customer_id)

    for eid in assignments:
        assignments[eid].sort()

    routes: List[RouteResult] = []
    scheduled: set[str] = set()
    unvisited: List[UnvisitedCustomer] = []

    for ex in executives:
        assigned = assignments.get(ex.executive_id, [])
        route_ids: List[str] = []

        for cid in assigned:
            if len(route_ids) >= ex.max_visits:
                cu = customers_by_id[cid]
                unvisited.append(
                    UnvisitedCustomer(
                        customer_id=cid,
                        ptp_today=cu.ptp_today,
                        reason_code="CAPACITY_FULL",
                        reason_detail="Baseline: executive at max_visits",
                    )
                )
                continue
            trial = route_ids + [cid]
            result = simulate_route(ex, trial, customers_by_id, dist_ctx)
            if result.valid:
                route_ids.append(cid)
            else:
                cu = customers_by_id[cid]
                code = result.rejection_reason or "NO_FEASIBLE_INSERTION"
                unvisited.append(
                    UnvisitedCustomer(
                        customer_id=cid,
                        ptp_today=cu.ptp_today,
                        reason_code=code,
                        reason_detail=f"Baseline route invalid after adding {cid}",
                    )
                )

        final = simulate_route(ex, route_ids, customers_by_id, dist_ctx)
        routes.append(final)
        scheduled.update(route_ids)

    scheduled_in_unvisited = {u.customer_id for u in unvisited}
    for cu in customers:
        if cu.customer_id not in scheduled and cu.customer_id not in scheduled_in_unvisited:
            unvisited.append(
                UnvisitedCustomer(
                    customer_id=cu.customer_id,
                    ptp_today=cu.ptp_today,
                    reason_code="NO_FEASIBLE_INSERTION",
                    reason_detail="Not scheduled by baseline heuristic",
                )
            )

    return PlanResult(routes=routes, unvisited=unvisited, algorithm="baseline")
