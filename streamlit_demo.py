import os
from typing import Any, Dict, List, Optional

import requests
import streamlit as st


# ============================================================
# Top-down wiring
# ============================================================
# 1. Configure page
# 2. Create API client
# 3. Render main workflow panels in order:
#    - Create organization
#    - Ingest document(s)
#    - Ask question(s)
# 4. Render accumulated session state on the right side
# 5. Reuse small helpers for HTTP, formatting, aggregation
#
# Important design decision:
# - This version does NOT require any new GET endpoints.
# - It uses ONLY the pydantic responses returned by:
#     POST /api/organizations
#     POST /api/ingest-document
#     POST /api/questions
# - The dashboard/state panel is therefore session-based for the current user.
# ============================================================


# ============================================================
# Configuration
# ============================================================
DEFAULT_API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
REQUEST_TIMEOUT_SECONDS = 60


# ============================================================
# API client
# ============================================================
class APIError(Exception):
    pass


class BackendClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def create_organization(self, name: str) -> Dict[str, Any]:
        payload = {"name": name}
        return self._post_json("/api/organizations", json=payload)

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
        payload = {"question": question}
        headers = {"X-API-Key": api_key}
        return self._post_json("/api/questions", json=payload, headers=headers)

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


# ============================================================
# Session state
# ============================================================
def initialize_session_state() -> None:
    defaults = {
        "organization": None,
        "organization_api_key": "",
        "documents": [],
        "questions": [],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ============================================================
# App entrypoint
# ============================================================
def main() -> None:
    st.set_page_config(
        page_title="AI Knowledge System Demo",
        page_icon="🧠",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    initialize_session_state()

    st.title("🧠 AI Knowledge System Demo")
    st.caption("Session-based demo using only the 3 existing POST endpoints")

    with st.expander("Backend connection", expanded=False):
        api_base_url = st.text_input("FastAPI base URL", value=DEFAULT_API_BASE_URL)
    client = BackendClient(api_base_url)

    left_col, right_col = st.columns([1.55, 1], gap="large")

    with left_col:
        render_workflow(client)

    with right_col:
        render_session_status_panel()


# ============================================================
# Workflow panels
# ============================================================
def render_workflow(client: BackendClient) -> None:
    st.subheader("Workflow")

    render_create_organization_section(client)
    st.divider()
    render_ingest_document_section(client)
    st.divider()
    render_ask_question_section(client)


def render_create_organization_section(client: BackendClient) -> None:
    st.markdown("### 1) Create organization")
    st.caption("This is the mandatory first step. The session starts from zero.")

    if st.session_state.get("organization") is not None:
        st.success("Organization already created in this session.")
        with st.expander("Current organization metadata", expanded=True):
            st.json(st.session_state["organization"])

        if st.button("Start new demo session", use_container_width=True):
            reset_demo_session()
            st.rerun()
        return

    with st.form("create_org_form", clear_on_submit=False):
        org_name = st.text_input("Organization name", placeholder="acme-inc")
        submitted = st.form_submit_button("Create organization", use_container_width=True)

    if submitted:
        clean_name = (org_name or "").strip()
        if not clean_name:
            st.error("Organization name cannot be empty.")
            return

        try:
            result = client.create_organization(clean_name)
            st.session_state["organization"] = result
            st.session_state["organization_api_key"] = extract_api_key(result)
            st.success("Organization created successfully.")
            st.json(result)
        except APIError as exc:
            st.error(str(exc))


def render_ingest_document_section(client: BackendClient) -> None:
    st.markdown("### 2) Ingest document")

    organization = st.session_state.get("organization")
    if organization is None:
        st.info("Create an organization first to enable document ingestion.")
        return

    api_key = st.session_state.get("organization_api_key", "")

    with st.form("ingest_document_form", clear_on_submit=True):
        st.text_input("API key", value=mask_secret(api_key), disabled=True)
        uploaded_file = st.file_uploader(
            "Upload document",
            type=["pdf", "txt", "md"],
            help="Adjust file types according to your backend.",
        )
        submitted = st.form_submit_button("Ingest document", use_container_width=True)

    if submitted:
        if not api_key:
            st.error("No API key found in session.")
            return
        if uploaded_file is None:
            st.error("Please upload a file.")
            return

        try:
            result = client.ingest_document(api_key, uploaded_file)
            enriched_result = enrich_document_result(result, uploaded_file.name)
            st.session_state["documents"].append(enriched_result)
            st.success("Document ingested successfully.")
            st.json(enriched_result)
        except APIError as exc:
            st.error(str(exc))

    if st.session_state["documents"]:
        st.markdown("#### Ingested documents in this session")
        for index, document in enumerate(st.session_state["documents"], start=1):
            with st.expander(f"Document {index}", expanded=False):
                st.json(document)


def render_ask_question_section(client: BackendClient) -> None:
    st.markdown("### 3) Ask question")

    organization = st.session_state.get("organization")
    if organization is None:
        st.info("Create an organization first to enable questions.")
        return

    api_key = st.session_state.get("organization_api_key", "")

    with st.form("ask_question_form", clear_on_submit=True):
        st.text_input("API key", value=mask_secret(api_key), disabled=True, key="masked_question_api_key")
        question = st.text_area(
            "Question",
            placeholder="What is this document about?",
            height=120,
        )
        submitted = st.form_submit_button("Ask question", use_container_width=True)

    if submitted:
        clean_question = (question or "").strip()
        if not api_key:
            st.error("No API key found in session.")
            return
        if not clean_question:
            st.error("Question cannot be empty.")
            return

        try:
            result = client.ask_question(api_key, clean_question)
            enriched_result = enrich_question_result(result, clean_question)
            st.session_state["questions"].append(enriched_result)
            st.success("Question answered successfully.")

            answer = enriched_result.get("answer") or enriched_result.get("generated_answer") or ""
            st.markdown("#### Answer")
            st.write(answer)

            cols = st.columns(5)
            cols[0].metric("Model", str(enriched_result.get("model_name", "-")))
            cols[1].metric("Prompt tokens", safe_int(enriched_result.get("prompt_tokens")))
            cols[2].metric("Completion tokens", safe_int(enriched_result.get("completion_tokens")))
            cols[3].metric("Total tokens", safe_int(enriched_result.get("total_tokens")))
            cols[4].metric("Latency ms", safe_int(enriched_result.get("latency_ms")))

            estimated_cost = enriched_result.get("estimated_cost_usd")
            if estimated_cost is not None:
                st.caption(f"Estimated cost: ${float(estimated_cost):.6f}")

            with st.expander("Raw response"):
                st.json(enriched_result)
        except APIError as exc:
            st.error(str(exc))

    if st.session_state["questions"]:
        st.markdown("#### Question history in this session")
        for index, item in enumerate(st.session_state["questions"], start=1):
            question_text = item.get("question", f"Question {index}")
            with st.expander(f"Q{index}: {truncate_text(question_text, 80)}", expanded=False):
                st.json(item)


# ============================================================
# Right-side session state panel
# ============================================================
def render_session_status_panel() -> None:
    st.subheader("Current session status")
    st.caption("Everything shown here is built only from accumulated POST responses.")

    render_organization_status()
    st.divider()
    render_documents_status()
    st.divider()
    render_questions_status()
    st.divider()
    render_usage_summary()


def render_organization_status() -> None:
    st.markdown("### Organization")
    organization = st.session_state.get("organization")

    if organization is None:
        st.caption("No organization created yet in this session.")
        return

    org_id = organization.get("organization_id") or organization.get("id") or "-"
    name = organization.get("name") or "-"
    created_at = organization.get("created_at") or "-"
    api_key = extract_api_key(organization)

    cols = st.columns(2)
    cols[0].metric("Name", name)
    cols[1].metric("Created at", created_at)

    st.caption(f"Organization ID: {org_id}")
    if api_key:
        st.code(api_key, language=None)

    with st.expander("Raw organization response"):
        st.json(organization)


def render_documents_status() -> None:
    st.markdown("### Documents")
    documents = st.session_state.get("documents", [])

    if not documents:
        st.caption("No documents ingested yet.")
        return

    total_documents = len(documents)
    total_chunks = sum(extract_chunk_count(doc) for doc in documents)

    cols = st.columns(2)
    cols[0].metric("Documents ingested", total_documents)
    cols[1].metric("Total chunks created", total_chunks)

    for index, document in enumerate(documents, start=1):
        filename = document.get("uploaded_filename") or document.get("filename") or f"Document {index}"
        chunk_count = extract_chunk_count(document)
        label = f"{filename} · {chunk_count} chunks"
        with st.expander(label, expanded=False):
            st.json(document)


def render_questions_status() -> None:
    st.markdown("### Questions")
    questions = st.session_state.get("questions", [])

    if not questions:
        st.caption("No questions asked yet.")
        return

    st.metric("Questions asked", len(questions))

    for index, item in enumerate(questions, start=1):
        question_text = item.get("question") or f"Question {index}"
        answer = item.get("answer") or item.get("generated_answer") or ""
        with st.expander(truncate_text(question_text, 90), expanded=False):
            st.write(answer)
            st.json(item)


def render_usage_summary() -> None:
    st.markdown("### LLM usage summary")
    questions = st.session_state.get("questions", [])

    if not questions:
        st.caption("No LLM usage yet.")
        return

    total_prompt_tokens = sum(safe_int(item.get("prompt_tokens")) for item in questions)
    total_completion_tokens = sum(safe_int(item.get("completion_tokens")) for item in questions)
    total_tokens = sum(safe_int(item.get("total_tokens")) for item in questions)
    total_cost = sum(safe_float(item.get("estimated_cost_usd")) for item in questions)
    request_count = len(questions)
    model_names = unique_non_empty([str(item.get("model_name", "")).strip() for item in questions])

    cols = st.columns(2)
    cols[0].metric("Requests", request_count)
    cols[1].metric("Model(s)", ", ".join(model_names) if model_names else "-")

    cols = st.columns(3)
    cols[0].metric("Prompt tokens", total_prompt_tokens)
    cols[1].metric("Completion tokens", total_completion_tokens)
    cols[2].metric("Total tokens", total_tokens)

    st.metric("Accumulated estimated cost (USD)", f"${total_cost:.6f}")


# ============================================================
# Helpers
# ============================================================
def reset_demo_session() -> None:
    st.session_state["organization"] = None
    st.session_state["organization_api_key"] = ""
    st.session_state["documents"] = []
    st.session_state["questions"] = []



def extract_api_key(payload: Dict[str, Any]) -> str:
    possible_keys = ["api_key", "organization_api_key", "x_api_key"]
    for key in possible_keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""



def enrich_document_result(result: Dict[str, Any], uploaded_filename: str) -> Dict[str, Any]:
    enriched = dict(result)
    if "uploaded_filename" not in enriched:
        enriched["uploaded_filename"] = uploaded_filename
    return enriched



def enrich_question_result(result: Dict[str, Any], original_question: str) -> Dict[str, Any]:
    enriched = dict(result)
    if not enriched.get("question"):
        enriched["question"] = original_question
    return enriched



def extract_chunk_count(document_payload: Dict[str, Any]) -> int:
    candidates = [
        document_payload.get("chunks_created"),
        document_payload.get("chunk_count"),
        document_payload.get("chunks_count"),
        document_payload.get("chunks"),
    ]
    for value in candidates:
        parsed = safe_int(value)
        if parsed:
            return parsed
    return 0



def mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}{'*' * (len(value) - 8)}{value[-4:]}"



def truncate_text(text: str, max_len: int) -> str:
    clean = (text or "").strip()
    if len(clean) <= max_len:
        return clean
    return clean[: max_len - 3] + "..."



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



def unique_non_empty(values: List[str]) -> List[str]:
    result: List[str] = []
    seen = set()
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


if __name__ == "__main__":
    main()
