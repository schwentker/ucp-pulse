"""Synthetic cursor and request fixtures, with networking blocked."""
import json
from urllib.parse import parse_qs, urlsplit
import pytest
from ucp_pulse.cli import main
from ucp_pulse.collectors import GitHub, SPEC
from ucp_pulse.http import Client
from ucp_pulse.runner import collect
from ucp_pulse.store import Store

NOW='2020-02-10T00:00:00Z'


@pytest.mark.parametrize('cursor,start,expected',[
    ({'last_complete':'2020-02-08T00:00:00Z','pagination_complete':True}, '2020-02-09T00:00:00Z','2020-02-01T00:00:00.000000Z'),
    ({},'2020-01-01T00:00:00Z','2020-01-01T00:00:00.000000Z'),
    ({'last_complete':'2020-02-08T00:00:00Z','pagination_complete':False},'2020-01-01T00:00:00Z','2020-01-01T00:00:00.000000Z'),
])
def test_commit_requests_use_cursor_overlap_or_initial_start(cursor,start,expected):
    requests=[]
    def send(url,headers,data):
        requests.append(url)
        value=[{'name':'main','commit':{'sha':'a'*40}}] if '/branches?' in url else []
        return 200,{'x-ratelimit-remaining':'999'},json.dumps(value).encode()
    batches=collect(Client(transport=send),{}, {'S3':cursor}, {'S3':{'enabled':True}},NOW,start)
    assert batches[0]['complete']
    queries=[parse_qs(urlsplit(url).query) for url in requests if '/commits?' in url]
    assert len(queries)==3 and all(q['since']==[expected] for q in queries)


def synthetic_pr(number,updated):
    return {'number':number,'title':'feat!: synthetic','state':'open','created_at':'2019-01-01T00:00:00Z',
            'updated_at':updated,'base':{'ref':'main'},'labels':[]}


def test_pr_pages_stop_at_overlap_and_include_boundary_ties():
    requests=[]
    def send(url,headers,data):
        requests.append(url)
        assert len(requests)==1, 'must not fetch a page entirely before the cursor overlap'
        values=[synthetic_pr(2,'2020-02-01T00:00:00Z'),synthetic_pr(1,'2020-02-01T00:00:00Z'),synthetic_pr(3,'2020-01-31T23:59:59Z')]
        return 200,{'x-ratelimit-remaining':'999','link':'<https://api.github.com/synthetic?page=2>; rel="next"'},json.dumps(values).encode()
    batches=collect(Client(transport=send),{}, {'S2':{'last_complete':'2020-02-08T00:00:00Z','pagination_complete':True}},
                    {'S2':{'enabled':True}},NOW,'2020-02-09T00:00:00Z')
    assert batches[0]['complete'] and {r['subject']['number'] for r in batches[0]['items']}=={1,2}
    assert 'sort=updated&direction=desc' in requests[0]


def test_recent_page_failure_preserves_last_complete_cursor(tmp_path):
    store=Store(tmp_path); store.apply([{'source':'S2','complete':True,'items':[]}],'2020-02-08T00:00:00Z','old')
    before=store.state('cursors')
    calls=[]
    def send(url,headers,data):
        calls.append(url)
        if len(calls)==2: return 200,{'x-ratelimit-remaining':'99'},b'[]'
        return 200,{'x-ratelimit-remaining':'999','link':'<https://api.github.com/synthetic?page=2>; rel="next"'},json.dumps([synthetic_pr(1,NOW)]).encode()
    batches=collect(Client(transport=send),{},before,{'S2':{'enabled':True}},NOW,'2020-01-01T00:00:00Z')
    assert not batches[0]['complete'] and len(calls)==2
    store.apply(batches,NOW,'failed')
    assert store.state('cursors')==before


def test_cli_uses_config_initial_bound_and_explicit_override(tmp_path,monkeypatch):
    config=tmp_path/'config'; config.mkdir()
    (config/'sources.yaml').write_text('S2: {enabled: true}\n')
    (config/'collection.yaml').write_text('history_start: "2020-01-01T00:00:00Z"\n')
    seen=[]
    def fake(client,previous,cursors,sources,observed,start):
        seen.append(start); return []
    monkeypatch.setattr('ucp_pulse.runner.collect',fake)
    args=['smoke-collect','--data',str(tmp_path),'--cache',str(tmp_path/'cache.json'),'--as-of',NOW]
    assert main(args)==0
    assert main(args+['--start','2020-01-15T00:00:00Z'])==0
    assert seen==['2020-01-01T00:00:00.000000Z','2020-01-15T00:00:00.000000Z']
