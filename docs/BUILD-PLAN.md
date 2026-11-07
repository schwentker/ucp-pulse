# ucp-pulse: build plan v2

Status: plan only. Written 2026-11-05. Decisions D1, D2, D3 accepted by Robert 2026-11-05 (recommended options). Supersedes the build sections of `PLAN.md` (v1). Inputs: `PLAN.md`,
`CODEX-REVIEW-1.md` (22 findings, verdict "needs rework"). Every finding ID (F01..F22) is answered in §12.
Where v1 and this file disagree, this file wins.

## 0. What changed from v1, in one screen

1. **Two repos.** Public engine (code, tests, fixtures). Private data repo (evidence, drafts, curation). Only
   approved briefs leave the private repo. (F01)
2. **Events have identity; observations have revisions.** No more `title`/`kind` in the id. Edits, backports
   and re-published packages become new revisions of the same event. (F04, F06)
3. **Discovery-time periods.** A brief covers everything first seen in its UTC week, so late, missed or
   re-run jobs lose nothing. Old events found late are labeled "late". (F05)
4. **Inventory state, not just a window.** Version board and pending breaking list come from persisted
   current state, rendered before any ranking. Nothing mandatory can fall below a top-N cut. (F09)
5. **v1 tracks declared breaking changes.** Signals: author-declared (`!`), notice-declared, analyst-confirmed.
   Schema changes are path-level alerts for human review, never auto-classified "additive". (F02, F03, F13)
6. **Humans edit curation, not prose.** The brief is re-rendered from evidence + curation; CI proves the
   committed brief equals the render. (F10, F16)
7. **Cut from v1:** live Shopify probe, LLM, Tier 2 community, broad blog aggregation, scoring weights,
   semantic schema diff. (F14, F16, F19, F20)

## 1. Goals and promise (narrowed)

- G1. Every UCP spec release, release amendment (backport), SDK tag and registry publication, within one weekly
  cycle, with exact refs.
- G2. Every **declared** breaking change (merged or pending) and every notice, with its status per fact.
- G3. Every change under normative paths (`source/**`, `docs/specification/**`) listed for human review.
- G4. Every claim in a published brief binds to an approved evidence revision.
- G5. $0. No paid service by default.

Public promise wording: "declared and reviewed changes, with coverage notes". Never "every breaking change".

## 2. Repos and publication boundary (F01, F12, F21)

| Repo | Visibility | Holds | Runs |
|---|---|---|---|
| `schwentker/ucp-pulse` | public | engine (`src/`), tests, fixtures, docs, exported approved briefs in `briefs/` | CI only (tests, lint). No secrets, no state writes. |
| `schwentker/ucp-pulse-data` | private | `data/`, `state/`, `drafts/`, `curation/`, workflows that collect and draft | Scheduled collect, report drafting, publish/export |

- Data workflows check out the engine at a pinned commit SHA (`config/engine.lock`).
- Export: on merge of an approved draft, a job opens a PR on the public repo adding `briefs/<period_id>.md|.json`
  and updating `briefs/latest.json` only if `period_end` is newer (no rollback by out-of-order merges).
- sandboxlabs.ai/ucp-pulse renders `briefs/latest.json` (v1: copied by hand into the Hugo site, like mpp-pulse).
- Private repo Actions minutes are limited on free plans (verify current allowance). Budget: daily collect
  <= 5 min, weekly draft <= 5 min, about 180 min/month. Pin `runs-on: ubuntu-latest` (standard runner only).

Decision D1 (Robert): confirm two repos. Alternative: everything public and the gate covers only the branded
brief. Recommended: two repos.

## 3. Data model (F04, F06, F10, F17)

### 3.1 Event and revision

