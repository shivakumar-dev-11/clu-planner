"""Streamlit dashboard for Clu Daily Visit Planner."""

from __future__ import annotations

import hashlib
import io
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from auth import allowed_executive_ids_for_user, logout_button, render_login_page
from baseline import run_baseline
from data_io import has_blocking_errors, load_customers, load_executives
from distance import DistanceContext
from export import (
    dataframe_to_csv_bytes,
    plan_to_dataframe,
    route_summary_dataframe,
    unvisited_to_dataframe,
)
from google_maps_ui import (
    customers_for_executive_plan,
    google_maps_directions_url,
    google_maps_route_url,
)
from route_map import render_route_map_panel
from metrics import compute_metrics
from optimizer import run_optimizer
from ui_theme import inject_global_styles, render_hero, render_kpi, render_steps

DATA_DIR = Path(__file__).parent / "data"
EXECUTIVES_PATH = DATA_DIR / "executives.csv"
TEMPLATE_PATH = DATA_DIR / "customers_upload_template.csv"


def _file_hash(cust_bytes: bytes, config: str) -> str:
    h = hashlib.sha256()
    h.update(EXECUTIVES_PATH.read_bytes())
    h.update(cust_bytes)
    h.update(config.encode())
    return h.hexdigest()


def _load_executives_internal():
    executives, issues = load_executives(EXECUTIVES_PATH)
    return executives, issues


def _executive_record(executives, user_id: str):
    for ex in executives:
        if ex.executive_id == user_id:
            return ex
    return None


def _customers_preview_df(customers) -> pd.DataFrame:
    from models import customer_display_address

    rows = []
    for c in customers:
        rows.append(
            {
                "customer_id": c.customer_id,
                "address": customer_display_address(
                    c.customer_id, c.area, c.address, c.lat, c.lon
                ),
                "lat": c.lat,
                "lon": c.lon,
                "priority": c.priority_score,
                "ptp": int(c.ptp_today),
            }
        )
    return pd.DataFrame(rows)


