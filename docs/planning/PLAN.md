# ucp-pulse: plan

Status: PLAN ONLY. Nothing built. Written 2026-11-04.
Repo (to create): github.com/schwentker/ucp-pulse. Local: /Users/andres/dev/ucp-pulse.
Public page (target): sandboxlabs.ai/ucp-pulse, same shape as sandboxlabs.ai/mpp-pulse.

## 0. One paragraph

ucp-pulse is open-source weekly intelligence on the Universal Commerce Protocol (UCP): spec releases, breaking
changes, SDK versions, governance, and where Shopify's live agent surfaces drift from the published spec. Like
mpp-pulse, it runs two decoupled schedules: a daily collector that persists evidence, and a weekly reporter that
writes a cited brief from the persisted window. Unlike mpp-pulse, it runs free: GitHub Actions cron, state as
append-only JSONL in the repo, reports as files, human review by pull request. Its distinctive source is the UCP
Flight Recorder: a small read-only live probe that records what Shopify actually serves, so the brief can say
"spec says X, live surface says Y" with evidence.

## 1. Goals and non-goals

Goals
- G1. Detect and explain every UCP spec version, breaking change, and SDK release within one weekly cycle.
- G2. Give early warning: breaking PRs are announced in GitHub Discussions 2 weeks before merge (policy, see §4).
- G3. Track docs-vs-live drift on Shopify surfaces, building on Flight Recorder findings (FIELD-NOTES §2).
- G4. Every claim in a published brief cites a stored evidence record with a URL and a status label.
- G5. $0 hosting. LLM spend capped and optional.

Non-goals (v1)
- No email subscriptions or subscriber data (mpp-pulse page says "subscriptions opening soon"; same here).
- No crawling of merchants at scale. No adoption counts of our own.
- No checkout, cart, or any mutating call to any merchant. Probe is read-only.
- No auto-publish. A human merges every brief.

## 2. What carries over from mpp-pulse (read from the repo, 2026-11-04)

mpp-pulse was readable (public). Reused design, by mpp-pulse concept:

| mpp-pulse | ucp-pulse | Note |
|---|---|---|
| Two EventBridge schedules, one Lambda, `mode` = collect / report / draft | Two GitHub Actions workflows calling one CLI with `--mode collect|report` | Same decoupling |
| `content_id` = SHA-256 of stable fields, excludes collection time | Same | Repeat runs insert 0 duplicates |
| DynamoDB conditional write `attribute_not_exists(pk)` | Dedupe against an id index file before append | See §6 |
| `LOCK#COLLECT/REPORT#END#date#WINDOW#n` | Lock = output file already exists for that window; `--force` overrides | |
| `COLLECTOR_REGISTRY`, collectors fail independently, `PARTIAL_SUCCESS` | Same | |
| Source heartbeats (zero-yield streak warnings) | Same, stored in `state/heartbeats.json` | |
| Tier-1 eligibility gate + fixtures + precision thresholds (`docs/tier1-source-precision-gates.md`) | Same gate, UCP entities, see §5 | Fixtures before enabling a collector |
| Deterministic score, top 50 to the model | Same | |
| Model gets a bounded packet with `[S#]` labels; app appends its own source ledger | Same | Model never discovers facts |
| Deterministic fallback report if Bedrock fails | Deterministic report is the base; LLM only writes prose | |
| Google Sheet `KEEP/CUT/WATCH` review queue | `curation/YYYY-MM-DD.yaml` edited in the report PR | Review lives in git |
| Private S3 HTML, 30-day expiry | Public markdown + JSON in repo | Brief is public by design |
| SES email | None in v1 | |

Not reused: AWS SAM, IAM, Bedrock, SES, SSM, Google Sheets client.

## 3. Hosting decision: GitHub Actions + repo-as-database

Choice: public repo `schwentker/ucp-pulse`; two scheduled workflows; evidence and reports committed to the repo;
the sandboxlabs.ai page reads an approved `latest.json`.

Why
- Free: Actions minutes are free for public repos (verify current GitHub billing page before relying on it).
- Primary sources are on GitHub; `GITHUB_TOKEN` gives authenticated REST and GraphQL (Discussions) reads with
  higher rate limits than anonymous.
