"""Ingest text/markdown documents into the RAG vector store.

Reads files from ``data/documents/``, splits them into overlapping chunks,
generates embeddings via a local Ollama model (default: ``qwen3-embedding:8b``),
and upserts into the ``documents`` + ``document_chunks`` tables.

Prerequisites:
    1. Ollama must be installed and running (``ollama serve``).
    2. Pull the embedding model: ``ollama pull qwen3-embedding:8b``

Usage:
    python -m scripts.ingest_documents                   # ingest all files
    python -m scripts.ingest_documents guide.md faq.txt  # specific files only
    python -m scripts.ingest_documents --dry-run          # preview without DB writes
    python -m scripts.ingest_documents --chunk-size 800   # custom chunk size
"""

import argparse
import json
import sys
from pathlib import Path
import sqlalchemy as sa
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings  # noqa: E402
from app.models.document import Document, DocumentChunk  # noqa: E402
from app.services.embedding import embed_texts  # noqa: E402

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "documents"
_SUPPORTED_EXTENSIONS = {".txt", ".md", ".markdown"}

_DEFAULT_CHUNK_SIZE = 1000  # characters
_DEFAULT_CHUNK_OVERLAP = 200  # characters

def _chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split *text* into overlapping chunks of roughly *chunk_size* chars."""
    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk.strip())
        start += chunk_size - overlap

    return chunks

def _discover_files(names: list[str] | None) -> list[Path]:
    """Return sorted list of document files to process."""
    if names:
        paths = []
        for name in names:
            p = DATA_DIR / name
            if not p.exists():
                print(f"  [warn] file not found: {p}")
                continue
            if p.suffix.lower() not in _SUPPORTED_EXTENSIONS:
                print(f"  [warn] unsupported extension: {p.suffix}")
                continue
            paths.append(p)
        return sorted(paths)

    return sorted(
        p
        for p in DATA_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in _SUPPORTED_EXTENSIONS
    )

def _load_sidecar(file_path: Path) -> dict | None:
    """Load the ``.meta.json`` sidecar written by ``get_documents``, if present."""
    meta_path = file_path.with_suffix(file_path.suffix + ".meta.json")
    if not meta_path.exists():
        return None
    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

def ingest_file(
    engine: sa.Engine,
    settings,
    file_path: Path,
    *,
    chunk_size: int,
    overlap: int,
    dry_run: bool,
) -> int:
    """Chunk, embed, and upsert a single document. Returns chunk count."""
    text = file_path.read_text(encoding="utf-8")
    if not text.strip():
        print(f"  [skip] {file_path.name} is empty")
        return 0

    sidecar = _load_sidecar(file_path)
    source_url = sidecar.get("source_url") if sidecar else None
    if sidecar:
        print(f"  [meta] source: {source_url or '(none)'}")

    chunks = _chunk_text(text, chunk_size, overlap)
    print(f"  {file_path.name}: {len(text)} chars -> {len(chunks)} chunks")

    if dry_run:
        for i, c in enumerate(chunks[:3]):
            preview = c[:120].replace("\n", " ")
            print(f"    chunk {i}: {preview}...")
        if len(chunks) > 3:
            print(f"    ... and {len(chunks) - 3} more")
        return len(chunks)

    doc_meta = {"path": str(file_path.relative_to(DATA_DIR))}
    if sidecar:
        doc_meta["fetched_at"] = sidecar.get("fetched_at")
        doc_meta["flags"] = sidecar.get("flags")

    print(f"  Embedding {len(chunks)} chunks...")
    vectors = embed_texts(chunks, settings, task_type="RETRIEVAL_DOCUMENT")

    with Session(engine) as session:
        existing = (
            session.query(Document)
            .filter(Document.title == file_path.name)
            .first()
        )
        if existing:
            session.query(DocumentChunk).filter(
                DocumentChunk.document_id == existing.id
            ).delete()
            doc = existing
            doc.url = source_url
            doc.source = "web" if source_url else "file"
            doc.meta = doc_meta
            print(f"  Replacing existing document (id={doc.id})")
        else:
            doc = Document(
                title=file_path.name,
                source="web" if source_url else "file",
                url=source_url,
                meta=doc_meta,
            )
            session.add(doc)
            session.flush()

        for i, (chunk_text, vector) in enumerate(zip(chunks, vectors)):
            dc = DocumentChunk(
                document_id=doc.id,
                chunk_text=chunk_text,
                embedding=vector,
                meta={"chunk_index": i},
            )
            session.add(dc)

        session.commit()
        print(f"  [done] {len(chunks)} chunks upserted for document id={doc.id}")

    return len(chunks)

def main():
    parser = argparse.ArgumentParser(
        description="Ingest text/markdown documents into the RAG vector store."
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="Specific filenames inside data/documents/ (default: all).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview chunks without writing to DB or calling the embedding API.",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=_DEFAULT_CHUNK_SIZE,
        help=f"Characters per chunk (default: {_DEFAULT_CHUNK_SIZE}).",
    )
    parser.add_argument(
        "--overlap",
        type=int,
        default=_DEFAULT_CHUNK_OVERLAP,
        help=f"Overlap between consecutive chunks (default: {_DEFAULT_CHUNK_OVERLAP}).",
    )
    args = parser.parse_args()

    settings = get_settings()
    engine = sa.create_engine(settings.database_url)

    files = _discover_files(args.files or None)
    if not files:
        print("No documents found in", DATA_DIR)
        return

    print(f"Found {len(files)} document(s) to process.\n")
    total_chunks = 0
    for f in files:
        total_chunks += ingest_file(
            engine,
            settings,
            f,
            chunk_size=args.chunk_size,
            overlap=args.overlap,
            dry_run=args.dry_run,
        )

    print(f"\nFinished. {total_chunks} total chunks processed.")

if __name__ == "__main__":
    main()