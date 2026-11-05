"""Command line interface. Network operations require an explicit command."""
import argparse
import json
from pathlib import Path
import sys
import yaml
from ucp_pulse.store import Store
from ucp_pulse.report import evidence_at, render_files
from ucp_pulse.render import seed


def main(argv=None):
    parser=argparse.ArgumentParser(prog='ucp-pulse')
    commands=parser.add_subparsers(dest='command',required=True)
    rebuild=commands.add_parser('rebuild'); rebuild.add_argument('--data',required=True); rebuild.add_argument('--check',action='store_true')
    for name in ('render','verify'):
        p=commands.add_parser(name); p.add_argument('--data',required=True); p.add_argument('--curation',required=True); p.add_argument('--output',required=True); p.add_argument('--draft',action='store_true',help='Structural draft checks only; never publishable')
    p=commands.add_parser('seed'); p.add_argument('--data',required=True); p.add_argument('--evidence-sha',required=True); p.add_argument('--as-of',required=True); p.add_argument('--period',required=True,help='JSON file with id/type/start/end/revision'); p.add_argument('--output',required=True)
    args=parser.parse_args(argv)
    try:
        if args.command=='rebuild':
            equal=Store(args.data).rebuild(check=args.check); print(json.dumps({'equal_before':equal,'checked':args.check}))
        elif args.command=='seed':
            records,_,_=evidence_at(args.data,args.evidence_sha)
            c=seed(records,args.evidence_sha,args.as_of,json.loads(Path(args.period).read_text()))
            path=Path(args.output)
            if path.exists(): raise ValueError('curation exists; refusing to overwrite human decisions')
            path.parent.mkdir(parents=True,exist_ok=True); path.write_text(yaml.safe_dump(c,sort_keys=True,allow_unicode=False))
        else:
            render_files(args.data,args.curation,args.output,draft=args.draft,check=args.command=='verify')
            print(json.dumps({'structural':True,'publishable':not args.draft}))
    except (ValueError, OSError, KeyError, TypeError, yaml.YAMLError) as error:
        print(type(error).__name__+': '+str(error),file=sys.stderr); return 1
    return 0
