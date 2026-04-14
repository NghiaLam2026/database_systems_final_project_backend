"""Fetch web pages and save extracted text as documents for RAG ingestion.

Uses trafilatura to download and extract clean text content from URLs.
Output files are saved to ``data/documents/`` ready for the ingestion
pipeline (``scripts/ingest_documents.py``).

Source note (important):
    For *component* documents in this project, I intentionally ingest content
    only from **Tom's Hardware**. The ``--clean`` post-processing heuristics
    are therefore tuned for common Tom's Hardware patterns (e.g. newsletter
    CTAs, nav links, and comment-section markers).

    The script will still work for other websites, but **you may need to tweak**
    the cleanup patterns in this file depending on the sources you ingest.

Usage:
    python -m scripts.get_documents URL [URL ...]
    python -m scripts.get_documents URL --format markdown
    python -m scripts.get_documents URL --name my_article
    python -m scripts.get_documents --file urls.txt
    python -m scripts.get_documents URL --with-metadata --include-links
    python -m scripts.get_documents URL --favor-precision

Recommended flags for RAG-quality documents:
    python -m scripts.get_documents URL --favor-precision --no-images --clean

    --favor-precision   Strips boilerplate, ads, and peripheral content.
    --no-images         Removes image markdown (CDN URLs aren't useful for
                        text-based RAG and waste chunk space).
    --clean             Post-processes the output to remove leftover noise
                        that trafilatura misses: user comments, newsletter
                        CTAs, nav links ("MORE: ..."), author bios, etc.

    Tables are kept by default (--include-tables) because spec comparison
    tables are high-value content for PC hardware RAG.

    If too much content is stripped, try without --favor-precision, or add
    --favor-recall to capture more (at the cost of some noise).
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from trafilatura import extract, fetch_url
from trafilatura.settings import Extractor

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "documents"

_FORMAT_EXTENSIONS = {
    "txt": ".txt",
    "markdown": ".md",
    "xml": ".xml",
    "json": ".json",
}

# --------------------------------------------------------------------------
# Noise patterns for --clean post-processing
# --------------------------------------------------------------------------

# Lines that are entirely one of these patterns get dropped.
_BOILERPLATE_LINE_PATTERNS = [
    re.compile(r"^-\s*MORE:\s+", re.IGNORECASE),
    re.compile(r"^Get .{3,60}('s)?\s+best .{3,40},?\s+straight to your inbox", re.IGNORECASE),
    re.compile(r"^Sign up to .{3,80}newsletter", re.IGNORECASE),
    re.compile(r"^Subscribe\b", re.IGNORECASE),
    re.compile(r"^(Read more|See also|Related):?\s*$", re.IGNORECASE),
]

# Once one of these patterns is seen, everything after it (inclusive) is
# treated as comment/footer noise and removed.  The heuristic looks for
# common comment-section markers that trafilatura sometimes misses.
_COMMENT_SECTION_MARKERS = [
    # "...Reply" at end of a non-table line (user comments on tech sites)
    re.compile(r"^(?!\|).*\bReply\s*$"),
    re.compile(r"^(?!\|).*\bReply\b.{0,5}$"),
    re.compile(r".*\bsaid:\s*$", re.IGNORECASE),
]

# Standalone lines that look like residual UI elements.
_UI_RESIDUE_PATTERNS = [
    re.compile(r"^-\s*$"),                   # bare "- " separators
    re.compile(r"^-\s*-\s*$"),               # "- -"
    re.compile(r"^-\s*\+\s*$"),              # "- +"
    re.compile(r"^\|\s*$"),                   # bare pipe
]

def _clean_content(text: str) -> str:
    """Remove boilerplate, comment sections, and UI noise from extracted text."""
    lines = text.split("\n")
    cleaned: list[str] = []
    in_comment_section = False

    for line in lines:
        stripped = line.strip()

        if in_comment_section:
            continue

        for marker in _COMMENT_SECTION_MARKERS:
            if marker.search(stripped):
                in_comment_section = True
                break
        if in_comment_section:
            continue

        if any(pat.match(stripped) for pat in _BOILERPLATE_LINE_PATTERNS):
            continue

        if any(pat.match(stripped) for pat in _UI_RESIDUE_PATTERNS):
            continue

        cleaned.append(line)

    # Remove trailing blank lines
    while cleaned and not cleaned[-1].strip():
        cleaned.pop()

    return "\n".join(cleaned)

def _slugify(text: str, max_len: int = 80) -> str:
    """Turn a string into a filesystem-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "_", text)
    return text[:max_len].strip("_")