```json
{
  "event_id": "ucp:pr:659",
  "family": "spec_pr",
  "subject": {"repo": "Universal-Commerce-Protocol/ucp", "kind": "pull_request", "number": 659},
  "revision_id": "sha256(event_id | material_digest)",
  "supersedes": "previous revision_id or null",
  "material": {"title": "...", "merge_commit_subject": "...", "base": "main", "merged_at": "2026-10-16T07:23:34Z",
               "merge_sha": "...", "labels": [], "body_digest": "sha256", "notice_links": []},
  "material_digest": "sha256 of canonical JSON of material",
  "norm_version": 1,
  "event_time": "2026-10-16T07:23:34Z",
  "event_time_kind": "merged | tagged | published | posted | committed | observed",
  "first_seen_at": "2026-11-05T14:02:11Z",
  "observed_at": "2026-11-05T14:02:11Z",
  "facts": {"merged": true, "author_declared_breaking": true},
  "authority": "official_repo | official_registry | official_vendor | secondary",
  "evidence": {"url": "https://github.com/...", "ref": "repo@sha:path", "pointer": "/json/pointer or null",
               "snapshot": "data/snapshots/<sha256>.json or null", "excerpt": "<= 400 chars verbatim"},
  "run_id": "uuid"
}
```

Rules
- `event_id` is upstream identity only. Table per family:

| Family | event_id |
|---|---|
| spec release line | `ucp:release:2026-04-08` (tag, GitHub release, `release/2026-04-08` branch, notes are all facts of one event) |
| PR (any repo) | `<repo-short>:pr:<number>` |
| commit on normative path | `ucp:commit:<sha>` |
| SDK/tool tag | `<repo-short>:tag:<name>` |
| registry version | `pypi:ucp-sdk:<version>`, `npm:@ucp-js/sdk:<version>` |
| announcement entry | `ucp:announce:<date>:<slug>` (file entry and Discussion link merged by URL/date) |
| governance file | `ucpgov:file:<path>` |
| Discussion | `ucp:discussion:<number>` |
| Shopify changelog item | `shopify:changelog:<guid>` |

- `material` lists exactly the fields whose change is meaningful for that family (defined in
  `src/ucp_pulse/families/*.py`, versioned by `norm_version`). Normalization-only changes produce no revision.
- A changed `material_digest` appends a new revision with `supersedes`. Nothing is overwritten.
- Release line facts tracked per revision: tag object SHA, peeled commit, release branch head, release
  `published_at`, notes digest, asset digests. Backport = new revision of an existing release line with fact
  `amended: branch_changed` and, only when assets/notes change, `artifact_republished`. (F04)
- Facts are independent booleans/values, not a status ladder: `opened`, `notice_posted`, `merged`, `tagged`,
  `release_published`, `package_published`, `amended`, `yanked`, `deleted`. The renderer shows facts; it never
  derives "available". (F16)
- Spec versions and SDK versions never share a field. Python tags are mixed (`v0.5.0`, date tags, suffixed date
  tags); store tag name verbatim plus `scheme: semver | spec_date | spec_date_suffixed`. (F17)
- `excerpt` is a pointer aid, not the evidence. Reproducibility comes from `ref` + `pointer` + `snapshot`
  (bounded before/after fragments for diffs). Store only what source licenses allow; link always. (F10)

### 3.2 Store

```text
data/events/YYYY-MM.jsonl   append-only revisions, partitioned by first_seen_at month
data/snapshots/<sha>.json   bounded fragments referenced by revisions
state/index.json            event_id -> latest revision_id (derived; rebuildable)
state/inventory.json        current facts per event (derived; rebuildable)
state/cursors.json          per source: last complete cursor, overlap, pagination_complete
state/periods.json          period ledger: due, drafted, pr_number, status (open|merged|abandoned)
state/health.json           per source: last_success, last_error, consecutive_failures, last_nonzero
state/runs.jsonl            one line per run
```

`ucp-pulse rebuild` regenerates every derived file from `data/events/**` and must equal the committed copies
(CI check). (F22)

## 4. Time model (F05)

- All times UTC. All periods half-open. Weekly period: `[Sunday 00:00Z, next Sunday 00:00Z)`;
  `period_id` = `p-` + start date, e.g. `p-2026-11-01` (ISO week numbers start Monday, so they are avoided).
- A brief for period P includes every revision with `first_seen_at` in P. Revisions whose `event_time` is
  before P's start go in a **Late arrivals** section with their original event time. Nothing is ever skipped.
