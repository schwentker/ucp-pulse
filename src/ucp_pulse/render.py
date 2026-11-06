"""Pure evidence rendering. All inputs are explicit; no clock, filesystem or network."""
import re
from datetime import timedelta
from ucp_pulse.store import Store
from ucp_pulse.runner import SOURCE_NAMES
from ucp_pulse.util import canonical, stamp, utc
from ucp_pulse.amendments import spec_path

FOOTER = 'Experimental. Independent. Not affiliated with or endorsed by Shopify, Google, or UCP governance bodies.'
BLOCKS = ['Version board', 'Breaking and pending-breaking', 'Release amendments', 'Normative changes for review']


def key(row):
    return row['event_id'] + '@' + row['revision_id']


def clean(value):
    return str(value).replace('\u2014', ' - ').replace('\r','').replace('\n',' ').replace('|', '\\|').replace('<','&lt;').replace('>','&gt;')


def fact_labels(facts):
    labels=[]
    names={'author_declared_breaking':'author-declared breaking',
           'notice_declared_breaking':'notice-declared breaking', 'ucp_scoped':'UCP-scoped'}
    for name,value in facts.items():
        label=names.get(name,name.replace('_',' '))
        if value is True:
            labels.append(label)
        elif isinstance(value,dict):
            labels.extend(label+' '+part.replace('_',' ') for part,enabled in sorted(value.items()) if enabled is True)
    return sorted(labels)


def readable_facts(row):
    labels=fact_labels(row['facts'])
    base=row['material'].get('base')
    if base: labels.append('base '+base)
    if row['family']=='announcement' and row['material'].get('date'):
        labels.append('official date '+row['material']['date'])
    return '; '.join(labels) or 'none recorded'


def scope(records, period, as_of):
    available = [r for r in records if utc(r['first_seen_at']) <= utc(as_of)]
    inventory = Store.derive(available)['inventory']
    if period['type'] == 'history':
        selected = available
    else:
        selected = [r for r in available if utc(period['start']) <= utc(r['first_seen_at']) < utc(period['end'])]
    # Mandatory board/pending state may cite older observations, without losing window revisions.
    rows = {key(r): r for r in selected}
    rows.update({key(r):r for r in inventory.values() if r['family'] in {'spec_release','sdk_tag','registry_version'} or r['facts'].get('author_declared_breaking') or r['facts'].get('notice_declared_breaking')})
    dependencies = {eid for r in rows.values() if r['family']=='spec_release' for eid in r['material'].get('amended_by', [])}
    rows.update({key(r):r for r in inventory.values() if r['event_id'] in dependencies})
    pinned = set()
    for row in rows.values():
        if row['family'] != 'spec_release':
            continue
        for eid, item in row['material'].get('amendment_items', {}).items():
            pinned.add(eid + '@' + item['revision'])
            pinned.add(item['path_event'] + '@' + item['path_revision'])
    rows.update({key(r):r for r in available if key(r) in pinned})
    return rows, inventory, {key(r) for r in selected}


def seed(records, evidence_sha, as_of, period):
    rows, _, _ = scope(records, period, as_of)
    return {'period':dict(period), 'evidence_sha':evidence_sha, 'as_of':stamp(as_of),
            'headline':{'text':'','evidence':[]}, 'signal':{'text':'','evidence':[]}, 'watch_next':[],
            'items':{k:{'decision':'PENDING','analyst':None,'affected':[],'migration':'','deadline':'','note':''} for k in sorted(rows)}}


