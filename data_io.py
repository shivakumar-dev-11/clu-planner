"""CSV ingestion, column normalization, and validation."""

from __future__ import annotations

import io
import re
from pathlib import Path
from typing import BinaryIO, List, Optional, Tuple, Union

import pandas as pd

from models import Customer, Executive, ValidationIssue

EXECUTIVE_REQUIRED = [
    "executive_id",
    "home_lat",
    "home_lon",
    "shift_start",
    "shift_end",
    "max_visits",
    "max_km",
]

CUSTOMER_COLUMN_ALIASES = {
    "id": "customer_id",
    "visit_id": "customer_id",
    "customer": "customer_id",
    "customer_name": "customer_id",
    "priority": "priority_score",
    "amount": "overdue_amount",
    "overdue": "overdue_amount",
    "svc": "service_min",
    "service": "service_min",
    "service_time": "service_min",
    "visit_duration": "service_min",
    "duration": "service_min",
    "duration_min": "service_min",
    "latitude": "lat",
    "longitude": "lon",
    "location": "address",
    "customer_address": "address",
    "preferred_start_time": "window_start",
    "preferred_end_time": "window_end",
    "start_time": "window_start",
    "end_time": "window_end",
    "time_window_start": "window_start",
    "time_window_end": "window_end",
    "ptp": "ptp_today",
    "ptp_flag": "ptp_today",
}

EXECUTIVE_COLUMN_ALIASES = {
    "exec_id": "executive_id",
    "id": "executive_id",
    "lat": "home_lat",
    "lon": "home_lon",
    "latitude": "home_lat",
    "longitude": "home_lon",
}

DEFAULT_WINDOW_START = "09:30"
DEFAULT_WINDOW_END = "18:00"
DEFAULT_SERVICE_MIN = "20"
DEFAULT_PRIORITY = "50"
DEFAULT_PTP = "0"


def to_minutes(value: str) -> int:
    raw = str(value).strip()
    if not raw:
        raise ValueError("empty time")
    parts = raw.split(":")
    if len(parts) == 2:
        h, m = int(parts[0]), int(parts[1])
    elif len(parts) == 3:
        h, m = int(parts[0]), int(parts[1])
    else:
        raise ValueError(f"Expected HH:MM, got {value!r}")
    if not (0 <= h <= 23 and 0 <= m <= 59):
        raise ValueError(f"Invalid clock time: {value!r}")
    return h * 60 + m


def minutes_to_hhmm(minutes: int) -> str:
    h, m = divmod(int(minutes), 60)
    return f"{h:02d}:{m:02d}"


def _normalize_headers(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
        .str.replace("-", "_")
    )
    return df


def _apply_aliases(df: pd.DataFrame, aliases: dict) -> pd.DataFrame:
    rename = {c: aliases[c] for c in df.columns if c in aliases}
    return df.rename(columns=rename)


def _split_window_column(df: pd.DataFrame) -> pd.DataFrame:
    if "window" not in df.columns:
        return df
    df = df.copy()
    if "window_start" not in df.columns or "window_end" not in df.columns:
        starts, ends = [], []
        for val in df["window"]:
            if pd.isna(val) or str(val).strip() == "":
                starts.append(None)
                ends.append(None)
            else:
                text = str(val).strip()
                parts = re.split(r"[-–to]+", text, maxsplit=1, flags=re.IGNORECASE)
                if len(parts) != 2:
                    parts = re.split(r"[-–]", text, maxsplit=1)
                if len(parts) != 2:
                    starts.append(None)
                    ends.append(None)
                else:
                    starts.append(parts[0].strip())
                    ends.append(parts[1].strip())
        if "window_start" not in df.columns:
            df["window_start"] = starts
        if "window_end" not in df.columns:
            df["window_end"] = ends
    return df


