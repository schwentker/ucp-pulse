# P3 report

Implemented S4 dated notices, S5 governance, S6 SDK/tool tags and PRs, S7 PyPI,
S8 npm and S10 RSS. Source configuration records activation gates and S9 denial.
Added bounded before/after diff fragments and a source-isolated collection runner
with seven-day cursor overlap. Registry binding validates repository metadata;
tags never imply package publication. No source data was published.

Validation: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q`:
237 passed, network blocked in parent and child Python processes. Added 21
announcement, 21 governance, 21 SDK tag, 22 PyPI, 22 npm and 22 RSS labeled
synthetic cases, plus source-isolation, overlap and fragment tests. Existing real
SDK merge-subject fixtures remain covered. A UTC datetime conversion defect found
by overlap validation was fixed before proceeding.

Manual smoke: `.venv/bin/python /tmp/ucp-p3-smoke.py`, read-only registry GET and
GraphQL query, 2026-11-05 UTC. Sanitized results in P3-SMOKE.json. npm succeeded:
12 version records, latest 0.5.1, repository binding to the official js-sdk.
Discussions failed: `GitHub remaining 0 < 100; reset=1793867601`. S9 is disabled.
The smoke response summary contains no token, cookie, author or personal fields.
Full upstream response bodies were not saved as fixtures.

Deviations: local smoke replaces Actions as required by the build prompt. No S9
collector is activated after denial. S10's labeled-set precision is 100%, with
zero bare-UCP false positives; future feed coverage is not implied. S4 parser
format and S5 paths still need a successful live GitHub collection. GitHub live
backfill will be constrained by the missing GITHUB_TOKEN and remaining-budget
threshold. See D011-D013.