- Due ledger: after a period closes it is `due`. Any run (scheduled or manual) drafts every `due` period in
  order. A dropped Sunday run is caught up on Monday's collect.
- Cron (UTC, stated plainly): collect `0 14 * * *` (06:00 PST / 07:00 PDT); draft `0 18 * * 0` (10:00 PST /
  11:00 PDT). Draft also runs at the end of every collect if a period is due and not drafted.
- Cursors: each source resumes from `last complete cursor - overlap` (overlap 7 days for list endpoints).
  Incomplete pagination or error keeps the old cursor. Dedupe absorbs overlap.
- Undated sources: `event_time_kind = observed`, labeled "observed, not published" in the brief.
- Inactivity auto-disable (60 days, scheduled workflows) cannot be revived by a heartbeat. Mitigation: daily
  commits keep the repo active; runbook documents manual re-enable; `health.json` staleness shows on the brief.

## 5. Sources for v1 (F11, F13, F18, F19)

Each source is enabled only after its gate in §9 passes.

| ID | Source | Method | Notes |
|---|---|---|---|
| S1 | ucp tags + releases + `release/*` branches | REST refs, releases (all pages), branch heads | release line model §3.1 |
| S2 | ucp PRs: merged (any base, incl. `release/*`) and open with `!` or breaking label | REST pulls, sort by `updated` | store current title, merge commit subject, base, labels, body digest; `!` in either title or merge subject = author_declared |
| S3 | ucp commits touching `source/**`, `docs/specification/**`, `docs/versioning.md` | REST commits by path | path-level alert; prose-only security changes surface here (#659 changed signing prose) |
| S4 | `docs/documentation/announcements.md` | file at HEAD, parse dated sections | official notices; link Discussions by URL |
| S5 | org `.github`: GOVERNANCE, MAINTAINERS, TC_ELECTIONS, charters | file digests | governance facts |
| S6 | js-sdk, python-sdk, ucp-schema: tags, releases, merged PRs/merge subjects with `!` | REST | SDK impact (e.g. python-sdk 48e173b removes `ucp_sdk.models.schemas.*` tree) |
| S7 | PyPI `ucp-sdk` JSON API | registry JSON | Codex retrieved 0.5.0 record; bind package to repo via project URLs |
| S8 | npm `@ucp-js/sdk` | registry JSON | UNVERIFIED (npm page 403 in review). Gate: one successful fetch from an Actions runner. If blocked, show "registry: unknown" |
| S9 | ucp Discussions | GraphQL with `GITHUB_TOKEN` | UNVERIFIED that the token can read an external repo's Discussions. Smoke test first. Fallback: S4 + Discussion URLs found in PR bodies; brief shows coverage gap |
| S10 | shopify.dev changelog `https://shopify.dev/changelog/feed.xml` | RSS | Path verified in review; parser fixture required. Gate: allowlisted host + exact `Universal Commerce Protocol`, `UCP` as a whole word next to a ucp.dev URL or capability id, or a `dev.ucp.` string. Other Shopify news is "adjacent", excluded from v1 |

Deferred (v1.1+): Shopify agent docs page hashing, Google/Shopify blogs, conformance/samples, Tier 2
community, ucpchecker (secondary), live probe.

Rate limits: `GITHUB_TOKEN` REST budget is per repo per hour (1,000 per review citation). Use conditional
requests (ETag/If-None-Match), `per_page=100`, and stop on `X-RateLimit-Remaining < 100` leaving cursors intact.

## 6. Schema handling in v1 (F02, F03, F15)

- No automatic compatibility verdicts in v1.
- For each S1/S3 revision touching `source/schemas/**` or `source/services/**`: list changed files, changed
  JSON pointers (structural diff), whether each pointer sits under `ucp_request` / `ucp_response`
  annotations, and which other schema files `$ref` the changed file (reachable dependents, local refs only).
- Classification field is `unknown` until a human sets `analyst: breaking | additive | clarification` in
  curation. The brief shows "analyst-confirmed" only for human-set values.
- v1.1 candidate: operation-specific request/response comparison using the official `ucp-schema` tool if it
  can compose contracts; unsupported keywords stay `unknown`.

## 7. Workflows and permissions (F07, F08, F11, F12)

All workflows: `permissions: {}` at top; actions pinned by full SHA; source text never interpolated into
`run:` lines (pass via files or env); no `pull_request_target`; no secrets except `GITHUB_TOKEN`.

| Workflow (private repo) | Trigger | Job permissions | Does |
|---|---|---|---|
| `collect.yml` | cron daily + dispatch | `contents: write` (single writer job) | fetch with cursors, append revisions, rebuild derived state, commit atomically; then draft any due period |
| `draft.yml` | cron Sunday + dispatch | `contents: write`, `pull-requests: write` | reconcile period ledger, render draft, open/update PR |
| `verify.yml` | PR to main | `contents: read` | tests; `rebuild` equality; brief == render(evidence, curation); zero PENDING/CUT ids in output; all cited ids KEEP |
| `export.yml` | push to main touching `drafts/` | `contents: read` + a fine-grained token scoped to the public repo `contents`/`pull-requests` only | open export PR on public repo |

Single writer: `collect.yml` and `draft.yml` share `concurrency: {group: ucp-pulse-state, cancel-in-progress:
false}`. GitHub replaces a pending run with a newer one; that is acceptable because the due ledger catches up.

Atomic commit: one commit contains new revisions + derived state + cursors + run line. Push without force. On
rejection: `git fetch && git reset --hard origin/main`, re-load state, re-apply the fetched raw responses
(cached in the runner workspace) through dedupe, rebuild, retry (max 3). Never replay JSONL lines blindly.

Report lifecycle (`state/periods.json`): key = `{period_id, type: weekly|history, revision: rN}`.
- `due` -> render to branch `draft/<period_id>-r1`, open PR, record PR number.
- Re-run while PR open and branch has only bot commits: regenerate same branch (idempotent).
- PR has a human commit: do not touch; post evidence-since-draft as a new file `drafts/<id>/addendum.json` only
  via `--revise` creating `r2`.
- PR closed unmerged: `abandoned`; re-draft needs `--revise`.
- Merged: `published`; human merge of the private PR is the approval.
- Branch protection on private `main`: require PR + `verify` passing for `drafts/**` and `curation/**`. The
  collect job's direct push to `data/**`, `state/**` is allowed by path (or via a ruleset bypass for the
  Actions bot). Document which one in the runbook. Checks on bot-created PRs may need manual approval; the
  runbook says how.
