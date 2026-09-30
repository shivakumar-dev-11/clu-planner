"""Normalized data models for Clu Daily Visit Planner."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ValidationIssue:
    row: int
    field: str
    value: str
    reason: str


@dataclass
class Executive:
    executive_id: str
    office_name: str
    office_address: str
    home_lat: float
    home_lon: float
    shift_start_min: int
    shift_end_min: int
    max_visits: int
    max_km: float


def customer_display_address(
    customer_id: str,
    area: Optional[str],
    address: Optional[str],
    lat: float,
    lon: float,
) -> str:
    if address and str(address).strip():
        return str(address).strip()
    if area:
        return f"{area}, Hyderabad, Telangana, India"
    return f"{customer_id} — {lat:.5f}, {lon:.5f}"


@dataclass
class Customer:
    customer_id: str
    area: Optional[str]
    address: Optional[str]
    lat: float
    lon: float
    dpd: Optional[int]
    overdue_amount: Optional[float]
    priority_score: float
    ptp_today: bool
    window_start_min: int
    window_end_min: int
    service_min: int


@dataclass
class StopDetail:
    customer_id: str
    physical_arrival_min: int
    visit_start_min: int
    visit_end_min: int
    wait_min: int
    leg_km: float
    cumulative_km: float


@dataclass
class RouteResult:
    executive: Executive
    customer_ids: List[str]
    stops: List[StopDetail]
    total_km: float
    return_time_min: int
    valid: bool
    rejection_reason: Optional[str] = None


@dataclass
class UnvisitedCustomer:
    customer_id: str
    ptp_today: bool
    reason_code: str
    reason_detail: str


@dataclass
class PlanResult:
    routes: List[RouteResult]
    unvisited: List[UnvisitedCustomer]
    algorithm: str = "heuristic"


@dataclass
class RunMetrics:
    score: float
    total_km: float
    scheduled_count: int
    unvisited_count: int
    priority_coverage_pct: Optional[float]
    ptp_hit_rate_pct: Optional[float]
    constraint_violations: int
    total_priority_scheduled: float
    total_priority_all: float
    ptp_scheduled: int
    ptp_total: int
