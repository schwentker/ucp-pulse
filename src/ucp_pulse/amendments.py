"""Derive release amendments from pinned facts, without implying shipment."""
from ucp_pulse.families import revision_id
from ucp_pulse.model import candidate
from ucp_pulse.util import utc


def spec_path(path):
    return path.startswith(('source/', 'docs/specification/')) or path == 'docs/versioning.md'


def path_scope(paths):
    if any(spec_path(path) for path in paths):
        return 'spec'
    if paths and all(path.startswith(('docs/', '.github/workflows/', 'site/', 'assets/'))
                     or path == 'mkdocs.yml' or path.rsplit('/', 1)[-1].upper() in {'README', 'README.MD', 'README.RST'}
                     for path in paths):
        return 'docs_site'
    return 'unknown'


def changed_pr_paths(row, paths):
    return candidate(row['family'], row['subject'], {**row['material'], 'files': sorted(set(paths))},
                     row['facts'], row['evidence'], row['event_time'], row['event_time_kind'],
                     row['authority'], row['source'])


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
    events = list(events)
    commits = {(event['subject'].get('repo'), event['material'].get('sha')): event
               for event in events if event['family'] == 'normative_commit'}
    items = {**old.get('amendment_items', {}), **m.get('amendment_items', {})}
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
                path_event = event
                paths = material.get('files', [])
                if pr and not paths:
                    path_event = commits.get((row['subject']['repo'], material.get('merge_sha')), event)
                    paths = path_event['material'].get('files', [])
                scope = path_scope(paths)
                # Normative commit records may contain only the normative subset.
                if path_event['family'] == 'normative_commit' and scope != 'spec':
                    scope = 'unknown'
                items[event['event_id']] = {
                    'scope': scope,
                    'revision': revision_id(event['event_id'], material),
                    'path_event': path_event['event_id'],
                    'path_revision': revision_id(path_event['event_id'], path_event['material']),
                }
    scopes = {item['scope'] for item in items.values()}
    refs_known = bool(m.get('branch_head') and m.get('tag_commit'))
    scoped_facts = {
        'amended_spec': 'spec' in scopes,
        'amended_docs_only': scopes == {'docs_site'},
        'branch_differs_from_tag': refs_known and m['branch_head'] != m['tag_commit'],
        'tag_at_branch_head': refs_known and m['branch_head'] == m['tag_commit'],
    }
    m.update(scoped_facts, amendment_items=items)
    m.update(amended=bool(m.get('amended') or old.get('amended') or ids),
             amended_by=sorted(ids), amendment_reasons=sorted(reasons))
    return candidate(row['family'], row['subject'], m, {**row['facts'], **scoped_facts, 'amended': m['amended']},
                     row['evidence'], row['event_time'], row['event_time_kind'], row['authority'], row['source'])