- Fork PRs: private repo, none expected; `verify` still runs without secrets.

## 8. Rendering and curation (F09, F10, F16, F20)

Renderer is a pure function: `render(evidence_commit_sha, as_of, period, curation) -> md, json`. No network,
no clock. Byte-stable.

Draft layout (fixed order; mandatory blocks before anything optional):

```text
UCP Pulse, period 2026-11-01 to 2026-11-08 (UTC), as of <evidence sha>
Headline / Signal / Watch next      human-written in curation, each with required evidence ids (may be empty)
Version board (mandatory, from inventory)
  Spec release lines: latest dated version, its current revision, amended? (branch/artifact), main ahead by N commits on normative paths
  js-sdk: latest tag | npm latest (or unknown)     python-sdk: latest semver tag, latest spec-date tag | PyPI latest
  ucp-schema: latest tag
Breaking and pending-breaking (mandatory, every row)
  | Change | Repo/PR | Facts (opened/notice/merged/base/tagged/released) | Signal (author/notice/analyst) | Affected ops or SDK symbols | Migration / workaround | Deadline or unknown | First seen | [S#] |
Release amendments (mandatory if any)
Normative changes for review (mandatory, path-level, classification shown)
Governance (if any)
Shopify changelog, UCP-scoped (if any)
Late arrivals (if any)
Coverage (mandatory): per source last success, failures, unknowns (npm, Discussions), stale >48h
Source ledger [S#] url, ref, event_time + kind, authority (generated)
Footer: experimental, independent, not affiliated with or endorsed by Shopify, Google, or UCP governance bodies.
```

Curation (`curation/<period_id>.yaml`), the only human-edited file:

