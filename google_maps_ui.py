"""Google Maps links and embeds (no API key required)."""

from __future__ import annotations

from typing import List, Optional
from urllib.parse import quote

import streamlit.components.v1 as components

from models import Customer, customer_display_address


def google_maps_url(lat: float, lon: float, query: Optional[str] = None) -> str:
    if query:
        return f"https://www.google.com/maps/search/?api=1&query={quote(query)}"
    return f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"


def google_maps_directions_url(
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float,
) -> str:
    return (
        "https://www.google.com/maps/dir/?api=1"
        f"&origin={origin_lat},{origin_lon}"
        f"&destination={dest_lat},{dest_lon}"
        "&travelmode=driving"
    )


def google_maps_route_url(
    office_lat: float,
    office_lon: float,
    customers_ordered: List[Customer],
    return_to_office: bool = True,
) -> str:
    """Multi-stop directions in Google Maps (opens in browser/app)."""
    parts = [f"{office_lat},{office_lon}"]
    for cu in customers_ordered:
        parts.append(f"{cu.lat},{cu.lon}")
    if return_to_office and customers_ordered:
        parts.append(f"{office_lat},{office_lon}")
    return "https://www.google.com/maps/dir/" + "/".join(parts)


def google_maps_embed_customer(lat: float, lon: float, height: int = 360) -> None:
    src = f"https://maps.google.com/maps?q={lat},{lon}&hl=en&z=15&output=embed"
    components.iframe(src, height=height)


def customers_for_executive_plan(
    plan,
    customers_by_id: dict,
    executive_id: str,
) -> List[Customer]:
    ordered: List[Customer] = []
    for route in plan.routes:
        if route.executive.executive_id != executive_id:
            continue
        for cid in route.customer_ids:
            if cid in customers_by_id:
                ordered.append(customers_by_id[cid])
    return ordered
