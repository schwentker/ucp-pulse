# Fix 1 report

R1-R6 are complete locally. Python 3.12.12; no dependencies added, network
collection, remote writes, secrets, README edits, KEEP decisions or headlines.
The existing README edit, LICENSE and staged document moves were preserved.

R1 derives sticky amendments from release-branch PRs/commits after publication,
branch/tag divergence and observation comparisons, including tag retargeting.
Release revisions retain supporting event IDs and reasons. Artifact republication
still requires notes/assets changes. Offline reconciliation appended four release
revisions, preserving prior evidence, source cursors and health timestamps.

R2/R3 add event time plus kind beside first seen, true-fact labels, and named
version-board columns. R4 gives complete cursors precedence with seven-day overlap,
stops PR pagination at the cutoff, and moves the initial bound to configuration.
R5 adds Base and groups same-day backports after main without hiding rows.
R6 supersedes D018 and shows D020/D021 provenance in Coverage.

Full offline command after every fix:
`PYTHONPATH=src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q`.
Counts: R1 290; R2 292; R3 294; R4 301; R5 302; R6 308, all passing.
Golden rendering is byte-stable. All 48 breaking rows remain. No JSON object
appears in a rendered table cell. All 864 r3 decisions remain PENDING;
`verify --draft` passes and publication `verify` rejects PENDING evidence.
R2 is byte-for-byte unchanged. R3 pins evidence commit
`6223ae41b5c2b6ba98328184f0a1cffa619e8766`.

## April amendment citations

The April release [S274] is amended; artifact_republished remains false.
Its ten PRs and ten corresponding commits are the following evidence pairs,
not twenty distinct changes. Citation labels refer to the r3 source ledger.

| PR | Corresponding commit |
| --- | --- |
| [#350](https://github.com/Universal-Commerce-Protocol/ucp/pull/350) [S279] | [d24e49823215](https://github.com/Universal-Commerce-Protocol/ucp/commit/d24e498232153077e1224327e7afbe1a3b3c411c) [S278] |
| [#356](https://github.com/Universal-Commerce-Protocol/ucp/pull/356) [S283] | [63737330e46a](https://github.com/Universal-Commerce-Protocol/ucp/commit/63737330e46a08ff47e63c68379ee95043c76079) [S282] |
| [#431](https://github.com/Universal-Commerce-Protocol/ucp/pull/431) [S347] | [a5f9d54af200](https://github.com/Universal-Commerce-Protocol/ucp/commit/a5f9d54af2009c02d433b2bb9b4e99a3eeddf95a) [S346] |
| [#433](https://github.com/Universal-Commerce-Protocol/ucp/pull/433) [S358] | [a2d8bf0b8f5a](https://github.com/Universal-Commerce-Protocol/ucp/commit/a2d8bf0b8f5a6fc790f677899c2c7da0684fe33d) [S357] |
| [#440](https://github.com/Universal-Commerce-Protocol/ucp/pull/440) [S345] | [fcf48d000033](https://github.com/Universal-Commerce-Protocol/ucp/commit/fcf48d00003352808f9f48778d15c1b9c592da75) [S344] |
| [#813](https://github.com/Universal-Commerce-Protocol/ucp/pull/813) [S677] | [a25a4a24e738](https://github.com/Universal-Commerce-Protocol/ucp/commit/a25a4a24e738b74c8fa83254448d0666e478f595) [S676] |
| [#828](https://github.com/Universal-Commerce-Protocol/ucp/pull/828) [S720] | [64564bbcc77a](https://github.com/Universal-Commerce-Protocol/ucp/commit/64564bbcc77a9dc47af085b216bb4a6d97e4c5d6) [S719] |
| [#829](https://github.com/Universal-Commerce-Protocol/ucp/pull/829) [S722] | [f021fcb2debb](https://github.com/Universal-Commerce-Protocol/ucp/commit/f021fcb2debbccc5fcf1d8c2eec0a1d889df609e) [S721] |
| [#885](https://github.com/Universal-Commerce-Protocol/ucp/pull/885) [S762] | [0f06734b8946](https://github.com/Universal-Commerce-Protocol/ucp/commit/0f06734b8946cea27157606080e77746657fca08) [S761] |
| [#935](https://github.com/Universal-Commerce-Protocol/ucp/pull/935) [S821] | [9c9d6fce39ff](https://github.com/Universal-Commerce-Protocol/ucp/commit/9c9d6fce39ffa8bf7cb66309c378b79fb75b5382) [S820] |

## Before/after table excerpt

Selected fields of the #431 breaking row, using the same source evidence:

| Draft | Base | Facts | Event time (kind) | First seen |
| --- | --- | --- | --- | --- |
| r2 | inside JSON | JSON including false opened | absent | 2026-11-05T15:21:35.523115Z |
| r3 | release/2026-04-08 | author-declared breaking; merged; base release/2026-04-08 | 2026-05-20T05:43:08.000000Z (merged) | 2026-11-05T15:21:35.523115Z |

## Choices and limits

D022-D027 record the choices. R5 refines R2 ordering within each UTC day;
other tables retain event-time order. Git recovery metadata was missing from
health, so a local repair cross-checked all 195 saved candidates against existing
evidence and restored the recorded pin without recollection:
`58c7ab92dcf80b3b1fc756d577b0552ec1cd503a`.
PR endpoints lack an updated-since filter; recent pages are read until the cutoff.
Snapshot sources still require full inventory reads. No live pagination or hosted
workflow was exercised. S9 remains disabled, and no claim is approved.
