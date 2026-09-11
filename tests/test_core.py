from __future__ import annotations

import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
import json

from ncci.answer import answer_question, validate_citations
from ncci.ingest import build_index, chunk_text, clean_page_text, infer_chapter
from ncci.retrieval import SearchHit, get_insights, search


class ChunkingTests(unittest.TestCase):
    def test_infers_roman_chapter_from_page_header(self) -> None:
        text = "Revision Date (Medicare): 1/1/2026\nIV-12\nPolicy text"
        self.assertEqual(infer_chapter(text), "IV")

    def test_chunks_long_text_with_overlap(self) -> None:
        text = " ".join(f"Sentence {number} explains policy." for number in range(100))
        chunks = chunk_text(text, target_words=45, overlap_sentences=2)
        self.assertGreater(len(chunks), 3)
        self.assertTrue(all(chunk.strip() for chunk in chunks))

    def test_repairs_split_initial_capitals(self) -> None:
        text = "R\nevision Date (Medicare): 1/1/2026\nM\nost policy text applies. M\nUEs are coding edits."
        self.assertEqual(clean_page_text(text), "Most policy text applies. MUEs are coding edits.")


class RetrievalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "test.db"
        pages = [
            "January 1, 2026 Page 1\nComplete Table of Contents\nGeneral information.",
            "Revision Date (Medicare): 1/1/2026\nI-3\nModifier 59 may be used only under appropriate circumstances. The documentation must support a distinct service.",
            "Revision Date (Medicare): 1/1/2026\nI-4\nMedically Unlikely Edits are coding edits and are not utilization edits.",
        ]
        build_index(pages, self.db_path)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_search_returns_page_aware_result(self) -> None:
        hits = search(self.db_path, "Is an MUE a utilization edit?", limit=3)
        self.assertTrue(hits)
        self.assertEqual(hits[0].page, 3)
        self.assertEqual(hits[0].citation, 1)

    def test_insights_are_generated_from_content(self) -> None:
        insights = get_insights(self.db_path)
        self.assertEqual(insights["pages"], 3)
        self.assertGreaterEqual(insights["chunks"], 3)


class CitationTests(unittest.TestCase):
    def test_rejects_out_of_range_citations(self) -> None:
        valid, warning = validate_citations("Supported [1], unsupported [7].", 3)
        self.assertEqual(valid, [1])
        self.assertIsNotNone(warning)

    def test_accepts_valid_citations(self) -> None:
        valid, warning = validate_citations("Policy statement [2].", 3)
        self.assertEqual(valid, [2])
        self.assertIsNone(warning)

    @patch("ncci.answer.urllib.request.urlopen")
    def test_gpt56_request_uses_low_reasoning(self, urlopen) -> None:
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return None

            def read(self):
                return json.dumps(
                    {"output": [{"type": "message", "content": [{"type": "output_text", "text": "Supported [1]."}]}]}
                ).encode("utf-8")

        urlopen.return_value = FakeResponse()
        hit = SearchHit(1, 33, "I", "General Correct Coding Policies", "Evidence.", 1, -1.0, 1)
        result = answer_question("Question?", [hit], "test-key")
        request = urlopen.call_args.args[0]
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(payload["model"], "gpt-5.6")
        self.assertEqual(payload["reasoning"], {"effort": "low"})
        self.assertEqual(result.cited, [1])
        self.assertEqual(result.model_used, "gpt-5.6")
        self.assertFalse(result.fallback_used)


if __name__ == "__main__":
    unittest.main()
