import uuid
from dataclasses import dataclass

import pytest

from app.application.use_cases import AskQuestion
from app.application.exceptions import (
    EmptyQuestionError,
    NoRelevantChunksFoundError,
    QueryPersistenceError,
    LLMUsagePersistenceError,
    QueryChunkPersistenceError,
    OrganizationNotFoundError,
    UseCaseError,
)
from app.domain.entities import Organization


FAKE_HASH = "a" * 64


def make_org(name: str = "Acme") -> Organization:
    return Organization(name=name, api_key_hash=FAKE_HASH)


@dataclass
class FakeRetrievedChunk:
    chunk_id: uuid.UUID
    similarity_score: float
    content: str = "Chunk content"
    chunk_index: int = 0


@dataclass
class FakeLLMResponse:
    generated_answer: str = "Fake answer"
    model_name: str = "fake-llm"
    latency_ms: int = 123
    prompt_tokens: int = 120
    completion_tokens: int = 10
    total_tokens: int = 130
    estimated_cost_usd: float = 0.001


class OrgRepoFake:
    def __init__(self, org=None):
        self.org = org
        self.calls = []

    def get_by_id(self, organization_id):
        self.calls.append(("get_by_id", organization_id))
        return self.org


class QueryRepoSpy:
    def __init__(self, fail_on_add=False, fail_on_update=False):
        self.fail_on_add = fail_on_add
        self.fail_on_update = fail_on_update
        self.added = []
        self.updated = []

    def add(self, query):
        if self.fail_on_add:
            raise Exception("db down on add")
        self.added.append(query)

    def update(self, query):
        if self.fail_on_update:
            raise Exception("db down on update")
        self.updated.append(query)


class LLMUsageRepoSpy:
    def __init__(self, fail_on_add=False):
        self.fail_on_add = fail_on_add
        self.added = []

    def add(self, usage):
        if self.fail_on_add:
            raise Exception("db down on llm usage add")
        self.added.append(usage)


class QueryChunkRepoSpy:
    def __init__(self, fail_on_add_links=False):
        self.fail_on_add_links = fail_on_add_links
        self.added_links = []

    def add_links(self, query_chunks):
        if self.fail_on_add_links:
            raise Exception("db down on query chunk add_links")
        self.added_links.extend(query_chunks)


class RetrieverSpy:
    def __init__(self, chunks=None, fail=False):
        self.chunks = chunks or []
        self.fail = fail
        self.calls = []

    def retrieve_best_chunks(self, organization_id, question):
        self.calls.append(("retrieve_best_chunks", organization_id, question))
        if self.fail:
            raise Exception("retriever failed")
        return self.chunks


class PromptBuilderSpy:
    def __init__(self, prompt="FINAL PROMPT", fail=False):
        self.prompt = prompt
        self.fail = fail
        self.calls = []

    def build_prompt(self, question, retrieved_chunks):
        self.calls.append(("build_prompt", question, retrieved_chunks))
        if self.fail:
            raise Exception("prompt builder failed")
        return self.prompt


class LLMClientSpy:
    def __init__(self, response=None, fail=False):
        self.response = response or FakeLLMResponse()
        self.fail = fail
        self.calls = []

    def call(self, prompt):
        self.calls.append(("call", prompt))
        if self.fail:
            raise Exception("llm failed")
        return self.response


def make_retrieved_chunk(score=0.95, content="Chunk content", chunk_index=0):
    return FakeRetrievedChunk(
        chunk_id=uuid.uuid4(),
        similarity_score=score,
        content=content,
        chunk_index=chunk_index,
    )


def build_use_case(
    org_repo=None,
    query_repo=None,
    llm_usage_repo=None,
    query_chunk_repo=None,
    retriever=None,
    prompt_builder=None,
    llm_client=None,
):
    if org_repo is None:
        org_repo = OrgRepoFake(org=make_org())
    if query_repo is None:
        query_repo = QueryRepoSpy()
    if llm_usage_repo is None:
        llm_usage_repo = LLMUsageRepoSpy()
    if query_chunk_repo is None:
        query_chunk_repo = QueryChunkRepoSpy()
    if retriever is None:
        retriever = RetrieverSpy(chunks=[make_retrieved_chunk()])
    if prompt_builder is None:
        prompt_builder = PromptBuilderSpy()
    if llm_client is None:
        llm_client = LLMClientSpy()

    uc = AskQuestion(
        org_repo=org_repo,
        query_repo=query_repo,
        llm_usage_repo=llm_usage_repo,
        query_chunk_repo=query_chunk_repo,
        retriever=retriever,
        prompt_builder=prompt_builder,
        llm_client=llm_client,
    )

    return uc, {
        "org_repo": org_repo,
        "query_repo": query_repo,
        "llm_usage_repo": llm_usage_repo,
        "query_chunk_repo": query_chunk_repo,
        "retriever": retriever,
        "prompt_builder": prompt_builder,
        "llm_client": llm_client,
    }


def test_ask_question_rejects_empty_question():
    uc, _ = build_use_case()

    with pytest.raises(EmptyQuestionError):
        uc.execute(organization_id=uuid.uuid4(), question="   ")


def test_ask_question_rejects_when_organization_does_not_exist():
    uc, _ = build_use_case(org_repo=OrgRepoFake(org=None))

    with pytest.raises(OrganizationNotFoundError):
        uc.execute(organization_id=uuid.uuid4(), question="What is RAG?")


