import copy
import json
import subprocess
from pathlib import Path
import pytest
import yaml
from ucp_pulse.model import revise
from ucp_pulse.secondary import governance,batch
from ucp_pulse.render import render,seed,key,validate,BLOCKS
from ucp_pulse.report import evidence_at,render_files,load_yaml
from ucp_pulse.store import Store

NOW='2020-02-03T00:00:00Z'
PERIOD={'id':'p-2020-02-02','type':'weekly','start':'2020-02-02T00:00:00Z','end':'2020-02-09T00:00:00Z','revision':'r1'}
SOURCES={'S5':{'enabled':True},'S9':{'enabled':False,'reason':'fixture denial'}}

def data():
    candidates=governance({'GOVERNANCE.md':'synthetic rules'},'a'*40,{},NOW)
    records=[revise(c,None,NOW,'test') for c in candidates]
    curation=seed(records,'a'*40,NOW,PERIOD)
    return records,curation

def keep(curation):
    for item in curation['items'].values(): item['decision']='KEEP'
    return curation

def test_byte_stable_pure_render_and_fixed_blocks():
    records,curation=data(); keep(curation)
    a=render(records,{},SOURCES,curation); b=render(copy.deepcopy(records),{},SOURCES,copy.deepcopy(curation))
    assert a==b
    md,js=a
    positions=[md.index('## '+n) for n in BLOCKS+['Coverage','Source ledger']]
    assert positions==sorted(positions)
    assert 'fixture denial' in md and 'observed, not published' in md
    assert 'unknown' in md and '/Users/' not in js and '/tmp/' not in js

def test_pending_structural_only_and_cut_excluded():
    records,curation=data()
    render(records,{},SOURCES,curation,draft=True)
    with pytest.raises(ValueError,match='PENDING'): render(records,{},SOURCES,curation)
    k=next(iter(curation['items'])); curation['items'][k]['decision']='CUT'
    md,js=render(records,{},SOURCES,curation)
    assert k not in js and not json.loads(js)['source_ledger']

@pytest.mark.parametrize('bad', ['unknown_field','missing_field','bad_sha','unknown_period','monday','bad_bounds','wrong_period_id','bad_revision','missing_item','extra_item','unknown_decision','bad_analyst','pending_analyst','pending_note','cut_migration','bad_affected','headline_without_citation','signal_without_citation','watch_without_citation','unknown_citation','cut_citation','pending_citation','event_not_revision','unknown_item_field','wrong_text_type','future_health'])
def test_seeded_invalid_curation(bad):
    records,c=data(); keep(c); k=next(iter(c['items'])); i=c['items'][k]; health={}
    if bad=='unknown_field': c['surprise']='x'
    if bad=='missing_field': del c['signal']
    if bad=='bad_sha': c['evidence_sha']='main'
    if bad=='unknown_period': c['period']['type']='daily'
    if bad=='monday': c['period']['start']='2020-02-03T00:00:00Z'
    if bad=='bad_bounds': c['period']['end']=c['period']['start']
    if bad=='wrong_period_id': c['period']['id']='p-2020-02-01'
    if bad=='bad_revision': c['period']['revision']='../../bad'
    if bad=='missing_item': c['items'].clear()
    if bad=='extra_item': c['items']['unknown']=i
    if bad=='unknown_decision': i['decision']='APPROVE'
    if bad=='bad_analyst': i['analyst']='compatible'
    if bad=='pending_analyst': i.update(decision='PENDING',analyst='breaking')
    if bad=='pending_note': i.update(decision='PENDING',note='claim')
    if bad=='cut_migration': i.update(decision='CUT',migration='claim')
    if bad=='bad_affected': i['affected']='operation'
    if bad in {'headline_without_citation','signal_without_citation'}: c[bad.split('_')[0]]['text']='claim'
    if bad=='watch_without_citation': c['watch_next']=[{'text':'claim','evidence':[]}]
    if bad in {'unknown_citation','cut_citation','pending_citation','event_not_revision'}:
        citation='unknown' if bad=='unknown_citation' else records[0]['event_id'] if bad=='event_not_revision' else k
        c['headline']={'text':'claim','evidence':[citation]}
        if bad=='cut_citation': i['decision']='CUT'
        if bad=='pending_citation': i['decision']='PENDING'
    if bad=='unknown_item_field': i['other']='claim'
    if bad=='wrong_text_type': i['note']=123
    if bad=='future_health': health={'S5':{'last_success':'2020-02-04T00:00:00Z'}}
    with pytest.raises(ValueError): render(records,health,SOURCES,c,draft=True)

