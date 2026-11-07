"""Explicit commands for local work and future deployed workflows."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import uuid
import yaml
from ucp_pulse.store import Store
from ucp_pulse.report import evidence_at, render_files, load_yaml, git
from ucp_pulse.render import seed
from ucp_pulse.util import canonical, stamp


def main(argv=None):
    parser=argparse.ArgumentParser(prog='ucp-pulse')
    commands=parser.add_subparsers(dest='command',required=True)
    p=commands.add_parser('rebuild'); p.add_argument('--data',required=True); p.add_argument('--check',action='store_true')
    for name in ('render','verify'):
        p=commands.add_parser(name); p.add_argument('--data',required=True); p.add_argument('--curation',required=True); p.add_argument('--output',required=True); p.add_argument('--draft',action='store_true',help='Structural only, not publishable')
    p=commands.add_parser('seed'); p.add_argument('--data',required=True); p.add_argument('--evidence-sha',required=True); p.add_argument('--as-of',required=True); p.add_argument('--period',required=True); p.add_argument('--output',required=True)
    p=commands.add_parser('smoke-collect',help='Explicit live source reads; cache candidates for transactional replay'); p.add_argument('--data',required=True); p.add_argument('--start',help='Initial history bound; defaults to config/collection.yaml; complete cursors take precedence'); p.add_argument('--cache',required=True); p.add_argument('--run-id'); p.add_argument('--as-of'); p.add_argument('--only',nargs='+')
    p=commands.add_parser('apply-cached'); p.add_argument('--data',required=True); p.add_argument('--cache',required=True); p.add_argument('--push',action='store_true'); p.add_argument('--remote',default='origin'); p.add_argument('--crash-before-push',action='store_true')
    p=commands.add_parser('draft'); p.add_argument('--data',required=True); p.add_argument('--period',required=True); p.add_argument('--as-of',required=True); p.add_argument('--type',choices=['weekly','history'],default='weekly'); p.add_argument('--revise',action='store_true'); p.add_argument('--pr-state')
    p=commands.add_parser('draft-due'); p.add_argument('--data',required=True); p.add_argument('--repo',required=True); p.add_argument('--as-of'); p.add_argument('--revise'); p.add_argument('--publish',action='store_true',required=True)
    p=commands.add_parser('export-local'); p.add_argument('--data',required=True); p.add_argument('--curation',required=True); p.add_argument('--output',required=True); p.add_argument('--public',required=True); p.add_argument('--approval',required=True)
    p=commands.add_parser('verify-all'); p.add_argument('--data',required=True)
    p=commands.add_parser('check-export'); p.add_argument('--public',required=True)
    args=parser.parse_args(argv)
    try:
        from ucp_pulse.automation import replay, draft_local, publish_due, export_local
        if args.command=='rebuild':
            equal=Store(args.data).rebuild(check=args.check); print(json.dumps({'equal_before':equal,'checked':args.check}))
        elif args.command=='seed':
            records,_,_=evidence_at(args.data,args.evidence_sha)
            c=seed(records,args.evidence_sha,args.as_of,json.loads(Path(args.period).read_text()))
            path=Path(args.output)
            if path.exists(): raise ValueError('curation exists; refusing to overwrite human decisions')
            path.parent.mkdir(parents=True,exist_ok=True); path.write_text(yaml.safe_dump(c,sort_keys=True,allow_unicode=False))
        elif args.command=='smoke-collect':
            from ucp_pulse.http import Client
            from ucp_pulse.runner import collect
            store=Store(args.data); config=load_yaml(Path(args.data)/'config/sources.yaml')
            if args.only:
                if set(args.only)-set(config): raise ValueError('unknown requested sources')
                config={k:v for k,v in config.items() if k in args.only}
            start=stamp(args.start or load_yaml(Path(args.data)/'config/collection.yaml')['history_start'])
            observed=stamp(args.as_of or datetime.now(timezone.utc))
            client=Client(cache=str(Path(args.cache).with_suffix('.http.json')))
            batches=collect(client,store.state('inventory'),store.state('cursors'),config,observed,start)
            envelope={'observed_at':observed,'run_id':args.run_id or str(uuid.uuid4()),'tracking_start':observed,'batches':batches}
            Path(args.cache).parent.mkdir(parents=True,exist_ok=True); Path(args.cache).write_text(canonical(envelope)+'\n')
            print(canonical({'requests':client.requests,'sources':[{'source':b['source'],'complete':b['complete'],'count':len(b.get('items',[])),'error':b.get('error')} for b in batches]}))
        elif args.command=='apply-cached':
            print(canonical(replay(args.data,json.loads(Path(args.cache).read_text()),args.push,args.remote,crash_before_push=args.crash_before_push)))
        elif args.command=='draft':
            pr=json.loads(Path(args.pr_state).read_text()) if args.pr_state else None
            result=draft_local(args.data,args.period,args.as_of,args.type,args.revise,pr)
            print(canonical({k:v for k,v in result.items() if k!='ledger'}))
        elif args.command=='draft-due':
            print(canonical(publish_due(args.data,args.repo,stamp(args.as_of or datetime.now(timezone.utc)),args.revise)))
        elif args.command=='export-local':
            print(canonical(export_local(args.data,args.curation,args.output,args.public,json.loads(Path(args.approval).read_text()))))
        elif args.command=='verify-all':
            Store(args.data).rebuild(check=True)
            for cp in sorted((Path(args.data)/'curation').glob('*.yaml')):
                render_files(args.data,cp,Path(args.data)/'drafts'/cp.stem/'brief',check=True)
            print(canonical({'verified':True}))
        elif args.command=='check-export':
            from ucp_pulse.exporting import check_public
            check_public(args.public); print(canonical({'verified':True}))
        else:
            render_files(args.data,args.curation,args.output,draft=args.draft,check=args.command=='verify')
            print(json.dumps({'structural':True,'publishable':not args.draft}))
    except (ValueError, OSError, KeyError, TypeError, yaml.YAMLError) as error:
        print(type(error).__name__+': '+str(error),file=sys.stderr); return 1
    return 0
