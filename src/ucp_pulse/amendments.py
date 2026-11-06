"""Derive release amendments from pinned facts, without implying shipment."""
from ucp_pulse.model import candidate
from ucp_pulse.util import utc


def amended_release(row, events=(), previous=None):
    m = dict(row['material'])
    old = (previous or {}).get('material', {})
    reasons = set(m.get('amendment_reasons', [])) | set(old.get('amendment_reasons', []))
    ids = set(m.get('amended_by', [])) | set(old.get('amended_by', []))
    if m.get('branch_head') and m.get('tag_commit') and m['branch_head'] != m['tag_commit']:
        reasons.add('branch differs from tag')
        ids.add(row['event_id'])
    if old.get('branch_head') and m.get('branch_head') != old['branch_head']:
        reasons.add('branch changed between observations')
        ids.add(row['event_id'])
    if old.get('tag_commit') and m.get('tag_commit') and m['tag_commit'] != old['tag_commit']:
        reasons.add('tag retargeted between observations')
        ids.add(row['event_id'])
    branch = 'release/' + row['subject']['version']
    if m.get('published_at'):
        for event in events:
            if event['subject'].get('repo') != row['subject']['repo']:
                continue
            material = event['material']
            pr = event['family'] == 'spec_pr' and event['facts'].get('merged') and material.get('base') == branch
            commit = event['family'] == 'normative_commit' and branch in material.get('branches', [])
            if (pr or commit) and utc(event['event_time']) > utc(m['published_at']):
                ids.add(event['event_id'])
                reasons.add('post-publication release-branch change')
    m.update(amended=bool(m.get('amended') or old.get('amended') or ids),
             amended_by=sorted(ids), amendment_reasons=sorted(reasons))
    return candidate(row['family'], row['subject'], m, {**row['facts'], 'amended': m['amended']},
                     row['evidence'], row['event_time'], row['event_time_kind'], row['authority'], row['source'])
