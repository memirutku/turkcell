#!/usr/bin/env python3
"""
One-time ingestion script: loads Turkish telecom documents, chunks, embeds, and indexes into Milvus.

Usage:
    cd backend && uv run python scripts/ingest_documents.py

Requires:
    - GEMINI_API_KEY set in .env or environment
    - Milvus running at MILVUS_HOST:MILVUS_PORT
"""

import logging
import sys
from pathlib import Path

# Ensure backend root is on sys.path so app.config can be imported
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings

from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_milvus import Milvus
from langchain_text_splitters import RecursiveCharacterTextSplitter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

DOCUMENTS_DIR = Path(__file__).parent.parent / "data" / "documents"

DOC_TYPE_MAP = {
    "tariff_descriptions": "tariff",
    "faq_genel": "faq",
    "kampanya_bilgileri": "campaign",
    "destek_rehberi": "support",
}

TURKISH_CHARS = set("şğüöçıİŞĞÜÖÇ")


def load_documents() -> list[Document]:
    """Load all .txt files from the documents directory."""
    documents: list[Document] = []
    txt_files = sorted(DOCUMENTS_DIR.glob("*.txt"))

    if not txt_files:
        logger.error("No .txt files found in %s", DOCUMENTS_DIR)
        sys.exit(1)

    for filepath in txt_files:
        logger.info("Loading: %s", filepath.name)
        with open(filepath, encoding="utf-8") as f:
            content = f.read()

        # Validate Turkish characters are present
        if not any(ch in TURKISH_CHARS for ch in content):
            logger.warning(
                "File %s does not contain any Turkish-specific characters (ş, ğ, ü, ö, ç, ı, İ)",
                filepath.name,
            )

        doc_type = DOC_TYPE_MAP.get(filepath.stem, "general")
        doc = Document(
            page_content=content,
            metadata={
                "source": filepath.name,
                "doc_type": doc_type,
                "language": "tr",
            },
        )
        documents.append(doc)
        logger.info(
            "  -> %d characters, doc_type=%s", len(content), doc_type
        )

    logger.info("Loaded %d documents total", len(documents))
    return documents


def chunk_documents(documents: list[Document]) -> list[Document]:
    """Split documents into chunks using RecursiveCharacterTextSplitter."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100,
        separators=["\n\n", "\n", ". ", "! ", "? ", " ", ""],
        length_function=len,
    )
    chunks = splitter.split_documents(documents)
    logger.info("Split into %d chunks (chunk_size=500, overlap=100)", len(chunks))
    return chunks


def main() -> None:
    """Main ingestion pipeline: load, chunk, embed, and index documents."""
    settings = get_settings()

    # Validate API key
    if not settings.gemini_api_key:
        logger.error(
            "GEMINI_API_KEY is not set. Please set it in .env or as an environment variable."
        )
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("Turkcell AI-Gen Document Ingestion")
    logger.info("=" * 60)
    logger.info("Milvus: %s:%d", settings.milvus_host, settings.milvus_port)
    logger.info("Collection: %s", settings.milvus_collection_name)
    logger.info("Documents dir: %s", DOCUMENTS_DIR)

    # Step 1: Load documents
    documents = load_documents()

    # Step 2: Chunk documents
    chunks = chunk_documents(documents)

    # Step 3: Create embeddings model
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001",
        google_api_key=settings.gemini_api_key,
    )
    logger.info("Embedding model: models/gemini-embedding-001")

    # Step 4: Index into Milvus
    # Note: Milvus.from_documents handles batching internally for both
    # embedding API calls and Milvus upserts, so no manual batching needed.
    connection_args = {"uri": f"http://{settings.milvus_host}:{settings.milvus_port}"}

    try:
        logger.info("Indexing %d chunks into Milvus...", len(chunks))
        vector_store = Milvus.from_documents(
            documents=chunks,
            embedding=embeddings,
            collection_name=settings.milvus_collection_name,
            connection_args=connection_args,
            drop_old=True,
        )
        logger.info(
            "Successfully indexed %d chunks into collection '%s'",
            len(chunks),
            settings.milvus_collection_name,
        )
    except Exception as exc:
        exc_name = type(exc).__name__
        if "Milvus" in exc_name or "grpc" in str(exc).lower() or "connect" in str(exc).lower():
            logger.error(
                "Failed to connect to Milvus at %s:%d. "
                "Ensure Milvus is running (docker compose up milvus-standalone). "
                "Error: %s",
                settings.milvus_host,
                settings.milvus_port,
                exc,
            )
        elif "api_key" in str(exc).lower() or "credential" in str(exc).lower():
            logger.error(
                "Embedding API error. Check that GEMINI_API_KEY is valid. Error: %s",
                exc,
            )
        else:
            logger.error("Unexpected error during indexing: %s: %s", exc_name, exc)
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("Ingestion complete!")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
