"""One-time repair of snapshot pointers produced by pre-normalization hashing.

The original Git commit remains an immutable audit trail. No material, revision
identity, event time, or facts are changed. Refuses any case it cannot prove.
"""
import argparse
import json
from collections import Counter
from pathlib import Path
from ucp_pulse.store import Store
from ucp_pulse.util import canonical, digest


def repair(root, apply=False):
    store = Store(root)
    with store.locked():
        records = store._records()
        changes = []
        for row in records:
            cited = row['evidence']['snapshot']
            if (store.root / cited).exists():
                content = json.loads((store.root / cited).read_text())
                if digest(content) != Path(cited).stem:
                    raise ValueError('existing snapshot has wrong content hash')
                continue
            target = 'data/snapshots/' + digest(row['material']) + '.json'
            path = store.root / target
            if not path.exists() or json.loads(path.read_text()) != row['material']:
                raise ValueError('cannot prove normalized snapshot for ' + row['event_id'])
            changes.append({'observation_id': row['observation_id'], 'old': cited, 'new': target})
            row['evidence']['snapshot'] = target
        summary = {'repaired': len(changes), 'by_family': dict(Counter(row['family'] for row in records if row['observation_id'] in {c['observation_id'] for c in changes}))}
        if apply and changes:
            partitions = {}
            for row in records:
                rel = 'data/events/' + row['first_seen_at'][:7] + '.jsonl'
                partitions.setdefault(rel, []).append(row)
            derived = Store.derive(records)
            updates = {rel: ''.join(canonical(row) + '\n' for row in rows) for rel, rows in partitions.items()}
            updates.update({f'state/{name}.json': canonical(value) + '\n' for name, value in derived.items()})
            updates['data/repairs/snapshot-pointer-repair.json'] = canonical({'changes': changes}) + '\n'
            store._write(updates)
        return summary


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--data', required=True)
    p.add_argument('--apply', action='store_true')
    args = p.parse_args()
    print(canonical(repair(args.data, args.apply)))
