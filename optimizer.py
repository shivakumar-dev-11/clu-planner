"""Greedy PTP-first insertion optimizer with marginal gain for optional visits."""

from __future__ import annotations

from typing import Dict, List

from constraints import (
    classify_best_failure,
    simulate_route,
    try_insertion_failure_reason,
)
from distance import DistanceContext
from models import Customer, Executive, PlanResult, RouteResult, UnvisitedCustomer


def _route_km(
    ex: Executive,
    route_ids: List[str],
    customers_by_id: Dict[str, Customer],
    dist_ctx: DistanceContext,
) -> float:
    res = simulate_route(ex, route_ids, customers_by_id, dist_ctx)
    return res.total_km if res.valid else float("inf")


def _sort_ptp(customers: List[Customer]) -> List[Customer]:
    ptp = [c for c in customers if c.ptp_today]
    ptp.sort(
        key=lambda c: (c.window_end_min, -c.priority_score, c.customer_id)
    )
    return ptp


def _sort_optional(customers: List[Customer]) -> List[Customer]:
    opt = [c for c in customers if not c.ptp_today]
    opt.sort(key=lambda c: (-c.priority_score, c.customer_id))
    return opt


def run_optimizer(
    executives: List[Executive],
    customers: List[Customer],
    dist_ctx: DistanceContext,
    lambda_value: float = 2.0,
) -> PlanResult:
    customers_by_id = {c.customer_id: c for c in customers}
    routes_map: Dict[str, List[str]] = {ex.executive_id: [] for ex in executives}
    unvisited: List[UnvisitedCustomer] = []
    scheduled: set[str] = set()

    def apply_insertion(eid: str, pos: int, cid: str) -> None:
        routes_map[eid] = (
            routes_map[eid][:pos] + [cid] + routes_map[eid][pos:]
        )
        scheduled.add(cid)

    for customer in _sort_ptp(customers):
        if customer.customer_id in scheduled:
            continue
        best = None
        best_delta = float("inf")
        best_eid = None
        best_pos = 0
        errors_all = []

        for ex in executives:
            eid = ex.executive_id
            route_ids = routes_map[eid]
            if len(route_ids) >= ex.max_visits:
                continue
            old_km = _route_km(ex, route_ids, customers_by_id, dist_ctx)

            for pos in range(len(route_ids) + 1):
                new_ids = route_ids[:pos] + [customer.customer_id] + route_ids[pos:]
                result = simulate_route(ex, new_ids, customers_by_id, dist_ctx)
                if not result.valid:
                    err = try_insertion_failure_reason(
                        ex, route_ids, customer, pos, customers_by_id, dist_ctx
                    )
                    if err:
                        errors_all.append(err)
                    continue
                delta_km = result.total_km - (old_km if route_ids else 0.0)
                tie = (delta_km, eid, customer.customer_id, pos)
                if best is None or tie < (best_delta, best_eid, customer.customer_id, best_pos):
                    best_delta = delta_km
                    best_eid = eid
                    best_pos = pos
                    best = True

        if best:
            apply_insertion(best_eid, best_pos, customer.customer_id)
        else:
            code, detail = classify_best_failure(errors_all)
            unvisited.append(
                UnvisitedCustomer(
                    customer_id=customer.customer_id,
                    ptp_today=True,
                    reason_code=code,
                    reason_detail=detail,
                )
            )

    for customer in _sort_optional(customers):
        if customer.customer_id in scheduled:
            continue
        best_feasible = False
        best_marginal = -float("inf")
        best_eid = None
        best_pos = 0
        best_delta = 0.0
        low_marginal_feasible = False
        errors_all = []

        for ex in executives:
            eid = ex.executive_id
            route_ids = routes_map[eid]
            if len(route_ids) >= ex.max_visits:
                continue
            old_km = _route_km(ex, route_ids, customers_by_id, dist_ctx)

            for pos in range(len(route_ids) + 1):
                new_ids = route_ids[:pos] + [customer.customer_id] + route_ids[pos:]
                result = simulate_route(ex, new_ids, customers_by_id, dist_ctx)
                if not result.valid:
                    err = try_insertion_failure_reason(
                        ex, route_ids, customer, pos, customers_by_id, dist_ctx
                    )
                    if err:
                        errors_all.append(err)
                    continue
                delta_km = result.total_km - (old_km if route_ids else 0.0)
                marginal = customer.priority_score - lambda_value * delta_km
                if marginal > 0:
                    tie = (-marginal, delta_km, eid, customer.customer_id)
                    if not best_feasible or tie < (
                        -best_marginal,
                        best_delta,
                        best_eid or "",
                        customer.customer_id,
                    ):
                        best_marginal = marginal
                        best_eid = eid
                        best_pos = pos
                        best_feasible = True
                        best_delta = delta_km
                else:
                    low_marginal_feasible = True

        if best_feasible:
            apply_insertion(best_eid, best_pos, customer.customer_id)
        elif low_marginal_feasible:
            unvisited.append(
                UnvisitedCustomer(
                    customer_id=customer.customer_id,
                    ptp_today=False,
                    reason_code="LOW_MARGINAL_VALUE",
                    reason_detail=(
                        "Skipped: added priority does not offset travel cost under λ"
                    ),
                )
            )
        else:
            code, detail = classify_best_failure(errors_all)
            unvisited.append(
                UnvisitedCustomer(
                    customer_id=customer.customer_id,
                    ptp_today=False,
                    reason_code=code,
                    reason_detail=detail,
                )
            )

    routes: List[RouteResult] = []
    for ex in executives:
        ids = routes_map[ex.executive_id]
        routes.append(simulate_route(ex, ids, customers_by_id, dist_ctx))

    return PlanResult(routes=routes, unvisited=unvisited, algorithm="heuristic")