- Git history is the audit log: every evidence record, every brief, every human edit is diffable. Fits the
  "evidence, not vibes" stance of Flight Recorder.
- Spec diffing needs a checkout of `Universal-Commerce-Protocol/ucp` at two tags and a JSON Schema diff over
  ~147 files. Comfortable in an Actions runner; awkward in a Worker.
- Human review gate = pull request. No extra tool.

Rejected
- Cloudflare Worker + Cron Trigger + KV/D1: free tier has tight CPU per invocation and no git; schema diffs and
  clones do not fit well. Keep as a later option for a tiny "latest.json" API if the page needs one.
- GitHub Pages for the public page: works, but the brand page already lives on sandboxlabs.ai (Hugo). Use the
  repo only as the engine and archive.

Known Actions constraints (design for them)
- Scheduled runs can start late or be dropped under load. Windows are computed from persisted data, not from
  run time, so a late run still reports the right window.
- Scheduled workflows in public repos can be auto-disabled after 60 days without repo activity (verify current
  rule). Daily evidence commits count as activity only if they happen; add a heartbeat commit to
  `state/heartbeats.json` every run.
- Both workflows write to `main`. Use one `concurrency` group (`ucp-pulse-state`) and a fetch-rebase-retry
  push (3 tries). Collector commits directly; reporter opens a PR.

## 4. Verified UCP facts the plan depends on

Checked 2026-11-04 from primary sources (git reads of the official repos, official blogs). Labels:
VERIFIED (primary source read), SECONDARY (third party), UNVERIFIED (not confirmed).

| Fact | Label | Source |
|---|---|---|
| Spec repo: `Universal-Commerce-Protocol/ucp`, Apache-2.0, "Copyright 2026 UCP Authors" | VERIFIED | repo LICENSE, README |
| Version tags: v2026-01-11, v2026-01-23, v2026-04-08, v2026-08-25. Latest is v2026-08-25 | VERIFIED | `git ls-remote --tags`; github.com/Universal-Commerce-Protocol/ucp/releases |
| Versions are dates; release branch `release/YYYY-MM-DD`; tag `vYYYY-MM-DD`; backports allowed on release branches | VERIFIED | `docs/versioning.md` |
| Breaking PRs carry `!` in the title and are announced in Discussions 2 weeks before merge; security fixes excepted | VERIFIED | `docs/versioning.md` "Breaking PRs" |
| Example breaking PR after v2026-08-25: `fix(order)!: cover webhook-id and webhook-timestamp in the signing gate (#659)`, 2026-10-16 | VERIFIED | ucp main history |
| Normative schemas under `source/schemas/` (shopping: cart, checkout, catalog_search, catalog_lookup, order, fulfillment, discount, ...), services under `source/services/` | VERIFIED | repo tree at 58c7ab9 (2026-10-31) |
| Announcements page in repo: `docs/documentation/announcements.md` (dated entries) | VERIFIED | repo |
| SDKs: `Universal-Commerce-Protocol/js-sdk` (npm name `@ucp-js/sdk`, latest tag v0.5.2), `python-sdk` (`ucp-sdk`, tags follow spec dates, latest v2026-08-25). Both merged `feat!: migrate model generation to ucp-schema generate-types` on 2026-10-28; source says 0.6.0, no 0.6.0 tag yet | VERIFIED (repos); registry pages UNVERIFIED | repo tags, package.json, pyproject.toml |
| `ucp-schema` tool repo tags v1.0.0..v1.4.1; `conformance` and `samples` repos exist | VERIFIED | `git ls-remote` |
| Governance docs live in `Universal-Commerce-Protocol/.github` (GOVERNANCE.md, MAINTAINERS.md, TC_ELECTIONS.md, charters) | VERIFIED | org repo |
| Shopify Catalog MCP endpoint `https://catalog.shopify.com/api/ucp/mcp` (anonymous `tools/list`, `search_catalog` worked) | VERIFIED live 2026-10-31, one client | Flight Recorder `src/`, FIELD-NOTES §1.1 |
| ucpchecker.com reports 19,740 verified stores, 62% on v2026-08-25 | SECONDARY | ucpchecker.com/specs, "not affiliated with the UCP Tech Council" |

## 5. Sources

