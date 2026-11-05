# Phase 2

Built a bounded HTTPS client with allowlisted hosts/paths, no credential forwarding across hosts, GET plus query-only GraphQL, ETag cache, pagination guards and rate-limit stops. S1 folds tags, releases and release branches into release-line revisions. S2 checks titles and merge subjects and preserves tracked withdrawals. S3 gathers normative commits across main/release branches and emits structural JSON pointers, direction-annotation locations and local reference dependents, always unknown.

Validation: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q`: 104 passed. Initial run: 98 passed, four failures exposed deletion-state oscillation and newline-only note republication. Implementations fixed; no test skipped or loosened. Fixture families: releases 21, PRs 25 (21 synthetic plus four upstream subsets), schema paths 22. Additional tests cover backport #431, tracked withdrawal, cache secrecy, off-host redirect, pagination failure, tag peeling and rate-limit preservation.

Live verification: none in P2. The four source-linked metadata fixtures were retrieved in the previous review on 2026-11-04: ucp #431, #659, js-sdk #87, python-sdk #101. Retrieval precision is explicitly a day. They omit bodies, user objects, emails and credentials; source URLs and transformation notes are retained. Synthetic fixtures are labeled.

No GITHUB_TOKEN is present. Runtime smoke/backfill must still honor the below-100 stop rule; no credential fallback was invented. Structural diff reports lexical local-reference dependents; it does not claim semantic resolution, compatibility or deployment. Full schema snapshots can be expensive; budget failure preserves cursors. P2 exit passed.
