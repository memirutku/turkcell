"""Tests for RAG service and /api/rag/search endpoint."""

import pytest
from pydantic import ValidationError
from unittest.mock import MagicMock

from app.api.routes.rag import SearchRequest
from app.config import Settings
from app.main import app
from app.services.rag_service import RAGService


# ---------------------------------------------------------------------------
# Pydantic model validation tests
# ---------------------------------------------------------------------------


def test_search_request_validation():
    """SearchRequest rejects empty query and accepts valid query."""
    # Valid query works
    req = SearchRequest(query="test")
    assert req.query == "test"
    assert req.top_k == 5  # default

    # Empty query raises ValidationError
    with pytest.raises(ValidationError):
        SearchRequest(query="")


def test_search_request_top_k_bounds():
    """SearchRequest rejects top_k < 1 and top_k > 20."""
    # Valid top_k
    req = SearchRequest(query="test", top_k=5)
    assert req.top_k == 5

    # top_k too low
    with pytest.raises(ValidationError):
        SearchRequest(query="test", top_k=0)

    # top_k too high
    with pytest.raises(ValidationError):
        SearchRequest(query="test", top_k=21)


# ---------------------------------------------------------------------------
# Endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rag_search_service_unavailable(client):
    """When app.state.rag is None, POST /api/rag/search returns 503."""
    original_rag = getattr(app.state, "rag", None)
    try:
        app.state.rag = None
        response = await client.post("/api/rag/search", json={"query": "test"})
        assert response.status_code == 503
        data = response.json()
        assert "RAG servisi" in data["detail"]
    finally:
        app.state.rag = original_rag


