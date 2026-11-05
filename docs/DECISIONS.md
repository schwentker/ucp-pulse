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

## D014: Exact revision curation and draft preview
Curation keys and claim citations use `event_id@revision_id`. The curation file
also pins the evidence commit, UTC as_of and full period metadata. Every revision
in the discovery window plus mandatory current inventory needs an explicit
KEEP/CUT/PENDING decision. Repeated observations of identical content share a
content revision. The draft preview may display pending evidence, labeled as
unapproved. `verify --draft` checks structure only; `verify` rejects every PENDING
item. Human text and analyst fields require KEEP even in a draft preview. No
export path may use draft validation. This resolves the P6 dry-run requirement.

## D015: Unknowns and inventory presentation
Render every current spec release line and SDK/registry version separately,
without inferred availability or arbitrary top-N cuts. An exact main-ahead count
is unknown until a complete ancestry scan exists; do not infer it from a partial
normative commit window. Sources with no successful observation are stale/unknown.
Evidence snapshots, derived state and source health come from the pinned Git
commit. Render code has no clock or network dependencies.

## D016: Local-only deployment boundary and lifecycle preservation
Future workflow code contains explicit remote-write commands; none were invoked
against GitHub during this build. CLI remote-write tests use file-protocol bare
repos only. Existing bot branches are preserved rather than regenerated in place;
new evidence uses --revise, as for human edits. This is the safer optional branch
update behavior. Orphan remote draft branches can recover by creating their PR.
Private-main ruleset bypass is broader than file paths; the runbook names the risk
and requires owner setup rather than asserting unavailable path permissions.

## D017: Conflict ordering and workflow budget
Reapply cached candidates after fetch/reset on rejected pushes, bounded at three
attempts. If a newer snapshot for that source is already committed, fail and
request recollection rather than regress inventory/cursors. Local Git tests cover
ordinary rejection replay, duplicate dispatch and crash recovery. Collection and
drafting are separate jobs to keep collect at contents:write only. This raises
the worst scheduled budget above 180 minutes/month; measure usage before enabling.

## D018: P6 partial backfill, no fallback identity guesses
The P6 GitHub REST response reported remaining=59. Stop subsequent GitHub reads
and retain all S1-S6 cursors. PyPI returned project_urls=null for ucp-sdk, so S7
cannot satisfy the specified binding and records failure. Do not substitute a
homepage or an inferred repository. S8/S10 succeeded independently. The local
history preview contains only these 21 collected revisions, all PENDING. Prior
review fixtures are not substituted for a successful live history backfill.
The feed is a current snapshot, not a guaranteed historical archive.

## D019: Normalize before naming snapshots
The original candidate helper hashed pre-normalized material while the batch
writer saved normalized material. This produced 501 broken pointers across PR,
SDK tag and governance families. The corrected helper hashes the normalized
material. The one-time repair tool requires each replacement snapshot to
already exist with content exactly equal to the stored material. Its private
mapping records every old and new pointer; the prior Git commit remains the
audit trail. No event identity, material, facts or times were changed.

## D020: Official provenance fallback for PyPI
The live ucp-sdk PyPI JSON has project_urls=null. Its public description links
to the exact official python-sdk repository, whose pinned pyproject.toml declares
project.name=ucp-sdk. When project URLs are absent, both facts are required and
the repository commit and path are stored as binding_ref. A lookalike URL or a
manifest mismatch fails closed. This is a documented departure from the plan's
project-URLs-only rule, and does not infer package publication from SDK tags.

## D021: Normative recovery through official public Git
Repeated REST S3 scans hit connection failures before pagination completed.
The public Git read path was explicitly allowed. A full clone at the official
GitHub URL, pinned at main head 58c7ab92dcf80b3b1fc756d577b0552ec1cd503a,
provided complete local objects. The fallback enumerates reachable commits on
main and maintained release branches from 2026-01-11, computes first-parent
changed paths and the same structural schema alerts. It yielded 195 records.
S3 is complete in the local data store. The ordinary REST collector remains for
scheduled runs; its transport now retries transient connection failures three
times, and its schema reader reuses unchanged blobs by hash.
