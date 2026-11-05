# Build prompt: ucp-pulse v1

Paste everything below the line into Codex, working in `/Users/andres/dev/ucp-pulse`.

---

## Role and goal

You are the engineer building **ucp-pulse v1**: open-source weekly intelligence on the Universal Commerce
Protocol (UCP) that tracks spec releases, release amendments, SDK versions and declared breaking changes, and
drafts a cited weekly brief for human approval.

The spec is `BUILD-PLAN.md` in this folder. It is normative. `PLAN.md` is background only; where they differ,
`BUILD-PLAN.md` wins. `CODEX-REVIEW-1.md` explains why the plan looks the way it does. Read all three first.

Owner decisions already made (BUILD-PLAN §13):
- D1: two repos. Public engine `schwentker/ucp-pulse` (this folder). Private data repo
  `schwentker/ucp-pulse-data` (create locally at `/Users/andres/dev/ucp-pulse-data`).
- D2: v1 promises declared and human-reviewed changes with coverage notes, never "every breaking change".
- D3: the export job uses a fine-grained token, stored only as a secret in the private repo, limited to
  `schwentker/ucp-pulse` contents and pull requests. Reference it by secret name `UCP_PULSE_EXPORT_TOKEN`; never
  create, print or commit a token.

## Scope

Build phases **P1 through P5** of BUILD-PLAN §10, then a **local dry run of P6** (backfill + history brief
draft). Stop there. Out of scope: P7, P8, everything in "Later", any Shopify live call, any LLM call, Tier 2
sources, scoring weights, semantic schema compatibility verdicts.

## Hard rules

1. **Local only.** Do not push, do not create or modify GitHub repos, settings, secrets, branch protection or
   tokens. `git init` and local commits are fine. Robert pushes.
2. **Network:** read-only GET/GraphQL queries to public GitHub (api.github.com, github.com git reads), PyPI JSON,
   npm registry, and `https://shopify.dev/changelog/feed.xml`. Nothing else. No calls to any Shopify store,
   catalog or checkout endpoint. Honor rate-limit headers; stop and keep cursors when remaining < 100.
   Use `GITHUB_TOKEN` from the environment if set; never print it.
3. **Tests are offline.** Every test runs with networking blocked (enforce it in the test harness). Live calls
   happen only in explicit smoke commands you run by hand. Save their outputs as fixtures only after checking
   they hold no token, cookie or personal data (they should be public data; check anyway).
4. **Facts:** do not invent versions, dates, counts, URLs, PR numbers or company names in code, fixtures, docs or
   rendered output. Fixtures derived from real upstream objects record their source URL and retrieval time.
   Synthetic fixtures are labeled synthetic.
5. **No em dashes** in any file you write. Terse docs.
6. **Python 3.12**, stdlib plus pinned `PyYAML` and `pytest` (dev). Add any other dependency only with a one-line
   justification in the phase report.
7. Workflow files: `permissions: {}` at top, per-job least privilege as in BUILD-PLAN §7, actions pinned by full
   commit SHA, no `pull_request_target`, no upstream text interpolated into `run:` lines.
8. If the plan is ambiguous or wrong, pick the safer reading, record it in `docs/DECISIONS.md` with a reason,
   and continue. If a phase exit criterion cannot be met, stop and report instead of weakening the criterion.
9. Never skip, delete or loosen a test to get green.

## Phases and exit criteria

Work in order. Commit locally at the end of each phase with message `pN: <summary>`. After each phase write
`docs/build/PHASE-N-REPORT.md`: what was built, commands run with results (test counts), what was verified live
and how, open issues, deviations from BUILD-PLAN with reasons. Continue to the next phase only if the exit
criterion passes.

**P1. Core, no network.**
Engine package `src/ucp_pulse/`: event/revision model (§3.1) with per-family `event_id` and `material`
definitions and `norm_version`; append-only store and derived state (§3.2); `ucp-pulse rebuild` with equality
check; UTC half-open weekly periods starting Sunday, `period_id = p-YYYY-MM-DD`, due ledger, first-seen
inclusion and late-arrival rule (§4); run ledger; cursors and health files.
Exit: BUILD-PLAN §9 "State/report" rows that need no network pass, including DST/midnight edges, dropped run,
late arrival, duplicate dispatch, crash-before-commit simulation, index rebuild equality.