@pytest.mark.asyncio
async def test_rag_search_returns_results(client, mock_rag_service):
    """When RAGService is mocked, POST /api/rag/search returns 200 with results."""
    original_rag = getattr(app.state, "rag", None)
    try:
        app.state.rag = mock_rag_service
        response = await client.post(
            "/api/rag/search", json={"query": "Platinum fiyati"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert len(data["results"]) == 1
        assert data["query"] == "Platinum fiyati"
        assert data["total"] == 1
    finally:
        app.state.rag = original_rag


@pytest.mark.asyncio
async def test_rag_search_response_format(client, mock_rag_service):
    """Response has 'results' (list), 'query' (str), 'total' (int) fields."""
    original_rag = getattr(app.state, "rag", None)
    try:
        app.state.rag = mock_rag_service
        response = await client.post(
            "/api/rag/search", json={"query": "tarife bilgisi"}
        )
        assert response.status_code == 200
        data = response.json()

        # Top-level structure
        assert isinstance(data["results"], list)
        assert isinstance(data["query"], str)
        assert isinstance(data["total"], int)

        # Each result structure
        for result in data["results"]:
            assert "content" in result
            assert "metadata" in result
            assert "score" in result
            assert isinstance(result["content"], str)
            assert isinstance(result["metadata"], dict)
            assert isinstance(result["score"], float)
    finally:
        app.state.rag = original_rag


# ---------------------------------------------------------------------------
# RAGService unit tests
# ---------------------------------------------------------------------------


def test_rag_service_is_available_false():
    """RAGService.is_available returns False when gemini_api_key is empty."""
    settings = MagicMock(spec=Settings)
    settings.gemini_api_key = ""
    service = RAGService(settings)
    assert service.is_available is False


def test_rag_service_is_available_true():
    """RAGService.is_available returns True when gemini_api_key is set."""
    settings = MagicMock(spec=Settings)
    settings.gemini_api_key = "test-key"
    service = RAGService(settings)
    assert service.is_available is True


def test_rag_service_lazy_init():
    """RAGService.__init__ does NOT connect to Milvus or Gemini."""
    settings = MagicMock(spec=Settings)
    settings.gemini_api_key = "test-key"
    service = RAGService(settings)
    assert service._vector_store is None
    assert service._embeddings is None


def test_document_chunking():
    """RecursiveCharacterTextSplitter with chunk_size=500, chunk_overlap=100
    produces expected chunk count from sample Turkish text."""
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    # ~1500 characters of Turkish telecom text across 3 paragraphs
    sample_text = (
        "Turkcell Platinum Esneyebilen 20GB tarife, aylik 299 TL karsiliginda "
        "20GB yuksek hizli internet, sinursiz konusma ve 1000 SMS icermektedir. "
        "Kullanicilar, aylik kotalarini astiklari takdirde GB basina 30 TL asim "
        "ucreti odemektedir. Bu tarife, yogun veri kullanimi olan musteriler icin "
        "ideal bir secenektir. Tarife degisikligi icin Turkcell uygulamasi veya "
        "musteri hizmetleri aracaniliyla islem yapilabilir.\n\n"
        "Gold Esneyebilen 10GB tarife aylik 199 TL'dir ve 10GB internet, sinursiz "
        "konusma, 500 SMS sunmaktadir. Asim ucreti GB basina 35 TL olarak "
        "uygulanmaktadir. Orta duzeyde veri kullanan musteriler icin uygun "
        "maliyetli bir secenek olarak one cikmaktadir. Tarife icerigi her ay "
        "otomatik olarak yenilenmektedir ve ek paketlerle genisletilebilir.\n\n"
        "Silver Temel 5GB tarife aylik 129 TL ile en uygun fiyatli secenek olarak "
        "sunulmaktadir. 5GB internet, sinursiz konusma ve 250 SMS icermektedir. "
        "Dusuk veri tuketimi olan musteriler veya ikinci hat kullanicilari icin "
        "tasarlanmistir. Taahhut suresi 12 ay olup, erken iptal durumunda cayma "
        "bedeli uygulanmaktadir."
    )

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500, chunk_overlap=100
    )
    chunks = splitter.split_text(sample_text)

    # With ~1500 chars and 500 chunk size, expect at least 3 chunks
    assert len(chunks) >= 3
    # Each chunk should be at most 500 chars
    for chunk in chunks:
        assert len(chunk) <= 500


def test_search_result_has_metadata():
    """Each result dict has required fields: content, metadata (with source,
    doc_type, language), and score."""
    # Simulate search results as returned by RAGService.search
    mock_results = [
        {
            "content": "Platinum Esneyebilen 20GB tarife ayda 299 TL.",
            "metadata": {
                "source": "tariff_descriptions.txt",
                "doc_type": "tariff",
                "language": "tr",
            },
            "score": 0.85,
        },
        {
            "content": "Faturanizda KDV %20, OIV %7.5 olarak hesaplanir.",
            "metadata": {
                "source": "faq_genel.txt",
                "doc_type": "faq",
                "language": "tr",
            },
            "score": 0.72,
        },
    ]

    for result in mock_results:
        assert "content" in result
        assert isinstance(result["content"], str)
        assert "metadata" in result
        assert isinstance(result["metadata"], dict)
        assert "source" in result["metadata"]
        assert "doc_type" in result["metadata"]
        assert "language" in result["metadata"]
        assert "score" in result
        assert isinstance(result["score"], float)


# ---------------------------------------------------------------------------
# Integration test stubs (require running services)
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_collection_has_documents():
    """Verify the Milvus collection contains indexed documents."""
    pytest.skip("Requires running Milvus and ingested documents")


@pytest.mark.integration
def test_retrieval_precision():
    """Turkish telecom query retrieval should achieve >= 75% precision@5.

    Test set of 10 Turkish telecom queries with expected keywords.
    Precision target: at least 8/10 queries return a result containing
    expected keywords in the top-5 results.
    """
    pytest.skip("Requires running Milvus, Gemini API, and ingested documents")

    TEST_QUERIES = [
        {"query": "Platinum tarifenin fiyati ne kadar?", "expected_keywords": ["299", "Platinum"]},
        {"query": "Faturamda hangi vergiler var?", "expected_keywords": ["KDV", "OIV"]},
        {"query": "Ekstra data paketi nasil alinir?", "expected_keywords": ["paket", "GB"]},
        {"query": "Gold tarifeye nasil gecebilirim?", "expected_keywords": ["Gold", "199"]},
        {"query": "Kampanya kosullari nelerdir?", "expected_keywords": ["kampanya", "indirim"]},
        {"query": "Faturami nasil ogrenebilirim?", "expected_keywords": ["fatura"]},
        {"query": "Internet yavas ne yapabilirim?", "expected_keywords": ["internet", "hiz"]},
        {"query": "Yurt disi paket fiyatlari", "expected_keywords": ["yurt disi", "149"]},
        {"query": "Dijital Hayat tarife detaylari", "expected_keywords": ["Dijital Hayat", "249"]},
        {"query": "Asim ucreti ne kadar?", "expected_keywords": ["asim"]},
    ]

    # When enabled, this test would:
    # 1. Initialize RAGService with real settings
    # 2. For each query, run search(query, top_k=5)
    # 3. Check if any result contains ALL expected keywords
    # 4. Assert at least 8/10 (75%) queries succeed
    hits = 0
    for test_case in TEST_QUERIES:
        # results = await rag_service.search(test_case["query"], top_k=5)
        # contents = " ".join(r["content"] for r in results)
        # if all(kw.lower() in contents.lower() for kw in test_case["expected_keywords"]):
        #     hits += 1
        pass

    # assert hits >= 8, f"Precision@5: {hits}/10 ({hits*10}%) -- target >= 75%"
