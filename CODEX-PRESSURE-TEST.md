# Pressure test: ucp-pulse PLAN.md

Paste everything below the line into Codex, with `PLAN.md` attached or in the working directory.

---

## Role

You are a skeptical staff engineer and protocol analyst. Review `PLAN.md` for **ucp-pulse**, an open-source
weekly intelligence pipeline on the Universal Commerce Protocol (UCP). Find what is wrong, missing, risky, or
over-built before any code exists. Do not write implementation code. Do not rewrite the plan. Produce findings.

## Context you need

- ucp-pulse is modeled on `github.com/schwentker/mpp-pulse` (public; read it if you can, especially
  `README.md`, `src/app.py`, `docs/tier1-source-precision-gates.md`). mpp-pulse runs two decoupled schedules
  (daily collect, weekly report) on AWS Lambda, DynamoDB, S3, Bedrock. ucp-pulse moves to free hosting:
  GitHub Actions cron, append-only JSONL in the repo, reports opened as pull requests for human review.
- Upstream sources: `github.com/Universal-Commerce-Protocol/ucp` (spec, date-versioned tags `vYYYY-MM-DD`),
  `js-sdk`, `python-sdk`, `ucp-schema`, `conformance`, `samples`, and the org `.github` repo (governance).
  Read `docs/versioning.md` in the spec repo: it defines breaking-change policy that the plan relies on.
- A related project, UCP Flight Recorder, made anonymous read-only and cart/checkout calls to Shopify's UCP
  surfaces and recorded docs-vs-live differences from one client, one merchant, one day. ucp-pulse proposes a
  much smaller weekly read-only probe in that lineage.
- The owner wants: $0 hosting, every published claim cited to stored evidence, a human merge before anything
  is public, and a first issue that summarizes UCP history (launch date, co-developers, endorsers) with sources.
- Today is 2026-11-04. Treat any fact in the plan as unverified until you check it against a primary source.

## What to check

1. **Fact check §4 and §11.** For each fact, confirm or refute from a primary source (repo files, git tags,
   release pages, official vendor posts). Report wrong dates, wrong names, wrong version contents, and any
   claim stated more strongly than its source. Flag anything labeled VERIFIED that you could not reproduce.
2. **Decoupling and state.** Does the reporter truly read only persisted state? Can two workflows corrupt
   `data/` or `state/`? Is the window math correct for late, dropped, or re-run cron jobs, timezone edges, and
   records with no `published_at`? Is "lock = output file exists" safe with PR-based reports that are not yet
   merged?
3. **Idempotency.** Is the `id` definition stable across runs and across upstream edits (PR title edits,
   release note edits, force-pushed tags, re-published packages)? When should an edited source make a new
   record vs update vs be ignored? Is a text file of ids enough as an index at 1 year of data?
4. **Breaking-change detection (§7).** Is the schema-diff rule set correct for JSON Schema 2020-12 as used in
   `source/schemas/**`? Name concrete cases it misclassifies (e.g. `$ref` indirection, `$defs`, `allOf` merges,
   request vs response direction, where "new required" is breaking only for one side). Is `title_bang` reliable
   given squash merges and title edits? How should a breaking change on a `release/*` backport branch be shown?
5. **Source gates (§5).** Precision risks per source; missing high-signal sources; sources that should be cut.
   Is entity matching for "UCP" tight enough? Are any listed feeds or registry names likely wrong?
6. **Live probe.** Legal, ethical, and operational risks of a weekly read-only probe of Shopify surfaces and
   `/.well-known/ucp` on up to 5 merchants. Is it worth it for v1? What must be true before enabling it?
   Is "drift vs the version the merchant advertises" well defined when versions negotiate per capability?
7. **GitHub Actions as a platform.** Scheduled-workflow limits, inactivity auto-disable, token permissions
   (least privilege per workflow), GraphQL access to Discussions with `GITHUB_TOKEN`, push-to-main vs branch
   protection, PR creation by `GITHUB_TOKEN` not triggering other workflows, secret exposure in a public repo,
   fork PR safety. Is the hosting choice justified against the rejected Cloudflare option?
8. **LLM step.** Is the validator in §8 step 6 sufficient to prevent invented versions, invented sources,
   or status upgrades? Is optional-by-default the right call?
9. **Report format (§10).** Will a builder who ships against UCP find it actionable? What is missing (e.g.
   migration hints, affected SDK symbols, deprecation windows)? Is anything noise?
10. **Scope and sequencing (§13).** What is over-built for v1? What should move earlier? What is the smallest
    version that delivers the core value (version board + breaking changes, cited)?
11. **Testing.** What fixtures and tests are required before each collector is enabled? Propose acceptance
    thresholds where the plan has none.
12. **Cost (§15).** Any hidden cost or rate-limit cliff.

## Rules

- Cite evidence for every factual correction: URL or `repo@ref:path`, plus a short quote.
- Say "could not verify" rather than guessing. No invented versions, dates, counts, or company names.
- Prefer findings that would change the build. Skip style nits unless they cause ambiguity.
- Do not propose paid services as defaults.
- No em dashes in your output.

## Output format

Write `CODEX-REVIEW-1.md` with:

1. **Verdict:** one of `ready`, `ready with fixes`, `needs rework`, and two sentences why.
2. **Findings table:** `ID | Severity (blocker/high/medium/low) | Section | Finding | Evidence | Proposed fix`.
   Order by severity.
3. **Fact-check table:** every fact in §4 and §11 with `confirmed / refuted / could not verify` and source.
4. **Minimum viable v1:** the smallest build order you would accept, as a numbered list.
5. **Open questions for the owner:** at most 5, each with your recommended answer.

Keep it under 1,500 words excluding tables.
