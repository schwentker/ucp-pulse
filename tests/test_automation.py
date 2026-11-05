import json
import os
from pathlib import Path
import subprocess
import sys
import pytest
import yaml
from ucp_pulse.secondary import governance,batch
from ucp_pulse.store import Store
from ucp_pulse.automation import lifecycle
from ucp_pulse.render import seed
from ucp_pulse.report import render_files
from ucp_pulse.util import canonical

NOW='2020-02-03T00:00:00Z'

def run(root,*args,ok=True):
    p=subprocess.run(['git','-C',str(root),*args],capture_output=True,text=True)
    if ok: assert p.returncode==0,p.stderr
    return p.stdout.strip()

def cli(*args,ok=True):
    p=subprocess.run([sys.executable,'-m','ucp_pulse',*map(str,args)],capture_output=True,text=True)
    if ok: assert p.returncode==0,p.stderr
    else: assert p.returncode!=0
    return p

def author(root):
    run(root,'config','user.name','Synthetic test'); run(root,'config','user.email','test@example.invalid')

def envelope(path,name,observed=NOW):
    items=governance({name+'.md':'synthetic '+name},'a'*40,{},observed)
    result={'batches':[batch('S5',items)],'observed_at':observed,'run_id':name,'tracking_start':'2020-01-26T00:00:00Z'}
    path.write_text(canonical(result)); return result

def repositories(tmp_path):
    bare_private=tmp_path/'private.git'; bare_public=tmp_path/'public.git'
    for bare in (bare_private,bare_public):
        subprocess.run(['git','init','--bare','--initial-branch=main',str(bare)],check=True,capture_output=True)
    private=tmp_path/'private'; public=tmp_path/'public'
    for root,remote in ((private,bare_private),(public,bare_public)):
        subprocess.run(['git','clone',str(remote),str(root)],check=True,capture_output=True); author(root)
        (root/'.gitignore').write_text('.ucp-lock\n.ucp-txn/\n.cache/\n')
        (root/'README.md').write_text('Synthetic offline test repository.\n')
        run(root,'add','.'); run(root,'commit','-m','synthetic scaffold'); run(root,'push','origin','main')
    (private/'config').mkdir(); (private/'config/sources.yaml').write_text('S5: {enabled: true}\n')
    path=tmp_path/'initial.json'; e=envelope(path,'initial'); Store(private).apply(e['batches'],NOW,'initial',tracking_start=e['tracking_start'])
    run(private,'add','.'); run(private,'commit','-m','synthetic evidence'); run(private,'push','origin','main')
    return private,public,bare_private,bare_public

