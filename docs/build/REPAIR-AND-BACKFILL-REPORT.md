# Snapshot repair and authenticated backfill

The 2026-11-05 authenticated sweep found 501 records citing nonexistent snapshot
paths: 339 spec PR, 140 SDK PR, 16 SDK tag and six governance observations. None
of their cited hashes equaled the hashes of their persisted normalized material.
All 501 normalized snapshots already existed. A checked one-time repair rewrote
only those pointers, updated derived inventory and saved a private old/new audit
map in data/repairs/snapshot-pointer-repair.json. The old Git commit preserves
the previous bytes. A second repair dry run found zero unresolved pointers.
Pinned evidence verification and `rebuild --check` passed.

The live announcement file uses headings such as `September 25, 2026`; the parser
now accepts this format. Ten sections were recovered from an already fetched
official contents response. Recovery verified the cached blob SHA-1 and pinned
commit before applying it. PyPI project_urls was null. The alternative binding
requires an exact repository URL in the PyPI description and the matching
`ucp-sdk` project name in the official Python SDK's pinned pyproject.toml. Ten
PyPI versions were collected with that binding ref.

S3 REST collection failed repeatedly with a connection error. A complete public
Git clone from the allowlisted official repository succeeded. Its pinned head
was 58c7ab92dcf80b3b1fc756d577b0552ec1cd503a. A local first-parent path
scan and the same structural schema alert code yielded 195 normative commits.
The redundant REST retry was stopped after this completed. S3 cursor and health
now record a successful local collection; no failed source remains in health.
No GitHub write, repository setting or secret changed.

Final private evidence commit before drafting: 0b55e35a45a684452921770aa376a9c5c62f5e5c.
There are 860 verified observations: four spec releases, 391 spec PRs, 195
normative commits, ten announcements, six governance files, 193 SDK PRs, 30 SDK
tags, 22 registry versions and nine Shopify changelog entries. The r2 history
draft is structurally valid with all 860 decisions PENDING. Publication
verification correctly rejects it until human review and narrative curation.

Validation: 282 offline tests passed, including new normalization, real heading
format, PyPI fallback and synthetic local-Git dependent-schema cases. The
private store's pinned evidence check verified every cited snapshot and its hash.
S9 Discussions is still disabled after its earlier rate-limited smoke; this
remains a visible coverage gap. The corrected engine must be pinned in the
private repo before any deployment.
