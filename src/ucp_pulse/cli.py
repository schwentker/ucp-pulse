"""Command line interface. Network operations require an explicit command."""
import argparse
import json
from ucp_pulse.store import Store


def main(argv=None):
    parser = argparse.ArgumentParser(prog="ucp-pulse")
    commands = parser.add_subparsers(dest="command", required=True)
    rebuild = commands.add_parser("rebuild")
    rebuild.add_argument("--data", required=True)
    rebuild.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "rebuild":
        equal = Store(args.data).rebuild(check=args.check)
        print(json.dumps({"equal_before": equal, "checked": args.check}))
    return 0
