"""Git transactions and report lifecycle. Remote writes are explicit opt-ins."""
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import yaml
from ucp_pulse.report import git, evidence_at, load_yaml, render_files
from ucp_pulse.render import seed
from ucp_pulse.store import Store
from ucp_pulse.util import canonical, digest, stamp, utc


def command(root,*args,check=True):
    result=subprocess.run(['git','-C',str(root),*args],capture_output=True,text=True)
    if check and result.returncode: raise ValueError('git '+args[0]+' failed')
    return result


def clean_repo(root):
    if git(root,'status','--porcelain').strip(): raise ValueError('worktree must be clean')


def commit(root,paths,message):
    command(root,'add','--',*paths)
    if command(root,'diff','--cached','--quiet',check=False).returncode:
        command(root,'commit','-m',message)
    return git(root,'rev-parse','HEAD').strip()


def replay(root,envelope,push=False,remote='origin',branch='main',crash_before_push=False):
    """Replay cached source candidates, never append prebuilt JSONL lines."""
    clean_repo(root)
    if not re.fullmatch(r'[A-Za-z0-9_./-]+',branch) or branch.startswith('-'): raise ValueError('invalid branch')
    original=git(root,'rev-parse','HEAD').strip()
    for attempt in range(3):
        store=Store(root)
        # Refuse to regress a source completed by a newer collector. A fresh fetch is needed.
        cursors=store.state('cursors')
        for batch in envelope['batches']:
            last=cursors.get(batch['source'],{}).get('last_complete')
            if last and utc(last)>utc(envelope['observed_at']):
                raise ValueError('newer source snapshot committed; recollect before retry')
        count=store.apply(envelope['batches'],envelope['observed_at'],envelope['run_id'],tracking_start=envelope.get('tracking_start'))
        sha=commit(root,['data','state'],'collect: '+envelope['run_id'])
        if crash_before_push: raise ValueError('simulated crash before push; remote unchanged')
        if not push: return {'added':count,'commit':sha,'attempts':attempt+1,'pushed':False}
        result=command(root,'push',remote,'HEAD:refs/heads/'+branch,check=False)
        if result.returncode==0: return {'added':count,'commit':sha,'attempts':attempt+1,'pushed':True}
        if attempt==2: raise ValueError('push rejected after 3 attempts; cached envelope retained')
        command(root,'fetch',remote,branch)
        command(root,'reset','--hard','FETCH_HEAD')
    raise AssertionError(original)


def lifecycle(ledger,period_id,kind='weekly',revise=False,pr=None):
    matches=[(k,v) for k,v in ledger.items() if v['period_id']==period_id and v['type']==kind]
    if not matches: raise ValueError('period is not due')
    k,row=max(matches,key=lambda p:p[1]['revision']); row=dict(row)
    if pr:
        if pr['state']=='MERGED': row['status']='published'
        elif pr['state']=='CLOSED': row['status']='abandoned'
        else: row['status']='open'
        row['pr_number']=pr['number']
        row['human_edited']=any(author!='github-actions[bot]' for author in pr['authors'])
    result={**ledger,k:row}
    if revise:
        new={**row,'revision':row['revision']+1,'status':'due','pr_number':None,'human_edited':False,'supersedes':k}
        newkey=f"{period_id}:{kind}:r{new['revision']}"; result[newkey]=new
        return result,newkey,'draft'
    if row['status'] in {'published','abandoned'}: return result,k,'skip'
    if row.get('human_edited'): return result,k,'human-edited'
    return result,k,'draft'


def draft_local(root,period_id,as_of,kind='weekly',revise=False,pr=None):
    """Make a reviewable local branch; never overwrites existing human curation."""
    clean_repo(root)
    store=Store(root)
    ledger,k,action=lifecycle(store.state('periods'),period_id,kind,revise,pr)
    row=ledger[k]
    if action!='draft': return {'action':action,'key':k,'ledger':ledger}
    branch=f"draft/{period_id}-r{row['revision']}"
    if command(root,'show-ref','--verify','--quiet','refs/heads/'+branch,check=False).returncode==0:
        # Existing branch content is preserved. --revise is the regeneration mechanism.
        return {'action':'existing','key':k,'branch':branch,'ledger':ledger}
    sha=git(root,'rev-parse','HEAD').strip()
    records,_,_=evidence_at(root,sha)
    period={'id':period_id,'type':kind,'start':row['start'],'end':row['end'],'revision':'r'+str(row['revision'])}
    curation=seed(records,sha,as_of,period)
    command(root,'switch','-c',branch)
    rel=f"{period_id}-r{row['revision']}"
    cp=Path(root)/'curation'/f'{rel}.yaml'; cp.parent.mkdir(parents=True,exist_ok=True)
    cp.write_text(yaml.safe_dump(curation,sort_keys=True,allow_unicode=False))
    output=Path(root)/'drafts'/rel/'brief'
    render_files(root,cp,output,draft=True)
    if revise:
        (output.parent/'addendum.json').write_text(canonical({'supersedes':row['supersedes'],'evidence_sha':sha,'revisions':sorted(curation['items'])})+'\n')
    commit(root,['curation','drafts'],'draft: '+rel)
    return {'action':'created','key':k,'branch':branch,'curation':str(cp),'output':str(output),'ledger':ledger}