Tier 1 (eligible as evidence). Every feed URL marked (verify) must be confirmed from the site itself before it is
configured. Do not guess feeds.

| ID | Source | Method | Emits kinds |
|---|---|---|---|
| T1-spec-rel | ucp releases + tags | REST `releases`, `tags` | `spec_release` |
| T1-spec-pr | ucp merged PRs | REST `pulls?state=closed`, keep `merged_at` in window | `merged_pr`, `breaking_pr` (title has `!` or label) |
| T1-spec-diff | ucp `source/` at last tag vs `main`, and tag vs previous tag | shallow fetch, JSON Schema diff (§7) | `schema_change` |
| T1-disc | ucp Discussions (Announcements category) | GraphQL | `announcement`, `breaking_notice` |
| T1-ann | `docs/documentation/announcements.md` | file diff | `announcement`, `governance` |
| T1-gov | `.github` org repo: GOVERNANCE, MAINTAINERS, TC_ELECTIONS | file diff | `governance` |
| T1-sdk | js-sdk, python-sdk, ucp-schema, conformance, samples: tags, releases, `!` PRs | REST | `sdk_release`, `breaking_pr`, `tooling` |
| T1-reg | npm `@ucp-js/sdk`, PyPI `ucp-sdk` (verify names) | registry JSON | `sdk_publish` (tag vs publish mismatch is a signal) |
| T1-shopify-docs | shopify.dev agent pages (Catalog, Cart MCP, Checkout MCP, profiles, auth-and-rate-limiting) | fetch, normalize, hash; store diff summary | `docs_change` |
| T1-shopify-log | shopify.dev changelog feed (verify) | RSS/Atom | `vendor_news` |
| T1-blogs | blog.google, developers.googleblog.com, shopify.engineering, shopify.com/news (feeds verify) | RSS/Atom, entity match required | `vendor_news` |

Tier 1L: live contract probe (Flight Recorder lineage). Weekly, opt-in, read-only.
- Catalog MCP `tools/list` at `catalog.shopify.com/api/ucp/mcp`: store tool names + input/output schema hash.
- `/.well-known/ucp` for a fixed allowlist of at most 5 merchants already seen in Flight Recorder traces:
  record `version`, `supported_versions`, capabilities, transports. No cart, no checkout, no buyer data.
- Same safety rules as Flight Recorder (HTTPS only, no IP literals, no redirects followed, time and byte caps,
  no retries on anything but reads). Identify with a UA that links the repo.
- Emits `live_drift` when live shape differs from the spec at the version the merchant advertises.

Tier 2 (context only, never sole support for a claim): HN Algolia, Reddit search RSS (same filters as mpp-pulse),
ucpchecker.com (SECONDARY; check terms before automated reads; v1 links it manually, does not scrape).

Entity match for Tier 1 non-GitHub sources: `Universal Commerce Protocol`, `UCP` with commerce context (bare
`UCP` is ambiguous), `ucp.dev`, `dev.ucp.`, repo names, `Agentic Storefronts`, `Catalog MCP`, `Checkout MCP`,
`Shop.dev`. Reject bare "agentic commerce" text without one of these.

## 6. Storage layout and evidence schema

```text
ucp-pulse/
  src/ucp_pulse/            collectors/, diff/, score.py, report.py, llm.py, cli.py
  config/sources.yaml       registry: id, tier, enabled, url, kinds, caps, fixtures path
  config/watch.yaml         repos, paths, merchants allowlist (<=5)
  data/evidence/YYYY-MM.jsonl   append-only; one record per line
  data/index/ids.txt        content ids already stored (dedupe)
  data/snapshots/           live probe and docs normalized snapshots (hash-named)
  state/heartbeats.json     per-source zero-yield streaks; last run per mode
  state/runs.jsonl          one line per run: id, mode, window, status, counts, errors
  reports/YYYY-MM-DD.md|.json   brief + machine-readable form (window end date)
  curation/YYYY-MM-DD.yaml  KEEP / CUT / WATCH per evidence id, edited in the PR
  site/latest.json          what sandboxlabs.ai renders (written only on merge)
  tests/fixtures/           accept/reject fixtures per source family
```

Evidence record (JSON, one line):

