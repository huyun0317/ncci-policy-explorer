# 30-Minute Demo Script

## Links to open before the meeting

- Public application: https://ncci-policy-explorer.onrender.com
- Source manual inside the application: https://ncci-policy-explorer.onrender.com/manual
- System architecture image: https://github.com/huyun0317/ncci-policy-explorer/blob/main/docs/system-design-diagram.png
- System design document: https://github.com/huyun0317/ncci-policy-explorer/blob/main/docs/SYSTEM_DESIGN.md
- Private source repository: https://github.com/huyun0317/ncci-policy-explorer
- Health check: https://ncci-policy-explorer.onrender.com/api/health

## Five-minute preparation checklist

Open the application, architecture image, and repository in separate browser tabs. Visit the health-check URL until it returns a status of `ok`. Render's free service may sleep after inactivity, so wake it at least five minutes before the meeting. Submit the modifier 59 question once to confirm that the model and citations are working. Return the application to its initial state before sharing your screen. Keep the architecture image open at full size and set the browser zoom so all labels are legible.

The demo is designed to take approximately 27 minutes of presentation and three minutes of questions. The quoted sections below are the words to say. The action notes are not part of the spoken script.

---

## 0:00-1:30 - Opening and outcome

**Action:** Share the application tab with the full page visible.

**Say:**

"Thank you for the opportunity to present my solution. I built NCCI Policy Explorer, an AI-assisted research application over the CMS 2026 Medicare National Correct Coding Initiative Policy Manual. The live application is available at ncci-policy-explorer dot onrender dot com.

The product has two main capabilities. First, it turns the manual into a set of dynamic, reproducible insights about chapters, policy topics, and frequently referenced codes. Second, it provides a citation-grounded chat experience in which every answer is based on retrieved passages and links back to the supporting PDF page.

My goal was not to build a production billing system in a few hours. My goal was to demonstrate an understandable retrieval pipeline, transparent evidence, graceful failure behavior, and a clear path from a small prototype to a production architecture. I will first show the user experience, then explain the system design and tradeoffs, and finally close with the improvements I would make next."

## 1:30-3:30 - Problem framing and design principles

**Action:** Keep the application visible. Point to the title, the model status, the policy insights panel, and the chat panel.

**Say:**

"The source manual contains 287 pages of detailed coding policy. A user may know a CPT code, a modifier, a service, or a policy concept, but may not know which chapter or page contains the relevant rule. Traditional keyword search can find exact phrases, but it requires the user to interpret many matches. A general language model can summarize text, but an unsupported answer is not acceptable for policy research.

I therefore used three design principles. The first principle is evidence before generation. The system retrieves passages before it asks a model to write an answer. The second principle is visible provenance. A reviewer can open the exact page behind every source. The third principle is graceful degradation. If the model is unavailable, the application still returns ranked evidence instead of becoming unusable.

The interface also states that this is a policy research tool. It is not medical, legal, or billing advice, and a user should confirm a coding decision against the complete CMS manual and applicable edit files."

## 3:30-6:00 - Dynamic insights

**Action:** Move the pointer over the policy insights panel. Point to the page count, passage count, section count, topic signals, chapter coverage, and code list.

**Say:**

"I will start with the dynamic insights on the left. These values are not hard-coded. They are computed during ingestion from the same passages used for retrieval.

The application extracted all 287 physical PDF pages and produced 884 overlapping, sentence-aware passages. Each passage retains its physical page number and inferred chapter. The interface then displays manual-wide aggregates, including topic mentions, chapter word volume, and frequently referenced code-like values.

These insights serve two purposes. They give a user a quick orientation to the manual, and they demonstrate that the ingestion pipeline is doing more than storing raw pages. The aggregates are deterministic and reproducible, so they do not consume model tokens each time the page loads.

The code list is intentionally labeled as descriptive rather than prescriptive. A high frequency does not make a code more important and is not a coding recommendation. It simply reveals patterns in the source document. In a production version, I would add filters by chapter, policy family, and manual release so users could compare changes over time."

## 6:00-10:30 - Live question one: modifier 59

**Action:** Click the suggested question for modifier 59, or enter the following question and click **Ask**.

> When may modifier 59 be used to bypass an NCCI procedure-to-procedure edit, and what documentation is required?

**Say while the answer loads:**

"This question is useful because it requires the system to combine a general modifier rule with the conditions for bypassing an edit. It also tests whether the answer distinguishes permission from automatic approval. The model does not receive the entire manual. It receives the user question and the top six retrieved passages, each with a numbered source label."

**Action:** When the answer appears, point to the model status, the conditions in the answer, and the citation numbers.

**Say:**

"The answer identifies the important conditions. An associated modifier may be used only when the edit permits it and the clinical circumstances satisfy the modifier criteria. The answer also explains that documentation must support the distinct encounter, anatomic site, specimen, or other applicable basis. It does not say that modifier 59 can be used simply to obtain payment.

The answer is synthesized with GPT-5.6 Sol using low reasoning. Low reasoning is a deliberate latency and cost tradeoff for a constrained summarization task. The retrieval layer supplies the policy evidence, while the model's job is to organize that evidence into a concise response.