def _filename_from_url(url: str, fmt: str) -> str:
    """Derive a filename from the URL path."""
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    if path:
        slug = _slugify(path.split("/")[-1])
    else:
        slug = _slugify(parsed.netloc)

    if not slug:
        slug = "document"

    ext = _FORMAT_EXTENSIONS.get(fmt, ".txt")
    return f"{slug}{ext}"

def _load_urls_from_file(filepath: str) -> list[str]:
    """Read URLs from a text file, one per line."""
    path = Path(filepath)
    if not path.exists():
        print(f"[error] URL file not found: {filepath}")
        sys.exit(1)

    urls = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            urls.append(line)
    return urls

def fetch_and_extract(
    url: str,
    *,
    output_format: str,
    custom_name: str | None,
    with_metadata: bool,
    include_links: bool,
    include_images: bool,
    include_tables: bool,
    include_comments: bool,
    include_formatting: bool,
    favor_precision: bool,
    favor_recall: bool,
    no_fallback: bool,
    target_language: str | None,
    clean: bool,
) -> Path | None:
    """Fetch a URL, extract content, and save to data/documents/."""
    print(f"\nFetching: {url}")
    downloaded = fetch_url(url)
    if downloaded is None:
        print(f"  [error] Failed to download: {url}")
        return None

    options = Extractor(
        output_format=output_format,
        with_metadata=with_metadata,
        links=include_links,
        images=include_images,
        tables=include_tables,
        comments=include_comments,
        formatting=include_formatting,
        precision=favor_precision,
        recall=favor_recall,
        fast=no_fallback,
        lang=target_language,
        url=url,
    )

    content = extract(downloaded, options=options)

    if not content or not content.strip():
        print(f"  [error] No content extracted from: {url}")
        return None

    if clean:
        before = len(content)
        content = _clean_content(content)
        removed = before - len(content)
        if removed > 0:
            print(f"  [clean] removed {removed:,} chars of noise")

    if custom_name:
        ext = _FORMAT_EXTENSIONS.get(output_format, ".txt")
        filename = f"{_slugify(custom_name)}{ext}"
    else:
        filename = _filename_from_url(url, output_format)

    output_path = OUTPUT_DIR / filename

    counter = 1
    base = output_path.stem
    while output_path.exists():
        output_path = OUTPUT_DIR / f"{base}_{counter}{output_path.suffix}"
        counter += 1

    output_path.write_text(content, encoding="utf-8")
    char_count = len(content)
    line_count = content.count("\n") + 1
    print(f"  [done] {char_count:,} chars, {line_count} lines -> {output_path.name}")

    # Write sidecar metadata file for the ingestion pipeline
    meta_path = output_path.with_suffix(output_path.suffix + ".meta.json")
    sidecar = {
        "source_url": url,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "output_format": output_format,
        "flags": {
            "favor_precision": favor_precision,
            "favor_recall": favor_recall,
            "no_fallback": no_fallback,
            "clean": clean,
            "include_tables": include_tables,
            "include_images": include_images,
            "include_comments": include_comments,
            "include_links": include_links,
            "include_formatting": include_formatting,
            "with_metadata": with_metadata,
        },
    }
    meta_path.write_text(json.dumps(sidecar, indent=2), encoding="utf-8")

    return output_path

