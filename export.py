"""CSV export helpers."""

from __future__ import annotations

import io
from typing import Dict, List, Optional

import pandas as pd

from data_io import minutes_to_hhmm
from google_maps_ui import google_maps_url
from models import Customer, PlanResult, customer_display_address


def plan_to_dataframe(
    plan: PlanResult,
    customers_by_id: Optional[Dict[str, Customer]] = None,
) -> pd.DataFrame:
    rows = []
    for route in plan.routes:
        if not route.valid and not route.stops:
            continue
        for seq, stop in enumerate(route.stops, start=1):
            row = {
                "executive_id": route.executive.executive_id,
                "seq": seq,
                "customer_id": stop.customer_id,
                "arrival_time": minutes_to_hhmm(stop.visit_start_min),
                "physical_arrival_time": minutes_to_hhmm(
                    stop.physical_arrival_min
                ),
                "wait_min": stop.wait_min,
                "km_from_prev": round(stop.leg_km, 4),
                "cumulative_km": round(stop.cumulative_km, 4),
            }
            if customers_by_id and stop.customer_id in customers_by_id:
                cu = customers_by_id[stop.customer_id]
                addr = customer_display_address(
                    cu.customer_id, cu.area, cu.address, cu.lat, cu.lon
                )
                row["address"] = addr
                row["google_maps"] = google_maps_url(cu.lat, cu.lon, addr)
            rows.append(row)
    return pd.DataFrame(rows)


def unvisited_to_dataframe(plan: PlanResult) -> pd.DataFrame:
    rows = [
        {
            "customer_id": u.customer_id,
            "ptp_today": int(u.ptp_today),
            "reason_code": u.reason_code,
            "reason_detail": u.reason_detail,
        }
        for u in plan.unvisited
    ]
    return pd.DataFrame(rows)


def route_summary_dataframe(plan: PlanResult) -> pd.DataFrame:
    rows = []
    for route in plan.routes:
        visits = len(route.customer_ids)
        priority = 0.0
        rows.append(
            {
                "executive_id": route.executive.executive_id,
                "visits": visits,
                "route_km_including_return": round(route.total_km, 4),
                "return_time": minutes_to_hhmm(route.return_time_min),
                "valid": route.valid,
            }
        )
    return pd.DataFrame(rows)


def dataframe_to_csv_bytes(df: pd.DataFrame) -> bytes:
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8")
