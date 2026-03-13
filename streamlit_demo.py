import os
from typing import Any, Dict, Optional

import pandas as pd
import requests
import streamlit as st

DEFAULT_API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
REQUEST_TIMEOUT_SECONDS = 60


class APIError(Exception):
    pass


class BackendClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def create_organization(self, name: str) -> Dict[str, Any]:
        return self._post_json("/api/organizations", json={"name": name})

    def ingest_document(self, api_key: str, uploaded_file) -> Dict[str, Any]:
        files = {
            "file": (
                uploaded_file.name,
                uploaded_file.getvalue(),
                uploaded_file.type or "application/octet-stream",
            )
        }
        headers = {"X-API-Key": api_key}
        return self._post_json("/api/ingest-document", headers=headers, files=files)

    def ask_question(self, api_key: str, question: str) -> Dict[str, Any]:
        headers = {"X-API-Key": api_key}
        return self._post_json(
            "/api/questions",
            json={"question": question},
            headers=headers,
        )

    def get_dashboard(self, api_key: str) -> Dict[str, Any]:
        headers = {"X-API-Key": api_key}
        return self._get_json("/api/dashboard", headers=headers)

    def _get_json(self, path: str, headers: Optional[Dict[str, str]] = None) -> Any:
        url = f"{self.base_url}{path}"
        try:
            response = requests.get(
                url,
                headers=headers,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            return self._handle_response(response)
        except requests.RequestException as exc:
            raise APIError(f"GET {url} failed: {exc}") from exc

    def _post_json(
        self,
        path: str,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        files: Optional[Dict[str, Any]] = None,
    ) -> Any:
        url = f"{self.base_url}{path}"
        try:
            response = requests.post(
                url,
                json=json,
                headers=headers,
                files=files,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            return self._handle_response(response)
        except requests.RequestException as exc:
            raise APIError(f"POST {url} failed: {exc}") from exc

    @staticmethod
    def _handle_response(response: requests.Response) -> Any:
        content_type = response.headers.get("content-type", "")

        if not response.ok:
            try:
                detail = response.json()
            except ValueError:
                detail = response.text
            raise APIError(f"{response.status_code} - {detail}")

        if "application/json" not in content_type:
            raise APIError(f"Unexpected content type: {content_type}")

        return response.json()


def initialize_session_state() -> None:
    defaults = {
        "orgs_by_id": {},
        "active_org_id": None,
        "last_create_response": None,
        "last_ingest_response": None,
        "last_question_response": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def main() -> None:
    st.set_page_config(
        page_title="AI Knowledge System Demo",
        page_icon="🧠",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    initialize_session_state()

    st.title("🧠 AI Knowledge System Demo")
    st.caption(
        "Multi-tenant RAG demo backed by FastAPI + PostgreSQL + pgvector + dashboard analytics"
    )

    with st.expander("Backend connection", expanded=False):
        api_base_url = st.text_input(
            "FastAPI base URL",
            value=DEFAULT_API_BASE_URL,
        )

    client = BackendClient(api_base_url)

    render_sidebar(client)

    if not st.session_state["orgs_by_id"]:
        render_empty_state()
        return

    active_org = get_active_org_data()
    if active_org is None:
        st.warning("No active organization selected.")
        return

    left_col, right_col = st.columns([1.15, 1], gap="large")

    with left_col:
        render_actions_panel(client, active_org)

    with right_col:
        render_dashboard_panel(active_org)


# ============================================================
# Sidebar
# ============================================================
def render_sidebar(client: BackendClient) -> None:
    with st.sidebar:
        st.header("Tenants")
        render_create_org_box(client)
        st.divider()
        render_connect_existing_box(client)
        st.divider()
        render_org_selector(client)
        st.divider()
        render_sidebar_summary()


def render_create_org_box(client: BackendClient) -> None:
    st.subheader("Create organization")
    with st.form("sidebar_create_org_form", clear_on_submit=True):
        org_name = st.text_input("Organization name", placeholder="acme-inc")
        submitted = st.form_submit_button("Create", use_container_width=True)

    if submitted:
        clean_name = (org_name or "").strip()
        if not clean_name:
            st.error("Organization name cannot be empty.")
            return

        try:
            result = client.create_organization(clean_name)
            api_key = extract_api_key(result)
            if not api_key:
                st.error("Organization created, but no API key was returned.")
                return

            dashboard = client.get_dashboard(api_key)
            store_connected_org(
                api_key=api_key,
                dashboard=dashboard,
                label=clean_name,
            )
            st.session_state["last_create_response"] = result
            st.success("Organization created and connected.")
        except APIError as exc:
            st.error(str(exc))


def render_connect_existing_box(client: BackendClient) -> None:
    st.subheader("Connect existing organization")
    with st.form("sidebar_connect_org_form", clear_on_submit=True):
        label = st.text_input(
            "Optional label",
            placeholder="prod-org / demo-client / acme",
            help="Only used in this Streamlit session.",
        )
        api_key = st.text_input("API key", type="password")
        submitted = st.form_submit_button("Connect", use_container_width=True)

    if submitted:
        clean_api_key = (api_key or "").strip()
        if not clean_api_key:
            st.error("API key is required.")
            return

        try:
            dashboard = client.get_dashboard(clean_api_key)
            inferred_label = (
                label.strip()
                if label.strip()
                else dashboard.get("organization_name", "connected-org")
            )
            store_connected_org(
                api_key=clean_api_key,
                dashboard=dashboard,
                label=inferred_label,
            )
            st.success("Organization connected.")
        except APIError as exc:
            st.error(str(exc))


def render_org_selector(client: BackendClient) -> None:
    st.subheader("Active organization")
    orgs = st.session_state["orgs_by_id"]
    if not orgs:
        st.caption("No organizations connected yet.")
        return

    options = list(orgs.keys())
    labels = [build_org_option_label(org_id, orgs[org_id]) for org_id in options]
    current_active = st.session_state.get("active_org_id")
    default_index = options.index(current_active) if current_active in options else 0

    selected_label = st.selectbox("Choose tenant", labels, index=default_index)
    selected_index = labels.index(selected_label)
    st.session_state["active_org_id"] = options[selected_index]

    if st.button("Refresh active dashboard", use_container_width=True):
        active_org = get_active_org_data()
        if active_org is not None:
            try:
                refreshed = client.get_dashboard(active_org["api_key"])
                update_active_org_dashboard(refreshed)
                st.success("Dashboard refreshed.")
            except APIError as exc:
                st.error(str(exc))

    if st.button("Disconnect active tenant", use_container_width=True):
        active_org_id = st.session_state["active_org_id"]
        orgs.pop(active_org_id, None)
        remaining = list(orgs.keys())
        st.session_state["active_org_id"] = remaining[0] if remaining else None
        st.rerun()


def render_sidebar_summary() -> None:
    st.subheader("Session summary")
    orgs = st.session_state["orgs_by_id"]
    st.metric("Connected tenants", len(orgs))

    total_documents = 0
    total_queries = 0
    total_tokens = 0
    total_cost = 0.0

    for org_data in orgs.values():
        dashboard = org_data.get("dashboard", {})
        docs = dashboard.get("documents", [])
        queries = dashboard.get("queries", [])
        usage = dashboard.get("usage_summary", {})

        total_documents += len(docs)
        total_queries += len(queries)
        total_tokens += safe_int(usage.get("total_tokens"))
        total_cost += safe_float(usage.get("total_estimated_cost_usd"))

    col1, col2 = st.columns(2)
    col1.metric("Documents", total_documents)
    col2.metric("Queries", total_queries)
    st.metric("Total tokens", total_tokens)
    st.metric("Total estimated cost", f"${total_cost:.6f}")


# ============================================================
# Empty state
# ============================================================
def render_empty_state() -> None:
    st.info(
        "No organization connected yet. Create a new organization from the sidebar "
        "or connect an existing one with its API key."
    )
    st.markdown("### Suggested flow")
    st.markdown(
        """
1. Create organization or connect existing tenant
2. Select the active organization
3. Ingest a document
4. Ask questions
5. Watch the dashboard update from persisted backend data
"""
    )


# ============================================================
# Main actions
# ============================================================
def render_actions_panel(client: BackendClient, active_org: Dict[str, Any]) -> None:
    dashboard = active_org["dashboard"]
    org_name = dashboard.get("organization_name", active_org.get("label", "organization"))

    st.subheader(f"Active tenant: {org_name}")
    render_active_org_metadata(active_org)
    st.divider()
    render_ingest_document_section(client, active_org)
    st.divider()
    render_ask_question_section(client, active_org)
    st.divider()
    render_last_operation_panel()


def render_active_org_metadata(active_org: Dict[str, Any]) -> None:
    dashboard = active_org["dashboard"]
    org_id = dashboard.get("organization_id", "-")
    org_name = dashboard.get("organization_name", "-")
    created_at = dashboard.get("organization_created_at", "-")

    col1, col2 = st.columns(2)
    col1.metric("Organization", org_name)
    col2.metric("Created at", created_at)
    st.caption(f"Organization ID: {org_id}")

    with st.expander("API key", expanded=False):
        st.code(active_org["api_key"], language=None)

    with st.expander("Raw dashboard payload", expanded=False):
        st.json(dashboard)


def render_ingest_document_section(
    client: BackendClient,
    active_org: Dict[str, Any],
) -> None:
    st.markdown("### Ingest document")
    with st.form("ingest_document_form", clear_on_submit=True):
        st.text_input(
            "Active tenant",
            value=active_org["dashboard"].get("organization_name", "-"),
            disabled=True,
        )
        uploaded_file = st.file_uploader(
            "Upload document",
            type=["pdf", "txt", "md"],
            help="Adjust this list to match your backend support.",
        )
        submitted = st.form_submit_button("Ingest document", use_container_width=True)

    if submitted:
        if uploaded_file is None:
            st.error("Please upload a file.")
            return

        try:
            result = client.ingest_document(active_org["api_key"], uploaded_file)
            st.session_state["last_ingest_response"] = result
            refreshed = client.get_dashboard(active_org["api_key"])
            update_active_org_dashboard(refreshed)
            st.success("Document ingested successfully.")
            st.json(result)
        except APIError as exc:
            st.error(str(exc))


def render_ask_question_section(
    client: BackendClient,
    active_org: Dict[str, Any],
) -> None:
    st.markdown("### Ask question")
    with st.form("ask_question_form", clear_on_submit=True):
        st.text_input(
            "Active tenant",
            value=active_org["dashboard"].get("organization_name", "-"),
            disabled=True,
        )
        question = st.text_area(
            "Question",
            placeholder="What is this document about?",
            height=120,
        )
        submitted = st.form_submit_button("Ask question", use_container_width=True)

    if submitted:
        clean_question = (question or "").strip()
        if not clean_question:
            st.error("Question cannot be empty.")
            return

        try:
            result = client.ask_question(active_org["api_key"], clean_question)
            st.session_state["last_question_response"] = result
            refreshed = client.get_dashboard(active_org["api_key"])
            update_active_org_dashboard(refreshed)
            st.success("Question answered successfully.")

            answer = result.get("answer") or result.get("generated_answer") or ""
            st.markdown("#### Answer")
            st.write(answer)

            cols = st.columns(5)
            cols[0].metric("Model", str(result.get("model_name", "-")))
            cols[1].metric("Prompt tokens", safe_int(result.get("prompt_tokens")))
            cols[2].metric("Completion tokens", safe_int(result.get("completion_tokens")))
            cols[3].metric("Total tokens", safe_int(result.get("total_tokens")))
            cols[4].metric("Latency ms", safe_int(result.get("latency_ms")))

            estimated_cost = safe_float(result.get("estimated_cost_usd"))
            st.caption(f"Estimated cost: ${estimated_cost:.6f}")

            with st.expander("Raw question response", expanded=False):
                st.json(result)
        except APIError as exc:
            st.error(str(exc))


def render_last_operation_panel() -> None:
    st.markdown("### Last responses")
    create_response = st.session_state.get("last_create_response")
    ingest_response = st.session_state.get("last_ingest_response")
    question_response = st.session_state.get("last_question_response")

    if not any([create_response, ingest_response, question_response]):
        st.caption("No operations executed yet in this Streamlit session.")
        return

    if create_response:
        with st.expander("Last create organization response", expanded=False):
            st.json(create_response)

    if ingest_response:
        with st.expander("Last ingest response", expanded=False):
            st.json(ingest_response)

    if question_response:
        with st.expander("Last question response", expanded=False):
            st.json(question_response)


# ============================================================
# Dashboard rendering
# ============================================================
def render_dashboard_panel(active_org: Dict[str, Any]) -> None:
    st.subheader("Dashboard")
    dashboard = active_org["dashboard"]
    render_usage_summary(dashboard)
    st.divider()
    render_documents_table(dashboard)
    st.divider()
    render_queries_table(dashboard)


def render_usage_summary(dashboard: Dict[str, Any]) -> None:
    usage = dashboard.get("usage_summary", {})

    st.markdown("### Usage summary")
    models_used = usage.get("models_used", [])
    model_label = ", ".join(models_used) if models_used else "-"

    col1, col2 = st.columns(2)
    col1.metric("Requests", safe_int(usage.get("request_count")))
    col2.metric("Model(s)", model_label)

    col1, col2, col3 = st.columns(3)
    col1.metric("Prompt tokens", safe_int(usage.get("total_prompt_tokens")))
    col2.metric("Completion tokens", safe_int(usage.get("total_completion_tokens")))
    col3.metric("Total tokens", safe_int(usage.get("total_tokens")))

    st.metric(
        "Estimated total cost",
        f"${safe_float(usage.get('total_estimated_cost_usd')):.6f}",
    )


def render_documents_table(dashboard: Dict[str, Any]) -> None:
    st.markdown("### Documents")
    documents = dashboard.get("documents", [])
    if not documents:
        st.caption("No documents for this organization yet.")
        return

    rows = []
    total_chunks = 0
    for doc in documents:
        chunks_created = safe_int(doc.get("chunks_created"))
        total_chunks += chunks_created
        rows.append(
            {
                "document_id": doc.get("document_id", "-"),
                "filename": doc.get("filename", "-"),
                "created_at": doc.get("created_at", "-"),
                "chunks_created": chunks_created,
            }
        )

    col1, col2 = st.columns(2)
    col1.metric("Documents", len(rows))
    col2.metric("Total chunks", total_chunks)

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def render_queries_table(dashboard: Dict[str, Any]) -> None:
    st.markdown("### Queries")
    queries = dashboard.get("queries", [])
    if not queries:
        st.caption("No queries for this organization yet.")
        return

    rows = []
    for query in queries:
        rows.append(
            {
                "query_id": query.get("query_id", "-"),
                "question": query.get("question", "-"),
                "created_at": query.get("created_at", "-"),
                "model_name": query.get("model_name", "-"),
                "total_tokens": safe_int(query.get("total_tokens")),
                "estimated_cost_usd": safe_float(query.get("estimated_cost_usd")),
            }
        )

    st.metric("Queries", len(rows))
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ============================================================
# State helpers
# ============================================================
def store_connected_org(api_key: str, dashboard: Dict[str, Any], label: str) -> None:
    org_id = dashboard.get("organization_id")
    if not org_id:
        raise ValueError("Dashboard payload does not contain organization_id")

    st.session_state["orgs_by_id"][org_id] = {
        "api_key": api_key,
        "dashboard": dashboard,
        "label": label,
    }
    st.session_state["active_org_id"] = org_id


def get_active_org_data() -> Optional[Dict[str, Any]]:
    active_org_id = st.session_state.get("active_org_id")
    if not active_org_id:
        return None
    return st.session_state["orgs_by_id"].get(active_org_id)


def update_active_org_dashboard(dashboard: Dict[str, Any]) -> None:
    active_org_id = st.session_state.get("active_org_id")
    if not active_org_id:
        return

    org_data = st.session_state["orgs_by_id"].get(active_org_id)
    if org_data is None:
        return

    org_data["dashboard"] = dashboard
    st.session_state["orgs_by_id"][active_org_id] = org_data


def build_org_option_label(org_id: str, org_data: Dict[str, Any]) -> str:
    dashboard = org_data.get("dashboard", {})
    name = dashboard.get("organization_name") or org_data.get("label") or "organization"
    docs = len(dashboard.get("documents", []))
    queries = len(dashboard.get("queries", []))
    short_id = org_id[:8]
    return f"{name} · docs:{docs} · queries:{queries} · {short_id}"


def extract_api_key(payload: Dict[str, Any]) -> str:
    for key in ["api_key", "organization_api_key", "x_api_key"]:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


# ============================================================
# Small helpers
# ============================================================
def safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


if __name__ == "__main__":
    main()
