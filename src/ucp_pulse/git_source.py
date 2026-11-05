"""S3 reader for a complete local clone of the official public Git repository."""
import json
import subprocess
from pathlib import Path
from ucp_pulse.collectors import SPEC,NORMATIVE,evidence
from ucp_pulse.diff import alerts
from ucp_pulse.model import candidate
from ucp_pulse.util import stamp


def git(repo,*args):
    result=subprocess.run(['git','-C',str(repo),*args],capture_output=True)
    if result.returncode:
        raise ValueError('local source Git read failed: '+args[0])
    return result.stdout


def normative_batch(repo,start,observed,previous):
    repo=Path(repo)
    # Check the official clone URL and pinned main head before trusting its objects.
    remote=git(repo,'remote','get-url','origin').decode().strip()
    if remote not in {'https://github.com/Universal-Commerce-Protocol/ucp.git','https://github.com/Universal-Commerce-Protocol/ucp'}:
        raise ValueError('unexpected source repository URL')
    head=git(repo,'rev-parse','refs/remotes/origin/main').decode().strip()
    refs=[r.strip() for r in git(repo,'for-each-ref','--format=%(refname)','refs/remotes/origin/main','refs/remotes/origin/release/').decode().splitlines()]
    if not refs or 'refs/remotes/origin/main' not in refs:
        raise ValueError('official main ref missing')
    shas=git(repo,'rev-list','--reverse','--topo-order','--since='+stamp(start),*refs,'--','source','docs/specification','docs/versioning.md').decode().splitlines()
    blobs={}; documents={}; items=[]
    def docs(ref):
        if ref in documents: return documents[ref]
        tree=git(repo,'ls-tree','-r','-z',ref)
        result={}
        for entry in tree.split(b'\0'):
            if not entry: continue
            meta,path=entry.split(b'\t',1)
            name=path.decode()
            if not name.startswith(('source/schemas/','source/services/')) or not name.endswith('.json'): continue
            sha=meta.split()[2].decode()
            if sha not in blobs: blobs[sha]=json.loads(git(repo,'cat-file','blob',sha))
            result[name]=blobs[sha]
        documents[ref]=result
        return result
    for sha in shas:
        if 'ucp:commit:'+sha in previous: continue
        meta=git(repo,'show','-s','--format=%P%x00%s%x00%cI',sha).decode().strip().split('\x00')
        parents=meta[0].split() if meta[0] else []
        changed=git(repo,'diff-tree','--no-commit-id','--name-only','-r','--root',parents[0] if parents else sha+'^{}',sha).decode().splitlines() if parents else git(repo,'diff-tree','--no-commit-id','--name-only','-r','--root',sha).decode().splitlines()
        paths=sorted({p for p in changed if p.startswith(NORMATIVE)})
        if not paths: continue
        branches=[]
        for ref in refs:
            if subprocess.run(['git','-C',str(repo),'merge-base','--is-ancestor',sha,ref],capture_output=True).returncode==0:
                branches.append(ref.removeprefix('refs/remotes/origin/'))
        changes=[]
        if any(p.startswith(('source/schemas/','source/services/')) for p in paths):
            changes=alerts(docs(parents[0]) if parents else {},docs(sha))
        payload={'sha':sha,'parents':parents,'subject':meta[1],'files':paths,'changes':changes,'branches':branches}
        items.append(candidate('normative_commit',{'repo':SPEC,'sha':sha},payload,{'classification':'unknown'},
                               evidence(f'https://github.com/{SPEC}/commit/{sha}',SPEC+'@'+sha,payload,payload['subject']),
                               meta[2],'committed','official_repo','S3'))
    return {'source':'S3','complete':True,'items':items,'snapshots':[i['material'] for i in items], 'pinned_head':head}
