"""Recover S4 from an already fetched, pinned official contents response."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
from ucp_pulse.secondary import announcements,batch,ANNOUNCEMENTS
from ucp_pulse.collectors import SPEC
from ucp_pulse.store import Store
from ucp_pulse.util import canonical,digest


def recover(root,http_cache,observed,output):
    cache=json.loads(Path(http_cache).read_text())
    def value(url):
        item=cache.get(digest([url,None]))
        if not item: raise ValueError('pinned source response absent from cache')
        return json.loads(item['body'])
    head=value(f'https://api.github.com/repos/{SPEC}/commits/main')['sha']
    source=value(f'https://api.github.com/repos/{SPEC}/contents/{ANNOUNCEMENTS}?ref={head}')
    if source['path']!=ANNOUNCEMENTS or source['encoding']!='base64':
        raise ValueError('cached contents identity mismatch')
    raw=base64.b64decode(source['content'])
    actual=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
    if actual!=source['sha']:
        raise ValueError('cached Git blob SHA mismatch')
    old=Store(root).state('inventory')
    rows=announcements(raw.decode('utf-8'),head,old,observed)
    result={'observed_at':observed,'run_id':'recovered-s4-'+head,'batches':[batch('S4',rows)]}
    Path(output).write_text(canonical(result)+'\n')
    return len(rows),head


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('data','http-cache','observed-at','output'): p.add_argument('--'+name,required=True)
    a=p.parse_args()
    print(recover(a.data,a.http_cache,a.observed_at,a.output))
