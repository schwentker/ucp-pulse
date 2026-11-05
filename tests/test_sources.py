"""Hand-labeled fixture gates, with socket access blocked by conftest."""
import json
from pathlib import Path
import pytest
from ucp_pulse.collectors import GitHub, SPEC, normalize_pr, release_lines
from ucp_pulse.diff import alerts
from ucp_pulse.http import Client, RateLimited, SourceError
from ucp_pulse.store import Store
from test_core import T

FIXTURES = Path(__file__).parent / 'fixtures'
def cases(name):
    return [row for p in sorted((FIXTURES/name).glob('*.json')) for row in json.loads(p.read_text())]


@pytest.mark.parametrize('row',cases('prs'),ids=lambda r:r.get('name',r.get('source_url')))
def test_pr_gate(row,tmp_path):
    out=normalize_pr(row['repo'],row['input'],row['merge_subject'],T)
    expected=row['expected']
    assert bool(out)==expected['accepted']
    if out:
        assert out['facts']['merged']==expected['merged']
        assert out['facts']['author_declared_breaking']==expected['breaking']
        store=Store(tmp_path)
        batch={'source':out['source'],'complete':True,'items':[out]}
        assert store.apply([batch],T,'a')==1
        assert store.apply([batch],T,'b')==0
        assert out['evidence']['url'] and out['evidence']['ref'] and out['authority']
        if row.get('source_url','').endswith('/431'):
            assert out['material']['base']=='release/2026-04-08'


@pytest.mark.parametrize('row',cases('releases'),ids=lambda r:r['name'])
def test_release_gate(row,tmp_path):
    # Every version, SHA and date in this scenario is synthetic.
    version='2026-01-11'
    tag={'name':'v'+version,'object':'a'*40,'commit':'a'*40,'time':None}
    release={'id':1,'tag_name':'v'+version,'published_at':'2026-01-11T01:00:00Z','body':'synthetic notes','assets':[]}
    branch={'name':'release/'+version,'commit':{'sha':'a'*40}}
    previous=release_lines([tag],[release],[branch],{},T)[0]
    tags=[dict(tag)]; releases=[dict(release)]; branches=[branch]; old={version:previous}
    n=row['name']
    if n in ('lightweight','annotated','after tag','alias collapse','draft','prerelease','branch only','no publication date'):old={}
    if n=='annotated':tags[0].update(object='c'*40,time='2026-01-11T00:00:00Z')
    if n=='notes edit':releases[0]['body']='synthetic revised'
    if n in ('asset digest','asset added'):releases[0]['assets']=[{'id':2,'digest':'sha256:synthetic','size':1}]
    if n in ('branch backport','branch no publication'):branches=[{'name':branch['name'],'commit':{'sha':'b'*40}}]
    if n=='retarget':tags[0]['commit']='b'*40
    if n=='annotation changes':tags[0]['object']='c'*40
    if n in ('delete tag','branch only'):tags=[]
    if n=='delete branch':branches=[]
    if n in ('delete release','branch only','no publication date'):releases=[]
    if n=='draft':releases[0]['draft']=True
    if n=='prerelease':releases[0]['prerelease']=True
    if n=='two releases':tags.append({'name':'v2026-01-18','object':'b'*40,'commit':'b'*40,'time':None})
    if n=='notes CRLF':releases[0]['body']='synthetic notes\r\n'
    out=release_lines(tags,releases,branches,old,T)
    key,expected=next(iter(row['expected'].items()))
    if key=='count':actual=len(out)
    elif key=='same':actual=out[0]['material']==previous['material']
    elif key.startswith('deleted_'):actual=out[0]['facts']['deleted'][key.split('_')[1]]
    elif key=='time_kind':actual=out[0]['event_time_kind']
    else:actual=out[0]['facts'].get(key,out[0]['material'].get(key))
    assert actual==expected
    # Another unchanged complete poll must not introduce a new revision.
    again=release_lines(tags,releases,branches,{x['subject']['version']:x for x in out},T)
    assert [x['material'] for x in again]==[x['material'] for x in out]


@pytest.mark.parametrize('row',cases('schema'),ids=lambda r:r['name'])
def test_schema_gate(row):
    before={'a.json':row['before'],'b.json':{'$ref':'a.json'},'c.json':{'$ref':'b.json'}}
    after={**before,'a.json':row['after']}
    out=alerts(before,after)
    assert len(out)==1 and out[0]['classification']==row['expected']
    assert out[0]['pointers'] and out[0]['dependents']==['b.json','c.json']
    if row['name']=='ucp_request':assert out[0]['annotations']==['ucp_request']
    if row['name']=='ucp_response':assert out[0]['annotations']==['ucp_response']
    if row['name']=='escaped pointer':assert out[0]['pointers']==['/a~1b~0c']