The citations are not decorative. Each citation number maps to one of the retrieved passages returned by the server. The application validates that cited numbers fall within the supplied evidence range. If the model omits citations or invents a source number, the server can surface a citation warning."

## 10:30-13:30 - Verify a citation in the manual

**Action:** Click one of the page 30 or page 33 citations. Let the bundled PDF open on the cited page. Highlight the relevant policy language visually without selecting or editing the PDF.

**Say:**

"I can now verify the answer against the source. The citation opens the complete CMS manual at the physical PDF page used during retrieval. The passage states that modifiers should not be used merely to bypass an NCCI edit and that documentation must satisfy the criteria for the modifier.

I chose page-level citations because physical pages are stable, understandable, and easy to verify in the official document. The tradeoff is that page-level provenance is broader than a highlighted sentence span. A production version would retain the page link while also storing character offsets or sentence identifiers so the interface could highlight the precise supporting text.

This verification step is central to the product. The application is designed to help a user reach the policy evidence faster, not to hide the evidence behind a confident answer."

**Action:** Return to the application tab.

## 13:30-16:30 - Live question two: policy distinction

**Action:** Enter the following question and click **Ask**.

> How does the manual distinguish medically unlikely edits from other utilization edits?

**Say while the answer loads:**

"The second question tests conceptual retrieval rather than a single exact modifier phrase. It asks the system to explain a distinction and support it with the manual."

**Action:** Point to the answer structure and its citations.

**Say:**

"The response explains the distinction using the retrieved policy language and provides citations that can be opened in the same way. This demonstrates the value of synthesis. A raw search result would show several passages, while the answer organizes the relevant definitions and limitations into a direct comparison.

This example also exposes the main limitation of my current retrieval approach. SQLite full-text search is strong for exact policy terms, abbreviations, and CPT or HCPCS codes. It can be weaker when a user paraphrases a concept with different vocabulary. I accepted that tradeoff for this prototype because the solution remains deterministic, inspectable, inexpensive, and easy to run locally. My first retrieval improvement would be hybrid search that combines FTS5 with embeddings, followed by a lightweight reranker."

## 16:30-18:00 - Search and failure behavior

**Action:** Point to the evidence-first label and the model status at the top of the application.

**Say:**

"The application separates retrieval from generation. Search results are available even without an OpenAI key. If the model call fails or the configured model is unavailable, the answer layer falls back to an evidence-only response containing the best excerpts and source links.

That fallback is important because model synthesis is an enhancement to the research workflow, not the only way to access the manual. The user should still be able to inspect relevant policy text during an external service failure. The health endpoint also reports whether the application is running in OpenAI mode or evidence-only mode, which helps with deployment monitoring and demo readiness."

## 18:00-22:30 - System architecture

**Action:** Open the full-resolution architecture image.

**Say:**

"This diagram separates the architecture into an index-build flow and a per-question flow.

The top row is the index build. The source is the CMS 2026 manual bundled as a PDF. The ingestion module uses pypdf to extract every page, normalizes repeated headers and extraction artifacts, infers chapter identifiers, and creates sentence-aware chunks of roughly 190 words with a two-sentence overlap. The overlap reduces the chance that an important rule is split across two independent passages.

Each chunk is stored with its physical page and chapter metadata. SQLite FTS5 indexes the text, and BM25 provides lexical ranking. The same ingestion pass computes the topic, chapter, and code aggregates shown in the interface. The generated database is excluded from Git because it can be reproduced from the source PDF.

The bottom row is the question-answering path. The browser sends a question to the Python API. The retrieval layer builds a safe full-text query, ranks matches, and adds page diversity so the top results are not six overlapping passages from one page. The top six passages become numbered evidence in a constrained prompt.

GPT-5.6 Sol produces the draft answer. The server then validates the citation identifiers and returns the answer, evidence, metadata, and source links to the browser. If generation is unavailable, the dashed path returns ranked evidence excerpts instead.

The application uses a small Python standard-library HTTP server rather than a larger web framework. That choice minimized setup time and dependencies for the exercise. It is appropriate for a low-traffic demonstration, but I would use a production application server and framework for authentication, middleware, structured validation, concurrency controls, and operational tooling."

## 22:30-25:00 - Grounding, safety, and trust boundaries

**Action:** Point to the trust-boundaries band at the bottom of the architecture image.

**Say:**

"There are three important trust boundaries.

First, the OpenAI API key is stored only as a protected Render environment secret and is not committed to Git or sent to the browser. Second, retrieved PDF content is treated as reference data rather than instructions. That reduces the risk that document text can override the answer policy. Third, every citation resolves to the source page, so users can independently inspect the supporting policy.

The Responses API request uses store false. The model sees the question and selected evidence, not unrelated application data. The application is also read-only, so it cannot submit claims, modify coding records, or make payment decisions.

Citation validation is useful but not sufficient by itself. It can detect an invalid citation number, but it does not prove that every statement is entailed by the cited text. A production evaluation suite should measure retrieval recall, answer faithfulness, citation correctness, refusal behavior, and consistency across representative coding questions."