def test_cli_two_bare_remotes_rejected_push_duplicate_and_crash(tmp_path):
    private,public,bare_private,bare_public=repositories(tmp_path)
    stale=tmp_path/'stale'; subprocess.run(['git','clone',str(bare_private),str(stale)],check=True,capture_output=True); author(stale)
    one=tmp_path/'one.json'; envelope(one,'one','2020-02-04T00:00:00Z')
    cli('apply-cached','--data',private,'--cache',one,'--push')
    two=tmp_path/'two.json'; envelope(two,'two','2020-02-05T00:00:00Z')
    response=cli('apply-cached','--data',stale,'--cache',two,'--push')
    assert json.loads(response.stdout)['attempts']==2
    assert len(Store(stale).records())==3
    head=run(stale,'rev-parse','HEAD')
    cli('apply-cached','--data',stale,'--cache',two,'--push')
    assert run(stale,'rev-parse','HEAD')==head
    three=tmp_path/'three.json'; envelope(three,'three','2020-02-06T00:00:00Z')
    remote_before=run(bare_private,'rev-parse','main')
    cli('apply-cached','--data',stale,'--cache',three,'--push','--crash-before-push',ok=False)
    assert run(bare_private,'rev-parse','main')==remote_before
    cli('apply-cached','--data',stale,'--cache',three,'--push')
    assert len(Store(stale).records())==4
    cli('rebuild','--data',stale,'--check')
    # Drive the publication CLI against the second local bare remote as well.
    sha=run(stale,'rev-parse','HEAD'); period={'id':'p-2020-02-02','type':'weekly','start':'2020-02-02T00:00:00Z','end':'2020-02-09T00:00:00Z','revision':'r1'}
    c=seed(Store(stale).records(),sha,'2020-02-06T00:00:00Z',period)
    for i in c['items'].values(): i['decision']='KEEP'
    (stale/'curation').mkdir(); cp=stale/'curation'/'p-2020-02-02-r1.yaml'; cp.write_text(yaml.safe_dump(c))
    output=stale/'drafts'/'p-2020-02-02-r1'/'brief'; render_files(stale,cp,output)
    run(stale,'add','curation','drafts'); run(stale,'commit','-m','synthetic human approval')
    approval=tmp_path/'approval.json'; approval.write_text(json.dumps({'commit':run(stale,'rev-parse','HEAD'),'merged':True,'merged_by':'synthetic-human'}))
    cli('export-local','--data',stale,'--curation',cp,'--output',output,'--public',public,'--approval',approval)
    run(public,'push','origin','HEAD:main')
    cli('check-export','--public',public)
    assert run(bare_public,'rev-parse','main')==run(public,'rev-parse','HEAD')
    # Out-of-order older approval leaves latest on the newer period.
    run(public,'switch','main'); run(public,'reset','--hard','origin/main')
    c['period']={'id':'p-2020-01-26','type':'weekly','start':'2020-01-26T00:00:00Z','end':'2020-02-02T00:00:00Z','revision':'r1'}
    c=seed(Store(stale).records(),sha,'2020-02-06T00:00:00Z',c['period'])
    cp2=stale/'curation'/'p-2020-01-26-r1.yaml'; cp2.write_text(yaml.safe_dump(c)); out2=stale/'drafts'/'p-2020-01-26-r1'/'brief'
    render_files(stale,cp2,out2); run(stale,'add','curation','drafts'); run(stale,'commit','-m','synthetic older approval')
    approval.write_text(json.dumps({'commit':run(stale,'rev-parse','HEAD'),'merged':True,'merged_by':'synthetic-human'}))
    cli('export-local','--data',stale,'--curation',cp2,'--output',out2,'--public',public,'--approval',approval)
    assert json.loads((public/'briefs/latest.json').read_text())['period_id']=='p-2020-02-02'
    cli('check-export','--public',public)
    latest=json.loads((public/'briefs/latest.json').read_text()); latest['period_end']='2020-02-02T00:00:00Z'; (public/'briefs/latest.json').write_text(json.dumps(latest))
    cli('check-export','--public',public,ok=False)

@pytest.mark.parametrize('state,authors,action,status',[('OPEN',['github-actions[bot]'],'draft','open'),('OPEN',['synthetic-human'],'human-edited','open'),('CLOSED',['synthetic-human'],'skip','abandoned'),('MERGED',['synthetic-human'],'skip','published')])
def test_lifecycle(state,authors,action,status):
    k='p-2020-01-26:weekly:r1'; ledger={k:{'period_id':'p-2020-01-26','type':'weekly','revision':1,'status':'due'}}
    result,key,actual=lifecycle(ledger,'p-2020-01-26',pr={'number':999999,'state':state,'authors':authors})
    assert actual==action and result[key]['status']==status
    revised,new,actual=lifecycle(result,'p-2020-01-26',revise=True)
    assert actual=='draft' and revised[new]['revision']==2 and revised[k]['status']==status

def test_cli_draft_duplicate_human_edit_and_revise(tmp_path):
    private,_,_,_=repositories(tmp_path)
    result=cli('draft','--data',private,'--period','p-2020-01-26','--as-of',NOW)
    branch=json.loads(result.stdout)['branch']; head=run(private,'rev-parse','HEAD')
    run(private,'switch','main')
    cli('draft','--data',private,'--period','p-2020-01-26','--as-of',NOW)
    assert run(private,'rev-parse',branch)==head
    pr=tmp_path/'pr.json'; pr.write_text(json.dumps({'number':999999,'state':'OPEN','authors':['synthetic-human']}))
    result=cli('draft','--data',private,'--period','p-2020-01-26','--as-of',NOW,'--pr-state',pr)
    assert json.loads(result.stdout)['action']=='human-edited' and run(private,'rev-parse',branch)==head
    cli('draft','--data',private,'--period','p-2020-01-26','--as-of',NOW,'--pr-state',pr,'--revise')
    assert (private/'drafts/p-2020-01-26-r2/addendum.json').exists()

def test_export_refuses_pending_and_unmerged(tmp_path):
    private,public,_,_=repositories(tmp_path)
    result=json.loads(cli('draft','--data',private,'--period','p-2020-01-26','--as-of',NOW).stdout)
    approval=tmp_path/'approval.json'; approval.write_text(json.dumps({'commit':run(private,'rev-parse','HEAD'),'merged':False,'merged_by':'synthetic-human'}))
    cli('export-local','--data',private,'--curation',result['curation'],'--output',result['output'],'--public',public,'--approval',approval,ok=False)
