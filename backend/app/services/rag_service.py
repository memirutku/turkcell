import logging

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_milvus import Milvus

from app.config import Settings

logger = logging.getLogger(__name__)


class RAGService:
    """
    RAG retrieval service that searches Turkish telecom documents
    indexed in Milvus using Gemini embeddings.

    Uses lazy connection pattern: Milvus and embedding clients are
    created on first use, not at init time.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._vector_store: Milvus | None = None
        self._embeddings: GoogleGenerativeAIEmbeddings | None = None

    def _get_embeddings(self) -> GoogleGenerativeAIEmbeddings:
        """Lazy-init Gemini embedding client."""
        if self._embeddings is None:
            self._embeddings = GoogleGenerativeAIEmbeddings(
                model="models/gemini-embedding-001",
                google_api_key=self._settings.gemini_api_key,
            )
        return self._embeddings

    def _get_vector_store(self) -> Milvus:
        """Lazy-init Milvus vector store connection with error handling."""
        if self._vector_store is None:
            try:
                connection_args = {
                    "uri": f"http://{self._settings.milvus_host}:{self._settings.milvus_port}"
                }
                self._vector_store = Milvus(
                    embedding_function=self._get_embeddings(),
                    collection_name=self._settings.milvus_collection_name,
                    connection_args=connection_args,
                )
            except Exception as e:
                logger.warning("Failed to connect to Milvus: %s", e)
                raise
        return self._vector_store

    async def search(self, query: str, top_k: int = 5) -> list[dict]:
        """
        Search for relevant document chunks matching the given Turkish query.

        Args:
            query: Turkish text query to search for.
            top_k: Number of top results to return (default 5).

        Returns:
            List of dicts with 'content', 'metadata', and 'score' keys.
        """
        try:
            vector_store = self._get_vector_store()
            docs_with_scores = vector_store.similarity_search_with_score(query, k=top_k)
            results = []
            for doc, score in docs_with_scores:
                results.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": round(float(score), 4),
                })
            return results
        except Exception as e:
            logger.error("RAG search failed: %s", e)
            return []

    @property
    def is_available(self) -> bool:
        """Check if the RAG service has the required API key configured."""
        return bool(self._settings.gemini_api_key)