## 25:00-27:00 - Deployment and operations

**Action:** Return to the application briefly, then show the repository root or `render.yaml` if helpful.

**Say:**

"The source is stored in a private GitHub repository and deployed through a Render Blueprint. A push to the main branch triggers a build, installs the single runtime dependency, and starts the application over HTTPS. Render injects the port and protected model configuration.

The free Render filesystem is ephemeral, so startup checks whether the SQLite index exists. If it does not, the application rebuilds the index from the bundled PDF. Render monitors the health endpoint and can restart an unhealthy instance.

The free tier may sleep after inactivity, which can add a cold-start delay. For a production service, I would use an always-on instance, persist versioned indexes in durable storage, build new indexes in a background job, and switch releases atomically after validation. I would also add structured logs, tracing, latency and token metrics, alerts, rate limits, and cost budgets."

## 27:00-29:00 - Tradeoffs and next iteration

**Say:**

"The strongest aspect of this solution is that it is small enough to understand end to end. Ingestion, ranking, model context, citation mapping, fallback behavior, and deployment are all visible in the code. That transparency was more valuable for this assignment than adding several managed services without time to evaluate them.

The main tradeoff is retrieval recall. Lexical BM25 search is excellent for codes and exact terms but is not the best solution for every paraphrase. My next iteration would add hybrid retrieval, a reranker, and a small gold evaluation set with questions from multiple chapters. I would compare the current baseline with the hybrid version before accepting the extra cost and complexity.

The next product improvement would be more precise evidence presentation. I would add highlighted sentence spans, chapter and topic filters, conversation context with explicit source carryover, and side-by-side comparison between manual releases. I would preserve the current evidence-first behavior and the ability to operate without model synthesis."

## 29:00-30:00 - Closing

**Action:** Return to the main application screen with both panels visible.

**Say:**

"To summarize, NCCI Policy Explorer ingests the complete 2026 CMS manual, builds a reproducible retrieval index, generates dynamic insights, answers policy questions with GPT-5.6 Sol, and links every source back to the manual. It also remains useful when model synthesis is unavailable.

The live application is ncci-policy-explorer dot onrender dot com, and the repository includes the source code, setup instructions, tests, deployment configuration, architecture diagram, and system design document.

Thank you. I am happy to answer questions or explore another policy question live."

---

## Optional questions if the live demo moves quickly

Use one of these only if extra time remains:

1. "What documentation is required when procedures are reported at separate anatomic sites?"
2. "When may an NCCI procedure-to-procedure edit with a CCMI of 1 be bypassed?"
3. "What does the manual say about reporting anesthesia services performed by the operating physician?"
4. "How should a provider interpret a medically unlikely edit value?"

## Short answers to likely reviewer questions

### Why did you choose SQLite FTS5 instead of embeddings?

"I wanted a transparent and reproducible baseline that performs well for exact coding terminology and identifiers. SQLite FTS5 requires no external search service and makes ranking easy to inspect. I would add embeddings only after measuring the baseline and identifying recall failures on a representative evaluation set."

### Why did you choose GPT-5.6 Sol with low reasoning?

"The model is performing constrained synthesis over retrieved evidence rather than solving an open-ended reasoning problem. Low reasoning provides a practical balance of answer quality, latency, and cost. The model is configurable, and the application can fall back to another model or to evidence-only results."

### How do you prevent hallucinations?

"I reduce hallucination risk by retrieving first, limiting model context to numbered evidence, instructing the model not to invent coding rules, requiring inline citations, validating citation numbers, and making every source directly inspectable. I would add automated faithfulness evaluation and sentence-level entailment checks for production use."

### How would this scale to more manuals?

"I would store documents and versioned indexes in durable managed services, add document and release metadata to every passage, run ingestion asynchronously, and route retrieval through a hybrid search service. The citation contract would remain the same, so every answer would still resolve to a specific document version and source span."

### What happens when the manual changes?

"The ingestion pipeline computes a source hash and builds a reproducible index. In production, I would create a new versioned index for each CMS release, run retrieval and faithfulness evaluations, and switch traffic only after the new index passes validation. I would retain older versions for auditability and comparison."

### What would you test next?

"I would create a gold set of questions covering exact codes, modifiers, paraphrases, chapter-spanning policies, ambiguous questions, and questions that the manual cannot answer. I would measure retrieval recall at six, citation precision, answer faithfulness, latency, fallback behavior, and cost per question."

## Backup language for demo problems

If Render is waking up, say: "This application is on Render's free tier, which sleeps after inactivity. The cold start is a hosting-plan behavior rather than an application dependency. While it wakes, I will explain the architecture, and then I will return to the live question."

If the model call fails, say: "The application has intentionally degraded to evidence-only mode. The retrieved passages and page links remain available, which demonstrates that source access does not depend on model generation."

If a question retrieves weak evidence, say: "This is a useful example of the limitation of lexical retrieval. I would capture this question in the evaluation set and use it to test whether hybrid retrieval and reranking improve recall without reducing precision."

