"""Golden brief built entirely from labeled synthetic evidence."""
import json
from pathlib import Path
from ucp_pulse.amendments import amended_release
from ucp_pulse.collectors import SPEC, evidence
from ucp_pulse.model import candidate, revise
from ucp_pulse.render import render, seed

NOW='2020-02-10T00:00:00Z'
PERIOD={'id':'history-2020-01-01','type':'history','start':'2020-01-01T00:00:00Z','end':NOW,'revision':'r1'}
GOLDEN=Path(__file__).parent/'golden'/'history.md'


DETAIL = {
    'file': 'source/schemas/synthetic.json',
    'pointers': [f'/field/{n}' for n in range(7)],
    'annotations': ['ucp_request'],
    'dependents': ['source/schemas/synthetic-dependent.json'],
    'classification': 'unknown',
}


def synthetic_records():
    rows=[]
    for n in (2,1):
        date=f'2020-01-0{n}T00:00:00Z'
        for family,subject,material,facts,kind in [
            ('spec_pr',{'repo':SPEC,'number':n},{'title':f'feat!: synthetic change {n}','base':'main'},
             {'merged':True,'opened':False,'author_declared_breaking':True},'merged'),
            ('normative_commit',{'repo':SPEC,'sha':str(n)*40},{'subject':f'synthetic normative {n}','files':['docs/specification/synthetic.md'],'changes':[DETAIL],'branches':['release/2020-01-01']},
             {'classification':'unknown'},'committed'),
            ('announcement',{'date':date[:10],'slug':f'synthetic-{n}'},{'title':f'Synthetic notice {n}','date':date[:10]},
             {'notice_posted':True,'deleted':False},'posted'),
            ('governance',{'repo':SPEC,'path':f'SYNTHETIC-{n}.md'},{'path':f'SYNTHETIC-{n}.md'},
             {'deleted':False},'observed'),
            ('changelog',{'guid':f'synthetic-{n}'},{'title':f'Synthetic changelog {n}','published_at':date},
             {'ucp_scoped':True},'published'),
        ]:
            # PR event times deliberately tie; identity resolves the tie.
            time='2020-01-02T00:00:00Z' if family=='spec_pr' else date
            c=candidate(family,subject,material,facts,evidence('https://example.invalid/synthetic', 'synthetic@'+'a'*40, material),time,kind,'official_repo','S1')
            rows.append(revise(c,None,NOW,'synthetic'))
    for family,subject,material,facts in [
        ('spec_release',{'repo':SPEC,'version':'2020-01-01'},
         {'version':'2020-01-01','tag':'v2020-01-01','tag_commit':'a'*40,'branch_head':'b'*40,'published_at':'2020-01-01T00:00:00Z','amended':True},
         {'tagged':True,'release_published':True,'amended':True,'artifact_republished':False,'deleted':{'tag':False,'branch':False}}),
        ('sdk_tag',{'repo':SPEC.replace('/ucp','/python-sdk'),'tag':'v1.0.0'},
         {'tag':'v1.0.0','scheme':'semver','tag_commit':'c'*40}, {'tagged':True,'release_published':False}),
        ('registry_version',{'registry':'pypi','package':'ucp-sdk','version':'1.0.0'},
         {'version':'1.0.0','published_at':'2020-01-02T00:00:00Z',
          'binding_ref':'Universal-Commerce-Protocol/python-sdk@'+'a'*40+':pyproject.toml'},
         {'package_published':True,'deleted':False,'yanked':False}),
        ('registry_version',{'registry':'npm','package':'@ucp-js/sdk','version':'1.0.0'},
         {'version':'1.0.0','published_at':'2020-01-02T00:00:00Z','dist_tags':['latest']},
         {'package_published':True,'deleted':False,'yanked':False}),
    ]:
        c=candidate(family,subject,material,facts,evidence('https://example.invalid/synthetic','synthetic@'+'a'*40,material),
                    material.get('published_at',NOW),'published' if material.get('published_at') else 'observed','official_repo','S1')
        if family=='spec_release':
            c=amended_release(c, rows)
        rows.append(revise(c,None,NOW,'synthetic'))
    return rows


def rendered():
    rows=synthetic_records()
    health={'S3':{'last_success':NOW,'git_recoveries':[{'pinned_head':'b'*40,'observed_at':NOW}]}}
    return render(rows,health,{},seed(rows,'a'*40,NOW,PERIOD),draft=True)


def test_history_golden_and_byte_stability():
    md,js=rendered()
    assert md==GOLDEN.read_text()
    assert (md,js)==rendered()