```yaml
period: p-2026-11-01
headline: {text: "...", evidence: [ucp:pr:659]}
signal:   {text: "...", evidence: []}
watch_next: [{text: "...", evidence: [ucp:discussion:912]}]
items:
  ucp:pr:659: {decision: KEEP, analyst: breaking, migration: "...", affected: ["dev.ucp.shopping.order"], note: ""}
```

`verify` fails if any text field cites a non-KEEP id or none when the field is non-empty, any id is PENDING,
or the committed brief differs from a fresh render. Entailment (does the cited evidence support the
sentence?) is a human review step, listed in the PR template checklist. (F16)

No scoring weights in v1: order is fixed by block, then by `event_time`. (F20)

## 9. Activation gates (from review, adopted)

A collector is enabled in `config/sources.yaml` only after its family passes. Fixtures live in the public
repo under `tests/fixtures/<family>/` (>= 20 hand-labeled cases each).

| Family | Must pass |
|---|---|
| All | 100% accepted records have URL, ref, authority, event_time + kind, event_id, revision_id; 100% unchanged reruns add 0 revisions; one source failing does not stop others; cursor kept on failure or partial pages |
| S1 releases/tags | annotated vs lightweight tags, retargeted/deleted tag, release after tag, edited notes, draft/prerelease, backport onto `release/*` (fixture from PR #431 into `release/2026-04-08`), two releases between runs; 100% alias collapse; every material revision kept |
| S2/S6 PRs | open, closed-unmerged, merged, reopened, edited title, squash subject `feat!:` with title `feat:` (js-sdk #87, python-sdk #101), old-created recent-merged, non-main base; 0 unmerged-as-merged; 100% seeded `!` signals recovered |
| S3 schema paths | moved file, shared `$defs` change with unchanged `$ref`, annotation-only change, unknown keyword; 100% surface as `unknown`; dependents listed |
| S4/S5/S9 | edited, moved, deleted discussion; non-maintainer author; duplicate file + discussion; changed charter; denied GraphQL degrades coverage visibly |
| S7/S8 registries | package-to-repo binding, tag vs publish mismatch, dist-tag move, yank, digest change; no inferred publication on failed fetch |
| S10 changelog | acronym collisions, unrelated Shop.dev/catalog posts, missing date, 304/404/redirect; >= 95% precision; 0 bare-UCP false positives |
| State/report | offline render with network blocked; empty week; dropped Sunday; DST and midnight edges; late arrival; duplicate dispatch; crash before push; rejected push; index rebuild; unmerged/closed PR; curation edits; out-of-order merges. 0 lost or duplicate events; byte-stable render; 0 CUT/PENDING in approved output |

## 10. Build phases (each ends green; one PR per phase on the public engine)

| Phase | Deliver | Exit |
|---|---|---|
| P0 | Robert: decide D1-D3 (§13); create both repos; branch protection | repos exist |
| P1 | Engine skeleton (Python 3.12, stdlib + PyYAML pinned), event/revision model, families registry, store, rebuild, time model, period ledger, run ledger. No network | state/report gate rows that need no network pass |
| P2 | HTTP client (timeouts, byte caps, ETag, rate-limit stop, no redirects off-host), S1, S2, S3 + fixtures | S1-S3 gates pass |
| P3 | S4, S5, S6, S7; smoke-test S8 and S9 from a real Actions run, enable or mark `unknown` | gates pass or coverage gap documented |
| P4 | Renderer + curation + `verify` | byte-stable; validator rejects every seeded bad case |
| P5 | Private repo workflows: collect, draft, verify, export; runbook (re-enable, approve checks, revise, abandon) | duplicate dispatch, crash-before-push, rejected-push tests pass in a scratch repo |
| P6 | Backfill 2026-01-11..now; render **history brief** (type `history`) from it; corrected facts §11 | Robert approves via merge |
| P7 | Run 2 weekly cycles end to end; S10 | 2 approved briefs |
| P8 | Hugo page on sandboxlabs.ai from `briefs/latest.json` | page live |
| Later | `ucp-schema`-based contract compare, Shopify docs hashing, probe (after terms decision), LLM (after 4 briefs + claim binding) | separate plans |

## 11. Issue #1 (history brief) corrections

Generated from backfilled evidence; these are the fact changes vs `PLAN.md` §11.

- Venue: launch remarks say "Today at the National Retail Federation (NRF)" (Sundar Pichai, 2026-01-11,
  blog.google/company-news/inside-google/message-ceo/nrf-2026-remarks/). Re-verify when drafting, then use.
- Endorsers: "more than 20" at launch (examples, not a roster). Do not say "about 40" or "has grown";
  ucp.dev currently shows about 51 logo labels; if used, cite the pinned `docs/index.md` commit and say "logos
  on ucp.dev as of <date>".
- First commit 2026-01-11 03:53Z (UTC).
- January releases: both `v2026-01-11` and `v2026-01-23` GitHub releases were published 2026-01-23. April
  release published 2026-04-09 01:48Z.
- April v2026-04-08 original content: cart, catalog search + lookup, request/response signing. Identity
  linking OAuth 2.0 foundation merged 2026-05-06 (#354) and was **backported** 2026-05-20 (#431) into
  `release/2026-04-08`. Present it as a later amendment.
- "Independent capability versioning" (August notes) is announcement wording; the August normative overview ties
  official capabilities to the selected release. Quote, do not paraphrase.
- Breaking policy: PR titles "should include" `!`; it is a convention, not a guarantee.
- Python SDK tags mix semver and spec-date schemes; both SDKs merged the generate-types migration 2026-10-28
  (PDT). Merge commit subjects carry `feat!:`; PR titles do not.
- Flight Recorder: on 2026-10-31, one merchant, `create_checkout` and `update_checkout` advertised a 4-value
  status enum; `get_checkout` has a second schema branch with `complete_in_progress` and `completed`. Do not
  say "live checkout has four statuses".
- ucpchecker numbers: omit (review could not reproduce 19,740 / 62%).

## 12. Finding-by-finding disposition

| ID | Disposition | Where |
|---|---|---|
| F01 | Adopted: two repos | §2 |
| F02 | Adopted: no auto verdicts; request/response annotations shown | §6 |
| F03 | Adopted: unknown by default; dependents listed; semantic diff deferred | §6, §10 |
| F04 | Adopted: release line model, backports as amendments | §3.1, §11 |
| F05 | Adopted: discovery-time periods, due ledger, cursors, UTC cron stated | §4 |
| F06 | Adopted: event_id vs revision_id, material per family | §3.1 |
| F07 | Adopted: period ledger lifecycle | §7 |
| F08 | Adopted: single writer, atomic commit, recompute on reject | §7 |
| F09 | Adopted: inventory state, mandatory blocks, coverage block, no top-N | §3.2, §8 |
| F10 | Adopted: refs/pointers/snapshots; brief must equal render; export only approved | §3.1, §7, §8 |
| F11 | Adopted: smoke tests for Discussions + checks on bot PRs; fallback | §5, §7 |
| F12 | Adopted: least privilege, pinned actions, no interpolation, protected main | §7 |
| F13 | Adopted: signal labels, merge subject + title, normative paths, no promise of completeness | §1, §5 |
| F14 | Adopted: probe deferred pending terms decision | §10 |
| F15 | Adopted with probe deferral; spec text quoted, not paraphrased | §11 |
| F16 | Adopted: LLM off; facts not ladder; curation-bound claims | §3.1, §8 |
| F17 | Adopted | §11 |
| F18 | Adopted: gates table | §9 |
| F19 | Adopted: strict entity gate; Tier 2 cut | §5 |
| F20 | Adopted: impact columns, empty Watch next allowed, reordered phases, no scoring | §8, §10 |
| F21 | Adopted: standard runner, budgets, ETags, runbook | §2, §4, §5 |
| F22 | Adopted: rebuildable index with equality check | §3.2 |

## 13. Decisions for Robert

- D1. Two repos (public engine, private data). Recommended: yes.
- D2. v1 promise = declared + reviewed changes with coverage notes. Recommended: yes.
- D3. Export token: a fine-grained PAT limited to `schwentker/ucp-pulse` contents + pull requests, stored as a
  secret in the private repo only. Recommended: yes; the alternative is copying approved briefs by hand.
