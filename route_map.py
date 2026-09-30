"""Multi-stop route map (office + customers) — no API key required."""

from __future__ import annotations

from typing import Dict, List, Optional, Set

import folium
import streamlit as st
import streamlit.components.v1 as components
from streamlit_folium import st_folium

from google_maps_ui import google_maps_route_url, google_maps_url
from models import Customer, Executive, PlanResult, customer_display_address


def _office_label(ex: Executive) -> str:
    return f"{ex.office_name} ({ex.executive_id})"


def build_route_map(
    plan: PlanResult,
    customers_by_id: Dict[str, Customer],
    filter_exec_ids: Optional[Set[str]] = None,
) -> Optional[folium.Map]:
    routes = plan.routes
    if filter_exec_ids:
        routes = [r for r in routes if r.executive.executive_id in filter_exec_ids]
    if not routes:
        return None

    all_lats: List[float] = []
    all_lons: List[float] = []
    for route in routes:
        all_lats.append(route.executive.home_lat)
        all_lons.append(route.executive.home_lon)
        for cid in route.customer_ids:
            cu = customers_by_id.get(cid)
            if cu:
                all_lats.append(cu.lat)
                all_lons.append(cu.lon)

    if not all_lats:
        return None

    mid_lat = sum(all_lats) / len(all_lats)
    mid_lon = sum(all_lons) / len(all_lons)
    m = folium.Map(location=[mid_lat, mid_lon], zoom_start=11)
    colors = ["#1e3a5f", "#c0392b", "#27ae60", "#8e44ad", "#d35400"]

    for ri, route in enumerate(routes):
        color = colors[ri % len(colors)]
        ex = route.executive
        folium.Marker(
            [ex.home_lat, ex.home_lon],
            popup=folium.Popup(
                f"<b>{_office_label(ex)}</b><br/>{ex.office_address}",
                max_width=280,
            ),
            tooltip=f"Office: {ex.executive_id}",
            icon=folium.Icon(color="black", icon="home"),
        ).add_to(m)

        points = [[ex.home_lat, ex.home_lon]]
        for seq, cid in enumerate(route.customer_ids, start=1):
            cu = customers_by_id.get(cid)
            if not cu:
                continue
            addr = customer_display_address(
                cu.customer_id, cu.area, cu.address, cu.lat, cu.lon
            )
            points.append([cu.lat, cu.lon])
            folium.Marker(
                [cu.lat, cu.lon],
                popup=folium.Popup(
                    f"<b>{seq}. {cid}</b><br/>{addr}",
                    max_width=300,
                ),
                tooltip=f"{seq}. {cid}",
                icon=folium.DivIcon(
                    html=(
                        f'<div style="background:{color};color:white;'
                        f'border-radius:50%;width:26px;height:26px;'
                        f'text-align:center;line-height:26px;font-weight:bold;'
                        f'font-size:12px;border:2px solid white;">{seq}</div>'
                    ),
                    icon_size=(26, 26),
                    icon_anchor=(13, 13),
                ),
            ).add_to(m)

        if len(points) > 1:
            folium.PolyLine(
                points,
                color=color,
                weight=4,
                opacity=0.85,
                tooltip=f"Route {ex.executive_id} (estimated)",
            ).add_to(m)

    folium.LayerControl().add_to(m)
    return m


def _google_embed_office(ex: Executive, height: int = 320) -> None:
    q = f"{ex.home_lat},{ex.home_lon}"
    src = f"https://maps.google.com/maps?q={q}&hl=en&z=14&output=embed"
    components.iframe(src, height=height)


def render_route_map_panel(
    plan: PlanResult,
    executives: List[Executive],
    customers_by_id: Dict[str, Customer],
    filter_exec_ids: Optional[Set[str]] = None,
    primary_executive_id: Optional[str] = None,
) -> None:
    """Route map + fixed office on Google Maps embed (no API key)."""
    shown_execs = executives
    if filter_exec_ids:
        shown_execs = [e for e in executives if e.executive_id in filter_exec_ids]

    if primary_executive_id:
        primary = next(
            (e for e in executives if e.executive_id == primary_executive_id),
            None,
        )
    elif shown_execs:
        primary = shown_execs[0]
    else:
        primary = executives[0] if executives else None

    if primary:
        st.markdown("#### Your branch office (fixed start / end)")
        st.markdown(
            f"**{primary.office_name}**  \n"
            f"{primary.office_address}  \n"
            f"Coordinates: `{primary.home_lat:.5f}, {primary.home_lon:.5f}`"
        )
        st.link_button(
            "Open office in Google Maps",
            google_maps_url(
                primary.home_lat,
                primary.home_lon,
                primary.office_address,
            ),
            use_container_width=True,
        )

    route_customers: List[Customer] = []
    if primary:
        for route in plan.routes:
            if route.executive.executive_id != primary.executive_id:
                continue
            for cid in route.customer_ids:
                if cid in customers_by_id:
                    route_customers.append(customers_by_id[cid])

    if primary and route_customers:
        st.link_button(
            "Open full visit route in Google Maps (office → all stops → office)",
            google_maps_route_url(
                primary.home_lat,
                primary.home_lon,
                route_customers,
                return_to_office=True,
            ),
            use_container_width=True,
        )

    st.markdown("#### Today's route map")
    st.caption(
        "Office (home icon) and numbered customer stops. "
        "Lines are estimated travel paths (Haversine × 1.3), not live road routing."
    )
    m = build_route_map(plan, customers_by_id, filter_exec_ids)
    if m:
        st_folium(m, width=None, height=500, use_container_width=True)
    else:
        st.info("Generate a plan with at least one visit to see the map.")

    if primary:
        st.markdown("#### Office location — Google Maps")
        _google_embed_office(primary)