```json
{
  "id": "sha256 of source_id|canonical_url|kind|stable_payload_hash",
  "source_id": "T1-spec-pr",
  "tier": "1",
  "kind": "breaking_pr",
  "title": "fix(order)!: cover webhook-id and webhook-timestamp in the signing gate (#659)",
  "canonical_url": "https://github.com/Universal-Commerce-Protocol/ucp/pull/659",
  "published_at": "2026-10-16T00:00:00Z",
  "collected_at": "2026-11-05T07:00:00Z",
  "status": "merged",
  "spec_versions": {"affects": ["draft"], "since_tag": "v2026-08-25"},
  "capabilities": ["dev.ucp.shopping.order"],
  "breaking": {"is_breaking": true, "basis": ["title_bang"], "schema_findings": []},
  "excerpt": "<= 400 chars, verbatim from source",
  "entity_match": ["repo:ucp"],
  "confidence": "high",
  "eligibility": "news",
  "provenance": "LIVE | OFFICIAL | SECONDARY",
  "run_id": "uuid"
}
```

Rules
- `id` excludes `collected_at` and `run_id`, so unchanged facts dedupe.
- `status` vocabulary is closed: `proposed` (open PR, discussion), `announced`, `merged`, `released` (tag/release),
  `published` (registry), `observed_live`, `doc_changed`. The brief may never upgrade a status.
- A release, its tag, and its notes are one event (mpp-pulse rule).
- `excerpt` is verbatim; no model-written text in evidence.

## 7. Breaking-change detection (core value)

Deterministic, three independent signals; a finding lists all that fired.
1. `title_bang`: conventional-commit `!` in a merged PR title (repo policy, §4).
2. `notice`: Discussions post or announcements entry that names a breaking change; links forward to the PR when
   it merges (G2 early warning).
3. `schema_diff`: JSON Schema diff of `source/schemas/**` and `source/services/**` between two refs. Rules:
   - Breaking: property removed; property newly `required`; type narrowed or changed; enum value removed; `const`
     changed; `additionalProperties` true to false; capability or service removed or renamed; transport binding
     removed.
   - Additive: new optional property, new enum value, new capability, new schema file.
   - Unknown: `$ref` target moved, combinator (`allOf/anyOf/oneOf`) changes. Report as "needs human read". This
     mirrors Flight Recorder's choice to refuse combinator subtrees instead of guessing.
