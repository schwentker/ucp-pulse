# UCP Pulse

Experimental weekly intelligence on declared and human-reviewed UCP changes,
with coverage notes. Python 3.12, stdlib and pinned PyYAML. Human review is required
before publication. No semantic compatibility verdicts, LLM calls or store probes.

Engine code, offline tests and deployment templates belong here. Evidence and
unapproved briefs belong in the separate private ucp-pulse-data repository.

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
export PYTHONPATH="$PWD/src"
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q
.venv/bin/python -m ucp_pulse --help
```

The build used locally available pinned dependencies without package downloads.
The installation commands above are for a future owner setup.

Start with the [build summary](docs/build/BUILD-SUMMARY.md),
[repair and backfill report](docs/build/REPAIR-AND-BACKFILL-REPORT.md),
[runbook](docs/RUNBOOK.md), [decisions](docs/DECISIONS.md), and the normative
[build plan](BUILD-PLAN.md). Both local repositories have no remote configured.
The local r2 history review draft has 860 PENDING evidence items and is not
publishable until a human curates and approves its claims.
