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

Start with [build summary](docs/build/BUILD-SUMMARY.md),
[runbook](docs/RUNBOOK.md), [decisions](docs/DECISIONS.md), and the normative
[build plan](BUILD-PLAN.md). Both local repositories have no remote configured.
The local P6 history is partial: GitHub collection stopped below its rate-limit
threshold, PyPI binding failed, and Discussions is disabled. The private history
draft has 21 PENDING evidence revisions and is not publishable.
