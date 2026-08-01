"""Commercial Bank Enterprise AI Assistant — Streamlit chat UI with agent activity panel."""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path
from typing import Any

# Ensure project root is on sys.path when Streamlit runs this file directly.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from frontend.api_client import AssistantApiClient, SSEMessage

DEFAULT_API_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

DEMO_USERS = {
    "Viewer": ("viewer@commercialbank.com", "viewer123"),
    "Analyst": ("analyst@commercialbank.com", "analyst123"),
    "Admin": ("admin@commercialbank.com", "admin123"),
}

NODE_COLORS = {
    "supervisor": "#2563eb",
    "retrieval": "#16a34a",
    "research": "#9333ea",
    "tools": "#ea580c",
    "response": "#0891b2",
    "validate": "#64748b",
    "system": "#dc2626",
}


def _init_session_state() -> None:
    defaults = {
        "api_base_url": DEFAULT_API_URL,
        "access_token": None,
        "user": None,
        "session_id": str(uuid.uuid4()),
        "messages": [],
        "activity_log": [],
        "current_node": None,
        "current_route": None,
        "last_validation_passed": None,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def _login(client: AssistantApiClient, email: str, password: str) -> None:
    profile = client.login(email, password)
    st.session_state.access_token = profile["access_token"]
    st.session_state.user = {
        "email": profile["email"],
        "role": profile["role"],
        "display_name": profile["display_name"],
        "user_id": profile["user_id"],
    }
    st.session_state.messages = []
    st.session_state.activity_log = []
    st.session_state.session_id = str(uuid.uuid4())


def _logout() -> None:
    st.session_state.access_token = None
    st.session_state.user = None
    st.session_state.messages = []
    st.session_state.activity_log = []
    st.session_state.session_id = str(uuid.uuid4())


def _auth_role() -> str:
    user = st.session_state.get("user")
    return user["role"] if user else "viewer"


def _render_activity_event(event: dict[str, Any]) -> str:
    node = event.get("node", "agent")
    event_type = event.get("event_type", "event")
    message = event.get("message", "")
    color = NODE_COLORS.get(node, "#475569")
    return (
        f'<div style="border-left: 3px solid {color}; padding: 0.35rem 0.6rem; '
        f'margin-bottom: 0.4rem; background: #f8fafc; border-radius: 4px;">'
        f'<strong style="color:{color}">{node}</strong> '
        f'<span style="color:#64748b;font-size:0.85em">({event_type})</span><br/>'
        f'<span style="font-size:0.92em">{message}</span></div>'
    )


def _render_activity_panel(
    *,
    activity_log: list[dict[str, Any]],
    current_node: str | None,
    current_route: str | None,
    validation_passed: bool | None,
) -> None:
    st.subheader("Agent Activity")
    if current_node:
        st.caption(f"Current node: **{current_node}**")
    if current_route:
        st.caption(f"Route: **{current_route}**")
    if validation_passed is not None:
        icon = "✅" if validation_passed else "⚠️"
        st.caption(f"Validation: {icon} {'passed' if validation_passed else 'flagged'}")

    if not activity_log:
        st.info("Agent events appear here while a query runs.")
        return

    html = "".join(_render_activity_event(ev) for ev in activity_log[-30:])
    st.markdown(html, unsafe_allow_html=True)


def _render_citations(citations: list[dict[str, Any]]) -> None:
    if not citations:
        return
    with st.expander(f"Sources ({len(citations)})", expanded=False):
        for i, cite in enumerate(citations, start=1):
            st.markdown(
                f"**{i}. [{cite.get('source_file', 'unknown')}]** "
                f"{cite.get('title', '')} "
                f"(score: {float(cite.get('hybrid_score', 0)):.3f})"
            )
            preview = cite.get("text_preview") or ""
            if preview:
                st.caption(preview[:280] + ("…" if len(preview) > 280 else ""))


def _handle_sse_event(msg: SSEMessage, activity_log: list[dict[str, Any]]) -> None:
    if msg.event == "node":
        st.session_state.current_node = msg.data.get("current_node") or msg.data.get("node")
        if msg.data.get("route"):
            st.session_state.current_route = msg.data["route"]
        activity_log.append(
            {
                "node": msg.data.get("node", "graph"),
                "event_type": msg.data.get("status", "node"),
                "message": f"Node {msg.data.get('node')} {msg.data.get('status', '')}".strip(),
            }
        )
    elif msg.event == "agent_event":
        activity_log.append(msg.data)
    elif msg.event == "started":
        st.session_state.session_id = msg.data.get("session_id", st.session_state.session_id)


def _sidebar(client: AssistantApiClient) -> None:
    st.sidebar.title("Commercial Bank AI")
    st.sidebar.caption("Enterprise knowledge assistant")

    st.session_state.api_base_url = st.sidebar.text_input(
        "API URL",
        value=st.session_state.api_base_url,
    )

    if client.health_ok():
        st.sidebar.success("API reachable")
    else:
        st.sidebar.warning("API unreachable — start backend with uvicorn")

    st.sidebar.divider()

    if st.session_state.user:
        user = st.session_state.user
        st.sidebar.markdown(f"**{user['display_name']}**")
        st.sidebar.markdown(f"Role: `{user['role']}`")
        if st.sidebar.button("Log out", use_container_width=True):
            _logout()
            st.rerun()
    else:
        st.sidebar.markdown("**Sign in**")
        for label, (email, password) in DEMO_USERS.items():
            if st.sidebar.button(f"Demo: {label}", use_container_width=True):
                try:
                    _login(client, email, password)
                    st.rerun()
                except Exception as exc:
                    st.sidebar.error(f"Login failed: {exc}")

        with st.sidebar.expander("Manual login"):
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            if st.button("Login", key="manual_login"):
                try:
                    _login(client, email, password)
                    st.rerun()
                except Exception as exc:
                    st.error(f"Login failed: {exc}")

        st.sidebar.caption("Dev mode: unauthenticated requests use viewer role.")

    st.sidebar.divider()
    st.sidebar.caption(f"Session: `{st.session_state.session_id[:8]}…`")
    if st.sidebar.button("New session", use_container_width=True):
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.session_state.activity_log = []
        st.rerun()


def main() -> None:
    st.set_page_config(
        page_title="Commercial Bank AI Assistant",
        page_icon="🏦",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _init_session_state()

    client = AssistantApiClient(st.session_state.api_base_url)
    _sidebar(client)

    st.title("Enterprise AI Assistant")
    st.caption(
        "Ask about incidents, runbooks, policies, and architecture. "
        "The activity panel shows live agent routing, retrieval, tools, and validation."
    )

    chat_col, activity_col = st.columns([2, 1], gap="large")

    with activity_col:
        activity_placeholder = st.empty()
        with activity_placeholder.container():
            _render_activity_panel(
                activity_log=st.session_state.activity_log,
                current_node=st.session_state.current_node,
                current_route=st.session_state.current_route,
                validation_passed=st.session_state.last_validation_passed,
            )

    with chat_col:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if msg["role"] == "assistant":
                    _render_citations(msg.get("citations") or [])
                    if msg.get("validation_passed") is False:
                        st.warning("Validation flagged issues in this answer.")

        if prompt := st.chat_input("Ask about Commercial Bank internal knowledge…"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            activity_log: list[dict[str, Any]] = []
            st.session_state.activity_log = activity_log
            st.session_state.current_node = None
            st.session_state.current_route = None
            st.session_state.last_validation_passed = None

            answer_parts: list[str] = []
            validation_passed: bool | None = None
            citations: list[dict[str, Any]] = []
            stream_error: str | None = None

            with st.chat_message("assistant"):
                answer_placeholder = st.empty()

                def refresh_activity() -> None:
                    with activity_placeholder.container():
                        _render_activity_panel(
                            activity_log=activity_log,
                            current_node=st.session_state.current_node,
                            current_route=st.session_state.current_route,
                            validation_passed=validation_passed,
                        )

                def on_event(msg: SSEMessage) -> None:
                    nonlocal validation_passed
                    _handle_sse_event(msg, activity_log)
                    if msg.event == "token":
                        answer_parts.append(msg.data.get("content", ""))
                        answer_placeholder.markdown("".join(answer_parts))
                    elif msg.event == "done":
                        validation_passed = msg.data.get("validation_passed")
                    refresh_activity()

                refresh_activity()

                try:
                    result = client.consume_stream(
                        prompt,
                        session_id=st.session_state.session_id,
                        token=st.session_state.access_token,
                        role=_auth_role(),
                        on_event=on_event,
                    )
                    stream_error = result.error
                    if result.answer and not answer_parts:
                        answer_parts = [result.answer]
                    citations = result.citations
                    validation_passed = result.validation_passed
                    if result.session_id:
                        st.session_state.session_id = result.session_id
                    if result.route:
                        st.session_state.current_route = result.route
                except Exception as exc:
                    stream_error = str(exc)
                    answer_parts = [f"Request failed: {exc}"]

                final_answer = "".join(answer_parts) or "_No answer returned._"
                answer_placeholder.markdown(final_answer)
                _render_citations(citations)
                if validation_passed is False:
                    st.warning("Validation flagged issues in this answer.")
                if stream_error:
                    st.error(stream_error)

            st.session_state.last_validation_passed = validation_passed
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": final_answer,
                    "citations": citations,
                    "validation_passed": validation_passed,
                }
            )
            refresh_activity()


if __name__ == "__main__":
    main()
