# P6 local dry-run report

Partial backfill only. Scope requested: 2026-01-11 through observation time
2026-11-05T07:55:21.818561Z. No GitHub writes, store probes or publication.

Manual live command:

```sh
.venv/bin/python -m ucp_pulse smoke-collect --data /Users/andres/dev/ucp-pulse-data --start 2026-01-11T00:00:00Z --cache /Users/andres/dev/ucp-pulse-data/.cache/p6-candidates.json --run-id p6-local-backfill
```

Four requests: one GitHub REST, one PyPI JSON, one npm registry, one exact Shopify
RSS feed. S1 failed `GitHub remaining 59 < 100; reset=1793868921`. The client made
no subsequent GitHub request; S2-S6 report the stopped client. GITHUB_TOKEN was
unset. S9 remains disabled after its earlier denied smoke. S7 failed
`registry package-to-repository binding failed`: its info.project_urls is null.
No package identity was inferred. S8 and S10 completed and advanced only their own
cursors. Raw response cache is ignored in the private repo, not an engine fixture.

Collected counts:

| Family | Revisions |
| --- | ---: |
| spec_release | 0 |
| spec_pr | 0 |
| normative_commit | 0 |
| announcement | 0 |
| governance | 0 |
| sdk_tag / sdk_pr | 0 / 0 |
| registry_version | 12, all npm |
| discussion | 0 |
| changelog | 9 |
| Total | 21 |

Surprises: npm latest is 0.5.1 with 12 returned versions; do not equate this to an
SDK tag or spec version. PyPI's 0.5.0 metadata lacks project URLs and was rejected.
The feed includes broader Hydrogen/catalog posts that mention the exact protocol
name or otherwise satisfy the explicit entity gate; human KEEP/CUT review is
still needed. A successful feed snapshot does not establish archive completeness.

History evidence commit: 54062636fac171cdd896f96f6d85f0eddb73cd6e.
Local branch: draft/history-2026-01-11-r1. Files:
curation/history-2026-01-11-r1.yaml and drafts/history-2026-01-11-r1/brief.md|.json.
All 21 decisions are PENDING; headline/signal/watch_next are empty. No KEEP items.

Validation: verify --draft passed structure, evidence/snapshot integrity, derived
state equality and exact rendering. Publication verify returned exit 1 with
`PENDING evidence is not publishable`, as required. Failed-source cursors remain
absent. Final offline suite: 278 passed. Final review added a regression ensuring
one revise dispatch creates one new revision even when older revisions exist.
No tests were deleted, skipped or loosened. actionlint remains unavailable.

## Requested history corrections

Each item below is **not supported by collected evidence** and is omitted from
human narrative in the draft:

- NRF launch venue, launch endorser count and current logo count.
- First repository commit timestamp.
- January/April GitHub release publication timestamps.
- Original April capabilities and the later identity-linking backport (#354/#431).
- August announcement wording versus normative capability versioning.
- PR-title breaking-change convention and its limits.
- Mixed Python tag schemes and both SDK migration merge dates/subjects.
- Flight Recorder merchant observations and checkout schema branches.
- ucpchecker counts, which remain omitted.

Some facts have older review fixtures, but they are not a substitute for this
live backfill. Vendor blogs, ucp.dev page fetches and merchant calls were outside
the permitted live-read scope and were not made.

Exit: local draft/structural checks and expected publication rejection passed.
The comprehensive GitHub/PyPI history remains incomplete. Resume collection only
with a valid environment token and sufficient observable GitHub budget, and
resolve PyPI provenance without weakening the binding requirement. Stop at P6;
no P7/P8 work, remote PR or deployment was performed.
