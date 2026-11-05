# Build summary

P1-P5 implemented and committed locally. P6 local dry run produced a partial
history draft; the comprehensive history backfill remains incomplete. Stopped
before P7/P8. No GitHub repository, settings, secrets or tokens were changed.
Neither local repository has a remote. No remote push or PR was created.

Validation: 278 offline tests passed. Python network access is blocked by the
test harness, child Python uses the same guard, and Git tests permit file
transport only. Tests cover 20+ labeled cases per enabled family, revision
identity, UTC periods, cursor retention, deterministic rendering, bad curation,
Git conflicts/crashes, lifecycle and monotonic exports. actionlint was unavailable;
YAML and workflow security-contract checks passed.

Local npm smoke succeeded; Discussions smoke failed with remaining=0 and is
explicitly disabled. P6 made four read requests. GitHub reported remaining=59,
so S1-S6 stopped with cursors intact. PyPI returned project_urls=null and failed
repository binding. npm supplied 12 version records; the exact Shopify feed
supplied nine entity-gated entries. The history preview has 21 PENDING items,
passes structural verify and correctly fails publication verify. No item is KEEP.
Evidence is pinned to 54062636fac171cdd896f96f6d85f0eddb73cd6e.

Configured sources: S1-S8 and S10 enabled after offline gates; S9 disabled.
Live healthy in P6: S8/S10. Live failed/unavailable: S1-S7/S9. Feed gate precision
was 100% on 22 synthetic labeled cases, not a future accuracy guarantee.

Deviations and limits: local smoke replaces Actions as instructed. Curation pins
exact revisions. Draft mode permits labeled pending evidence; export never does.
Main-ahead remains unknown; all observed version schemes are shown separately.
Existing draft branches are preserved; --revise creates addenda. Stale cached
source snapshots are refused after a newer collection. Ruleset bypass is broader
than path permissions and needs owner review. Bot PR checks, Actions permissions,
runner availability and monthly minutes need first-deployment verification. The
split jobs can exceed the plan's 180-minute estimate. All requested historical
corrections lack sufficient evidence in this backfill and are omitted. See
PHASE-6-REPORT.md, DECISIONS.md and RUNBOOK.md.

## Owner commands

Review the runbook first. These commands were **not run**. If repos already exist,
configure their existing SSH remote instead of creating them. Push engine first:

```sh
cd /Users/andres/dev/ucp-pulse
gh repo create schwentker/ucp-pulse --public --source=. --remote=origin
git push -u origin main
cd /Users/andres/dev/ucp-pulse-data
git switch main
gh repo create schwentker/ucp-pulse-data --private --source=. --remote=origin
git push -u origin main
gh secret set UCP_PULSE_EXPORT_TOKEN --repo schwentker/ucp-pulse-data
```

Use the interactive secret prompt, never a literal token in a command. Limit it
to public-repo Contents and Pull requests read/write. Configure reviewed private
writer bypass and required human PR checks; public main must require its verify
check to prevent latest rollback. Allow Actions PR creation in the private repo.
Then:

```sh
gh workflow enable collect.yml --repo schwentker/ucp-pulse-data
gh workflow enable draft.yml --repo schwentker/ucp-pulse-data
gh workflow run collect.yml --repo schwentker/ucp-pulse-data
```

Optional private review branch upload, after reviewing its incomplete coverage:

```sh
git push -u origin draft/history-2026-01-11-r1
```

Do not merge the pending history draft. Curate, rerender without --draft, verify,
and confirm the exact PR-head check is green before a human merge. Keep source
failures visible; never lower rate thresholds or infer registry ownership.
