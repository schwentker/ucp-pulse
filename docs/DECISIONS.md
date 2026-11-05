# Implementation decisions

- D001: The attached build prompt overrides P0, hosted smoke tests, remote PRs and P6 approval. This build is local only; no remote writes occur.
- D002: first_seen_at belongs to an appended observation, not the upstream event. Content can return A to B to A. revision_id remains its specified content hash; observation_id identifies each transition. Unchanged reruns append nothing.
- D003: Only index and inventory are derived from evidence. Cursors, health, runs and period lifecycle are operational state, not reconstructible from evidence alone. Rebuild checks both derived files and validates revision chains.
- D004: Weekly catch-up starts at an explicit persisted tracking start. Historical collection does not manufacture earlier observation timestamps.
- D005: Local writes use a recoverable journal under one file lock; the later git commit/push is the publication transaction. Uncommitted journals are discarded; committed journals roll forward.
- D006: Curation will pin revision IDs in addition to event IDs. A PENDING draft can pass structural verification but cannot pass publication verification. Human strings and curation metadata are distinct types.
- D007: Upstream text is kept verbatim in evidence. Authored text contains no em dashes; JSON uses ASCII escaping. Rendering will replace that punctuation without changing stored source snapshots.
- D008: P2 real regression fixtures reuse selected public metadata retrieved in the preceding review on 2026-11-04. Their recorded retrieval precision is one day; no exact timestamp is invented. Bodies, author/user objects and emails are excluded. All constructed payloads and dates are labeled synthetic.
- D009: A previously tracked PR is retained when closed without merge or when its breaking label/title is withdrawn. Its facts are updated; it is never marked merged. Untracked ordinary open and closed-unmerged PRs are excluded.
- D010: Missing GitHub rate-limit headers fail closed. Once remaining drops below 100, no further GitHub request is made in that client session. A failed/partial source does not advance its cursor.

## D011: Local activation and unavailable Discussions
S8 passed the explicit local registry smoke and its offline fixtures. S9 returned
`GitHub remaining 0 < 100; reset=1793867601`; leave it disabled. No token was set.
The prompt replaces the plan's Actions-runner smoke with a local read. S10 uses
22 synthetic labeled cases: 100% precision and zero bare-UCP false positives.
This is a fixture gate, not a measured precision claim about future feed items.

## D012: Source identity and undated material
Announcement date plus heading slug identifies an entry. Moving an unchanged
entry preserves identity; renaming a heading records removal plus a new identity.
Ambiguous duplicate identities and unrecognized nonempty files fail closed.
Governance uses path identity, so a move is removal plus addition. npm deprecation
is not a yank. Deleted registry versions retain their previous digest evidence.
Unknown SDK tag formats remain verbatim with scheme unknown.

## D013: Diff evidence and rate-stop isolation
Structural alerts include bounded 1,000-character JSON fragments and full-value
hashes, including explicit absent markers. GitHub's rate stop blocks further
GitHub reads in the same client, while independent registry/feed sources continue.
