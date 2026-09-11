from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path


STOP_WORDS = {
    "a", "about", "an", "and", "are", "as", "at", "be", "by", "can", "do",
    "does", "for", "from", "how", "i", "if", "in", "is", "it", "may", "of",
    "on", "or", "should", "that", "the", "this", "to", "under", "what", "when",
    "where", "which", "with",
}
TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9&-]*")


@dataclass(frozen=True)
class SearchHit:
    id: int
    page: int
    chapter_code: str
    chapter_title: str
    text: str
    word_count: int
    rank: float
    citation: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


def _connection(db_path: str | Path) -> sqlite3.Connection:
    connection = sqlite3.connect(f"file:{Path(db_path)}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def _fts_query(question: str) -> str:
    tokens = []
    seen = set()
    for token in TOKEN_RE.findall(question):
        normalized = token.lower().strip("-")
        if len(normalized) < 2 or normalized in STOP_WORDS or normalized in seen:
            continue
        seen.add(normalized)
        tokens.append(normalized)
    if not tokens:
        tokens = [token.lower() for token in TOKEN_RE.findall(question)[:4]]
    return " OR ".join(f'"{token.replace(chr(34), "")}"' for token in tokens[:14])


def search(db_path: str | Path, question: str, limit: int = 6) -> list[SearchHit]:
    query = _fts_query(question)
    if not query:
        return []

    with _connection(db_path) as connection:
        rows = connection.execute(
            """
            SELECT
                c.id,
                c.page,
                c.chapter_code,
                c.chapter_title,
                c.text,
                c.word_count,
                bm25(chunks_fts, 1.0, 0.25) AS rank
            FROM chunks_fts
            JOIN chunks c ON c.id = chunks_fts.rowid
            WHERE chunks_fts MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            (query, max(limit * 4, 20)),
        ).fetchall()

    selected: list[SearchHit] = []
    per_page: dict[int, int] = {}
    for row in rows:
        if per_page.get(row["page"], 0) >= 2:
            continue
        per_page[row["page"]] = per_page.get(row["page"], 0) + 1
        selected.append(
            SearchHit(
                id=row["id"],
                page=row["page"],
                chapter_code=row["chapter_code"],
                chapter_title=row["chapter_title"],
                text=row["text"],
                word_count=row["word_count"],
                rank=float(row["rank"]),
                citation=len(selected) + 1,
            )
        )
        if len(selected) == limit:
            break
    return selected


def get_metadata(db_path: str | Path) -> dict[str, str]:
    with _connection(db_path) as connection:
        rows = connection.execute("SELECT key, value FROM metadata").fetchall()
    return {row["key"]: row["value"] for row in rows}


def get_insights(db_path: str | Path) -> dict:
    metadata = get_metadata(db_path)
    insights = json.loads(metadata.get("insights", "{}"))
    insights["source_name"] = metadata.get("source_name", "")
    insights["indexed_at"] = metadata.get("indexed_at", "")
    return insights

