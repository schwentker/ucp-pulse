"""Pure evidence rendering. All inputs are explicit; no clock, filesystem or network."""
import re
from datetime import timedelta
from ucp_pulse.store import Store
from ucp_pulse.runner import SOURCE_NAMES
from ucp_pulse.util import canonical, stamp, utc

FOOTER = 'Experimental. Independent. Not affiliated with or endorsed by Shopify, Google, or UCP governance bodies.'
BLOCKS = ['Version board', 'Breaking and pending-breaking', 'Release amendments', 'Normative changes for review']


def key(row):
    return row['event_id'] + '@' + row['revision_id']


def clean(value):
    return str(value).replace('\u2014', ' - ').replace('\r','').replace('\n',' ').replace('|', '\\|').replace('<','&lt;').replace('>','&gt;')


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
    ordered=sorted(visible,key=lambda k:(visible[k]['event_time'],visible[k]['event_id'],k))
    numbers={k:'S'+str(i+1) for i,k in enumerate(ordered)}
    def cite(k): return '['+numbers[k]+']'
    def label(r):
        m=r['material']
        return m.get('title') or m.get('subject') or m.get('tag') or m.get('version') or m.get('path') or r['event_id']
    def rowtext(k):
        r=visible[k]; item=choices[k]
        signal='analyst-confirmed: '+item['analyst'] if item['analyst'] else 'author-declared' if r['facts'].get('author_declared_breaking') else 'notice-declared' if r['facts'].get('notice_declared_breaking') else 'unknown'
        review='; pending review' if item['decision']=='PENDING' else ''
        base=r['material'].get('base')
        facts=canonical({**r['facts'],**({'base':base} if base else {})})
        return '| '+' | '.join(clean(v) for v in [label(r),r['subject'].get('repo','unknown'),facts,signal+review,', '.join(item['affected']) or 'unknown',item['migration'] or 'unknown',item['deadline'] or 'unknown',r['first_seen_at'],cite(k)])+' |'
    period=curation['period']; title=f"UCP Pulse, {period['type']} {period['start']} to {period['end']} (UTC)"
    lines=['# '+title,'',f"Evidence commit: {curation['evidence_sha']}; as of {curation['as_of']}.",'']
    if draft: lines+=['Draft for review. Pending evidence is unapproved.','']
    for name,claims in [('Headline',[curation['headline']]),('Signal',[curation['signal']]),('Watch next',curation['watch_next'])]:
        lines+=['## '+name,'']
        texts=[clean(c['text'])+' '+ ' '.join(cite(k) for k in c['evidence']) for c in claims if c['text'].strip()]
        lines+=texts or ['No curated statement.']; lines+=['']
    current={key(r):r for r in inventory.values() if key(r) in visible}
    lines+=['## Version board','', '| Component | Observed facts | Evidence |','| --- | --- | --- |']
    # Each current release line is mandatory; SDK schemes and registry versions stay separate.
    for component,families,repo in [('Spec release lines',{'spec_release'},None),('js-sdk',{'sdk_tag'},'js-sdk'),('python-sdk',{'sdk_tag'},'python-sdk'),('ucp-schema',{'sdk_tag'},'ucp-schema'),('PyPI',{'registry_version'},'pypi'),('npm',{'registry_version'},'npm')]:
        matches=[k for k,r in current.items() if r['family'] in families and (repo is None or r['subject'].get('repo','').endswith('/'+repo) or r['subject'].get('registry')==repo)]
        if not matches: lines+=['| '+component+' | unknown | |']; continue
        for k in sorted(matches,key=lambda k:(current[k]['event_time'],k)):
            r=current[k]; m=r['material']
            facts={field:m.get(field) for field in ('version','tag','scheme','tag_commit','branch_head','published_at','dist_tags') if field in m}
            facts.update(r['facts'])
            lines+=['| '+component+' | '+clean(canonical(facts))+' | '+cite(k)+' |']
    lines+=['','Main ahead on normative paths: unknown (no complete ancestry count).','']
    sections={
        'Breaking and pending-breaking':[k for k in ordered if visible[k]['facts'].get('author_declared_breaking') or visible[k]['facts'].get('notice_declared_breaking') or choices[k]['analyst']=='breaking'],
        'Release amendments':[k for k in ordered if k in selected and visible[k]['family']=='spec_release' and visible[k]['facts'].get('amended')],
        'Normative changes for review':[k for k in ordered if k in selected and visible[k]['family']=='normative_commit'],
        'Official notices':[k for k in ordered if k in selected and visible[k]['family']=='announcement'],
        'Governance':[k for k in ordered if k in selected and visible[k]['family']=='governance'],
        'Shopify changelog, UCP-scoped':[k for k in ordered if k in selected and visible[k]['family']=='changelog'],
        'Late arrivals':[k for k in ordered if k in selected and utc(visible[k]['event_time'])<utc(period['start'])]}
    for name,keys in sections.items():
        if not keys and name not in BLOCKS: continue
        lines+=['## '+name,'']
        if not keys: lines+=['No approved evidence in this block.' if not draft else 'No evidence in this block.','']; continue
        lines+=['| Change | Repo | Facts | Signal | Affected | Migration | Deadline | First seen | Evidence |','| --- | --- | --- | --- | --- | --- | --- | --- | --- |']
        lines += [rowtext(k) for k in keys]
        for k in keys:
            r=visible[k]
            if name=='Late arrivals': lines+=['',f"{cite(k)} Original time: {r['event_time']} ({r['event_time_kind']})."]
            if name in {'Normative changes for review','Release amendments'}:
                lines+=['',cite(k)+' Structural classification: '+(choices[k]['analyst'] or 'unknown')+'.']
                if r['material'].get('files'): lines+=['Files: '+clean(', '.join(r['material']['files']))]
                for change in r['material'].get('changes',[]):
                    lines+=['- '+clean(canonical({f:change[f] for f in ('file','pointers','annotations','dependents','classification')}))]
            if name=='Release amendments':
                reasons=r['material'].get('amendment_reasons', [])
                if reasons: lines+=['Amendment evidence: '+clean('; '.join(reasons))+'.']
                for eid in r['material'].get('amended_by', []):
                    if eid==r['event_id']: continue
                    supporting=[j for j in ordered if visible[j]['event_id']==eid]
                    if supporting:
                        j=supporting[-1]
                        lines+=['- '+clean(eid)+': '+clean(label(visible[j]))+' '+cite(j)]
                    else:
                        lines+=['- Supporting evidence excluded by curation.']
            if choices[k]['note']: lines+=['',clean(choices[k]['note'])+' '+cite(k)]
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
        entry={'source':source,'name':name,'enabled':bool(config.get('enabled')),'last_success':last,'failures':status.get('consecutive_failures',0),'stale':stale,'gap':gap}
        coverage.append(entry)
        lines+=['| '+' | '.join(clean(v) for v in [source+' '+name,last or 'unknown',entry['failures'],gap or 'unknown'])+' |']
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
