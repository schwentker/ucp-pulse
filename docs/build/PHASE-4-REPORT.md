# P4 report

Built pure Markdown/JSON rendering, exact revision curation, pinned Git evidence
loading, duplicate-key-safe YAML parsing and CLI seed/render/verify commands.
Mandatory blocks precede optional blocks; coverage and generated citations are
always present. Draft previews label pending evidence. Publication verification
rejects every PENDING decision, non-KEEP claim citation, unbound human text,
unknown curation fields and output mismatch. Derived state and snapshot hashes
are verified. Human entailment remains a review responsibility.

Validation: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -q`:
269 passed offline. Tests include repeat byte equality, clones in two different
path layouts, 26 seeded invalid cases, CUT exclusion, draft-only PENDING handling,
empty weeks, late arrivals, all window revisions, 48-hour stale boundaries,
pinned evidence, output tampering and duplicate YAML keys. Tests found and fixed
mutable aliasing in revision construction and curation seeding. No live calls.

Deviations: D014 requires revision-qualified evidence citations, stronger than
the plan's illustrative event-only YAML. D015 shows main-ahead as unknown rather
than guessing from incomplete ancestry; all observed versions are listed rather
than silently selecting a latest version using mixed SDK tag schemes. Pending
preview is structurally valid but explicitly not publishable. Final renderer
uses pinned content, not current working-directory state.