def main():
    parser = argparse.ArgumentParser(
        description="Fetch web pages and save extracted text for RAG ingestion.",
        epilog=(
            "Output files are saved to data/documents/ for use with ingest_documents.py.\n\n"
            "Recommended for RAG:\n"
            "  python -m scripts.get_documents URL --favor-precision --no-images --clean"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "urls",
        nargs="*",
        help="One or more URLs to fetch and extract.",
    )
    parser.add_argument(
        "--file", "-f",
        dest="url_file",
        help="Path to a text file containing URLs (one per line).",
    )
    parser.add_argument(
        "--name", "-n",
        dest="custom_name",
        help="Custom filename (without extension) for the output. "
             "Only works when fetching a single URL.",
    )
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=["txt", "markdown", "xml", "json"],
        default="txt",
        help="Output format (default: txt).",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Post-process output to remove comment sections, newsletter "
             "CTAs, nav links, and other noise trafilatura may miss. "
             "Recommended for RAG.",
    )
    parser.add_argument(
        "--with-metadata",
        action="store_true",
        help="Include metadata (title, date, etc.) in the output.",
    )
    parser.add_argument(
        "--include-links",
        action="store_true",
        help="Preserve link targets in the output.",
    )
    parser.add_argument(
        "--include-images",
        action="store_true",
        default=True,
        help="Keep image references (default: enabled).",
    )
    parser.add_argument(
        "--no-images",
        action="store_true",
        help="Exclude image references from the output.",
    )
    parser.add_argument(
        "--include-tables",
        action="store_true",
        default=True,
        help="Extract text from HTML tables (default: enabled).",
    )
    parser.add_argument(
        "--no-tables",
        action="store_true",
        help="Exclude tables from the output.",
    )
    parser.add_argument(
        "--include-comments",
        action="store_true",
        help="Include comment sections from articles.",
    )
    parser.add_argument(
        "--include-formatting",
        action="store_true",
        help="Preserve text formatting (bold, italic, etc.).",
    )
    parser.add_argument(
        "--favor-precision",
        action="store_true",
        help="Prioritize precision (less noise, may miss some content).",
    )
    parser.add_argument(
        "--favor-recall",
        action="store_true",
        help="Prioritize recall (more content, may include noise).",
    )
    parser.add_argument(
        "--no-fallback",
        action="store_true",
        help="Skip fallback algorithms for faster extraction.",
    )
    parser.add_argument(
        "--language",
        dest="target_language",
        help="Target language (2-letter ISO 639-1 code, e.g. 'en'). "
             "Discards results that don't match.",
    )
    args = parser.parse_args()

    urls = list(args.urls) if args.urls else []
    if args.url_file:
        urls.extend(_load_urls_from_file(args.url_file))

    if not urls:
        parser.error("Provide at least one URL or use --file to supply a URL list.")

    if args.custom_name and len(urls) > 1:
        parser.error("--name can only be used with a single URL.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    include_images = args.include_images and not args.no_images
    include_tables = args.include_tables and not args.no_tables

    saved: list[Path] = []
    failed: list[str] = []

    for url in urls:
        result = fetch_and_extract(
            url,
            output_format=args.output_format,
            custom_name=args.custom_name,
            with_metadata=args.with_metadata,
            include_links=args.include_links,
            include_images=include_images,
            include_tables=include_tables,
            include_comments=args.include_comments,
            include_formatting=args.include_formatting,
            favor_precision=args.favor_precision,
            favor_recall=args.favor_recall,
            no_fallback=args.no_fallback,
            target_language=args.target_language,
            clean=args.clean,
        )
        if result:
            saved.append(result)
        else:
            failed.append(url)

    print(f"\n{'='*50}")
    print(f"Results: {len(saved)} saved, {len(failed)} failed")
    if saved:
        print(f"Output directory: {OUTPUT_DIR}")
        for p in saved:
            print(f"  - {p.name}")
    if failed:
        print("Failed URLs:")
        for u in failed:
            print(f"  - {u}")

    if saved:
        print(f"\nNext step: python -m scripts.ingest_documents")


if __name__ == "__main__":
    main()