def test_ask_question_persists_query_asap_and_raises_if_no_relevant_chunks():
    retriever = RetrieverSpy(chunks=[])
    uc, deps = build_use_case(retriever=retriever)

    with pytest.raises(NoRelevantChunksFoundError):
        uc.execute(organization_id=uuid.uuid4(), question="What is RAG?")

    assert len(deps["query_repo"].added) == 1
    persisted_query = deps["query_repo"].added[0]
    assert persisted_query.question == "What is RAG?"

    assert len(deps["prompt_builder"].calls) == 0
    assert len(deps["llm_client"].calls) == 0
    assert len(deps["llm_usage_repo"].added) == 0
    assert len(deps["query_chunk_repo"].added_links) == 0


def test_ask_question_wraps_query_add_persistence_error():
    query_repo = QueryRepoSpy(fail_on_add=True)
    uc, _ = build_use_case(query_repo=query_repo)

    with pytest.raises(QueryPersistenceError):
        uc.execute(organization_id=uuid.uuid4(), question="What is RAG?")


def test_ask_question_wraps_retriever_error():
    retriever = RetrieverSpy(fail=True)
    uc, _ = build_use_case(retriever=retriever)

    with pytest.raises(UseCaseError):
        uc.execute(organization_id=uuid.uuid4(), question="What is RAG?")


def test_ask_question_wraps_prompt_builder_error():
    prompt_builder = PromptBuilderSpy(fail=True)
    uc, _ = build_use_case(prompt_builder=prompt_builder)

    with pytest.raises(UseCaseError):
        uc.execute(organization_id=uuid.uuid4(), question="What is RAG?")


def test_ask_question_wraps_llm_error():
    llm_client = LLMClientSpy(fail=True)
    uc, _ = build_use_case(llm_client=llm_client)

    with pytest.raises(UseCaseError):
        uc.execute(organization_id=uuid.uuid4(), question="What is RAG?")


def test_ask_question_happy_path_returns_answer_and_persists_everything():
    organization_id = uuid.uuid4()
    chunks = [
        make_retrieved_chunk(score=0.91, content="RAG retrieves relevant chunks.", chunk_index=0),
        make_retrieved_chunk(score=0.88, content="The LLM answers using that context.", chunk_index=1),
    ]
    llm_response = FakeLLMResponse(
        generated_answer="RAG first retrieves relevant chunks and then the LLM answers from that context.",
        model_name="fake-llm",
        latency_ms=123,
        prompt_tokens=120,
        completion_tokens=10,
        total_tokens=130,
        estimated_cost_usd=0.001,
    )

    uc, deps = build_use_case(
        org_repo=OrgRepoFake(org=make_org()),
        retriever=RetrieverSpy(chunks=chunks),
        prompt_builder=PromptBuilderSpy(prompt="FINAL PROMPT"),
        llm_client=LLMClientSpy(response=llm_response),
    )

    result = uc.execute(
        organization_id=organization_id,
        question="  What is RAG?  ",
    )

    assert result.query_id is not None
    assert result.question == "What is RAG?"
    assert result.answer == llm_response.generated_answer
    assert result.model_name == "fake-llm"
    assert result.latency_ms == 123
    assert result.prompt_tokens == 120
    assert result.completion_tokens == 10
    assert result.total_tokens == 130
    assert result.estimated_cost_usd == 0.001

    assert len(deps["query_repo"].added) == 1
    added_query = deps["query_repo"].added[0]
    assert added_query.organization_id == organization_id
    assert added_query.question == "What is RAG?"
    assert added_query.answer is None

    assert len(deps["retriever"].calls) == 1
    assert len(deps["prompt_builder"].calls) == 1
    assert len(deps["llm_client"].calls) == 1
    assert deps["llm_client"].calls[0][1] == "FINAL PROMPT"

    assert len(deps["query_repo"].updated) == 1
    updated_query = deps["query_repo"].updated[0]
    assert updated_query.answer == llm_response.generated_answer
    assert updated_query.latency_ms == 123

    assert len(deps["llm_usage_repo"].added) == 1
    usage = deps["llm_usage_repo"].added[0]
    assert usage.model_name == "fake-llm"
    assert usage.prompt_tokens == 120
    assert usage.completion_tokens == 10
    assert usage.total_tokens == 130
    assert usage.estimated_cost_usd == 0.001

    assert len(deps["query_chunk_repo"].added_links) == 2
    assert deps["query_chunk_repo"].added_links[0].rank == 1
    assert deps["query_chunk_repo"].added_links[1].rank == 2


def test_ask_question_trims_question_before_persisting():
    uc, deps = build_use_case()

    uc.execute(
        organization_id=uuid.uuid4(),
        question="   What is vector search?   ",
    )

    assert len(deps["query_repo"].added) == 1
    persisted_query = deps["query_repo"].added[0]
    assert persisted_query.question == "What is vector search?"


def test_ask_question_wraps_query_update_persistence_error():
    query_repo = QueryRepoSpy(fail_on_update=True)
    uc, _ = build_use_case(query_repo=query_repo)

    with pytest.raises(QueryPersistenceError):
        uc.execute(organization_id=uuid.uuid4(), question="What is RAG?")


def test_ask_question_wraps_llm_usage_persistence_error():
    llm_usage_repo = LLMUsageRepoSpy(fail_on_add=True)
    uc, _ = build_use_case(llm_usage_repo=llm_usage_repo)

    with pytest.raises(LLMUsagePersistenceError):
        uc.execute(organization_id=uuid.uuid4(), question="What is RAG?")


def test_ask_question_wraps_query_chunk_persistence_error():
    query_chunk_repo = QueryChunkRepoSpy(fail_on_add_links=True)
    uc, _ = build_use_case(query_chunk_repo=query_chunk_repo)

    with pytest.raises(QueryChunkPersistenceError):
        uc.execute(organization_id=uuid.uuid4(), question="What is RAG?")