"""Exercise S3 against synthetic local Git history with networking blocked."""
import json
import subprocess
from pathlib import Path
from ucp_pulse.git_source import normative_batch


def git(root,*args):
    p=subprocess.run(['git','-C',str(root),*args],check=True,capture_output=True,text=True)
    return p.stdout.strip()


def test_local_git_normative_history_and_dependents(tmp_path):
    root=tmp_path/'repo'; root.mkdir()
    git(root,'init','-b','main')
    git(root,'config','user.name','Synthetic test')
    git(root,'config','user.email','test@example.invalid')
    git(root,'remote','add','origin','https://github.com/Universal-Commerce-Protocol/ucp.git')
    schema=root/'source/schemas/a.json'; schema.parent.mkdir(parents=True)
    schema.write_text(json.dumps({'ucp_request':{'type':'string'}}))
    dependent=root/'source/schemas/b.json'; dependent.write_text(json.dumps({'$ref':'a.json'}))
    git(root,'add','.'); git(root,'commit','-m','synthetic initial schema')
    first=git(root,'rev-parse','HEAD')
    schema.write_text(json.dumps({'ucp_request':{'type':'number'}}))
    git(root,'add','.'); git(root,'commit','-m','synthetic schema revision')
    second=git(root,'rev-parse','HEAD')
    git(root,'update-ref','refs/remotes/origin/main',second)
    batch=normative_batch(root,'2000-01-01T00:00:00Z','2026-11-05T00:00:00Z',{})
    assert batch['complete'] and batch['pinned_head']==second
    row=next(i for i in batch['items'] if i['subject']['sha']==second)
    change=next(c for c in row['material']['changes'] if c['file']=='source/schemas/a.json')
    assert change['classification']=='unknown'
    assert change['annotations']==['ucp_request']
    assert change['dependents']==['source/schemas/b.json']
    assert row['evidence']['ref'].endswith('@'+second)
    assert row['material']['parents']==[first]