**P2. HTTP client + S1, S2, S3.**
Client: timeouts, byte caps, HTTPS only, no off-host redirects, ETag/If-None-Match, pagination, rate-limit stop.
Collectors S1 (tags, releases, `release/*` branch heads, release line model incl. amendments), S2 (PRs: merged on
any base, open with `!` or breaking label; title and merge commit subject both checked), S3 (commits on
normative paths; changed files, JSON pointers, `ucp_request`/`ucp_response` location, local `$ref` dependents;
classification always `unknown`).
Fixtures (>= 20 per family) must include the real cases named in BUILD-PLAN §9: backport PR #431 into
`release/2026-04-08`, js-sdk #87 and python-sdk #101 (title `feat:`, merge subject `feat!:`), ucp #659.
Exit: §9 rows for S1, S2/S6 (S2 part), S3 pass.

**P3. S4, S5, S6, S7, then smoke-test S8 and S9.**
Announcements file parser (S4), org `.github` governance digests (S5), SDK and `ucp-schema` repos (S6, mixed
Python tag schemes stored verbatim with `scheme`), PyPI `ucp-sdk` (S7, bind package to repo via project URLs).
S8 npm `@ucp-js/sdk` and S9 Discussions GraphQL: run one live smoke read each. If it works, add fixtures and
enable. If it fails, leave disabled and make the brief show the coverage gap. Record the exact error.
S10 Shopify changelog feed: build with fixtures and the strict entity gate (§5), enabled only if >= 95% precision
and zero bare-UCP false positives on the labeled set.
Exit: §9 rows pass for enabled sources; disabled sources documented with reason.

**P4. Renderer, curation, verify.**
Pure `render(evidence_sha, as_of, period, curation) -> (md, json)` with the fixed block order of §8; mandatory
blocks never cut; coverage block always present; source ledger generated. Curation YAML schema as in §8.
`ucp-pulse verify`: brief equals fresh render; every non-empty text field cites >= 1 KEEP id; no PENDING or CUT
id appears in output; derived state equals rebuild.
Exit: byte-stable render across two runs and two machines' path layouts (no absolute paths in output);
every seeded bad case rejected.

**P5. Private data repo scaffold + workflows.**
Create `/Users/andres/dev/ucp-pulse-data` (local git only): `config/engine.lock` (engine commit SHA),
`config/sources.yaml`, workflows `collect.yml`, `draft.yml`, `verify.yml`, `export.yml` per §7 (shared
concurrency group, single writer, atomic commit, fetch-reset-reapply on rejected push, period lifecycle incl.
bot-only vs human-edited PR branches, `--revise`, abandoned). PR template with the human entailment checklist.
`docs/RUNBOOK.md`: first deploy steps for Robert (create repos, branch protection or ruleset bypass for the
Actions bot on `data/**` and `state/**`, add `UCP_PULSE_EXPORT_TOKEN`, enable workflows), re-enabling an
auto-disabled schedule, approving checks on bot PRs, revise, abandon, manual catch-up.
Lint workflows with `actionlint` if available; otherwise say so.
Exit: duplicate dispatch, crash-before-push and rejected-push behaviors proven by tests that drive the CLI
against two local bare git remotes (no GitHub).

**P6 (dry run). Backfill + history brief draft.**
Run collectors live (read-only, within rule 2) from 2026-01-11 to now into the local data repo. Render a
`history` brief draft and a curation file with every item PENDING. Apply the fact corrections in BUILD-PLAN §11
only where your collected evidence supports them; for any that it does not, list them in the report as
"not supported by collected evidence" rather than writing them in. Do not mark anything KEEP.
Exit: draft renders and `verify` passes its structural checks (it will correctly flag PENDING ids as not
publishable); report lists counts per family, coverage gaps and any upstream surprises.

## Final deliverable

`docs/build/BUILD-SUMMARY.md` in the engine repo: phases completed, test totals, live smoke results, enabled vs
disabled sources, deviations from BUILD-PLAN with reasons, known limits, and the exact commands Robert runs to
push both repos and do the first deploy. Keep it under 800 words.
