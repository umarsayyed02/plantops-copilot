# Resume and interview guide

Use only claims you can explain and demonstrate. The benchmark is intentionally small, so say “on a versioned 11-question evaluation set,” not “production accuracy.”

## Resume project entry

**PlantOps Copilot — Evaluated RAG Assistant for Maintenance Manuals**  
Python, FastAPI, BM25, BGE/FastEmbed, RAG, Pytest, CI, JavaScript

- Built a citation-first RAG application that ingests PDF, Markdown, and text maintenance manuals, retrieves supporting passages with hybrid BM25/vector search, and returns page-level evidence or safely abstains.
- Designed a versioned 11-question evaluation harness covering Recall@5, MRR, citation precision, abstention accuracy, and latency; achieved 1.00 Recall@5, 1.00 MRR, 1.00 citation precision, and 1.00 abstention accuracy on the documented synthetic benchmark.
- Added optional BGE semantic embeddings and grounded LLM generation with citation-ID validation and automatic extractive fallback; shipped the system as a tested FastAPI web app with CI, health checks, a native Python deployment, and secure public-demo controls.

### Shorter two-bullet version

- Developed an evaluated RAG assistant using FastAPI, BM25, optional BGE embeddings, evidence thresholds, and citation-backed responses for industrial maintenance manuals.
- Built 27 automated tests plus a versioned retrieval benchmark, a responsive evidence interface, a native Python deployment, and optional non-root Docker packaging validated by CI.

### GitHub description

Evaluated citation-first RAG assistant for maintenance manuals with hybrid retrieval, safe abstention, grounded LLM fallback, FastAPI, CI, and a responsive evidence UI.

## 30-second explanation

“PlantOps Copilot is a RAG assistant for maintenance manuals. A user asks a troubleshooting question, the system retrieves relevant chunks using BM25 plus an optional vector backend, applies an evidence threshold, and either returns a concise answer with traceable citations or abstains. I also built a versioned evaluation harness so I could compare the lightweight baseline against BGE embeddings using retrieval, citation, abstention, and latency metrics.”

## 90-second interview pitch

“I built PlantOps Copilot because industrial troubleshooting is a good example of where a confident unsupported answer is worse than no answer. The application ingests text-based PDFs, Markdown, and text files, splits them into overlapping chunks, and persists a local index. At query time it combines BM25 with either deterministic hashing vectors or BGE semantic embeddings, reranks the results, and filters weak evidence.

The default generator is extractive, so the project works offline. I also added Ollama and OpenAI-compatible generation, but LLM output is accepted only if it cites valid retrieved evidence IDs; otherwise the system falls back to the extractive answer. Unsupported questions produce a deliberate abstention.

The part I would emphasize is evaluation. I created a versioned set of answerable and unanswerable questions and measured Recall@5, MRR, citation precision, abstention accuracy, and latency. On this small synthetic benchmark both backends have the same quality metrics, while the baseline is faster, so I kept it as the default. That result showed me why model choices should be measured rather than assumed.”

## Five-minute demo script

1. Open the interface and point out the indexed manual and visible benchmark cards.
2. Ask: “What can cause the motor to overheat?” Show the answer, evidence score, source, excerpt, and citation ID.
3. Ask: “How do I configure satellite telemetry encryption?” Show that the assistant abstains because the manual contains no evidence.
4. Explain the architecture: ingestion, chunks, hybrid retrieval, threshold, generation, validation, citations.
5. Open the evaluation report and compare baseline versus semantic latency and quality.
6. End with one production improvement: authenticated persistent document storage plus a larger held-out evaluation set.

## Likely interview questions and strong answer points

### 1. Why is this RAG rather than fine-tuning?

The knowledge lives in changeable manuals, citations are required, and the current dataset is too small for useful fine-tuning. Retrieval keeps source content separate from model behavior and allows reindexing without retraining.

### 2. Why combine BM25 and vector retrieval?

BM25 is strong for exact equipment terms, part names, and error codes. Dense vectors help paraphrases and semantic similarity. Combining them can improve robustness, but the project keeps the weighting configurable and evaluates whether the extra latency is worthwhile.

### 3. Why did the baseline beat or match BGE here?

The corpus is tiny and the questions share vocabulary with the manual, which strongly favors lexical retrieval. The lexical baseline also produced better citation precision in the current run. The honest conclusion is not that hashing is universally better; it is that this dataset cannot yet demonstrate a semantic advantage.

### 4. How do you prevent hallucinations?

The system filters low-evidence retrieval results, tells the generator to use only supplied evidence, requires valid bracketed citation IDs, converts explicit insufficient-evidence output into abstention, and falls back to deterministic extraction when provider calls or citation validation fail.

### 5. What does the confidence score mean?

It is an average of the cited retrieval scores, not a calibrated probability that the answer is correct. In production I would calibrate it against labeled validation data or rename it more explicitly as an evidence score.

### 6. How is citation precision measured?

