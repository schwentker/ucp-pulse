import copy
import json
from pathlib import Path
from xml.sax.saxutils import escape
import pytest
from ucp_pulse.collectors import ORG
from ucp_pulse.http import SourceError
from ucp_pulse.model import revise
from ucp_pulse.secondary import announcements, governance, sdk_tags, registry, eligible, changelog

NOW = '2020-02-01T00:00:00Z'
ROOT = Path(__file__).parent / 'fixtures'

def cases(name):
    value = json.loads((ROOT / name / 'synthetic.json').read_text())
    assert value['origin'] == 'synthetic' and len(value['cases']) >= 20
    return value['cases']

def stable(items):
    for i in items:
        row = revise(i, None, NOW, 'test')
        assert revise(i, row, NOW, 'again') is None
        assert row['revision_id'] and row['evidence']['ref'] and row['evidence']['url'].startswith('https://')
        assert row['event_time'] and row['event_time_kind'] and row['authority']

@pytest.mark.parametrize('case', cases('announcements'), ids=lambda c:c['case'])
def test_announcements(case):
    c=case['case']; text='## 2020-01-01 Test\nBody'; previous={}
    initial=announcements(text,'a'*40,{},NOW)[0]
    if c in {'two_entries','reordered'}: text += '\n## 2020-01-02 Second\nBody'
    if c=='reordered': text='## 2020-01-02 Second\nBody\n## 2020-01-01 Test\nBody'
    if c=='edited': text += ' edited'; previous={initial['event_id']:initial}
    if c in {'deleted','deletion_rerun'}:
        text=''; previous={initial['event_id']:initial}
        if c=='deletion_rerun': previous={i['event_id']:i for i in announcements(text,'b'*40,previous,NOW)}
    if c in {'duplicate_discussion_link','nonmaintainer_link'}: text += '\nhttps://github.com/Universal-Commerce-Protocol/ucp/discussions/999999\n' * 2
    if c=='no_date_error': text='# Undated'
    if c=='invalid_date_error': text='# 2020-99-99 Test'
    if c=='duplicate_identity_error': text+='\n'+text
    if c=='empty': text=''
    if c=='subheading': text+='\n### Details\nMore'
    if c=='crlf': text=text.replace('\n','\r\n')
    if c=='unicode': text+=' café'
    if c=='punctuation_slug': text='# 2020-01-01 Test: A!\nBody'
    if c=='date_only': text='# 2020-01-01\nBody'
    if c=='deep_heading': text='###### 2020-01-01 Test\nBody'
    if c=='body_date': text+='\n2020-01-03 in body'
    if c=='moving_entry': text='Intro\n\n'+text
    if c=='restore': previous={i['event_id']:i for i in announcements('','b'*40,{initial['event_id']:initial},NOW)}
    if c.endswith('_error'):
        with pytest.raises((SourceError,ValueError)): announcements(text,'b'*40,previous,NOW)
        return
    items=announcements(text,'b'*40,previous,NOW)
    assert len(items)==case['expected']; stable(items)
    if c in {'deleted','deletion_rerun'}: assert items[0]['facts']['deleted']
    if c=='duplicate_discussion_link': assert len(items[0]['material']['discussion_urls'])==1
    if c=='edited': assert items[0]['material']!=initial['material']

@pytest.mark.parametrize('case', cases('governance'), ids=lambda c:c['case'])
def test_governance(case):
    path=case['path']; before={} if case['before'] is None else {path:case['before']}
    previous={i['event_id']:i for i in governance(before,'a'*40,{},NOW)}
    after={} if case['after'] is None else {path:case['after']}
    items=governance(after,'b'*40,previous,NOW); stable(items)
    assert len(items)==bool(before or after)
    if items:
        assert items[0]['facts']['deleted']==(case['after'] is None)
        assert items[0]['event_time_kind']=='observed'
        rerun=governance(after,'b'*40,{i['event_id']:i for i in items},NOW)
        assert [i['material'] for i in rerun]==[i['material'] for i in items]

