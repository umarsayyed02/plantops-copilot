# Retrieval benchmark

Benchmark date: 18 October 2026  
Corpus: one synthetic induction-motor manual, split into three overlapping chunks  
Dataset: 11 versioned questions (8 answerable, 3 deliberately unsupported)

| Metric | BM25 + hashing baseline | BM25 + BGE semantic vectors |
|---|---:|---:|
| Recall@5 | 1.0000 | 1.0000 |
| Mean reciprocal rank | 1.0000 | 1.0000 |
| Abstention accuracy | 1.0000 | 1.0000 |
| Citation precision | 1.0000 | 0.8889 |
| p50 latency | 4.920 ms | 44.382 ms |
| p95 latency | 9.749 ms | 52.822 ms |

## Interpretation

The two backends produced the same aggregate retrieval ranking and abstention scores on this small, terminology-heavy corpus. The lexical baseline produced higher citation precision and much lower query latency, so the semantic backend has not yet demonstrated enough value here to justify enabling it by default.

This does **not** establish that hashing is generally better than semantic embeddings. The corpus is too small, the questions share vocabulary with the manual, and the relevance labels have not been independently reviewed. It does establish that a heavier embedding model should not be adopted without a measured benefit.

## Next evaluation work

1. Expand to at least 10 manuals and 100 questions.
2. Include paraphrases with little lexical overlap to test semantic retrieval fairly.
3. Have another person review relevance and unanswerable labels.
4. Evaluate Recall@1/3/5, nDCG and citation correctness at the sentence level.
5. Tune BM25/vector weights on a development set, then report once on a held-out test set.

To reproduce:

```bash
python -m app.evaluation --output evaluation/reports/baseline.json
PLANTOPS_EMBEDDING_BACKEND=fastembed \
  python -m app.evaluation --output evaluation/reports/semantic.json
```