def test_empty_period_and_48_hour_stale_boundary():
    c=seed([],'a'*40,NOW,PERIOD)
    _,js=render([],{'S5':{'last_success':'2020-02-01T00:00:00Z'}},SOURCES,c)
    assert not next(r for r in json.loads(js)['coverage'] if r['source']=='S5')['stale']
    _,js=render([],{'S5':{'last_success':'2020-01-31T23:59:59Z'}},SOURCES,c)
    assert next(r for r in json.loads(js)['coverage'] if r['source']=='S5')['stale']

def test_late_revision_and_every_window_revision_retained():
    candidates=governance({'GOVERNANCE.md':'synthetic'},'a'*40,{},NOW)
    first=revise(candidates[0],None,NOW,'a'); first['event_time']='2020-01-01T00:00:00Z'
    candidates[0]['material']['body']='changed'
    second=revise(candidates[0],first,'2020-02-04T00:00:00Z','b')
    rows=[first,second]; c=keep(seed(rows,'a'*40,'2020-02-05T00:00:00Z',PERIOD))
    md,js=render(rows,{},SOURCES,c)
    assert '## Late arrivals' in md and len(json.loads(js)['source_ledger'])==2

def run(root,*args):
    return subprocess.run(['git','-C',str(root),*args],check=True,capture_output=True,text=True).stdout.strip()

def test_pinned_evidence_and_two_path_layouts(tmp_path):
    root=tmp_path/'machine-a'/'data'; root.mkdir(parents=True)
    run(root,'init','-b','main'); run(root,'config','user.name','Synthetic test'); run(root,'config','user.email','test@example.invalid')
    (root/'config').mkdir(); (root/'config/sources.yaml').write_text(yaml.safe_dump(SOURCES))
    store=Store(root); candidates=governance({'GOVERNANCE.md':'synthetic'},'a'*40,{},NOW)
    store.apply([batch('S5',candidates)],NOW,'test')
    run(root,'add','data','state','config'); run(root,'commit','-m','synthetic evidence')
    sha=run(root,'rev-parse','HEAD'); rows,_,_=evidence_at(root,sha)
    c=keep(seed(rows,sha,NOW,PERIOD)); cp=root/'curation.yaml'; cp.write_text(yaml.safe_dump(c))
    output=root/'drafts'/'test'; a=render_files(root,cp,output)
    render_files(root,cp,output,check=True)
    clone=tmp_path/'different'/'layout'; clone.parent.mkdir()
    subprocess.run(['git','clone',str(root),str(clone)],check=True,capture_output=True)
    (clone/'curation.yaml').write_text(cp.read_text())
    b=render_files(clone,clone/'curation.yaml',clone/'drafts'/'test')
    assert a==b
    output.with_suffix('.md').write_text(a[0]+'tamper')
    with pytest.raises(ValueError,match='fresh render'): render_files(root,cp,output,check=True)
    (root/'state/index.json').write_text('{}')
    with pytest.raises(ValueError,match='derived'): render_files(root,cp,output,check=True)

def test_yaml_duplicate_rejected(tmp_path):
    p=tmp_path/'duplicate.yaml'; p.write_text('items: {}\nitems: {}\n')
    with pytest.raises(ValueError,match='duplicate'): load_yaml(p)