@pytest.mark.parametrize('case', cases('sdk_tags'), ids=lambda c:c['case'])
def test_sdk_tags(case):
    c=case['case']; name=case['tag']; repo=ORG+'/python-sdk'
    tags=[{'name':name,'object':'a'*40,'commit':'a'*40,'time':None}]
    releases=[{'tag_name':name,'body':'notes','published_at':NOW,'assets':[{'id':999999,'digest':'sha256:a'}]}]
    previous={i['event_id']:i for i in sdk_tags(repo,tags,releases,{},NOW)}
    if c=='annotated': tags[0]['object']='b'*40
    if c=='retarget': tags[0]['commit']='b'*40
    if c=='delete_tag': tags=[]
    if c=='delete_release': releases=[]
    if c=='notes': releases[0]['body']='edited'
    if c=='asset_digest': releases[0]['assets'][0]['digest']='sha256:b'
    if c=='draft': releases[0]['draft']=True
    if c=='prerelease': releases[0]['prerelease']=True
    if c=='release_after_tag': previous={i['event_id']:i for i in sdk_tags(repo,tags,[],{},NOW)}
    if c=='two_versions': tags.append({'name':'v0.3.0','object':'c'*40,'commit':'c'*40,'time':None})
    items=sdk_tags(repo,tags,releases,previous,NOW); stable(items)
    row=next(i for i in items if i['subject']['tag']==name)
    assert row['material']['scheme']==case['scheme']
    assert row['subject']['tag']==name
    if c in {'draft','prerelease','delete_release'}: assert not row['facts']['release_published']
    if c=='delete_tag': assert row['facts']['deleted']['tag']
    if c=='two_versions': assert len(items)==2
    assert [i['material'] for i in sdk_tags(repo,tags,releases,{i['event_id']:i for i in items},NOW)]==[i['material'] for i in items]

@pytest.mark.parametrize('reg', ['pypi','npm'])
@pytest.mark.parametrize('index', range(22))
def test_registries(reg,index):
    case=cases(reg)[index]; c=case['case']; repo=ORG+('/python-sdk' if reg=='pypi' else '/js-sdk')
    url='https://github.com/'+repo
    pypi={'info':{'name':'ucp-sdk','version':'0.0.1','project_urls':{'Source':url}},'releases':{'0.0.1':[{'filename':'synthetic.whl','digests':{'sha256':'a'*64},'upload_time_iso_8601':NOW}]}}
    npm={'name':'@ucp-js/sdk','repository':{'url':url},'dist-tags':{'latest':'0.0.1'},'time':{'0.0.1':NOW},'versions':{'0.0.1':{'name':'@ucp-js/sdk','version':'0.0.1','dist':{'integrity':'sha512:synthetic'}}}}
    value=pypi if reg=='pypi' else npm
    previous={i['event_id']:i for i in registry(reg,value,{},NOW)}
    versions=value['releases' if reg=='pypi' else 'versions']
    if c in {'wrong_repo','wrong_host','missing_binding','git_suffix','case_binding'}:
        link={'wrong_repo':'https://github.com/example/other','wrong_host':'https://github.com.evil.invalid/'+repo,'missing_binding':'','git_suffix':'git+'+url+'.git','case_binding':url.upper().replace('HTTPS','https')}[c]
        if reg=='pypi': value['info']['project_urls']={'Source':link}
        else: value['repository']={'url':link}
    if c=='wrong_name': (value['info'] if reg=='pypi' else value)['name']='wrong'
    if c in {'multiple_versions','tag_move','deleted_version','restore'}:
        versions['0.0.2']=copy.deepcopy(versions['0.0.1'])
        if reg=='npm': versions['0.0.2']['version']='0.0.2'
        if c!='multiple_versions':
            if reg=='pypi': value['info']['version']='0.0.2'
            else: value['dist-tags']['latest']='0.0.2'
        if c=='deleted_version': del versions['0.0.1']
        if c=='restore': previous[next(iter(previous))]['material']['deleted']=True
    if c=='empty_versions': versions.clear()
    if c=='missing_latest_version':
        if reg=='pypi': value['info']['version']='missing'
        else: value['dist-tags']['latest']='missing'
    if reg=='pypi':
        if c=='yank': versions['0.0.1'][0]['yanked']=True
        if c=='digest_change': versions['0.0.1'][0]['digests']['sha256']='b'*64
        if c=='file_change': versions['0.0.1'][0]['filename']='other.whl'
        if c=='empty_files': versions['0.0.1']=[]
        if c=='missing_time': versions['0.0.1'][0].pop('upload_time_iso_8601')
        if c=='mismatched_publication_date': versions['0.0.1'][0]['upload_time_iso_8601']='2020-01-02T00:00:00Z'
    else:
        if c=='digest_change': versions['0.0.1']['dist']['integrity']='sha512:changed'
        if c=='file_change': versions['0.0.1']['dist']['shasum']='b'*40
        if c in {'yank','deprecation'}: versions['0.0.1']['deprecated']='test deprecation'
        if c=='wrong_version_repo': versions['0.0.1']['repository']={'url':'https://github.com/example/other'}
        if c=='missing_time': value['time']={}
        if c=='mismatched_publication_date': value['time']['0.0.1']='2020-01-02T00:00:00Z'
    if case['reject']:
        with pytest.raises(SourceError): registry(reg,value,previous,NOW)
        return
    items=registry(reg,value,previous,NOW); stable(items)
    assert [i['material'] for i in registry(reg,value,{i['event_id']:i for i in items},NOW)]==[i['material'] for i in items]
    row=next(i for i in items if i['subject']['version']=='0.0.1')
    if c=='deleted_version': assert row['facts']['deleted'] and not row['facts']['package_published']
    if c=='yank': assert row['facts']['yanked']==(reg=='pypi')
    if c=='missing_time': assert row['event_time_kind']=='observed'
    if c=='tag_move': assert 'latest' not in row['material']['dist_tags']

