"""Synthetic provenance must survive collection and remain pinned in coverage."""
import json
import pytest
from ucp_pulse.render import render, seed
from ucp_pulse.store import Store
from test_render_tables import NOW, PERIOD, rendered


def test_both_documented_departures_with_exact_pins():
    md,js=rendered()
    coverage=md.split('## Coverage')[1].split('## Source ledger')[0]
    assert 'D020: PyPI binding via description link plus pinned manifest' in coverage
    assert 'python-sdk@'+'a'*40+':pyproject.toml' in coverage
    assert 'D021: Normative commits recovered from a pinned official Git clone; pinned head '+'b'*40 in coverage
    notes={r['source']:r['notes'] for r in json.loads(js)['coverage']}
    assert notes['S3'] and notes['S7'] and not notes['S2']


def test_empty_evidence_does_not_invent_recovery_or_binding():
    md,js=render([],{}, {},seed([],'a'*40,NOW,PERIOD),draft=True)
    assert 'D020' not in md and 'D021' not in md
    assert all(not r['notes'] for r in json.loads(js)['coverage'])


def test_git_recovery_pin_survives_later_rest_runs_and_failed_batches(tmp_path):
    store=Store(tmp_path)
    first={'source':'S3','complete':True,'items':[],'pinned_head':'b'*40}
    store.apply([first],NOW,'git')
    expected=[{'pinned_head':'b'*40,'observed_at':'2020-02-10T00:00:00.000000Z'}]
    assert store.state('health')['S3']['git_recoveries']==expected
    store.apply([{'source':'S3','complete':True,'items':[]}],NOW,'rest')
    store.apply([{'source':'S3','complete':False,'pinned_head':'c'*40}],NOW,'failed')
    assert store.state('health')['S3']['git_recoveries']==expected
    store.apply([first],NOW,'same-git')
    assert store.state('health')['S3']['git_recoveries']==expected


@pytest.mark.parametrize('head,time',[('main',NOW),('b'*40,'2020-02-11T00:00:00Z')])
def test_coverage_rejects_unpinned_or_future_recovery(head,time):
    health={'S3':{'git_recoveries':[{'pinned_head':head,'observed_at':time}]}}
    with pytest.raises(ValueError,match='provenance'):
        render([],health,{},seed([],'a'*40,NOW,PERIOD),draft=True)


def test_writer_rejects_unpinned_git_batch_transactionally(tmp_path):
    store=Store(tmp_path)
    with pytest.raises(ValueError,match='full commit'):
        store.apply([{'source':'S3','complete':True,'items':[],'pinned_head':'main'}],NOW,'bad')
    assert store.state('health')=={} and store.state('cursors')=={}
