"""Route simulator and plan validation — single source of truth for feasibility."""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

from distance import DistanceContext, EPS_KM, travel_minutes
from models import (
    Customer,
    Executive,
    PlanResult,
    RouteResult,
    StopDetail,
    UnvisitedCustomer,
)


class SimulationError:
    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail


def simulate_route(
    executive: Executive,
    customer_ids: List[str],
    customers_by_id: Dict[str, Customer],
    dist_ctx: DistanceContext,
) -> RouteResult:
    current_lat = executive.home_lat
    current_lon = executive.home_lon
    current_time = float(executive.shift_start_min)
    total_km = 0.0
    stops: List[StopDetail] = []
    prev_id: Optional[str] = None

    if len(customer_ids) > executive.max_visits:
        return RouteResult(
            executive=executive,
            customer_ids=customer_ids,
            stops=[],
            total_km=0.0,
            return_time_min=0,
            valid=False,
            rejection_reason="CAPACITY_FULL",
        )

    if not customer_ids:
        return RouteResult(
            executive=executive,
            customer_ids=[],
            stops=[],
            total_km=0.0,
            return_time_min=int(executive.shift_start_min),
            valid=True,
        )

    for cid in customer_ids:
        if cid not in customers_by_id:
            return RouteResult(
                executive=executive,
                customer_ids=customer_ids,
                stops=[],
                total_km=0.0,
                return_time_min=0,
                valid=False,
                rejection_reason="INVALID_INPUT",
            )
        cu = customers_by_id[cid]
        if prev_id is None:
            leg_km = dist_ctx.km_exec_to_customer(executive.executive_id, cid)
        else:
            leg_km = dist_ctx.km_customer_to_customer(prev_id, cid)

        travel = travel_minutes(leg_km)
        physical_arrival = current_time + travel
        visit_start = max(physical_arrival, float(cu.window_start_min))
        wait = visit_start - physical_arrival
        visit_end = visit_start + cu.service_min

        if visit_start > cu.window_end_min + EPS_KM:
            return RouteResult(
                executive=executive,
                customer_ids=customer_ids,
                stops=stops,
                total_km=total_km,
                return_time_min=int(current_time),
                valid=False,
                rejection_reason="TIME_WINDOW",
            )
        if visit_end > cu.window_end_min + EPS_KM:
            return RouteResult(
                executive=executive,
                customer_ids=customer_ids,
                stops=stops,
                total_km=total_km,
                return_time_min=int(current_time),
                valid=False,
                rejection_reason="TIME_WINDOW",
            )

        total_km += leg_km
        cumulative = total_km
        stops.append(
            StopDetail(
                customer_id=cid,
                physical_arrival_min=int(round(physical_arrival)),
                visit_start_min=int(round(visit_start)),
                visit_end_min=int(round(visit_end)),
                wait_min=int(round(wait)),
                leg_km=leg_km,
                cumulative_km=cumulative,
            )
        )
        current_time = visit_end
        current_lat = cu.lat
        current_lon = cu.lon
        prev_id = cid

    return_km = dist_ctx.km_customer_to_point(
        prev_id, executive.home_lat, executive.home_lon
    ) if prev_id else 0.0
    if prev_id is None:
        return_km = 0.0
        return_time = int(round(current_time))
    else:
        return_time_f = current_time + travel_minutes(return_km)
        return_time = int(round(return_time_f))
        total_km += return_km

    if total_km > executive.max_km + EPS_KM:
        return RouteResult(
            executive=executive,
            customer_ids=customer_ids,
            stops=stops,
            total_km=total_km,
            return_time_min=return_time,
            valid=False,
            rejection_reason="MAX_KM",
        )
    if return_time > executive.shift_end_min:
        return RouteResult(
            executive=executive,
            customer_ids=customer_ids,
            stops=stops,
            total_km=total_km,
            return_time_min=return_time,
            valid=False,
            rejection_reason="SHIFT_END",
        )

    return RouteResult(
        executive=executive,
        customer_ids=customer_ids,
        stops=stops,
        total_km=total_km,
        return_time_min=return_time,
        valid=True,
    )


def try_insertion_failure_reason(
    executive: Executive,
    route_ids: List[str],
    customer: Customer,
    insert_at: int,
    customers_by_id: Dict[str, Customer],
    dist_ctx: DistanceContext,
) -> Optional[SimulationError]:
    new_ids = route_ids[:insert_at] + [customer.customer_id] + route_ids[insert_at:]
    result = simulate_route(executive, new_ids, customers_by_id, dist_ctx)
    if result.valid:
        return None
    code = result.rejection_reason or "NO_FEASIBLE_INSERTION"
    return SimulationError(code, f"Insertion at {insert_at} failed: {code}")


def classify_best_failure(
    errors: List[SimulationError],
) -> Tuple[str, str]:
    priority = [
        "TIME_WINDOW",
        "SHIFT_END",
        "MAX_KM",
        "CAPACITY_FULL",
        "TOO_FAR",
        "NO_FEASIBLE_INSERTION",
    ]
    codes = {e.code for e in errors}
    for p in priority:
        if p in codes:
            match = next(e for e in errors if e.code == p)
            return match.code, match.detail
    if errors:
        return errors[0].code, errors[0].detail
    return "NO_FEASIBLE_INSERTION", "No feasible insertion was found by the heuristic."


def final_validate_plan(
    plan: PlanResult,
    all_customer_ids: Set[str],
    customers_by_id: Dict[str, Customer],
    dist_ctx: DistanceContext,
) -> int:
    """Return count of constraint violations (0 = valid)."""
    violations = 0
    scheduled: Set[str] = set()
    unvisited_ids = {u.customer_id for u in plan.unvisited}

    for route in plan.routes:
        if not route.valid:
            violations += 1
        for cid in route.customer_ids:
            if cid in scheduled:
                violations += 1
            scheduled.add(cid)
        resim = simulate_route(
            route.executive,
            route.customer_ids,
            customers_by_id,
            dist_ctx,
        )
        if not resim.valid:
            violations += 1
        if resim.total_km > route.executive.max_km + EPS_KM:
            violations += 1
        if resim.return_time_min > route.executive.shift_end_min:
            violations += 1

    if scheduled & unvisited_ids:
        violations += len(scheduled & unvisited_ids)
    if scheduled | unvisited_ids != all_customer_ids:
        violations += 1
    if len(scheduled) != len(set(scheduled)):
        violations += 1

    return violations
