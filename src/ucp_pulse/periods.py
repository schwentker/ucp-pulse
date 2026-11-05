"""Sunday UTC half-open periods and recoverable due ledger."""
from datetime import timedelta
from ucp_pulse.util import stamp, utc


def period_for(value):
    dt = utc(value)
    day = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    start = day - timedelta(days=(day.weekday() + 1) % 7)
    end = start + timedelta(days=7)
    return {"period_id": "p-" + start.date().isoformat(), "start": stamp(start.isoformat()),
            "end": stamp(end.isoformat()), "type": "weekly"}


def reconcile(ledger, tracking_start, as_of):
    ledger = {k: dict(v) for k, v in ledger.items()}
    period = period_for(tracking_start)
    while utc(period["end"]) <= utc(as_of):
        key = period["period_id"] + ":weekly:r1"
        ledger.setdefault(key, {**period, "revision": 1, "status": "due", "pr_number": None})
        period = period_for(period["end"])
    return ledger


def in_period(record, period):
    return utc(period["start"]) <= utc(record["first_seen_at"]) < utc(period["end"])


def late(record, period):
    return in_period(record, period) and utc(record["event_time"]) < utc(period["start"])


def transition(ledger, key, status, pr_number=None):
    allowed = {"due": {"open"}, "open": {"open", "published", "abandoned"},
               "published": set(), "abandoned": set()}
    row = dict(ledger[key])
    if status not in allowed[row["status"]]:
        raise ValueError("invalid period transition; use revise for a new revision")
    row.update(status=status, pr_number=pr_number or row.get("pr_number"))
    return {**ledger, key: row}
