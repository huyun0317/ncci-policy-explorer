# NCCI Policy Explorer

NCCI Policy Explorer is a small, explainable retrieval-augmented application for the CMS 2026 Medicare NCCI Coding Policy Manual. It combines index-generated policy insights with a citation-grounded question-and-answer interface.

The project is intentionally scoped for a take-home exercise: it favors transparent retrieval, page-level provenance, and a small operational footprint over production infrastructure.

For a guided presentation, use the [30-minute demo script](docs/DEMO_SCRIPT.md).

## What it does

- Ingests all 287 pages of the CMS PDF with `pypdf`.
- Cleans repeated page headers and splits each page into overlapping, sentence-aware passages.
- Indexes passages in SQLite FTS5 and ranks them with BM25.
- Generates manual-wide topic, chapter, and code-frequency insights during ingestion.
- Answers questions with the OpenAI Responses API when `OPENAI_API_KEY` is configured.
- Falls back to evidence search when no model key is available.
- Links every retrieved citation directly to the supporting PDF page.

## Run locally

Requirements: Python 3.10 or newer.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py ingest
python app.py serve
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000).

The supplied manual should be located at `data/2026-ncci-medicare-policy-manual-all-chapters.pdf`. A different file can be provided with `python app.py ingest --pdf /path/to/manual.pdf` and the same `--pdf` value when serving.

## Enable synthesized answers

The app is fully testable in evidence-search mode without a model key. To enable generated answers, copy `.env.example` to `.env` and set:

```text
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-5.6
OPENAI_REASONING_EFFORT=low
OPENAI_FALLBACK_MODEL=gpt-4.1-mini
```

The answer step uses the Responses API with `store: false`. The `gpt-5.6` alias runs with low reasoning by default. GPT-5.6 requires an API project with model access and billing; if the API returns `model_not_found`, the app retries with the configured fallback and identifies the model used in the interface.

## Deploy on Render

The included `render.yaml` defines a free Python web service. Push this folder to a Git repository, create a new Render Blueprint from that repository, and enter `OPENAI_API_KEY` when Render prompts for the secret.

Render supplies `PORT` automatically. The app detects Render, binds to `0.0.0.0`, and rebuilds the SQLite index from the included PDF whenever the generated database is absent. The free filesystem can therefore remain ephemeral.

## Architecture

See the [system design document](docs/SYSTEM_DESIGN.md), [full-resolution architecture image](docs/system-design-diagram.png), and [editable Mermaid source](docs/system-design.mmd) for the component model, request flow, trust boundaries, deployment topology, tradeoffs, and production evolution.

```text
CMS PDF
  -> page-aware extraction and cleaning
  -> sentence-aware chunks with page and chapter metadata
  -> SQLite FTS5 index and ingestion-time insights
  -> BM25 retrieval with page diversity
  -> constrained answer prompt
  -> inline citations and links to the source PDF
```

The browser communicates with a small standard-library HTTP server. `GET /api/insights` returns aggregates built from the indexed manual; `GET /api/search` exposes retrieval results; and `POST /api/chat` performs retrieval followed by optional synthesis.

## Grounding strategy

Each retrieved passage keeps its physical PDF page and inferred chapter. The model receives only the top six passages, each labeled with a citation number. Its instructions require a citation after every factual claim, forbid unsupported coding rules, and explicitly treat retrieved content as reference data rather than instructions. The server checks that citations are within the supplied evidence range and reports a warning if the model omits or invents a citation.

This is page-level, not sentence-level, provenance. Page citations are dependable and easy to verify in the original manual, but they can be broader than a production-grade span citation.

## Tradeoffs and next steps

SQLite FTS5 keeps setup fast, deterministic, and inspectable. It works especially well for CPT and HCPCS codes and exact policy language. It is less effective for paraphrases than a semantic embedding index. A production iteration would add hybrid dense and lexical retrieval, reranking, automated retrieval and faithfulness evaluation, OCR fallback, authentication, audit logging, and a formal update process for new CMS releases.

The interface is intentionally read-only and should not be used as medical, legal, or billing advice. Reviewers can open every citation in the complete manual before relying on a policy statement.

## Tests

```bash
python -m unittest discover -s tests -v
```

The tests cover chapter inference, chunking, page-aware retrieval, dynamic insight generation, and citation validation.

## Command-line option

The same pipeline can be exercised without the web interface:

```bash
python app.py ask "How does the manual distinguish MUEs from utilization edits?"
```

## Source

CMS, 2026 Medicare NCCI Coding Policy Manual: https://www.cms.gov/files/document/2026-ncci-medicare-policy-manual-all-chapters.pdf
