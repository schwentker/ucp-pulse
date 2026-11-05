"""Synthetic state/time fixtures. No upstream claims."""
import copy
import json
import socket
import subprocess
import sys
import pytest
from ucp_pulse.model import candidate
from ucp_pulse.periods import period_for, reconcile, in_period, late, transition
from ucp_pulse.store import Store
from ucp_pulse.util import canonical

T = "2026-11-05T00:00:00Z"


def item(title="synthetic A"):
    return candidate("spec_pr", {"repo": "synthetic/fixture", "number": 1},
                     {"number": 1, "title": title, "labels": []}, {"merged": False},
                     {"url": "https://example.invalid/synthetic", "ref": "synthetic:fixture", "excerpt": title},
                     "2026-01-11T00:00:00Z", "posted", "secondary", "synthetic")


def batch(value=None):
    return {"source": "synthetic", "complete": True, "items": [value or item()]}


def test_network_guard():
    with pytest.raises(AssertionError):
        socket.create_connection(("example.invalid", 443))
    result = subprocess.run([sys.executable, "-c", "import socket; socket.create_connection(('example.invalid',443))"], capture_output=True)
    assert result.returncode != 0 and b"network disabled" in result.stderr


@pytest.mark.parametrize("value,start", [
    ("2026-11-01T00:00:00Z", "2026-11-01"),
    ("2026-10-31T23:59:59Z", "2026-10-25"),
    ("2026-11-08T00:00:00Z", "2026-11-08"),
    ("2026-11-01T01:30:00-07:00", "2026-11-01"),
    ("2026-11-01T01:30:00-08:00", "2026-11-01"),
    ("2026-03-08T01:59:59-08:00", "2026-03-08"),
    ("2026-03-08T03:00:00-07:00", "2026-03-08"),
])
def test_utc_edges(value, start):
    assert period_for(value)["period_id"] == "p-" + start


def test_naive_clock_rejected():
    with pytest.raises(ValueError):
        period_for("2026-11-01T00:00:00")


def test_dropped_run_and_empty_week():
    ledger = reconcile({}, "2026-10-25T00:00:00Z", "2026-11-09T10:00:00Z")
    assert list(ledger) == ["p-2026-10-25:weekly:r1", "p-2026-11-01:weekly:r1"]
    assert reconcile(ledger, "2026-10-25T00:00:00Z", "2026-11-09T11:00:00Z") == ledger
    ledger = transition(ledger, "p-2026-10-25:weekly:r1", "open", 1)
    ledger = transition(ledger, "p-2026-10-25:weekly:r1", "abandoned")
    with pytest.raises(ValueError):
        transition(ledger, "p-2026-10-25:weekly:r1", "open")


def test_revisions_dedupe_late_and_rebuild(tmp_path):
    store = Store(tmp_path)
    assert store.apply([batch()], T, "run-a") == 1
    assert store.apply([batch()], T, "run-a") == 0
    assert store.apply([batch()], T, "run-b") == 0
    first = store.records()[0]
    assert late(first, period_for(T))
    assert in_period(first, period_for(T))
    assert not in_period(first, period_for("2026-11-08T00:00:00Z"))
    assert store.apply([batch(item("synthetic B"))], T, "run-c") == 1
    rows = store.records()
    assert rows[0]["event_id"] == rows[1]["event_id"]
    assert rows[1]["supersedes"] == rows[0]["revision_id"]
    assert store.rebuild(check=True)
    (tmp_path / "state/index.json").write_text("{}")
    with pytest.raises(ValueError):
        store.rebuild(check=True)
    assert not store.rebuild()
    assert store.rebuild(check=True)


def test_reversion_is_observed_again(tmp_path):
    store = Store(tmp_path)
    for n, title in enumerate(["A", "B", "A"]):
        assert store.apply([batch(item(title))], T, str(n)) == 1
    assert len({x["revision_id"] for x in store.records()}) == 2
    assert len({x["observation_id"] for x in store.records()}) == 3
    assert store.state("inventory")["fixture:pr:1"]["material"]["title"] == "A"


def test_crash_before_commit(tmp_path):
    store = Store(tmp_path)
    store.apply([batch()], T, "before")
    original = store.records()
    with pytest.raises(RuntimeError):
        store.apply([batch(item("B"))], T, "crash", fail_before_commit=True)
    assert Store(tmp_path).records() == original
    assert store.apply([batch(item("B"))], T, "crash") == 1
    assert store.rebuild(check=True)


def test_source_failure_preserves_cursor_and_other_source(tmp_path):
    store = Store(tmp_path)
    store.apply([batch()], T, "a")
    cursor = store.state("cursors")
    other = item("other")
    other["event_id"] = "other:pr:1"
    store.apply([{"source": "synthetic", "complete": False, "error": "synthetic failure"},
                 {"source": "other", "complete": True, "items": [other]}], T, "b")
    assert store.state("cursors")["synthetic"] == cursor["synthetic"]
    assert store.state("health")["synthetic"]["consecutive_failures"] == 1
    assert len(store.records()) == 2


def test_normalization_and_facts_contract(tmp_path):
    store = Store(tmp_path)
    store.apply([batch()], T, "a")
    assert store.apply([batch(item(" synthetic A\r\n"))], T, "b") == 0
    wrong = item()
    wrong["facts"] = {"merged": True}
    with pytest.raises(ValueError):
        store.apply([batch(wrong)], T, "c")


def test_identity_ignores_clock_and_run():
    assert item()["event_id"] == item("changed")["event_id"]
    with pytest.raises(ValueError):
        candidate("spec_pr", {"repo": "s/x", "number": 1}, {"unregistered": 1}, {},
                  {"url": "https://example.invalid", "ref": "synthetic"}, T, "posted", "secondary", "synthetic")


def test_jsonl_tampering_rejected(tmp_path):
    store = Store(tmp_path)
    store.apply([batch()], T, "a")
    path = next((tmp_path / "data/events").glob("*"))
    row = json.loads(path.read_text())
    row["material"]["title"] = "tampered"
    path.write_text(canonical(row) + "\n")
    with pytest.raises(ValueError):
        store.rebuild(check=True)

def test_normalized_snapshot_pointer_matches_persisted_material():
    from ucp_pulse.model import candidate
    from ucp_pulse.util import digest
    evidence={'url':'https://github.com/example/repo','ref':'example/repo@'+'a'*40,'snapshot':'data/snapshots/'+'0'*64+'.json','excerpt':''}
    item=candidate('governance',{'path':'GOVERNANCE.md'}, {'path':'GOVERNANCE.md','body':'  rules\r\n','deleted':False}, {'deleted':False},evidence,'2020-01-01T00:00:00Z','observed','official_repo','S5')
    assert item['evidence']['snapshot']=='data/snapshots/'+digest(item['material'])+'.json'
