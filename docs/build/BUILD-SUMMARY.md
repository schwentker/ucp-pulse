# Build summary

P1-P5 and the local P6 history draft are implemented. R1-R6 are complete with
six local engine fix commits and corresponding local data updates. This fix run
performed no network collection, push, GitHub changes, deployment or secret setup.
Existing README edits, LICENSE and staged document moves were preserved.

Validation: 308 offline tests pass on Python 3.12.12, with no dependencies added.
The required full suite passed after each fix: 290, 292, 294, 301, 302 and 308.
The harness blocks Python networking, including child processes; Git tests use
file transport only. Synthetic golden tests cover table layout, dates, ordering,
readable facts and provenance. Request fixtures verify cursor overlap and early
PR pagination termination. Workflow security-contract checks pass; no hosted
workflow was run. Actionlint was unavailable in the original build.

The private history now has 864 observations: the original 860 plus four derived
release revisions. Original evidence remains unchanged. The r3 draft pins
`6223ae41b5c2b6ba98328184f0a1cffa619e8766` and retains all 48 breaking rows.
It is byte-stable, passes `verify --draft`, and fails publication `verify` because
all 864 curation decisions are PENDING. No headline, analyst statement or claim
was approved. The r2 draft and curation remain byte-for-byte unchanged.

Release amendments now derive from post-publication release-branch PR/commit
facts and branch/tag divergence on first observation, while retaining comparisons
between observations, including tag retargeting. The April line cites ten PRs
and ten corresponding commits, including #431; artifact_republished remains
false. Event times and kinds appear separately from first seen. Version-board
columns and fact labels replace raw JSON. Base is explicit, with same-day
backports following main changes and no rows suppressed.

Complete source cursors override the initial bound and resume with seven days of
overlap. PR collection stops when updated-descending pages cross that boundary.
The initial history date is in config/collection.yaml, copied into the local data
repo with the updated workflow. Snapshot sources still read complete inventory.
See ../RUNBOOK.md for upgrade and recovery instructions.

Coverage states the D020 PyPI description-link plus pinned-manifest binding and
D021 normative recovery via an official Git clone pinned at
`58c7ab92dcf80b3b1fc756d577b0552ec1cd503a`. The missing recovery metadata was
restored from the saved batch after checking all 195 candidates against stored
evidence. Source timestamps and cursors did not change. D018 is superseded for
S7; D022-D027 explain the new choices. S9 Discussions remains disabled.

The original snapshot repair, source counts and backfill audit remain documented
in REPAIR-AND-BACKFILL-REPORT.md. FIX-1-REPORT.md includes the amendment citations,
before/after table excerpt and per-fix results. P7/P8 remain out of scope. Owner
deployment commands and required human checks remain in ../RUNBOOK.md; publication
still requires reviewed curation and a successful publication verification.
