# Build summary

P1-P5 are implemented and committed locally. The P6 local history backfill now
contains 860 verified observations and a separate r2 review draft. No remote
push, public PR or deployment has occurred. Neither local repository has a remote.

Validation: 282 offline tests passed. The test harness blocks Python network
access, including child Python processes, and Git tests use file transport only.
The suite covers event revision identity, UTC periods, source gates, deterministic
rendering, bad curation, Git retries/crashes, lifecycle and monotonic exports.
Actionlint was unavailable; YAML and workflow security-contract checks passed.

A one-time repair corrected 501 snapshot pointers that had been computed before
normalization. The replacement snapshots already existed and matched stored
material. The private repository records every pointer change and retains the
prior commit as an audit trail. Pinned verification now confirms every snapshot.
The writer now hashes the normalized material that it persists.

Authenticated and cached reads yielded four spec releases, 391 spec PRs, 195
normative commits, ten official announcements, six governance files, 193 SDK PRs,
30 SDK tags, ten PyPI and 12 npm versions, and nine Shopify changelog entries.
S3 recovered from the allowlisted public Git repository at a pinned head after
REST connection failures. PyPI binding uses its exact source link plus the
matching pinned official package manifest because project_urls is null. S9
Discussions remains disabled and is shown as a coverage gap.

The r2 history draft passes structural verification with all 860 decisions
PENDING. No headline or human narrative has been approved. Publication verify
correctly fails until curation and review. See REPAIR-AND-BACKFILL-REPORT.md and
DECISIONS.md for the repair, source evidence and limits.

Owner deployment remains local-only pending review. Push the engine first, then
the private data repo, set a fine-grained export token only in private secrets,
configure human PR checks and the reviewed automation writer bypass, then enable
workflows. Exact commands and the checks to perform are in docs/RUNBOOK.md.
Do not merge the history draft until every claim cites approved evidence and
publication verification passes. P7/P8 were not attempted.
