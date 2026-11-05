# P5 report

Created the local private data repository, reusable scaffold, four private
workflows, public CI, runbook and human entailment checklist. Added explicit CLI
commands for live reads, cached transactional application, local draft/revise,
publication verification and local approved export. Deployed-only helpers create
PRs, reconcile open/closed/merged state, protect human branches and retry state
pushes without force. Shared workflow concurrency covers collect and draft.
Export checks the human-merged private commit and publication verification.
Public CI checks latest against all included approved periods at merge time.

Validation: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q`:
277 passed offline. CLI tests drive two local bare file remotes: duplicate
application, rejected push with fetch/reset/reapply, crash before push and
recovery, rebuild equality, private approval to public export, older publication
without latest rollback, and rejection of a tampered latest pointer. Lifecycle
fixtures cover bot/human edits, closed-unmerged, merged and explicit r2 addenda.
Workflow tests enforce permissions, full action SHAs, shared concurrency, secret
placement and no expressions embedded in run scripts. actionlint is unavailable;
YAML parsing and static contracts passed. No Actions run or GitHub mutation.

The private engine.lock is set to this phase's completed engine commit after
committing the engine. Public and private repositories have no configured remote.
The GitHub checkout action is pinned to 11bd71901bbe5b1630ceea73d27597364c9af683.
Runtime setup requires Python 3.12 and installs only the exact requirements pins.

Deviations: preserve existing bot draft branches instead of optional regeneration;
use --revise for additional evidence. Newer source snapshots cause safe replay
refusal and recollection, rather than applying stale facts over them. Main ruleset
bypass and bot PR check triggering need owner validation on deployment. The job
split can exceed the original 180-minute monthly estimate; see D016-D017 and the
runbook. Local tests establish Git transaction behavior, not GitHub service rules.
