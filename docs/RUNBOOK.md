# Runbook

Local build only. Robert performs all GitHub setup and pushes. Python 3.12,
Git and gh are required. Workflows use standard ubuntu-latest runners. Budget
both collect and draft jobs: worst scheduled allocation is 10 minutes per day
plus Sunday drafts and CI, above the plan's 180-minute estimate. Measure actual
usage and lower cadence before exceeding the account's available minutes.
No free-tier allowance has been assumed or verified in this local build.

## First deploy

Inspect both local repositories and phase reports. Do not push the local history
draft as an approved brief. The private engine pin must identify an engine commit
already on the public remote. Commands, after review:

```sh
cd /Users/andres/dev/ucp-pulse
gh repo create schwentker/ucp-pulse --public --source=. --remote=origin
git push -u origin main
cd /Users/andres/dev/ucp-pulse-data
gh repo create schwentker/ucp-pulse-data --private --source=. --remote=origin
git switch main
git push -u origin main
```

If a repository already exists, use `git remote add origin` with its GitHub SSH
URL instead of `gh repo create`. Do not change an existing remote blindly.
Configure Actions to allow creating PRs in the private repo. Set a fine-grained
PAT limited to the public engine repository with Contents and Pull requests
read/write. Store it only as private-repo `UCP_PULSE_EXPORT_TOKEN`, using the
interactive prompt (no literal token in a command):

```sh
gh secret set UCP_PULSE_EXPORT_TOKEN --repo schwentker/ucp-pulse-data
```

Configure a private-main ruleset requiring PR review and the `verify` job, with
an explicitly reviewed bypass actor for the automation writer. Ordinary branch
protection cannot simply allow direct pushes by path. A bypass can also bypass
review of drafts: this is a residual risk, not path-scoped protection. Restrict
who can edit workflows/engine.lock, require human review for those changes, and
keep collect writes limited to data/state. If the account cannot grant a suitably
restricted automation bypass, do not enable collection writes; use reviewed
manual data commits until a compatible ruleset/App setup exists. No repo setting
was changed by this build.

Public main must require its `verify` check on PRs. This check runs on GitHub's
merged PR tree and rejects a latest pointer older than any included brief, so an
out-of-order export cannot silently roll latest backward. Re-run checks or update
an export branch when another export merges. Never bypass the latest check.

Enable workflows only after settings and permissions are checked:

```sh
gh workflow enable collect.yml --repo schwentker/ucp-pulse-data
gh workflow enable draft.yml --repo schwentker/ucp-pulse-data
gh workflow run collect.yml --repo schwentker/ucp-pulse-data
```

## Local commands and approval

The build environment used offline-copied pinned dependencies. A fresh machine
installs requirements-dev.txt into a Python 3.12 venv. Use `PYTHONPATH` pointing to
the engine src directory, or run from the engine with the local .pth setup.
All examples below use `python -m ucp_pulse`; the installed console entry point
has the same arguments.

```sh
export PYTHONPATH=/Users/andres/dev/ucp-pulse/src
/Users/andres/dev/ucp-pulse/.venv/bin/python -m ucp_pulse --help
```

Check out the draft branch. Edit only its curation YAML: exact event@revision
keys, KEEP/CUT decisions, cited headline/signal/watch_next, optional analyst
classification and per-item migration/affected/deadline/note fields. Nonempty
analyst fields require KEEP. Cite every nonempty claim. Then run render without
`--draft`, followed by verify with identical arguments:

```sh
python -m ucp_pulse render --data /path/to/data --curation /path/to/data/curation/PERIOD-r1.yaml --output /path/to/data/drafts/PERIOD-r1/brief
python -m ucp_pulse verify --data /path/to/data --curation /path/to/data/curation/PERIOD-r1.yaml --output /path/to/data/drafts/PERIOD-r1/brief
```

Commit curation and both rendered files to that PR. Human merge is the approval;
export re-verifies and checks that GitHub associates the trigger commit with a
human-merged private PR. Draft mode can never export. Private export is the only
job referencing the export token. Public CI has no secrets or state writes.

Bot-created PRs using GITHUB_TOKEN may not trigger pull_request workflows.
Manually dispatch Verify on the draft branch; confirm the required check attaches
to the exact head commit. If necessary push a human curation commit to trigger PR
CI. Do not merge until the required check is actually green. First deployment
must verify this behavior on GitHub; local tests cannot prove GitHub trigger rules.

## Recovery and lifecycle

Daily collect: 14:00 UTC (06:00 PST / 07:00 PDT). Sunday draft: 18:00 UTC
(10:00 PST / 11:00 PDT). Shared non-canceling concurrency serializes both workflows.
Every collect checks the due ledger, catching dropped Sunday dispatches. Empty
periods are still drafted. The tracking start is first observation, not backfill
start, so first collection does not invent historical discovery weeks.

Dispatch collect.yml for catch-up. A collector failure leaves its cursor intact
and records health; other sources continue. Below 100 remaining, GitHub reads
stop. Missing rate headers fail closed. S9 remains disabled until a new smoke
read and fixture gate pass. Never lower the limit to force a backfill.

Cached candidates are replayed against fetched state after a rejected push,
maximum three attempts, without force. Cache files stay outside the checkout and
may contain public upstream text; do not publish them as fixtures unreviewed.
If a newer source snapshot is already committed, replay refuses to regress it;
run a fresh collect. Crash before push leaves remote unchanged; rerun the same
cached envelope to publish the local commit without duplicate observations.

Existing draft branches are preserved. Human-edited branches are never rewritten.
Use Draft workflow dispatch input `revise=PERIOD` for r2 and an addendum. Closed
unmerged PRs become abandoned on the next reconciliation; ordinary dispatch does
not reopen them. A new revision is explicit. Merged PRs become published. The
local `draft --revise` command prepares a branch without publishing it.

If GitHub disables a schedule, manually enable the workflow in Actions or use
`gh workflow enable`, then dispatch collect. Do not rely on a heartbeat to revive
it. Check coverage last_success and health errors after every recovery.

Updating the engine: review/test the new engine commit, push it first, then change
config/engine.lock in a reviewed private PR to its full 40-character SHA. Workflow
permissions and checkout pins must remain least privilege. actionlint was not
available in the local build; run it before first deployment if available.

## Collection bounds after backfill

The workflow reads the initial bound from `config/collection.yaml` (`history_start`)
instead of embedding it in the daily command. Copy this file with the updated
collect template when upgrading the private repo. `smoke-collect --start` overrides
that initial bound only for sources without a complete cursor. A complete source
always resumes at `last_complete - 7 days`, even if `--start` is later. Failed or
incomplete pagination keeps the old cursor. Legacy cursors with last_complete but
no pagination_complete flag still represent complete runs; an explicit false
flag is not resumable. PR endpoints have no server-side updated-since filter, so
the collector reads pages sorted by updated descending and stops at the cutoff.
Commit endpoints send the cutoff as `since`; snapshot sources still read their
current inventory. To redo history, use a separate local data checkout with the
relevant cursor removed, retaining the original checkout as the audit trail.