def export_local(data,curation,output,public,approval,revision=None):
    """Prepare approved files on a local public branch; never push by default."""
    c=load_yaml(curation)
    private_head=git(data,'rev-parse','HEAD').strip()
    if approval.get('commit')!=private_head or not approval.get('merged') or approval.get('merged_by') in {None,'github-actions[bot]'}:
        raise ValueError('export requires a human-merged private commit')
    render_files(data,curation,output,check=True,draft=False)
    clean_repo(public)
    period=c['period']; rel=period['id']+('-'+period['revision'] if period['revision']!='r1' else '')
    branch='export/'+rel
    if command(public,'show-ref','--verify','--quiet','refs/heads/'+branch,check=False).returncode==0:
        command(public,'switch',branch)
    else: command(public,'switch','-c',branch)
    directory=Path(public)/'briefs'; directory.mkdir(parents=True,exist_ok=True)
    for ext in ('.md','.json'):
        (directory/(rel+ext)).write_bytes(Path(output).with_suffix(ext).read_bytes())
    latest=directory/'latest.json'
    prior=json.loads(latest.read_text()) if latest.exists() else None
    if not prior or utc(period['end'])>utc(prior['period_end']):
        latest.write_text(canonical({'period_id':period['id'],'period_end':period['end'],'revision':period['revision'],'brief':rel+'.json'})+'\n')
    sha=commit(public,['briefs'],'export: '+rel)
    return {'branch':branch,'commit':sha,'period':period['id']}


def gh(*args,token=None):
    env=os.environ.copy()
    if token is not None: env['GH_TOKEN']=token
    result=subprocess.run(['gh',*args],capture_output=True,text=True,env=env)
    if result.returncode: raise ValueError('GitHub operation failed: '+args[0])
    return json.loads(result.stdout) if result.stdout.strip() else None


def publish_due(root,repo,as_of,revise_period=None):
    """Deployed workflow only. PR recovery is keyed by deterministic branch name."""
    clean_repo(root)
    command(root,'switch','main'); command(root,'fetch','origin','main'); command(root,'reset','--hard','origin/main')
    ledger=Store(root).state('periods')
    keys=sorted(ledger,key=lambda k:(ledger[k]['start'],ledger[k]['revision']))
    for initial_key in keys:
        initial=ledger[initial_key]
        if initial['status'] not in {'due','open'} and initial['period_id']!=revise_period: continue
        branch=f"draft/{initial['period_id']}-r{initial['revision']}"
        prs=gh('pr','list','--repo',repo,'--head',branch,'--state','all','--json','number,state,commits,headRefOid')
        pr=None
        remote_branch=command(root,'fetch','origin',branch,check=False)
        if remote_branch.returncode==0 and command(root,'show-ref','--verify','--quiet','refs/heads/'+branch,check=False).returncode:
            command(root,'branch',branch,'FETCH_HEAD')
        if prs:
            p=prs[0]; pr={'number':p['number'],'state':p['state'],'authors':[a.get('login','unknown') for commit in p['commits'] for a in commit['authors']]}
            if p['state']=='OPEN':
                command(root,'fetch','origin',branch)
                if command(root,'show-ref','--verify','--quiet','refs/heads/'+branch,check=False).returncode:
                    command(root,'branch',branch,'FETCH_HEAD')
        result=draft_local(root,initial['period_id'],as_of,initial['type'],initial['period_id']==revise_period,pr)
        ledger=result['ledger']
        if result['action']=='created' or result['action']=='existing' and not pr:
            if result['action']=='created': command(root,'push','origin','HEAD:refs/heads/'+result['branch'])
            title='Review UCP Pulse '+initial['period_id']
            with tempfile.NamedTemporaryFile('w',suffix='.md') as body:
                body.write('Review curation and rerender with publication mode before merging. Check every claim against its pinned evidence. Pending drafts fail verify intentionally.\n'); body.flush()
                response=subprocess.run(['gh','pr','create','--repo',repo,'--head',result['branch'],'--base','main','--title',title,'--body-file',body.name],capture_output=True,text=True)
                if response.returncode: raise ValueError('draft PR creation failed; next run recovers by head branch')
            prs=gh('pr','list','--repo',repo,'--head',result['branch'],'--state','open','--json','number')
            ledger[result['key']].update(status='open',pr_number=prs[0]['number'])
        command(root,'switch','main')
        for attempt in range(3):
            current=Store(root).state('periods')
            # Merge only the lifecycle entries this iteration reconciled.
            updates={key:value for key,value in ledger.items() if key==result['key'] or key==initial_key}
            Store(root).update_periods({**current,**updates})
            commit(root,['state'],'draft: reconcile period lifecycle')
            if command(root,'push','origin','HEAD:refs/heads/main',check=False).returncode==0: break
            if attempt==2: raise ValueError('period ledger push rejected after 3 attempts')
            command(root,'fetch','origin','main'); command(root,'reset','--hard','origin/main')
    return {'periods':len(ledger)}