def _apply_customer_defaults(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    n = len(df)
    if n == 0:
        return df

    def fill_col(name: str, default: str) -> None:
        if name not in df.columns:
            df[name] = [default] * n
        else:
            df[name] = df[name].apply(
                lambda v: default if str(v).strip() == "" else str(v).strip()
            )

    fill_col("window_start", DEFAULT_WINDOW_START)
    fill_col("window_end", DEFAULT_WINDOW_END)
    fill_col("service_min", DEFAULT_SERVICE_MIN)
    fill_col("priority_score", DEFAULT_PRIORITY)
    fill_col("ptp_today", DEFAULT_PTP)
    return df


def _read_csv_source(
    source: Union[str, Path, BinaryIO, io.BytesIO],
) -> pd.DataFrame:
    if isinstance(source, (str, Path)):
        with open(source, "rb") as f:
            raw = f.read()
    else:
        raw = source.read()
        if hasattr(source, "seek"):
            source.seek(0)

    if not raw or not raw.strip():
        raise ValueError("CSV file is empty")

    last_err: Optional[Exception] = None
    for encoding in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
        for sep in (",", ";", "\t"):
            try:
                df = pd.read_csv(
                    io.BytesIO(raw),
                    dtype=str,
                    keep_default_na=False,
                    encoding=encoding,
                    sep=sep,
                )
                if df.shape[1] >= 3:
                    return df
            except Exception as e:
                last_err = e
                continue
    try:
        return pd.read_csv(
            io.BytesIO(raw),
            dtype=str,
            keep_default_na=False,
            encoding="utf-8-sig",
            sep=None,
            engine="python",
        )
    except Exception as e:
        raise ValueError(f"Could not read CSV: {last_err or e}") from e


def load_executives(
    source: Union[str, BinaryIO, io.BytesIO],
) -> Tuple[List[Executive], List[ValidationIssue]]:
    df = _normalize_headers(_read_csv_source(source))
    df = _apply_aliases(df, EXECUTIVE_COLUMN_ALIASES)
    issues: List[ValidationIssue] = []

    missing = [c for c in EXECUTIVE_REQUIRED if c not in df.columns]
    if missing:
        issues.append(
            ValidationIssue(0, "schema", "", f"Missing columns: {missing}")
        )
        return [], issues

    executives: List[Executive] = []
    seen_ids: set[str] = set()

    for idx, row in df.iterrows():
        row_num = int(idx) + 2
        eid = str(row["executive_id"]).strip()
        if not eid:
            issues.append(
                ValidationIssue(row_num, "executive_id", "", "Required, empty")
            )
            continue
        if eid in seen_ids:
            issues.append(
                ValidationIssue(
                    row_num, "executive_id", eid, "Duplicate executive_id"
                )
            )
            continue
        seen_ids.add(eid)

        try:
            lat = float(row["home_lat"])
            lon = float(row["home_lon"])
            if not (-90 <= lat <= 90):
                raise ValueError("latitude out of range")
            if not (-180 <= lon <= 180):
                raise ValueError("longitude out of range")
            shift_start = to_minutes(row["shift_start"])
            shift_end = to_minutes(row["shift_end"])
            if shift_start >= shift_end:
                raise ValueError("shift_start must be before shift_end")
            max_visits = int(float(row["max_visits"]))
            max_km = float(row["max_km"])
            if max_visits < 0 or max_km < 0:
                raise ValueError("max_visits and max_km must be non-negative")
        except (ValueError, TypeError) as e:
            issues.append(
                ValidationIssue(row_num, "row", str(row.to_dict()), str(e))
            )
            continue

        office_name = str(row.get("office_name", "")).strip() or f"CLU Office {eid}"
        office_address = (
            str(row.get("office_address", "")).strip()
            or f"Branch {eid} ({lat:.4f}, {lon:.4f})"
        )

        executives.append(
            Executive(
                executive_id=eid,
                office_name=office_name,
                office_address=office_address,
                home_lat=lat,
                home_lon=lon,
                shift_start_min=shift_start,
                shift_end_min=shift_end,
                max_visits=max_visits,
                max_km=max_km,
            )
        )

    dup_issues = [i for i in issues if "Duplicate" in i.reason]
    if dup_issues:
        return [], issues

    return executives, issues


def _parse_ptp(val: str) -> Optional[bool]:
    s = str(val).strip().lower()
    if s in ("1", "true", "yes", "y"):
        return True
    if s in ("0", "false", "no", "n", ""):
        return False if s != "" else None
    return None


def load_customers(
    source: Union[str, BinaryIO, io.BytesIO],
) -> Tuple[List[Customer], List[ValidationIssue]]:
    issues: List[ValidationIssue] = []
    try:
        df = _normalize_headers(_read_csv_source(source))
    except ValueError as e:
        issues.append(ValidationIssue(0, "file", "", str(e)))
        return [], issues

    if df.empty:
        issues.append(ValidationIssue(0, "file", "", "CSV has no data rows"))
        return [], issues

    df = _apply_aliases(df, CUSTOMER_COLUMN_ALIASES)
    df = _split_window_column(df)
    df = _apply_customer_defaults(df)

    missing = [c for c in ("customer_id", "lat", "lon") if c not in df.columns]
    if missing:
        issues.append(
            ValidationIssue(
                0,
                "schema",
                "",
                f"Missing required columns: {missing}. "
                f"Accepted names include id, visit_id, latitude, longitude, "
                f"window or preferred_start_time/preferred_end_time.",
            )
        )
        return [], issues

    customers: List[Customer] = []
    seen_ids: set[str] = set()

    for idx, row in df.iterrows():
        row_num = int(idx) + 2
        cid = str(row["customer_id"]).strip()
        if not cid:
            issues.append(
                ValidationIssue(row_num, "customer_id", "", "Required, empty")
            )
            continue
        if cid in seen_ids:
            issues.append(
                ValidationIssue(
                    row_num, "customer_id", cid, "Duplicate customer_id"
                )
            )
            continue
        seen_ids.add(cid)

        ptp_raw = str(row.get("ptp_today", DEFAULT_PTP)).strip()
        ptp = _parse_ptp(ptp_raw)
        if ptp is None:
            ptp = False

        try:
            lat = float(str(row["lat"]).replace(",", "."))
            lon = float(str(row["lon"]).replace(",", "."))
            if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                raise ValueError("invalid coordinates")
            priority = float(str(row.get("priority_score", DEFAULT_PRIORITY)))
            if priority < 0:
                raise ValueError("priority_score must be non-negative")
            if priority > 100:
                priority = min(priority, 100.0)
            ws = to_minutes(str(row.get("window_start", DEFAULT_WINDOW_START)))
            we = to_minutes(str(row.get("window_end", DEFAULT_WINDOW_END)))
            if ws >= we:
                raise ValueError("window_start must be before window_end")
            service = int(float(str(row.get("service_min", DEFAULT_SERVICE_MIN))))
            if service < 0:
                raise ValueError("service_min must be non-negative")
            area = str(row.get("area", "")).strip() or None
            address = str(row.get("address", "")).strip() or None
            dpd_val = row.get("dpd", "")
            dpd = int(float(dpd_val)) if str(dpd_val).strip() else None
            amt_val = row.get("overdue_amount", "")
            amount = float(amt_val) if str(amt_val).strip() else None
        except (ValueError, TypeError) as e:
            issues.append(
                ValidationIssue(row_num, "row", str(row.to_dict()), str(e))
            )
            continue

        customers.append(
            Customer(
                customer_id=cid,
                area=area,
                address=address,
                lat=lat,
                lon=lon,
                dpd=dpd,
                overdue_amount=amount,
                priority_score=priority,
                ptp_today=ptp,
                window_start_min=ws,
                window_end_min=we,
                service_min=service,
            )
        )

    if any("Duplicate" in i.reason for i in issues):
        return customers, issues

    return customers, issues


def has_blocking_errors(
    issues: List[ValidationIssue],
    loaded_count: int = 0,
) -> bool:
    if any("Duplicate" in i.reason for i in issues):
        return True
    if any(i.field in ("schema", "file") for i in issues):
        return True
    if loaded_count == 0:
        return len(issues) > 0
    return False
