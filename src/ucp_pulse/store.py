"""Append-only evidence with recoverable local file transactions.

Git is the cross-process publication transaction in the workflow layer.
All local readers recover a committed journal while holding the same lock.
"""
import fcntl
import json
import os
import shutil
from contextlib import contextmanager
from pathlib import Path
from ucp_pulse.families import revision_id
from ucp_pulse.model import revise
from ucp_pulse.amendments import amended_release
from ucp_pulse.periods import reconcile
from ucp_pulse.util import canonical, digest, json_file, safe_relative, stamp


class Store:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def locked(self):
        with (self.root / ".ucp-lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            self._recover()
            yield

    def _recover(self):
        journal = self.root / ".ucp-txn"
        if (journal / "COMMIT").exists():
            for rel in json_file(journal / "manifest.json"):
                target = self.root / safe_relative(rel)
                target.parent.mkdir(parents=True, exist_ok=True)
                temporary = target.with_name(target.name + ".new")
                shutil.copyfile(journal / "files" / rel, temporary)
                os.replace(temporary, target)
        if journal.exists():
            shutil.rmtree(journal)

    def _write(self, updates, fail_before_commit=False):
        journal = self.root / ".ucp-txn"
        for rel, content in updates.items():
            path = journal / "files" / safe_relative(rel)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
        (journal / "manifest.json").write_text(canonical(sorted(updates)))
        if fail_before_commit:
            raise RuntimeError("simulated crash before commit")
        with (journal / "COMMIT").open("w") as handle:
            handle.write("committed\n")
            handle.flush()
            os.fsync(handle.fileno())
        self._recover()

    def _records(self):
        records = []
        for path in sorted((self.root / "data/events").glob("*.jsonl")):
            records.extend(json.loads(line) for line in path.read_text().splitlines() if line)
        return records

    @staticmethod
    def derive(records):
        inventory = {}
        observations = set()
        for row in records:
            eid = row["event_id"]
            if row["material_digest"] != digest(row["material"]) or row["revision_id"] != revision_id(eid, row["material"]):
                raise ValueError("invalid revision digest")
            if row["observation_id"] in observations:
                raise ValueError("duplicate observation")
            prior = inventory.get(eid)
            if row["supersedes"] != (prior["revision_id"] if prior else None):
                raise ValueError("broken revision chain")
            observations.add(row["observation_id"])
            inventory[eid] = row
        return {"index": {key: value["revision_id"] for key, value in inventory.items()}, "inventory": inventory}

    def records(self):
        with self.locked():
            return self._records()

    def state(self, name, default=None):
        if name not in {"index", "inventory", "cursors", "health", "periods", "tracking"}:
            raise ValueError("unknown state name")
        with self.locked():
            return json_file(self.root / f"state/{name}.json", {} if default is None else default)

    def rebuild(self, check=False):
        with self.locked():
            derived = self.derive(self._records())
            equal = all(json_file(self.root / f"state/{key}.json", {}) == value for key, value in derived.items())
            if check and not equal:
                raise ValueError("derived state differs from evidence")
            if not check:
                self._write({f"state/{key}.json": canonical(value) + "\n" for key, value in derived.items()})
            return equal

    def apply(self, batches, observed_at, run_id, tracking_start=None, fail_before_commit=False):
        with self.locked():
            records = self._records()
            inventory = self.derive(records)["inventory"]
            runs_path = self.root / "state/runs.jsonl"
            run_lines = runs_path.read_text() if runs_path.exists() else ""
            if any(json.loads(line)["run_id"] == run_id for line in run_lines.splitlines()):
                return 0
            if records and stamp(observed_at) < max(row["observed_at"] for row in records):
                raise ValueError("observation time cannot move backwards")
            cursors = json_file(self.root / "state/cursors.json", {})
            health = json_file(self.root / "state/health.json", {})
            updates = {}
            additions = []
            combined = dict(inventory)
            for batch in batches:
                if batch.get("complete", False):
                    combined.update({i["event_id"]: i for i in batch.get("items", [])})
            releases = {eid: amended_release(row, combined.values(), inventory.get(eid))
                        for eid, row in combined.items() if row['family'] == 'spec_release'}
            written_releases = set()
            for batch in batches:
                source = batch["source"]
                old = health.get(source, {})
                if not batch.get("complete", False):
                    health[source] = {**old, "last_error": batch.get("error", "incomplete pagination"),
                                      "consecutive_failures": old.get("consecutive_failures", 0) + 1}
                    continue
                count = 0
                for item in batch.get("items", []):
                    if item['event_id'] in releases:
                        item = releases[item['event_id']]
                        written_releases.add(item['event_id'])
                        updates[item['evidence']['snapshot']] = canonical(item['material']) + "\n"
                    row = revise(item, inventory.get(item["event_id"]), observed_at, run_id)
                    if row:
                        additions.append(row)
                        inventory[row["event_id"]] = row
                        count += 1
                for value in batch.get("snapshots", []):
                    updates[f"data/snapshots/{digest(value)}.json"] = canonical(value) + "\n"
                cursors[source] = {"last_complete": stamp(observed_at), "cursor": batch.get("cursor"),
                                   "overlap_days": 7, "pagination_complete": True}
                health[source] = {"last_success": stamp(observed_at), "last_error": None,
                                  "consecutive_failures": 0,
                                  "last_nonzero": stamp(observed_at) if count else old.get("last_nonzero")}
            # Derived revisions do not pretend that S1 performed a new upstream read.
            for eid, item in sorted(releases.items()):
                if eid in written_releases:
                    continue
                row = revise(item, inventory.get(eid), observed_at, run_id)
                if row:
                    additions.append(row)
                    updates[item['evidence']['snapshot']] = canonical(item['material']) + "\n"
            if additions:
                rel = "data/events/" + stamp(observed_at)[:7] + ".jsonl"
                path = self.root / rel
                updates[rel] = (path.read_text() if path.exists() else "") + "".join(canonical(row) + "\n" for row in additions)
            derived = self.derive(records + additions)
            tracking = json_file(self.root / "state/tracking.json", {"start": stamp(tracking_start or observed_at)})
            periods = reconcile(json_file(self.root / "state/periods.json", {}), tracking["start"], observed_at)
            states = {**derived, "cursors": cursors, "health": health, "periods": periods, "tracking": tracking}
            updates.update({f"state/{key}.json": canonical(value) + "\n" for key, value in states.items()})
            run = {"run_id": run_id, "observed_at": stamp(observed_at), "added": len(additions),
                   "sources": [{"source": b["source"], "complete": b.get("complete", False)} for b in batches]}
            updates["state/runs.jsonl"] = run_lines + canonical(run) + "\n"
            self._write(updates, fail_before_commit)
            return len(additions)

    def update_periods(self, ledger):
        with self.locked():
            self._write({"state/periods.json": canonical(ledger) + "\n"})
