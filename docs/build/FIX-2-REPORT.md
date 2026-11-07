# Fix 2 report

Fix A passed 309 offline tests. Fix B passed 310. Both used Python 3.12 and
the required pytest command. R4 renders byte for byte across runs and passes
`verify --draft`. Publication verification rejects its 875 PENDING decisions.

All four lines qualify as **spec** under the requested path rule. Citations
refer to the r4 source ledger.

| Line | Example supporting evidence |
| --- | --- |
| v2026-01-11 | Commit `3f25ffec1401` changed `docs/specification/ap2-mandates.md` [S203]. PR #282 is separately listed as docs-only because its merge changed only `docs/stylesheets/custom.css`. |
| v2026-01-23 | Commit `109ab925b9e7` changed `docs/specification/buyer-consent.md` [S160]. |
| v2026-04-08 | All ten PRs have cited spec paths. #431's merge touched `source/schemas/common/identity_linking.json`. The tag is at the observed branch head. |
| v2026-08-25 | Commit `3a541e135caf` changed `docs/specification/getting-started.md` [S752]. |

Before, abbreviated from r3:

```text
{"annotations":[],"classification":"unknown","dependents":[...],"file":"source/schemas/capability.json","pointers":[...]}
```

After:

```text
source/schemas/capability.json: 8 changed pointers (/$defs/base/allOf, /$defs/base/properties, /$defs/base/type, /$defs/business_schema, /$defs/discovery, and 3 more); 15 dependents; classification unknown
```

The Markdown check found zero literal JSON openings. Full pointer and
dependent lists remain in JSON.

For seven PRs lacking a matching normative snapshot, path evidence came
from first-parent diffs in the existing D021 pinned Git clone. Local
reconciliation appended those seven revisions and four release revisions.
There was no recollection or cursor advance. Items outside the spec and
docs/site path categories remain unknown. The r2 and r3 artifacts were
preserved. D028 and D029 record these choices.