For each answerable evaluation case, the harness checks whether cited chunks contain a labeled expected phrase and come from the expected source. Relevant citations divided by all evaluated citations gives citation precision. Sentence-level human review would be a stronger next step.

### 7. Why use overlapping chunks?

Overlap reduces the chance that a useful procedure is split across chunk boundaries. Too much overlap creates duplicates and wastes retrieval capacity, so chunk size and overlap are configurable and should be tuned on a development set.

### 8. How does abstention work?

Retrieved hits must pass an absolute minimum score, a relative floor compared with the best hit, and non-zero query-term overlap. If no hit passes, the service returns no citations, zero confidence, and an explicit insufficient-evidence message.
Questions that request live or real-time equipment measurements are also rejected explicitly because a static document index cannot provide telemetry.

### 9. What happens if the LLM returns an invalid citation?

The validator extracts bracketed IDs and rejects missing or out-of-range references. The request then returns a locally generated extractive answer instead of exposing unsupported model output.

### 10. How would you scale this?

Move raw files to object storage, metadata and feedback to Postgres, and embeddings to a vector-capable store. Run ingestion asynchronously, add tenant-aware authorization, cache repeated queries, use structured telemetry, and deploy stateless API replicas.

### 11. What security issues remain?

Public document upload requires authentication, rate limiting, malware scanning, stricter PDF processing isolation, content quotas, and audit logs. The portfolio Blueprint disables uploads and adds basic browser security headers, but it is not presented as a complete production security boundary.

### 12. Why FastAPI?

It provides typed request validation with Pydantic, automatic OpenAPI documentation, simple async file upload handling, and a small deployment footprint. It also makes the retrieval service easy to test through an in-process client.

### 13. How did you test the system?

Unit tests cover token normalization, scoring, provider behavior, citation validation, fallback, evaluation metrics, and port configuration. API tests cover health, UI assets, queries, upload size, disabled public uploads, benchmark delivery, and security headers.

### 14. What was a bug you found while testing the UI?

An overheating suggestion initially returned a generic safety and restart sentence. Several retrieval scores had saturated at 1.0, and word forms such as “overheat” and “overheating” did not align. I added lightweight term normalization, recalibrated reranking so scores no longer saturated, and changed sentence selection to reject incidental low-overlap matches. The focused answer then cited the actual overheating passage, and citation precision improved from 0.667 to 0.778 on the small benchmark.

### 15. What would you build next?

First expand the corpus and independently reviewed evaluation set. Then add OCR, persistent authenticated storage, background ingestion, structured observability, and sentence-level reranking. I would measure each change on a held-out set before adopting it.

## Architecture whiteboard order

When asked to draw the system, use this order:

1. Documents enter an ingestion API.
2. Loaders extract page text and metadata.
3. A chunker creates overlapping evidence units.
4. The index stores chunk text, IDs, source, and page.
5. A question enters lexical and vector retrieval.
6. Scores are normalized, combined, and reranked.
7. Evidence thresholds decide answer versus abstention.
8. A generator extracts or synthesizes the answer.
9. Citation validation maps claims back to evidence.
10. The API returns answer, citations, confidence, and generator metadata.
11. Feedback and evaluation create the improvement loop.

## Claims to avoid

- Do not say “100% accurate.” Say “1.00 Recall@5 on a versioned 11-question synthetic evaluation set.”
- Do not call the evidence score a probability.
- Do not call the app production-ready; explain the remaining authentication, persistence, security, and evaluation work.
- Do not claim the BGE backend improved results when the current aggregate quality metrics are equal.
- Do not imply the synthetic manual came from a real employer or customer.

## One-week preparation plan

### Day 1: Run and explain

Run the app from scratch and deliver the 30-second and 90-second explanations without notes.

### Day 2: Retrieval fundamentals

Review TF-IDF, BM25, cosine similarity, embeddings, hybrid retrieval, chunking, and reranking. Be ready to derive precision, recall, and reciprocal rank with a small example.

### Day 3: RAG reliability

Trace supported, unsupported, provider-failure, and invalid-citation requests through the code. Explain hallucination controls and their limitations.

### Day 4: API and testing

Review FastAPI dependency flow, Pydantic validation, HTTP status codes, test isolation, fixtures, and the difference between unit, integration, and end-to-end tests.

### Day 5: Deployment

Deploy with the native Python Blueprint and explain build/start commands, dynamic ports, ephemeral storage, CI-gated deploys, and why public uploads are disabled. Explain Docker as an optional CI-validated packaging path.

### Day 6: System design

Whiteboard the current architecture, then redesign it for 100 manuals, 10,000 manuals, and multiple organizations. Discuss object storage, queues, databases, vector indexes, caching, and observability.

### Day 7: Mock interview

Record a five-minute demo and answer the 15 questions above. Replace vague phrases with evidence from the code or benchmark. End each answer with one honest tradeoff or next improvement.
