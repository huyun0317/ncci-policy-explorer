from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

from pypdf import PdfReader


CHAPTERS = {
    "Front": "Complete Table of Contents",
    "Intro": "Introduction",
    "I": "General Correct Coding Policies",
    "II": "Anesthesia Services",
    "III": "Surgery Integumentary System",
    "IV": "Surgery Musculoskeletal System",
    "V": "Surgery Respiratory Cardiovascular Hemic and Lymphatic Systems",
    "VI": "Surgery Digestive System",
    "VII": "Surgery Urinary Genital Maternity Care and Delivery Systems",
    "VIII": "Surgery Endocrine Nervous Eye and Auditory Systems",
    "IX": "Radiology Services",
    "X": "Pathology and Laboratory Services",
    "XI": "Medicine and Evaluation and Management Services",
    "XII": "Supplemental Services",
    "XIII": "Category III Codes",
}

TOPIC_PATTERNS = {
    "Modifiers": re.compile(r"\bmodifier(?:s)?\b", re.I),
    "Medically Unlikely Edits": re.compile(r"\b(?:MUEs?|Medically Unlikely Edits?)\b", re.I),
    "Procedure-to-Procedure Edits": re.compile(r"\b(?:PTP|procedure-to-procedure)\b", re.I),
    "Evaluation and Management": re.compile(r"\b(?:E&M|evaluation and management)\b", re.I),
    "Anesthesia": re.compile(r"\banesthes(?:ia|iology|etic)\w*\b", re.I),
    "Global Surgery": re.compile(r"\bglobal surgery\b", re.I),
    "Bundling and Unbundling": re.compile(r"\b(?:bundl\w+|unbundl\w+)\b", re.I),
}

MARKER_RE = re.compile(
    r"\b(Intro|XIII|XII|XI|IX|VIII|VII|VI|IV|III|II|X|V|I)\s*-\s*\d+\b",
    re.I,
)
DATE_LINE_RE = re.compile(
    r"^(?:Revision Date \(Medicare\):\s*)?1/1/2026$|^January 1, 2026(?:\s+Page\s+\d+)?$",
    re.I,
)
CODE_RE = re.compile(r"\b(?:\d{5}|[A-V]\d{4})\b")


@dataclass(frozen=True)
class Chunk:
    page: int
    chapter_code: str
    chapter_title: str
    text: str
    word_count: int


def _normalize_paragraphs(text: str) -> list[str]:
    text = text.replace("\x00", " ").replace("\u00ad", "")
    # The source PDF occasionally places a word's first capital on its own line.
    text = re.sub(r"(?m)^([A-Z])\s*\n(?=[a-z])", r"\1", text)
    paragraphs: list[str] = []
    for raw in re.split(r"\n\s*\n", text):
        lines = []
        for line in raw.splitlines():
            clean = re.sub(r"\s+", " ", line).strip()
            if not clean or DATE_LINE_RE.match(clean) or MARKER_RE.fullmatch(clean):
                continue
            lines.append(clean)
        if lines:
            paragraph = " ".join(lines)
            paragraph = re.sub(r"\b([A-Z]) ([A-Z]{1,4}s)\b", r"\1\2", paragraph)
            paragraphs.append(paragraph)
    return paragraphs


def clean_page_text(text: str) -> str:
    return "\n\n".join(_normalize_paragraphs(text))


def infer_chapter(raw_text: str, previous: str = "Front") -> str:
    marker = MARKER_RE.search(raw_text[:700])
    if marker:
        value = marker.group(1)
        return "Intro" if value.lower() == "intro" else value.upper()
    if "Complete Table of Contents" in raw_text[:400]:
        return "Front"
    return previous


def _split_sentences(text: str) -> list[str]:
    compact = re.sub(r"\s+", " ", text).strip()
    if not compact:
        return []
    return [
        item.strip()
        for item in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9(])", compact)
        if item.strip()
    ]


def chunk_text(text: str, target_words: int = 190, overlap_sentences: int = 2) -> list[str]:
    sentences = _split_sentences(text)
    if not sentences:
        return []

    chunks: list[str] = []
    current: list[str] = []
    current_words = 0

    for sentence in sentences:
        sentence_words = len(sentence.split())
        if current and current_words + sentence_words > target_words:
            chunks.append(" ".join(current))
            current = current[-overlap_sentences:]
            current_words = sum(len(item.split()) for item in current)
        current.append(sentence)
        current_words += sentence_words

    if current:
        final = " ".join(current)
        if not chunks or final != chunks[-1]:
            chunks.append(final)
    return chunks