def test_all_discovery_tables_show_event_and_observation_separately():
    md,js=rendered()
    ledger={r['citation']:r for r in json.loads(js)['source_ledger']}
    count=0
    for block in md.split('## ')[1:]:
        lines=[l for l in block.splitlines() if l.startswith('|')]
        if not lines or 'First seen' not in lines[0]: continue
        count+=1
        columns=[v.strip() for v in lines[0].split('|')[1:-1]]
        assert 'Event time (kind)' in columns
        order=[]
        for line in lines[2:]:
            values=[v.strip() for v in line.split('|')[1:-1]]
            row=ledger[values[-1].strip('[]')]
            kind='observed, not published' if row['event_time_kind']=='observed' else row['event_time_kind']
            assert values[columns.index('Event time (kind)')]==row['event_time']+' ('+kind+')'
            assert values[columns.index('First seen')]=='2020-02-10T00:00:00.000000Z'
            order.append((row['event_time'],row['key'].split('@')[0]))
        assert order==sorted(order)
    assert count==6
    notices=md.split('## Official notices')[1].split('## Governance')[0]
    assert '2020-01-01T00:00:00.000000Z (posted)' in notices


def test_named_version_board_and_true_facts_only():
    md,_=rendered()
    tables='\n'.join(l for l in md.splitlines() if l.startswith('|'))
    assert '{"' not in tables
    assert '| Component | Version or tag | Tag commit (short) | Published | Amended | Notes | Evidence |' in md
    assert '| Spec release lines | v2020-01-01 | aaaaaaaaaaaa | 2020-01-01T00:00:00Z | spec |' in md
    assert '| python-sdk | v1.0.0 | cccccccccccc | unknown | unknown |' in md
    assert 'author-declared breaking; merged; base main' in md
    for absent in ('opened','artifact republished','deleted tag','deleted branch','yanked','available','shipped','{"'):
        assert absent not in tables
    assert 'official date 2020-01-01' in md


def test_only_true_nested_deletion_facts_are_named():
    from ucp_pulse.render import readable_facts
    row={'family':'spec_release','material':{},'facts':{'deleted':{'tag':True,'release':False},'amended':False}}
    assert readable_facts(row)=='deleted tag'


def test_breaking_base_and_same_day_backports_after_main_without_losing_rows():
    rows=[r for r in synthetic_records() if r['family']=='spec_pr']
    for row in rows:
        row['material']['base']='release/2020-01-01' if row['subject']['number']==2 else 'main'
        row['event_time']='2020-01-02T09:00:00.000000Z' if row['subject']['number']==2 else '2020-01-02T10:00:00.000000Z'
    prior={**rows[0],'event_id':'ucp:pr:3','subject':{**rows[0]['subject'],'number':3},
           'material':{**rows[0]['material'],'title':'feat!: synthetic previous-day backport','base':'release/2020-01-01'},
           'event_time':'2020-01-01T09:00:00.000000Z'}
    tied={**rows[1],'event_id':'ucp:pr:4','subject':{**rows[1]['subject'],'number':4},
          'material':{**rows[1]['material'],'title':'feat!: synthetic tied main','base':'main'},
          'event_time':'2020-01-02T10:00:00.000000Z'}
    rows=[revise(r,None,NOW,'synthetic') for r in [tied,*rows,prior]]
    md,js=render(rows,{},{},seed(rows,'a'*40,NOW,PERIOD),draft=True)
    block=md.split('## Breaking and pending-breaking')[1].split('## Release amendments')[0]
    assert '| Change | Repo | Base |' in block
    citations={r['citation']:r['key'].split('@')[0] for r in json.loads(js)['source_ledger']}
    lines=[l for l in block.splitlines() if l.startswith('| feat!:')]
    ids=[citations[l.split('|')[-2].strip().strip('[]')] for l in lines]
    assert ids==['ucp:pr:3','ucp:pr:1','ucp:pr:4','ucp:pr:2']
    assert len(lines)==len(rows)==4
    assert sum('| release/2020-01-01 |' in line for line in lines)==2


def test_structural_detail_is_bounded_and_json_keeps_full_evidence():
    md, js = rendered()
    assert '{"' not in md
    assert '7 changed pointers (/field/0, /field/1, /field/2, /field/3, /field/4, and 2 more)' in md
    assert 'request annotations: ucp_request; 1 dependent; classification unknown' in md
    assert '/field/5' not in md and DETAIL['dependents'][0] not in md
    details = [c for row in json.loads(js)['evidence'] for c in row['material'].get('changes', [])]
    assert details == [DETAIL, DETAIL]


def release_amendments_with_superseded_revision():
    rows = synthetic_records()
    prior = next(row for row in rows if row['family'] == 'spec_release')
    updated = {
        **prior,
        'material': {**prior['material'], 'tag': 'v2020-01-01-current'},
    }
    latest = revise(updated, prior, NOW, 'synthetic-latest')
    rows.append(latest)
    md, js = render(rows, {}, {}, seed(rows, 'a'*40, NOW, PERIOD), draft=True)
    start = md.index('## Release amendments\n')
    end = md.index('## Normative changes for review\n', start)
    return md[start:end], js, prior, latest


def test_release_amendments_latest_revision_golden():
    block, js, prior, latest = release_amendments_with_superseded_revision()
    expected = GOLDEN.with_name('release-amendments-latest.md').read_text()
    assert block == expected
    ledger = {entry['key']: entry['citation'] for entry in json.loads(js)['source_ledger']}
    from ucp_pulse.render import key
    assert f"[{ledger[key(prior)]}]" not in block
    assert f"[{ledger[key(latest)]}]" in block
