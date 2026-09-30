"""Collection executive login (demo-grade; use secrets in production)."""

from __future__ import annotations

import os
from typing import Optional, Set

import bcrypt
import streamlit as st

# Demo passwords: executive_id / password (change via env or secrets.toml in production)
_DEFAULT_CREDENTIALS: dict[str, str] = {
    "E01": "clu_exec_01",
    "E02": "clu_exec_02",
    "E03": "clu_exec_03",
    "admin": "clu_admin_planner",
}


def _hash_password(password: str) -> bytes:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())


def _verify_password(password: str, hashed: bytes) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed)
    except ValueError:
        return False


def _load_password_hashes() -> dict[str, bytes]:
    """Build hash map from env CLU_EXEC_PASSWORDS or defaults."""
    env_raw = os.environ.get("CLU_EXEC_PASSWORDS", "")
    plain: dict[str, str] = dict(_DEFAULT_CREDENTIALS)
    if env_raw:
        for part in env_raw.split(";"):
            if ":" in part:
                uid, pwd = part.split(":", 1)
                plain[uid.strip()] = pwd.strip()
    return {uid: _hash_password(pwd) for uid, pwd in plain.items()}


_PASSWORD_HASHES: Optional[dict[str, bytes]] = None


def get_password_hashes() -> dict[str, bytes]:
    global _PASSWORD_HASHES
    if _PASSWORD_HASHES is None:
        _PASSWORD_HASHES = _load_password_hashes()
    return _PASSWORD_HASHES


def authenticate(executive_id: str, password: str) -> bool:
    eid = executive_id.strip()
    if not eid or not password:
        return False
    hashes = get_password_hashes()
    hashed = hashes.get(eid)
    if hashed is None:
        return False
    return _verify_password(password, hashed)


def allowed_executive_ids_for_user(logged_in_id: str) -> Optional[Set[str]]:
    """Admin sees all routes; executives see only their own ID."""
    if logged_in_id == "admin":
        return None
    return {logged_in_id}


def init_session_auth() -> None:
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "executive_user_id" not in st.session_state:
        st.session_state.executive_user_id = None


def render_login_page() -> bool:
    """Return True if user is authenticated."""
    from ui_theme import inject_global_styles, render_hero

    init_session_auth()
    if st.session_state.authenticated:
        return True

    inject_global_styles(login_page=True)
    render_hero(
        "Clu Daily Visit Planner",
        "Optimize field collection routes — priority coverage, travel distance, and hard constraints.",
        badge="CLU Cloud",
    )

    st.markdown("#### Sign in")
    st.caption("Collection executives and planners")
    submitted = False
    executive_id = ""
    password = ""
    with st.form("login_form"):
        executive_id = st.text_input("Executive ID", placeholder="E01 or admin")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button(
            "Sign in", type="primary", use_container_width=True
        )

    with st.expander("Demo credentials"):
        st.code(
            "E01 / clu_exec_01\nE02 / clu_exec_02\nE03 / clu_exec_03\nadmin / clu_admin_planner",
            language=None,
        )

    if submitted:
        if authenticate(executive_id, password):
            st.session_state.authenticated = True
            st.session_state.executive_user_id = executive_id.strip()
            st.rerun()
        else:
            st.error("Invalid executive ID or password.")

    return False


def logout_button() -> None:
    if st.sidebar.button("Sign out"):
        st.session_state.authenticated = False
        st.session_state.executive_user_id = None
        for key in ("plan_result", "metrics", "baseline_metrics", "input_hash"):
            st.session_state.pop(key, None)
        st.rerun()