@pytest.mark.parametrize('case',cases('changelog'),ids=lambda c:c['case'])
def test_feed_gate(case):
    assert eligible(case['title'],case['body'],case['url'])==case['accept']
    xml='<rss><channel><item>'+''.join('<'+k+'>'+escape(v)+'</'+k+'>' for k,v in [('title',case['title']),('description',case['body']),('link',case['url'])])+'</item></channel></rss>'
    rows=changelog(xml,NOW); assert bool(rows)==case['accept']; stable(rows)
    if rows: assert rows[0]['event_time_kind']=='observed'

def test_xml_refuses_entities_and_invalid_shapes():
    for xml in ['<!DOCTYPE rss><rss><channel/></rss>','<html/>','<rss><channel><item><title>Universal Commerce Protocol</title><link>https://shopify.dev/test</link><pubDate>nonsense</pubDate></item></channel></rss>']:
        with pytest.raises(SourceError): changelog(xml,NOW)

def test_rate_stop_does_not_block_other_hosts():
    from ucp_pulse.http import Client, RateLimited
    def transport(url, headers, data):
        return (200, {'x-ratelimit-remaining':'0'}, b'{}') if 'api.github.com' in url else (200, {}, b'{}')
    client=Client(transport=transport)
    with pytest.raises(RateLimited): client.json('https://api.github.com/rate_limit')
    assert client.json('https://pypi.org/pypi/ucp-sdk/json')=={}

def test_source_failure_isolated_and_overlap():
    from ucp_pulse.runner import collect
    from ucp_pulse.secondary import Secondary
    from unittest.mock import patch
    def bad(*args): raise SourceError('fixture denial')
    seen=[]
    def good(self,previous,observed,since):
        seen.append(since); return {'source':'S6','complete':True,'items':[],'snapshots':[]}
    with patch.object(Secondary,'s4',bad), patch.object(Secondary,'s6',good):
        rows=collect(object(),{}, {'S6':{'last_complete':NOW}}, {'S4':{'enabled':True},'S6':{'enabled':True}},NOW,'2020-01-01T00:00:00Z')
    assert not rows[0]['complete'] and rows[1]['complete']
    assert seen==['2020-01-25T00:00:00.000000Z']

def test_diff_fragments_bounded_and_missing_distinct_from_null():
    from ucp_pulse.diff import alerts
    rows=alerts({'a.json':{'value':None}}, {'a.json':{'other':'x'*3000}})
    parts={f['pointer']:f for f in rows[0]['fragments']}
    assert parts['/value']['before']['present'] and not parts['/value']['after']['present']
    assert parts['/other']['after']['truncated'] and len(parts['/other']['after']['json_fragment'])==1000

def test_pypi_fallback_requires_description_link_and_pinned_manifest_ref():
    value={'info':{'name':'ucp-sdk','version':'1.0.0','project_urls':None,
                   'description':'Source: https://github.com/Universal-Commerce-Protocol/python-sdk.git'},
           'releases':{'1.0.0':[{'filename':'synthetic.whl','digests':{'sha256':'a'*64},'upload_time_iso_8601':NOW}]}}
    ref='Universal-Commerce-Protocol/python-sdk@'+'a'*40+':pyproject.toml'
    with pytest.raises(SourceError): registry('pypi',value,{},NOW)
    row=registry('pypi',value,{},NOW,binding_ref=ref)[0]
    assert row['material']['binding_ref']==ref and row['facts']['package_published']
    value['info']['description']='Source: https://github.com/Universal-Commerce-Protocol/python-sdk.evil.invalid'
    with pytest.raises(SourceError): registry('pypi',value,{},NOW,binding_ref=ref)

def test_actual_announcement_heading_format_is_dated_and_stable():
    source='## September 25, 2026: Synthetic capability notice\nBody\n## January 11, 2026: Synthetic launch\nText'
    rows=announcements(source,'a'*40,{},NOW)
    assert [r['subject']['date'] for r in rows]==['2026-09-25','2026-01-11']
    assert [r['event_time_kind'] for r in rows]==['posted','posted']
    stable(rows)
