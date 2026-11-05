# Phase 1

Built the Python 3.12 core: family identity/material contracts, immutable revisions and observation transitions, append-only JSONL, recoverable local transactions, derived index/inventory, cursor/health/run state and Sunday UTC due periods. The rebuild command checks equality and revision-chain integrity.

Validation: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q` passed: 17 tests. Fixtures are explicitly synthetic. Tests deny socket access in pytest and Python children; git children are restricted to file transport. Cases cover DST/midnight, missing Sunday, empty periods, late discovery, duplicate dispatch, crash before commit, independent source failure, reversion and index recovery.

Runtime: Python 3.12.12. Dependencies were copied offline from an existing local Python 3.12 environment: PyYAML 6.0.3, pytest 7.4.3 and pytest's required iniconfig 2.3.0, packaging 25.0, pluggy 1.6.0. No dependency download or network call. These transitive test dependencies are pinned for reproducibility.

Decisions D001-D007 resolve prompt/plan conflicts, operational versus derived state, content reversion and structural versus publishable verification. No weakened gate. Git remote remains unset. P1 exit passed.