def test_ref_cycle_and_external_ref():
    before={'a.json':{'$ref':'b.json'},'b.json':{'$ref':'a.json'},'c.json':{'$ref':'https://example.invalid/a.json'}}
    assert alerts(before,{**before,'a.json':False})[0]['dependents']==['b.json']


def transport(responses,requests):
    def send(url,headers,data):
        requests.append((url,dict(headers),data))
        return responses.pop(0)
    return send


def test_http_etag_pagination(tmp_path):
    requests=[]
    responses=[(200,{'ETag':'synthetic','X-RateLimit-Remaining':'999','Link':'<https://api.github.com/example?page=2>; rel="next"'},b'[1]'),
               (200,{'X-RateLimit-Remaining':'998'},b'[2]'),
               (304,{'X-RateLimit-Remaining':'997'},b''),
               (200,{'X-RateLimit-Remaining':'996'},b'[2]')]
    client=Client(cache=tmp_path/'cache.json',token='synthetic-secret',transport=transport(responses,requests))
    assert client.pages('https://api.github.com/example')==[1,2]
    assert client.pages('https://api.github.com/example')==[1,2]
    assert requests[2][1]['If-None-Match']=='synthetic'
    assert 'synthetic-secret' not in (tmp_path/'cache.json').read_text()


@pytest.mark.parametrize('url',['http://api.github.com/x','https://evil.invalid/x','https://shopify.dev/docs/agents','https://catalog.shopify.com/api/ucp/mcp','https://user:pass@api.github.com/x','https://api.github.com:444/x'])
def test_http_url_guard(url):
    with pytest.raises(SourceError):Client(transport=lambda *a:pytest.fail('network')).get(url)


@pytest.mark.parametrize('status,headers,body,error',[
 (200,{'x-ratelimit-remaining':'99'},b'{}',RateLimited),
 (200,{},b'{}',SourceError),
 (429,{'x-ratelimit-remaining':'100','retry-after':'30'},b'{}',SourceError),
 (200,{'x-ratelimit-remaining':'100'},b'x'*20,SourceError),
 (302,{'x-ratelimit-remaining':'100','location':'https://registry.npmjs.org/a'},b'',SourceError),
 (304,{'x-ratelimit-remaining':'100'},b'',SourceError),
])
def test_http_fail_closed(status,headers,body,error):
    with pytest.raises(error):Client(byte_cap=10,transport=lambda *a:(status,headers,body)).get('https://api.github.com/example')


def test_failed_second_page_keeps_cursor(tmp_path):
    store=Store(tmp_path)
    store.apply([{'source':'S2','complete':True,'items':[],'cursor':'synthetic-old'}],T,'a')
    requests=[]
    responses=[(200,{'x-ratelimit-remaining':'101','link':'<https://api.github.com/example?page=2>; rel="next"'},b'[]'),
               (200,{'x-ratelimit-remaining':'99'},b'[]')]
    client=Client(transport=transport(responses,requests))
    with pytest.raises(RateLimited):client.pages('https://api.github.com/example')
    store.apply([{'source':'S2','complete':False,'error':'rate limit'}],T,'b')
    assert store.state('cursors')['S2']['cursor']=='synthetic-old'
    with pytest.raises(RateLimited):client.get('https://api.github.com/example')


def test_tag_peeling_and_bounds():
    class Fake:
        def json(self,url):
            if 'matching-refs' in url:return [{'ref':'refs/tags/v2026-01-11','object':{'sha':'a'*40,'type':'tag'}}]
            return {'object':{'sha':'b'*40,'type':'commit'},'tagger':{'date':T}}
    assert GitHub(Fake()).tags(SPEC)[0]=={'name':'v2026-01-11','object':'a'*40,'commit':'b'*40,'time':T}


def test_fixture_minimums():
    for family in ('releases','prs','schema'):
        assert len(cases(family))>=20
    sources={x.get('source_url','') for x in cases('prs')}
    assert all(any(s.endswith('/'+str(n)) for s in sources) for n in (431,659,87,101))


def test_tracked_pr_withdrawal():
    row=cases('prs')[0]
    pr={**row['input'],'state':'closed','merged_at':None,'title':'feat: withdrawn synthetic change'}
    assert normalize_pr(SPEC,pr,'',T) is None
    result=normalize_pr(SPEC,pr,'',T,tracked=True)
    assert result['facts']=={'opened':False,'merged':False,'author_declared_breaking':False}


def test_actual_backport_fixture_release_line():
    real=next(row for row in cases('prs') if row.get('source_url','').endswith('/431'))
    version=real['input']['base']['ref'].split('/',1)[1]
    before=release_lines([],[],[{'name':real['input']['base']['ref'],'commit':{'sha':'a'*40}}],{},T)[0]
    after=release_lines([],[],[{'name':real['input']['base']['ref'],'commit':{'sha':real['input']['merge_commit_sha']}}],{version:before},T)[0]
    assert after['event_id']==before['event_id']
    assert after['facts']['amended'] and not after['facts']['artifact_republished']
