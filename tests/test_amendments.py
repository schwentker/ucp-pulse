"""Public #431 regression plus explicitly synthetic ref/history variations."""
import json
from pathlib import Path
import pytest
from ucp_pulse.amendments import amended_release
from ucp_pulse.collectors import SPEC, normalize_pr, release_lines
from ucp_pulse.model import revise
from ucp_pulse.render import key, render, seed
from ucp_pulse.store import Store

FIXTURES = Path(__file__).parent/'fixtures'
NOW = '2026-11-05T20:00:00Z'  # Synthetic observation time, not an upstream claim.


def inputs():
    f = json.loads((FIXTURES/'release_amendment.json').read_text())
    p = next(p for p in json.loads((FIXTURES/'prs/upstream.json').read_text()) if p['input']['number']==431)
    pr = normalize_pr(SPEC, p['input'], p['merge_subject'], NOW)
    return f, pr


def release(f, events=(), previous=None):
    return release_lines([f['tag']], [f['release']], [f['branch']], previous or {}, NOW, events=events)[0]


def test_first_backfill_431_with_equal_refs_and_citations(tmp_path):
    f, pr = inputs()
    assert pr['event_time']=='2026-05-20T05:43:08.000000Z'
    assert f['release']['published_at']=='2026-04-09T01:48:20Z'
    line = release(f, [pr])
    assert line['facts']['amended'] and not line['facts']['artifact_republished']
    assert line['material']['amended_by']==['ucp:pr:431']
    store = Store(tmp_path)
    # S1 precedes S2, as in the daily collector. It still writes one release revision.
    assert store.apply([{'source':'S1','complete':True,'items':[release(f)]},
                        {'source':'S2','complete':True,'items':[pr]}], NOW, 'first')==2
    records = store.records()
    board = store.state('inventory')[line['event_id']]
    assert board['material']==line['material']
    assert json.loads((tmp_path/board['evidence']['snapshot']).read_text())==board['material']
    period = {'id':'history-2026-01-11','type':'history','start':'2026-01-11T00:00:00Z','end':NOW,'revision':'r3'}
    md, js = render(records, {}, {}, seed(records, 'a'*40, NOW, period), draft=True)
    amendments = md.split('## Release amendments')[1].split('## Normative')[0]
    assert 'ucp:pr:431' in amendments and '[S2]' in amendments
    assert json.loads(js)['evidence'][0]['facts']['amended']
    with pytest.raises(ValueError, match='PENDING'):
        render(records, {}, {}, seed(records, 'a'*40, NOW, period))


def test_equal_refs_without_later_merge_not_amended():
    f, pr = inputs()
    for change in ({'event_time':f['release']['published_at']},
                   {'facts':{**pr['facts'],'merged':False}},
                   {'material':{**pr['material'],'base':'main'}}):
        line = release(f, [{**pr, **change}])
        assert not line['facts']['amended'] and line['material']['amended_by']==[]
    assert not release(f)['facts']['amended']


def test_divergent_head_on_first_observation():
    f, _ = inputs(); f['branch']['commit']['sha']='b'*40  # Synthetic divergence.
    line = release(f)
    assert line['facts']['amended'] and not line['facts']['artifact_republished']
    assert line['material']['amended_by']==[line['event_id']]


def test_retarget_between_observations_even_when_refs_match():
    f, _ = inputs(); before=release(f)
    # Synthetic simultaneous tag and branch movement; divergence alone cannot detect it.
    f['tag']['commit']=f['branch']['commit']['sha']='b'*40
    after=release(f, previous={'2026-04-08':before})
    assert after['facts']['amended'] and not after['facts']['artifact_republished']
    assert 'tag retargeted between observations' in after['material']['amendment_reasons']
    assert release(f, previous={'2026-04-08':after})['material']==after['material']


def test_normative_commit_reachability_and_early_commit_exclusion():
    f, pr=inputs(); line=release(f)
    # Synthetic commit candidate using the PR's known public merge ref.
    commit={**pr,'family':'normative_commit','event_id':'ucp:commit:'+pr['material']['merge_sha'],
            'material':{'branches':['main','release/2026-04-08']},'facts':{},'event_time_kind':'committed'}
    after=amended_release(line,[commit])
    assert after['material']['amended_by']==[commit['event_id']]
    commit['event_time']=f['release']['published_at']
    assert not amended_release(line,[commit])['facts']['amended']


def test_later_source_and_offline_reconciliation_preserve_cursors(tmp_path):
    f, pr=inputs(); store=Store(tmp_path)
    store.apply([{'source':'S1','complete':True,'items':[release(f)]}],NOW,'release')
    before=store.state('cursors')['S1']; health=store.state('health')['S1']
    assert store.apply([{'source':'S2','complete':True,'items':[pr]}],NOW,'backport')==2
    assert store.state('cursors')['S1']==before and store.state('health')['S1']==health
    assert store.apply([],NOW,'reconcile')==0
    assert store.rebuild(check=True)


def test_failed_batch_cannot_supply_amendment_evidence(tmp_path):
    f, pr=inputs(); store=Store(tmp_path)
    store.apply([{'source':'S1','complete':True,'items':[release(f)]},
                 {'source':'S2','complete':False,'items':[pr]}],NOW,'partial')
    assert not store.state('inventory')['ucp:release:2026-04-08']['facts']['amended']


def test_weekly_amendment_includes_older_supporting_evidence():
    f, pr=inputs()
    old=revise(pr,None,'2026-06-01T00:00:00Z','old')
    new=revise(release(f,[pr]),None,NOW,'new')
    period={'id':'p-2026-11-01','type':'weekly','start':'2026-11-01T00:00:00Z','end':'2026-11-08T00:00:00Z','revision':'r1'}
    c=seed([old,new],'a'*40,NOW,period)
    assert key(old) in c['items']
    md,_=render([old,new],{},{},c,draft=True)
    assert 'ucp:pr:431' in md.split('## Release amendments')[1].split('## Normative')[0]