def validate(records, curation, publishable):
    if set(curation) != {'period','evidence_sha','as_of','headline','signal','watch_next','items'}:
        raise ValueError('unexpected or missing curation fields')
    if not re.fullmatch('[0-9a-f]{40}', curation['evidence_sha']):
        raise ValueError('evidence SHA must be a full commit')
    period = curation['period']
    if set(period) != {'id','type','start','end','revision'} or period['type'] not in {'weekly','history'} or not re.fullmatch('r[1-9][0-9]*',period['revision']):
        raise ValueError('invalid period metadata')
    if not re.fullmatch(r'(?:p|history)-\d{4}-\d{2}-\d{2}',period['id']):
        raise ValueError('invalid period id')
    start,end,as_of = utc(period['start']),utc(period['end']),utc(curation['as_of'])
    if start >= end or as_of < start:
        raise ValueError('invalid period bounds')
    if period['type']=='weekly' and (start.weekday()!=6 or start.hour or start.minute or start.second or start.microsecond or end-start!=timedelta(days=7) or period['id']!='p-'+start.date().isoformat()):
        raise ValueError('invalid Sunday UTC week')
    rows,inventory,selected = scope(records,period,curation['as_of'])
    items=curation['items']
    if not isinstance(items,dict) or set(items)!=set(rows):
        raise ValueError('curation must decide every scoped evidence revision exactly once')
    for k,item in items.items():
        if set(item)!={'decision','analyst','affected','migration','deadline','note'}:
            raise ValueError('unexpected or missing item fields')
        if item['decision'] not in {'KEEP','CUT','PENDING'} or item['analyst'] not in {None,'breaking','additive','clarification'}:
            raise ValueError('invalid curation decision or analyst value')
        if not isinstance(item['affected'],list) or any(not isinstance(s,str) for s in item['affected']) or any(not isinstance(item[f],str) for f in ('migration','deadline','note')):
            raise ValueError('invalid item text')
        if (item['analyst'] or item['affected'] or any(item[f] for f in ('migration','deadline','note'))) and item['decision']!='KEEP':
            raise ValueError('nonempty analyst fields require their exact revision KEEP')
        if publishable and item['decision']=='PENDING':
            raise ValueError('PENDING evidence is not publishable')
    if not isinstance(curation['watch_next'],list):
        raise ValueError('watch_next must be a list')
    for claim in [curation['headline'],curation['signal'],*curation['watch_next']]:
        if not isinstance(claim,dict) or set(claim)!={'text','evidence'} or not isinstance(claim['text'],str) or not isinstance(claim['evidence'],list):
            raise ValueError('invalid claim shape')
        if claim['text'].strip() and not claim['evidence']:
            raise ValueError('nonempty claim needs evidence')
        if any(k not in items or items[k]['decision']!='KEEP' for k in claim['evidence']):
            raise ValueError('claim cites unknown or non-KEEP revision')
    return rows,inventory,selected