def main_dashboard() -> None:
    inject_global_styles()

    user_id = st.session_state.executive_user_id
    render_hero(
        "Daily Visit Planner",
        f"Welcome back, {user_id}. Load customers, generate your route, and navigate with Google Maps.",
        badge="Smart collections",
    )

    st.sidebar.markdown("### Account")
    st.sidebar.caption(user_id)
    logout_button()

    filter_ids = allowed_executive_ids_for_user(user_id)

    executives, exec_issues = _load_executives_internal()
    my_office = _executive_record(executives, user_id)
    if my_office:
        st.sidebar.markdown("---")
        st.sidebar.markdown("### Branch office")
        st.sidebar.markdown(f"**{my_office.office_name}**")
        st.sidebar.caption(my_office.office_address)

    if exec_issues:
        st.error("Executive configuration is invalid. Contact your administrator.")
        st.dataframe(pd.DataFrame([i.__dict__ for i in exec_issues]))
        return

    st.sidebar.markdown("---")
    st.sidebar.markdown("### Customer data")
    data_source = st.sidebar.radio(
        "Data source",
        ["Sample customers", "Upload my CSV"],
        horizontal=False,
        label_visibility="collapsed",
    )

    cust_bytes: bytes | None = None
    source_label = ""

    if data_source == "Sample customers":
        cust_bytes = DATA_DIR.joinpath("customers.csv").read_bytes()
        source_label = "Sample file (data/customers.csv)"
    else:
        st.sidebar.download_button(
            "Download CSV template",
            TEMPLATE_PATH.read_bytes(),
            file_name="customers_upload_template.csv",
            use_container_width=True,
        )
        cust_file = st.sidebar.file_uploader(
            "Choose customers CSV",
            type=["csv"],
            help="UTF-8 CSV with columns: id, lat, lon (see template).",
        )
        if not cust_file:
            render_steps(
                [
                    "Download the CSV template (sidebar)",
                    "Fill in customer id, latitude, longitude",
                    "Upload the file here",
                    "Click Generate plan",
                ]
            )
            st.info("Upload a customers CSV to continue, or switch to **Sample customers**.")
            return
        cust_bytes = cust_file.getvalue()
        source_label = cust_file.name

    try:
        customers, cust_issues = load_customers(io.BytesIO(cust_bytes))
    except Exception as e:
        st.error(f"Could not read file: {e}")
        return

    customers_by_id = {c.customer_id: c for c in customers}

    row_warnings = [i for i in cust_issues if i.field not in ("schema", "file")]
    if row_warnings:
        with st.expander(f"Row warnings ({len(row_warnings)}) — other rows were loaded"):
            st.dataframe(
                pd.DataFrame([i.__dict__ for i in row_warnings]),
                use_container_width=True,
                hide_index=True,
            )

    if has_blocking_errors(cust_issues, len(customers)):
        st.error("Could not load customer data. Check the messages below.")
        if cust_issues:
            st.dataframe(
                pd.DataFrame([i.__dict__ for i in cust_issues]),
                use_container_width=True,
                hide_index=True,
            )
        st.markdown(
            "**Required columns:** `id` (or `customer_id`), `lat`, `longitude` / `lon`. "
            "Optional: `address`, `priority`, `ptp_today`, `window` (e.g. 09:30-18:00), `svc`."
        )
        return

    st.success(f"Loaded **{len(customers)}** customers from *{source_label}*.")
    with st.expander("Preview loaded customers", expanded=data_source == "Upload my CSV"):
        st.dataframe(
            _customers_preview_df(customers),
            use_container_width=True,
            hide_index=True,
        )

    st.sidebar.markdown("---")
    st.sidebar.markdown("### Planner settings")
    lambda_value = st.sidebar.number_input(
        "λ (score penalty per km)", value=2.0, min_value=0.0
    )
    algorithm = st.sidebar.selectbox(
        "Algorithm", ["heuristic", "baseline", "compare both"]
    )

    config_key = f"{lambda_value}:{algorithm}"
    input_hash = _file_hash(cust_bytes, config_key)
    if st.session_state.get("input_hash") != input_hash:
        for key in ("plan_result", "metrics", "baseline_plan", "baseline_metrics"):
            st.session_state.pop(key, None)
        st.session_state.input_hash = input_hash

    _, btn_col, _ = st.columns([1, 2, 1])
    with btn_col:
        run_clicked = st.button(
            "Generate plan",
            type="primary",
            use_container_width=True,
        )

    if run_clicked:
        dist_ctx = DistanceContext(executives, customers)
        with st.spinner("Optimizing routes…"):
            if algorithm == "baseline":
                plan = run_baseline(executives, customers, dist_ctx)
                st.session_state.plan_result = plan
                st.session_state.metrics = compute_metrics(
                    plan, customers, dist_ctx, lambda_value
                )
            elif algorithm == "heuristic":
                plan = run_optimizer(
                    executives, customers, dist_ctx, lambda_value=lambda_value
                )
                st.session_state.plan_result = plan
                st.session_state.metrics = compute_metrics(
                    plan, customers, dist_ctx, lambda_value
                )
            else:
                base_plan = run_baseline(executives, customers, dist_ctx)
                opt_plan = run_optimizer(
                    executives, customers, dist_ctx, lambda_value=lambda_value
                )
                st.session_state.baseline_plan = base_plan
                st.session_state.baseline_metrics = compute_metrics(
                    base_plan, customers, dist_ctx, lambda_value
                )
                st.session_state.plan_result = opt_plan
                st.session_state.metrics = compute_metrics(
                    opt_plan, customers, dist_ctx, lambda_value
                )

    plan = st.session_state.get("plan_result")
    metrics = st.session_state.get("metrics")
    if not plan or not metrics:
        return

    if metrics.constraint_violations > 0:
        st.warning(
            f"Plan has {metrics.constraint_violations} validation issue(s). "
            "Review routes before export."
        )

    cov = (
        f"{metrics.priority_coverage_pct:.1f}%"
        if metrics.priority_coverage_pct is not None
        else "N/A"
    )
    ptp = (
        f"{metrics.ptp_hit_rate_pct:.1f}%"
        if metrics.ptp_hit_rate_pct is not None
        else "N/A"
    )
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    with k1:
        render_kpi("Scheduled", str(metrics.scheduled_count))
    with k2:
        render_kpi("Unvisited", str(metrics.unvisited_count))
    with k3:
        render_kpi("Total km", f"{metrics.total_km:.1f}")
    with k4:
        render_kpi("Score", f"{metrics.score:.1f}")
    with k5:
        render_kpi("Priority", cov)
    with k6:
        render_kpi("PTP hit rate", ptp)

    tab_overview, tab_schedule, tab_map, tab_export = st.tabs(
        ["Overview", "My visits", "Route map", "Export"]
    )

    plan_df = plan_to_dataframe(plan, customers_by_id)
    if filter_ids:
        plan_df = plan_df[plan_df["executive_id"].isin(filter_ids)]
    unv_df = unvisited_to_dataframe(plan)

    map_customers: list = []
    primary_eid = None
    if filter_ids and len(filter_ids) == 1:
        primary_eid = next(iter(filter_ids))
        map_customers = customers_for_executive_plan(
            plan, customers_by_id, primary_eid
        )

    with tab_overview:
        if st.session_state.get("baseline_metrics"):
            bm = st.session_state.baseline_metrics
            fig = go.Figure(
                data=[
                    go.Bar(
                        name="Baseline",
                        x=["Score", "Total km", "Scheduled"],
                        y=[bm.score, bm.total_km, bm.scheduled_count],
                        marker_color="#94a3b8",
                    ),
                    go.Bar(
                        name="Heuristic",
                        x=["Score", "Total km", "Scheduled"],
                        y=[metrics.score, metrics.total_km, metrics.scheduled_count],
                        marker_color="#2d6ba8",
                    ),
                ]
            )
            fig.update_layout(
                barmode="group",
                title="Baseline vs heuristic",
                template="plotly_white",
                height=360,
            )
            st.plotly_chart(fig, use_container_width=True)
        st.markdown("#### Unvisited customers")
        if unv_df.empty:
            st.success("All customers are scheduled.")
        else:
            st.dataframe(unv_df, use_container_width=True, hide_index=True)

    with tab_schedule:
        st.markdown("#### Your visit list (with addresses)")
        if plan_df.empty:
            st.info("No visits assigned yet for your account.")
        else:
            col_config = {}
            if "google_maps" in plan_df.columns:
                col_config["google_maps"] = st.column_config.LinkColumn(
                    "Open in Google Maps",
                    display_text="Navigate",
                )
            st.dataframe(
                plan_df,
                use_container_width=True,
                hide_index=True,
                column_config=col_config,
            )
            if primary_eid and map_customers:
                office = _executive_record(executives, primary_eid)
                if office:
                    st.link_button(
                        "Navigate: office → first customer (Google Maps)",
                        google_maps_directions_url(
                            office.home_lat,
                            office.home_lon,
                            map_customers[0].lat,
                            map_customers[0].lon,
                        ),
                        use_container_width=True,
                    )
                    if len(map_customers) > 1:
                        st.link_button(
                            "Open full route in Google Maps",
                            google_maps_route_url(
                                office.home_lat,
                                office.home_lon,
                                map_customers,
                                return_to_office=True,
                            ),
                            use_container_width=True,
                        )

    with tab_map:
        render_route_map_panel(
            plan,
            executives,
            customers_by_id,
            filter_exec_ids=filter_ids,
            primary_executive_id=primary_eid or user_id if user_id != "admin" else None,
        )

    with tab_export:
        st.markdown("#### Download results")
        full_plan = plan_to_dataframe(plan, customers_by_id)
        d1, d2, d3 = st.columns(3)
        with d1:
            st.download_button(
                "Download plan.csv",
                dataframe_to_csv_bytes(full_plan),
                file_name="plan.csv",
                use_container_width=True,
            )
        with d2:
            st.download_button(
                "Download unvisited_customers.csv",
                dataframe_to_csv_bytes(unvisited_to_dataframe(plan)),
                file_name="unvisited_customers.csv",
                use_container_width=True,
            )
        with d3:
            st.download_button(
                "Download route_summary.csv",
                dataframe_to_csv_bytes(route_summary_dataframe(plan)),
                file_name="route_summary.csv",
                use_container_width=True,
            )


def main() -> None:
    st.set_page_config(
        page_title="Clu Daily Visit Planner",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            "Get help": None,
            "Report a bug": None,
            "About": None,
        },
    )
    if not render_login_page():
        return
    main_dashboard()


if __name__ == "__main__":
    main()