def chunks_from_pages(pages: Sequence[str]) -> list[Chunk]:
    chunks: list[Chunk] = []
    chapter_code = "Front"
    for page_number, raw_text in enumerate(pages, start=1):
        chapter_code = infer_chapter(raw_text, chapter_code)
        cleaned = clean_page_text(raw_text)
        for passage in chunk_text(cleaned):
            chunks.append(
                Chunk(
                    page=page_number,
                    chapter_code=chapter_code,
                    chapter_title=CHAPTERS.get(chapter_code, chapter_code),
                    text=passage,
                    word_count=len(passage.split()),
                )
            )
    return chunks


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _insight_payload(chunks: Iterable[Chunk], total_pages: int) -> dict:
    chunk_list = list(chunks)
    combined = "\n".join(chunk.text for chunk in chunk_list)
    topic_counts = {
        label: len(pattern.findall(combined)) for label, pattern in TOPIC_PATTERNS.items()
    }
    code_counts = Counter(CODE_RE.findall(combined))
    chapter_counts: dict[str, dict] = {}
    for chunk in chunk_list:
        current = chapter_counts.setdefault(
            chunk.chapter_code,
            {
                "code": chunk.chapter_code,
                "title": chunk.chapter_title,
                "pages": set(),
                "chunks": 0,
                "words": 0,
            },
        )
        current["pages"].add(chunk.page)
        current["chunks"] += 1
        current["words"] += chunk.word_count

    order = list(CHAPTERS)
    chapters = []
    for code in order:
        if code not in chapter_counts:
            continue
        item = chapter_counts[code]
        chapters.append(
            {
                "code": code,
                "title": item["title"],
                "pages": len(item["pages"]),
                "chunks": item["chunks"],
                "words": item["words"],
            }
        )

    return {
        "pages": total_pages,
        "chunks": len(chunk_list),
        "words": sum(chunk.word_count for chunk in chunk_list),
        "chapters": chapters,
        "topics": [
            {"label": label, "count": count}
            for label, count in sorted(topic_counts.items(), key=lambda item: item[1], reverse=True)
        ],
        "frequent_codes": [
            {"code": code, "count": count} for code, count in code_counts.most_common(10)
        ],
    }


def build_index(
    pages: Sequence[str],
    db_path: str | Path,
    source_path: str | Path | None = None,
) -> dict:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = db_path.with_suffix(db_path.suffix + ".building")
    if temp_path.exists():
        temp_path.unlink()

    chunks = chunks_from_pages(pages)
    insights = _insight_payload(chunks, len(pages))
    source = Path(source_path) if source_path else None
    metadata = {
        "source_name": source.name if source else "in-memory-pages",
        "source_sha256": _sha256(source) if source and source.exists() else "",
        "indexed_at": datetime.now(timezone.utc).isoformat(),
        "insights": json.dumps(insights),
    }

    connection = sqlite3.connect(temp_path)
    try:
        connection.executescript(
            """
            PRAGMA journal_mode = WAL;
            CREATE TABLE metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE chunks (
                id INTEGER PRIMARY KEY,
                page INTEGER NOT NULL,
                chapter_code TEXT NOT NULL,
                chapter_title TEXT NOT NULL,
                text TEXT NOT NULL,
                word_count INTEGER NOT NULL
            );
            CREATE VIRTUAL TABLE chunks_fts USING fts5(
                text,
                chapter_title,
                tokenize = 'porter unicode61'
            );
            CREATE INDEX chunks_page_idx ON chunks(page);
            CREATE INDEX chunks_chapter_idx ON chunks(chapter_code);
            """
        )
        connection.executemany(
            "INSERT INTO metadata(key, value) VALUES (?, ?)", metadata.items()
        )
        for chunk in chunks:
            cursor = connection.execute(
                """
                INSERT INTO chunks(page, chapter_code, chapter_title, text, word_count)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    chunk.page,
                    chunk.chapter_code,
                    chunk.chapter_title,
                    chunk.text,
                    chunk.word_count,
                ),
            )
            connection.execute(
                "INSERT INTO chunks_fts(rowid, text, chapter_title) VALUES (?, ?, ?)",
                (cursor.lastrowid, chunk.text, chunk.chapter_title),
            )
        connection.commit()
    finally:
        connection.close()

    os.replace(temp_path, db_path)
    return insights


def ingest_pdf(pdf_path: str | Path, db_path: str | Path) -> dict:
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"Manual not found: {pdf_path}")
    reader = PdfReader(str(pdf_path))
    pages = [(page.extract_text() or "") for page in reader.pages]
    if not any(page.strip() for page in pages):
        raise ValueError("The PDF did not contain extractable text.")
    return build_index(pages, db_path, pdf_path)
