"""Explicit live collection entry point; no network at import time."""
from datetime import timedelta
from ucp_pulse.collectors import GitHub
from ucp_pulse.secondary import Secondary
from ucp_pulse.util import stamp, utc
from ucp_pulse.http import SourceError

SOURCE_NAMES = {'S1':'Spec releases', 'S2':'Spec PRs', 'S3':'Normative commits', 'S4':'Announcements',
                'S5':'Governance', 'S6':'SDKs and schema tool', 'S7':'PyPI', 'S8':'npm', 'S9':'Discussions', 'S10':'Shopify changelog'}


def collect(client, previous, cursors, config, observed, start):
    gh = GitHub(client)
    secondary = Secondary(gh)
    batches = []
    for source, entry in config.items():
        if source not in SOURCE_NAMES:
            raise ValueError('unknown source in config')
        if not entry.get('enabled'):
            continue
        last = cursors.get(source, {}).get('last_complete')
        since = stamp(max(utc(start), utc(last) - timedelta(days=7))) if last else stamp(start)
        try:
            if source == 'S9':
                raise SourceError('Discussions disabled: live smoke did not pass')
            owner = gh if source in {'S1','S2','S3'} else secondary
            method = getattr(owner, source.lower())
            args = (previous, observed, since) if source in {'S2','S3','S6'} else (previous, observed)
            result = method(*args)
            batches.append(result)
        except (SourceError, ValueError, KeyError, TypeError, OSError) as error:
            # These messages are bounded and do not contain request headers or tokens.
            message = str(error) if isinstance(error, SourceError) else type(error).__name__ + ': source parsing or transport failed'
            batches.append({'source':source, 'complete':False, 'error':message})
    return batches
