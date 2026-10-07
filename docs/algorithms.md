# KShield — Detection Algorithms

Companion to [features.md](features.md) (what each detector does and its
known gaps) and [architecture.md](architecture.md) (how the system is
wired together) — this is the third layer: the actual math behind each
detector, for anyone tuning thresholds or extending the engine. Every
formula and threshold below is quoted directly from the current source,
not paraphrased from memory — check the linked file if it's been retuned
since.

---

## Shannon entropy — secret detection

`backend/app/engine/entropy.py`, `_shannon_entropy()`

```
H(s) = -Σ p(c)·log₂(p(c))     over each unique character c in s
       where p(c) = count(c) / len(s)
```

Measures how "random-looking" a string is, in bits per character. A
repeated or structured string (English text, an identifier, `"aaaaaaa"`)
scores low; a generated secret (`"kX9$mZ2pQvR8..."`) scores close to the
theoretical max (`log₂(alphabet size)`).

- **Threshold:** flagged as `High Entropy Credential` (HIGH) if score >
  **4.8** and the quoted literal is ≥ **24 characters** (`_ENTROPY_THRESHOLD`,
  `_MIN_SECRET_LENGTH`).
- **Runs only as a fallback** — 30+ named signatures (GitHub/AWS/Stripe/
  OpenAI/Anthropic/etc. token shapes) are checked first via regex and
  trusted CRITICAL outright; entropy only evaluates lines with no named
  match.
- **Allowlist before scoring:** UUIDs, MD5/SHA-1/SHA-256/SHA-512 hex,
  semver strings, and short base64 are excluded — all can score high on
  entropy without being secrets.
- **Placeholder filter, applied to named-pattern matches too:** a template
  value shaped like a real key (`sk_test_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`)
  is rejected if fewer than 30% of its characters are unique
  (`len(set(s)) / len(s) < 0.3`) — a real generated secret is very unlikely
  to repeat one character that much.

---

## Levenshtein edit distance — typosquat detection

`backend/app/engine/dependency_audit.py`, `_levenshtein()` / `_closest_popular()`

Standard dynamic-programming edit distance — minimum single-character
insertions/deletions/substitutions to turn one string into another —
implemented with the O(min(n,m)) space optimization (two rolling rows
instead of a full matrix), O(n·m) time.

Every import not already declared/stdlib/first-party is compared against
a curated popular-package list (`_POPULAR_PYTHON`, `_POPULAR_NPM`):

- Length pre-filter: skip candidates whose length differs by more than 2
  (pure speed — cuts the comparison set before running the DP).
- **Distance 1 → CRITICAL, distance 2 → HIGH, distance 0 or > 2 → ignored**
  (0 means it *is* the popular package; > 2 is no longer a plausible typo).
- **Cross-checked against real registry existence before flagging.**
  Real bug found dogfooding against `adk-python`: `retry` (a real PyPI
  package) is edit-distance 2 from `poetry`, and `mcp` (Anthropic's real
  SDK) is edit-distance 2 from `mypy` — two genuinely independent published
  packages, not squatting on each other, just short names close together
  in edit-distance space. Fix: a name already confirmed to exist on the
  registry (`sandbox.py`'s cache, built once per repo-wide audit — see
  `orchestrator.py`'s two-pass batching) is never flagged, regardless of
  distance.

---

## Signature normalization — false-positive memory

`backend/app/engine/quiet_office.py`

Not a distance metric — a normalize-then-exact-match approach. Findings
are template-generated, so the only parts that vary between two "same
kind of problem" findings are quoted identifiers and file paths:

```
signature(description) = lowercase(
    description
      .replace(/'[^']*'|"[^"]*"/,        "<X>")      # quoted identifiers
      .replace(/\b[\w./-]+\.(py|js|ts|...)\b/, "<FILE>")  # file paths
)
```

Dismissing one finding stores this normalized signature; every future
finding of the *same anomaly_type* gets its own signature computed and
compared for an **exact match** against stored ones. This is why
dismissing "Import `foo` used in `a.py`..." also auto-suppresses "Import
`bar` used in `b.py`..." — same shape, different variable — without ever
needing a similarity threshold to tune.

Suppression here is sticky-additive, not overriding: a prior pass
(`.kshield.yml`/global-suppress rules, applied earlier in
`orchestrator.py`) may have already marked a finding suppressed for an
unrelated reason, and this step never flips that back to unsuppressed just
because it doesn't also match a dismissed signature.

---

## Not real math: the "embedding" vector

`backend/app/engine/model.py`, `generate_embedding_vector()`

Flagged here explicitly because the name is misleading — this is not an
embedding model:

```python
seed = int(hashlib.md5(text_payload.encode()).hexdigest(), 16) % (2**32)
rng = np.random.RandomState(seed)
vec = rng.randn(1536)
return (vec / np.linalg.norm(vec)).tolist()
```

It's a hash-seeded random unit vector in R¹⁵³⁶ (1536 chosen to match real
embedding-model dimensionality, so it fits the `pgvector` column shape).
Deterministic per exact input text, which is the only property it
actually has in common with a real embedding — **two findings with
similar-but-not-identical descriptions get essentially unrelated random
vectors**, because MD5 has no notion of semantic closeness. Any
cosine-similarity search built on this column today would be comparing
structured noise, not meaning. Already called out in
[features.md's Known Limitations](features.md#known-limitations); repeated
here because it's the one place in the engine where the name (`sequence
_classifier_node`, `generate_embedding_vector`) actively implies real ML
that isn't there — the actual "AI Structural Hallucination" detection is
100% curated regex (`_INDICATORS`, ~40 hand-written patterns), not a
classifier. Making this real would mean replacing this function with an
actual embedding-model call (local or API) — a real feature to build, not
a bug to fix in the current function.

---

## Quick reference

| Detector | Technique | Complexity | Threshold |
|---|---|---|---|
| Hardcoded Secret | Regex signature match | O(patterns × lines) | Named shape match |
| High Entropy Credential | Shannon entropy | O(n) per literal | > 4.8 bits/char, ≥ 24 chars |
| Possible Typosquat | Levenshtein distance | O(n·m) per candidate, length-filtered | distance ≤ 2 |
| False-positive memory | Signature normalize + exact match | O(1) per stored signature | Exact match only |
| AI Structural Hallucination | Regex pattern match | O(patterns × lines) | Named pattern match |
| Broken Access Control | AST/graph guard lookup | O(routes × files) | No `Depends()`/`Security()` found |
| Vulnerability embedding | *(not real — see above)* | — | — |