def render(records, health, sources, curation, draft=False):
    rows, inventory, selected = validate(records,curation,publishable=not draft)
    choices=curation['items']
    visible={k:r for k,r in rows.items() if choices[k]['decision']=='KEEP' or draft and choices[k]['decision']=='PENDING'}
    ordered=sorted(visible,key=lambda k:(utc(visible[k]['event_time']),visible[k]['event_id'],k))
    numbers={k:'S'+str(i+1) for i,k in enumerate(ordered)}
    def cite(k): return '['+numbers[k]+']'
    def label(r):
        m=r['material']
        return m.get('title') or m.get('subject') or m.get('tag') or m.get('version') or m.get('path') or r['event_id']
    def support(r):
        for eid, item in r['material'].get('amendment_items', {}).items():
            event_key = eid + '@' + item['revision']
            path_key = item['path_event'] + '@' + item['path_revision']
            if event_key in visible and path_key in visible:
                yield item['scope'], event_key, path_key

    def amendment_status(r):
        facts = r['facts']
        scopes = [scope for scope, _, _ in support(r)]
        if facts.get('amended_spec') and 'spec' in scopes:
            return 'spec'
        items = r['material'].get('amendment_items', {})
        if facts.get('amended_docs_only') and items and len(scopes) == len(items):
            return 'docs only'
        if facts.get('tag_at_branch_head') and r['material'].get('published_at') and not (items or set(r['material'].get('amended_by', [])) - {r['event_id']}):
            return 'none'
        if facts.get('amended') is False and 'amended_spec' not in facts:
            return 'none'
        return 'unknown'

    def event_time(r):
        kind='observed, not published' if r['event_time_kind']=='observed' else r['event_time_kind']
        return r['event_time']+' ('+kind+')'
    def rowtext(k, show_base=False):
        r=visible[k]; item=choices[k]
        signal='analyst-confirmed: '+item['analyst'] if item['analyst'] else 'author-declared' if r['facts'].get('author_declared_breaking') else 'notice-declared' if r['facts'].get('notice_declared_breaking') else 'unknown'
        review='; pending review' if item['decision']=='PENDING' else ''
        facts=readable_facts(r)
        if r['family']=='spec_release' and 'amended_spec' in r['facts']:
            shown={name:value for name,value in r['facts'].items()
                   if name not in {'amended','amended_spec','amended_docs_only'}}
            status=amendment_status(r)
            if status in {'spec','docs only'}:
                shown['amended_'+status.replace(' ','_')]=True
            facts=readable_facts({**r,'facts':shown})
        values=[label(r),r['subject'].get('repo','unknown')]
        if show_base: values.append(r['material'].get('base') or 'unknown')
        values += [facts,signal+review,', '.join(item['affected']) or 'unknown',item['migration'] or 'unknown',item['deadline'] or 'unknown',event_time(r),r['first_seen_at'],cite(k)]
        return '| '+' | '.join(clean(v) for v in values)+' |'
    period=curation['period']; title=f"UCP Pulse, {period['type']} {period['start']} to {period['end']} (UTC)"
    lines=['# '+title,'',f"Evidence commit: {curation['evidence_sha']}; as of {curation['as_of']}.",'']
    if draft: lines+=['Draft for review. Pending evidence is unapproved.','']
    for name,claims in [('Headline',[curation['headline']]),('Signal',[curation['signal']]),('Watch next',curation['watch_next'])]:
        lines+=['## '+name,'']
        texts=[clean(c['text'])+' '+ ' '.join(cite(k) for k in c['evidence']) for c in claims if c['text'].strip()]
        lines+=texts or ['No curated statement.']; lines+=['']
    current={key(r):r for r in inventory.values() if key(r) in visible}
    lines+=['## Version board','', '| Component | Version or tag | Tag commit (short) | Published | Amended | Notes | Evidence |','| --- | --- | --- | --- | --- | --- | --- |']
    # Each current release line is mandatory; SDK schemes and registry versions stay separate.
    for component,families,repo in [('Spec release lines',{'spec_release'},None),('js-sdk',{'sdk_tag'},'js-sdk'),('python-sdk',{'sdk_tag'},'python-sdk'),('ucp-schema',{'sdk_tag'},'ucp-schema'),('PyPI',{'registry_version'},'pypi'),('npm',{'registry_version'},'npm')]:
        matches=[k for k,r in current.items() if r['family'] in families and (repo is None or r['subject'].get('repo','').endswith('/'+repo) or r['subject'].get('registry')==repo)]
        if not matches: lines+=['| '+component+' | unknown | unknown | unknown | unknown | none recorded | |']; continue
        for k in sorted(matches,key=lambda k:(utc(current[k]['event_time']),current[k]['event_id'],k)):
            r=current[k]; m=r['material']
            notes=fact_labels({name:value for name,value in r['facts'].items() if name not in {'amended','amended_spec','amended_docs_only'}})
            if m.get('branch_head'): notes.append('branch '+m['branch_head'][:12])
            if m.get('scheme'): notes.append('scheme '+m['scheme'])
            if m.get('dist_tags'): notes.append('registry labels '+', '.join(m['dist_tags']))
            notes.extend(name for name in ('draft','prerelease') if m.get(name) is True)
            if choices[k]['decision']=='PENDING': notes.append('pending review')
            amended=amendment_status(r)
            if amended in {'spec', 'docs only'}:
                _, event_key, path_key = next(item for item in support(r)
                                               if item[0] == ('spec' if amended == 'spec' else 'docs_site'))
                notes.append('scope evidence '+cite(event_key)+(cite(path_key) if path_key != event_key else ''))
            values=[component,m.get('tag') or m.get('version') or 'unknown',
                    (m.get('tag_commit') or '')[:12] or 'unknown',m.get('published_at') or 'unknown',
                    amended,'; '.join(notes) or 'none recorded',cite(k)]
            lines+=['| '+' | '.join(clean(v) for v in values)+' |']
    lines+=['','Main ahead on normative paths: unknown (no complete ancestry count).','']
    sections={
        'Breaking and pending-breaking':[k for k in ordered if visible[k]['facts'].get('author_declared_breaking') or visible[k]['facts'].get('notice_declared_breaking') or choices[k]['analyst']=='breaking'],
        'Release amendments':[k for k in ordered if k in selected and visible[k]['family']=='spec_release' and (visible[k]['facts'].get('amended') or visible[k]['material'].get('amendment_items'))],
        'Normative changes for review':[k for k in ordered if k in selected and visible[k]['family']=='normative_commit'],
        'Official notices':[k for k in ordered if k in selected and visible[k]['family']=='announcement'],
        'Governance':[k for k in ordered if k in selected and visible[k]['family']=='governance'],
        'Shopify changelog, UCP-scoped':[k for k in ordered if k in selected and visible[k]['family']=='changelog'],
        'Late arrivals':[k for k in ordered if k in selected and utc(visible[k]['event_time'])<utc(period['start'])]}
    for name,keys in sections.items():
        if not keys and name not in BLOCKS: continue
        lines+=['## '+name,'']
        if not keys: lines+=['No approved evidence in this block.' if not draft else 'No evidence in this block.','']; continue
        show_base=name=='Breaking and pending-breaking'
        if show_base:
            # R5 groups same-day backports after main, then preserves time/identity order.
            keys=sorted(keys,key=lambda k:(utc(visible[k]['event_time']).date(),
                        (visible[k]['material'].get('base') or '').startswith('release/'),
                        utc(visible[k]['event_time']),visible[k]['event_id'],k))
        columns=['Change','Repo']+(['Base'] if show_base else [])+['Facts','Signal','Affected','Migration','Deadline','Event time (kind)','First seen','Evidence']
        lines+=['| '+' | '.join(columns)+' |','| '+' | '.join('---' for _ in columns)+' |']
        lines += [rowtext(k, show_base) for k in keys]
        scoped_groups = {'spec': [], 'docs_site': [], 'unknown': []}
        scoped_releases = {visible[k]['event_id'] for k in keys
                           if 'amendment_items' in visible[k]['material']}
        for k in keys:
            r=visible[k]
            if name=='Late arrivals': lines+=['',f"{cite(k)} Original time: {r['event_time']} ({r['event_time_kind']})."]
            if name in {'Normative changes for review','Release amendments'}:
                lines+=['',cite(k)+' Structural classification: '+(choices[k]['analyst'] or 'unknown')+'.']
                if r['material'].get('files'): lines+=['Files: '+clean(', '.join(r['material']['files']))]
                for change in r['material'].get('changes',[]):
                    lines+=['- '+clean(canonical({f:change[f] for f in ('file','pointers','annotations','dependents','classification')}))]
            if name=='Release amendments':
                for scope_name, event_key, path_key in support(r):
                    item = visible[event_key]
                    path_citation = ' (paths '+cite(path_key)+')' if path_key != event_key else ''
                    paths = visible[path_key]['material'].get('files', [])
                    sample = next((path for path in paths if spec_path(path)), paths[0] if paths else '')
                    path_text = ' ('+clean(sample)+')' if scope_name != 'unknown' and sample else ''
                    scoped_groups[scope_name].append(
                        '- '+clean(label(r))+' '+cite(k)+': '+clean(item['event_id'])+': '
                        +clean(label(item))+' '+cite(event_key)+path_citation+path_text)
                if r['event_id'] not in scoped_releases:
                    for eid in r['material'].get('amended_by', []):
                        supporting=[j for j in ordered if visible[j]['event_id']==eid and eid!=r['event_id']]
                        if supporting:
                            j=supporting[-1]
                            scoped_groups['unknown'].append('- '+clean(eid)+': '+clean(label(visible[j]))+' '+cite(j))
            if choices[k]['note']: lines+=['',clean(choices[k]['note'])+' '+cite(k)]
        if name=='Release amendments':
            for scope_name, heading in [('spec','Spec amendments'), ('docs_site','Docs-only amendments'),
                                        ('unknown','Amendments with unknown scope')]:
                if scoped_groups[scope_name]:
                    lines+=['', '### '+heading, '', *scoped_groups[scope_name]]
        lines+=['']
    coverage=[]
    lines+=['## Coverage','','| Source | Last success | Failures | State / gap |','| --- | --- | --- | --- |']
    for source,name in SOURCE_NAMES.items():
        status=health.get(source,{})
        config=sources.get(source,{'enabled':False,'reason':'not configured'})
        last=status.get('last_success')
        stale=not last or utc(curation['as_of'])-utc(last)>timedelta(hours=48)
        gap=config.get('reason') if not config.get('enabled') else status.get('last_error') or ('stale' if stale else 'current')
        if last and utc(last)>utc(curation['as_of']): raise ValueError('health is newer than as_of')
        notes=[]
        if source=='S7':
            refs=sorted({r['material']['binding_ref'] for r in inventory.values()
                         if r['family']=='registry_version' and r['subject'].get('registry')=='pypi' and r['material'].get('binding_ref')})
            if refs:
                notes.append('D020: PyPI binding via description link plus pinned manifest: '+', '.join(refs)+'.')
        if source=='S3':
            for recovery in status.get('git_recoveries', []):
                head=recovery['pinned_head']
                if not re.fullmatch('[0-9a-f]{40}',head) or utc(recovery['observed_at'])>utc(curation['as_of']):
                    raise ValueError('invalid pinned Git recovery provenance')
                notes.append('D021: Normative commits recovered from a pinned official Git clone; pinned head '+head+'.')
        entry={'source':source,'name':name,'enabled':bool(config.get('enabled')),'last_success':last,'failures':status.get('consecutive_failures',0),'stale':stale,'gap':gap,'notes':notes}
        coverage.append(entry)
        lines+=['| '+' | '.join(clean(v) for v in [source+' '+name,last or 'unknown',entry['failures'],gap or 'unknown'])+' |']
    lines+=['']+['- '+clean(note) for entry in coverage for note in entry['notes']]
    lines+=['','## Source ledger','']
    ledger=[]
    for k in ordered:
        r=visible[k]; e=r['evidence']
        entry={'citation':numbers[k],'key':k,'url':e['url'],'ref':e['ref'],'snapshot':e['snapshot'],'event_time':r['event_time'],'event_time_kind':r['event_time_kind'],'authority':r['authority']}
        ledger.append(entry)
        time_note='observed, not published' if r['event_time_kind']=='observed' else r['event_time_kind']
        lines+=['- '+cite(k)+' '+clean(e['url'])+'; ref '+clean(e['ref'])+'; '+r['event_time']+' ('+time_note+'); '+r['authority']+'.']
    if not ledger: lines+=['No cited evidence.']
    lines+=['',FOOTER,'']
    output={'period':period,'evidence_sha':curation['evidence_sha'],'as_of':curation['as_of'],'draft':draft,'coverage':coverage,'source_ledger':ledger,
            'evidence':[{'key':k,'material':visible[k]['material'],'facts':visible[k]['facts'],'curation':choices[k]} for k in ordered]}
    return '\n'.join(lines), canonical(output)+'\n'
