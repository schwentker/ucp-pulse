"""Local Git evidence loading and deterministic report verification."""
import json
import re
import subprocess
from pathlib import Path
import yaml
from ucp_pulse.render import render
from ucp_pulse.store import Store
from ucp_pulse.util import canonical, digest


class UniqueLoader(yaml.SafeLoader):
    pass


def unique_mapping(loader,node,deep=False):
    result={}
    for key_node,value_node in node.value:
        key=loader.construct_object(key_node,deep=deep)
        if key in result: raise ValueError('duplicate YAML key')
        result[key]=loader.construct_object(value_node,deep=deep)
    return result

UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,unique_mapping)


def load_yaml(path):
    return yaml.load(Path(path).read_text(),Loader=UniqueLoader)


def git(root,*args):
    result=subprocess.run(['git','-C',str(root),*args],capture_output=True,text=True)
    if result.returncode: raise ValueError('local git operation failed: '+args[0])
    return result.stdout


def evidence_at(root,sha):
    if not re.fullmatch('[0-9a-f]{40}',sha): raise ValueError('full evidence commit SHA required')
    if git(root,'rev-parse',sha+'^{commit}').strip()!=sha: raise ValueError('evidence is not a commit')
    paths=git(root,'ls-tree','-r','--name-only',sha).splitlines()
    def read(path): return git(root,'show',sha+':'+path)
    records=[]
    for path in sorted(p for p in paths if re.fullmatch(r'data/events/\d{4}-\d{2}\.jsonl',p)):
        records.extend(json.loads(line) for line in read(path).splitlines() if line)
    derived=Store.derive(records)
    for name,value in derived.items():
        path='state/'+name+'.json'
        if (json.loads(read(path)) if path in paths else {})!=value: raise ValueError('pinned derived state differs')
    for row in records:
        snapshot=row['evidence'].get('snapshot')
        if not snapshot or not re.fullmatch(r'data/snapshots/[0-9a-f]{64}\.json',snapshot) or snapshot not in paths:
            raise ValueError('missing or invalid evidence snapshot')
        if digest(json.loads(read(snapshot)))!=Path(snapshot).stem: raise ValueError('snapshot digest mismatch')
    health=json.loads(read('state/health.json')) if 'state/health.json' in paths else {}
    sources=yaml.load(read('config/sources.yaml'),Loader=UniqueLoader)
    return records,health,sources


def render_files(data,curation_path,output,draft=False,check=False):
    curation=load_yaml(curation_path)
    records,health,sources=evidence_at(data,curation['evidence_sha'])
    md,js=render(records,health,sources,curation,draft=draft)
    # A forbidden revision must not leak even through human prose.
    forbidden=[k for k,v in curation['items'].items() if v['decision']=='CUT' or not draft and v['decision']=='PENDING']
    if any(k in md or k in js for k in forbidden): raise ValueError('CUT/PENDING revision leaked to output')
    output=Path(output)
    if check:
        Store(data).rebuild(check=True)
        if output.with_suffix('.md').read_text()!=md or output.with_suffix('.json').read_text()!=js:
            raise ValueError('committed brief differs from fresh render')
    else:
        output.parent.mkdir(parents=True,exist_ok=True)
        output.with_suffix('.md').write_text(md)
        output.with_suffix('.json').write_text(js)
    return md,js
