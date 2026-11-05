# Implementation decisions

- D001: The attached build prompt overrides P0, hosted smoke tests, remote PRs and P6 approval. This build is local only; no remote writes occur.
- D002: first_seen_at belongs to an appended observation, not the upstream event. Content can return A to B to A. revision_id remains its specified content hash; observation_id identifies each transition. Unchanged reruns append nothing.
- D003: Only index and inventory are derived from evidence. Cursors, health, runs and period lifecycle are operational state, not reconstructible from evidence alone. Rebuild checks both derived files and validates revision chains.
- D004: Weekly catch-up starts at an explicit persisted tracking start. Historical collection does not manufacture earlier observation timestamps.
- D005: Local writes use a recoverable journal under one file lock; the later git commit/push is the publication transaction. Uncommitted journals are discarded; committed journals roll forward.
- D006: Curation will pin revision IDs in addition to event IDs. A PENDING draft can pass structural verification but cannot pass publication verification. Human strings and curation metadata are distinct types.
- D007: Upstream text is kept verbatim in evidence. Authored text contains no em dashes; JSON uses ASCII escaping. Rendering will replace that punctuation without changing stored source snapshots.