Comparisons run for: previous tag to latest tag (once per release), and latest tag to `main` (weekly, "what is
coming"). Output includes affected capability ids so readers can map to their code.

Fixtures: synthetic schema pairs for every rule, plus a real pair (v2026-04-08 to v2026-08-25; release notes call
out a Fulfillment schema restructure) as a regression case.

## 8. Two schedules

Collect (daily, `cron: 0 14 * * *` UTC; ~07:00 PT)
1. Load registry; run enabled collectors in isolation with per-source timeouts.
2. Normalize, gate (§5), compute `id`, drop known ids, append new records.
3. Update heartbeats, append run line, commit `data/` and `state/` with message `collect: <date> +N`.
4. No LLM call, no PR.

Report (weekly, `cron: 30 18 * * 0` UTC; Sunday ~11:30 PT, mirrors mpp-pulse)
1. Window = 7 days ending the previous day, computed from dates, not from run time.
2. Lock: if `reports/<end>.md` exists, exit unless `--force`.
3. Read evidence in window (`published_at`, falling back to first `collected_at`). The reporter makes no
   network calls to sources. The live probe and the tag-to-`main` schema diff are weekly collectors (registry
   `cadence: weekly`, run by the Saturday collect), so the reporter only reads persisted state.
4. Score (§9), take top 50, build packet with `[S1..Sn]`.
5. Deterministic draft: version board, breaking table, drift table, ledger. Always produced.
6. Optional LLM pass writes headline, Signal, Watch next only, from the packet. Validator rejects any `[S#]`
   not in the packet, any version string not in evidence, and any status word stronger than the record's.
   On failure keep the deterministic text.
7. Open PR `report/<end>` with `reports/`, `curation/` (all ids `PENDING`). Human sets KEEP/CUT, edits prose,
   merges. A merge workflow regenerates `site/latest.json` from KEEP rows only.

Manual: `workflow_dispatch` on both, with `force`, `window_end`, `window_days` inputs (mpp-pulse `events/*.json`
parity).

## 9. Scoring

Deterministic, weights in `config/score.yaml` (public; mpp-pulse keeps tuned weights private, but for a protocol
tracker transparency is worth more). Starting weights: spec release 100; breaking (schema_diff) 90; breaking
notice 80; live_drift 75; sdk_release with `!` 70; governance 50; docs_change on Shopify agent pages 45;
merged non-breaking spec PR 30; vendor_news 25; tier 2 10. Recency and capability count as small boosts.
Inventory-only changes (logo swaps, typo PRs, dependency bumps) score 0 and are hidden by default.

## 10. Report format

Same blocks as the live mpp-pulse page (Current Pulse, Signal, Evidence, Watch next) plus UCP-specific tables.

```text
UCP Pulse, week ending YYYY-MM-DD
Headline (one sentence)
Signal      one line: what changed that a builder must act on, or "no verified breaking change"
Version board
  Spec latest | Spec main ahead by N PRs | js-sdk tag / npm | python-sdk tag / PyPI | ucp-schema | Shopify advertised
Breaking and pending-breaking
  | Change | Capability | Status | Basis | Migration note | [S#] |
Docs vs live (Flight Recorder lineage)
  | Surface | Docs say | Live shows | First seen | [S#] |
Evidence    3 to 6 bullets, each cited
Watch next  2 to 3 items, each tied to a pending PR, notice, or drift
Source ledger  [S#] title, URL, kind, status, provenance (appended by code, not model)
Footer: experimental; independent; not affiliated with or endorsed by Shopify, Google, or the UCP Tech Council.
```

Limits: <= 700 words before the ledger. "Inference:" prefix on any non-cited sentence.

## 11. Issue #1: UCP history post (outline, facts pre-verified)

Title idea: "UCP, ten months in: versions, councils, and what breaks next". Short, cited, then hands off to the
weekly format. Each line below has its source; the post may only use these or newly verified ones.

1. Launch, 2026-01-11. Google announced UCP as an open standard for agentic commerce. VERIFIED:
   blog.google/products/ads-commerce/agentic-commerce-ai-tools-protocol-retailers-platforms/ ;
   developers.googleblog.com/en/under-the-hood-universal-commerce-protocol-ucp/ ;
   shopify.engineering/ucp (Ilya Grigorik) ; shopify.com/news/ai-commerce-at-scale.
   Venue (NRF 2026): UNVERIFIED; no launch page names an event. Leave out unless a primary source is found.
2. Co-developers at launch: Shopify, Etsy, Wayfair, Target, Walmart, with Google. VERIFIED (Google blog quote:
   "co-developed with industry leaders including Shopify, Etsy, Wayfair, Target and Walmart").
3. Endorsers at launch: "more than 20", named: Adyen, American Express, Best Buy, Flipkart, Macy's Inc.,
   Mastercard, Stripe, The Home Depot, Visa, Zalando. VERIFIED (same post). ucp.dev today lists ~40 endorsers;
   say "the list has grown" and link, do not count.
4. Open source: Apache-2.0 repo, first commit 2026-01-11. VERIFIED.
5. Versions: v2026-01-11, v2026-01-23, v2026-04-08 (cart, catalog search and lookup, request/response signing,
   identity linking foundation), v2026-08-25 (multi-vertical refactor, 3DS2, independent capability versioning,
   grocery readiness, fulfillment restructure). VERIFIED from release notes/announcements. Note: GitHub shows
   both January releases published 2026-01-23.
6. Governance: Tech Council expanded to 16 seats on 2026-04-24 (adds Amazon, Meta, Microsoft, Stripe,
   Salesforce); Stripe joins Governing Council 2026-04-28 alongside permanent members Google and Shopify;
   Food TC 2026-07-16; Lodging TC 2026-08-11; Payments TC 2026-09-02 (Adyen, Ant International, Coinbase,
   Global Payments, Google, PayPal, Shopify, Stripe); Lodging booking draft 2026-09-25. VERIFIED
   (announcements.md, each links a Discussion).
7. Shopify side: Agentic Storefronts and Google AI Mode / Gemini integration announced 2026-01-11; Fall '26
   Edition 2026-10-28 opens catalog, cart and checkout "to any agent or app" via Shop.dev. VERIFIED
   (shopify.com/news/ai-commerce-at-scale ; shopify.com/news/fall-26-edition-developer). GA dates of individual
   surfaces: UNVERIFIED.
8. What the Flight Recorder saw (one client, one merchant, 2026-10-31): docs vs live gaps on Checkout (4 vs 6
   status values, bare resource vs wrapper, required fields). LIVE, label clearly as a single observation.
9. Adoption: cite ucpchecker only as SECONDARY ("an independent tracker reports ..."), or omit.
10. Close: what ucp-pulse will watch weekly, and the pending breaking change list from `main`.

## 12. Public page (sandboxlabs.ai/ucp-pulse)

Clone `layouts/mpp-pulse/single.html` and `content/mpp-pulse.md` to `ucp-pulse`. Sections: 01 Current Pulse
(from `site/latest.json`), 02 What it watches (Spec, Implementation, Shopify live, Evidence), 03 Why it exists,
04 Built in public (link repo). v1: copy `latest.json` into the site repo by hand after each merged brief (same
human gate as mpp-pulse). v2: site build fetches the raw file at a pinned commit. Card on the home "Featured
experiments" grid optional.

## 13. Build order (each step ends green before the next)

1. Repo skeleton, CLI, registry, JSONL store, id/dedupe, run log, tests. No network.
2. Fixtures + gates for T1-spec-rel, T1-spec-pr, T1-sdk. Enable.
3. Schema diff engine with synthetic fixtures + v2026-04-08..v2026-08-25 regression.
4. Collect workflow (daily), concurrency, retrying push. Run 7 days.
5. Deterministic report + PR workflow. Backfill: one report covering 2026-01-11..now becomes Issue #1 data.
6. T1-disc, T1-ann, T1-gov, T1-reg.
7. Shopify docs hashing + live probe (weekly, allowlist, read-only).
8. Optional LLM prose pass + validator.
9. Site page.

## 14. Risks

| Risk | Mitigation |
|---|---|
| Bare "UCP" collides with other meanings | Entity gate requires commerce context or repo/domain match |
| Treating a merged PR as a released feature | Closed status vocabulary; validator blocks upgrades |
| Schema diff false "breaking" (refactor, moved `$ref`) | `unknown` class; human read; regression fixtures |
| Live probe looks like scraping or breaks merchant ToS | <=5 merchants, weekly, read-only, UA with repo link, stop on any 4xx policy signal |
| Anonymous Catalog throughput "shared and not guaranteed" | Probe failure is non-fatal, recorded as heartbeat |
| Actions cron late, dropped, or disabled | Date-based windows, heartbeat commit, a manual dispatch runbook |
| Two workflows race on `main` | One concurrency group, rebase-retry push |
| Repo grows from snapshots | Store hashes + normalized diffs, not full pages; monthly JSONL files |
| LLM invents versions or upgrades status | Deterministic base; validator; fallback |
| Shopify docs pages restructure (URL churn) | Treat 404/redirect as `docs_change` evidence, not crash |
| Copyright of quoted docs | Excerpts <= 400 chars, always linked |
| Public brief implies endorsement | Fixed footer; no logos |
| Secrets in a public repo | Only `GITHUB_TOKEN` and optional LLM key as Actions secrets; never logged |

## 15. Cost

- Hosting, schedules, storage: $0 (public repo Actions; verify current free-minute rules).
- GitHub API: within `GITHUB_TOKEN` limits (dozens of calls per day).
- LLM (optional): one call per week, ~50 items, <= ~15k input + 2k output tokens. Estimate well under $1/month
  on a current Claude model; exact price UNVERIFIED, check pricing before enabling. Off by default; the
  deterministic brief stands alone.
- Domain/page: existing sandboxlabs.ai.

## 16. Open decisions for Robert

1. LLM pass in v1, or deterministic-only until 4 briefs are reviewed? (Recommend deterministic-only first.)
2. Merchant allowlist for the live probe: reuse the Flight Recorder merchants only? (Recommend yes, max 5.)
3. Python (mpp-pulse parity, reuse code) or TypeScript (Flight Recorder parity, reuse safe-http)? Recommend
   Python for the pulse engine, porting only the probe safety rules.
