"""Approved export and merge-time monotonic latest validation."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
from ucp_pulse.automation import gh, export_local, command
from ucp_pulse.report import git, load_yaml
from ucp_pulse.util import utc


def check_public(root):
    directory=Path(root)/'briefs'
    documents=[json.loads(p.read_text()) for p in directory.glob('*.json') if p.name!='latest.json']
    if not documents: return
    for doc in documents:
        if doc.get('draft') or any(i['curation']['decision']!='KEEP' for i in doc['evidence']):
            raise ValueError('unapproved public evidence')
        keys={i['key'] for i in doc['evidence']}
        if keys!={i['key'] for i in doc['source_ledger']}: raise ValueError('public citation mismatch')
    latest=json.loads((directory/'latest.json').read_text())
    if utc(latest['period_end'])!=max(utc(d['period']['end']) for d in documents):
        raise ValueError('latest pointer would roll back or skip a newer approved period')
    target=json.loads((directory/latest['brief']).read_text())
    if target['period']['id']!=latest['period_id'] or target['period']['end']!=latest['period_end']:
        raise ValueError('latest pointer target mismatch')


def publish_approved(data,public,private_repo,public_repo,sha):
    """Only called by the private export workflow after a human merge."""
    if git(data,'rev-parse','HEAD').strip()!=sha: raise ValueError('checkout does not match export trigger')
    pulls=gh('api',f'repos/{private_repo}/commits/{sha}/pulls')
    approved=[p for p in pulls if p.get('merged_at') and p.get('merge_commit_sha')==sha and p.get('base',{}).get('ref')=='main']
    if not approved: raise ValueError('no merged private PR for this commit')
    details=[gh('api',f"repos/{private_repo}/pulls/{p['number']}") for p in approved]
    merged=[p for p in details if p.get('merged_by',{}).get('login') not in {None,'github-actions[bot]'}]
    if not merged: raise ValueError('no human merge approval')
    approval={'commit':sha,'merged':True,'merged_by':merged[0]['merged_by']['login']}
    changed=git(data,'diff-tree','--no-commit-id','--name-only','-r',sha+'^1',sha).splitlines()
    stems={Path(p).stem for p in changed if p.startswith('curation/') and p.endswith('.yaml')}
    stems.update(Path(p).parts[1] for p in changed if p.startswith('drafts/') and len(Path(p).parts)>2)
    token=os.environ.get('UCP_PULSE_EXPORT_TOKEN')
    if not token: raise ValueError('export token missing')
    for stem in sorted(stems):
        curation=Path(data)/'curation'/(stem+'.yaml')
        if not curation.exists(): continue
        period=load_yaml(curation)['period']
        branch='export/'+period['id']+('' if period['revision']=='r1' else '-'+period['revision'])
        existing=gh('pr','list','--repo',public_repo,'--head',branch,'--state','all','--json','number,state',token=token)
        if existing: continue
        command(public,'switch','main'); command(public,'fetch','origin','main'); command(public,'reset','--hard','origin/main')
        result=export_local(data,curation,Path(data)/'drafts'/stem/'brief',public,approval)
        check_public(public)
        # gh's repository-scoped token is used only for this job, including Git auth.
        env=os.environ.copy(); env['GH_TOKEN']=token
        auth=subprocess.run(['gh','auth','setup-git','--hostname','github.com'],capture_output=True,env=env)
        if auth.returncode: raise ValueError('export git authentication failed')
        pushed=subprocess.run(['git','-C',str(public),'push','origin','HEAD:refs/heads/'+result['branch']],capture_output=True,env=env)
        if pushed.returncode: raise ValueError('export push rejected; no force push attempted')
        existing=gh('pr','list','--repo',public_repo,'--head',result['branch'],'--state','all','--json','number,state',token=token)
        if existing: continue
        with tempfile.NamedTemporaryFile('w',suffix='.md') as body:
            body.write('Approved private brief. Verify the latest pointer remains monotonic before merge.\n'); body.flush()
            result=subprocess.run(['gh','pr','create','--repo',public_repo,'--head','export/'+load_yaml(curation)['period']['id']+('' if load_yaml(curation)['period']['revision']=='r1' else '-'+load_yaml(curation)['period']['revision']),'--base','main','--title','Publish UCP Pulse '+stem,'--body-file',body.name],capture_output=True,env=env)
            if result.returncode: raise ValueError('export PR creation failed')
