"""Golden brief built entirely from labeled synthetic evidence."""
import json
from pathlib import Path
from ucp_pulse.collectors import SPEC, evidence
from ucp_pulse.model import candidate, revise
from ucp_pulse.render import render, seed

NOW='2020-02-10T00:00:00Z'
PERIOD={'id':'history-2020-01-01','type':'history','start':'2020-01-01T00:00:00Z','end':NOW,'revision':'r1'}
GOLDEN=Path(__file__).parent/'golden'/'history.md'


def synthetic_records():
    rows=[]
    for n in (2,1):
        date=f'2020-01-0{n}T00:00:00Z'
        for family,subject,material,facts,kind in [
            ('spec_pr',{'repo':SPEC,'number':n},{'title':f'feat!: synthetic change {n}','base':'main'},
             {'merged':True,'opened':False,'author_declared_breaking':True},'merged'),
            ('normative_commit',{'repo':SPEC,'sha':str(n)*40},{'subject':f'synthetic normative {n}','files':['docs/specification/synthetic.md']},
             {'classification':'unknown'},'committed'),
            ('announcement',{'date':date[:10],'slug':f'synthetic-{n}'},{'title':f'Synthetic notice {n}','date':date[:10]},
             {'notice_posted':True,'deleted':False},'posted'),
            ('governance',{'repo':SPEC,'path':f'SYNTHETIC-{n}.md'},{'path':f'SYNTHETIC-{n}.md'},
             {'deleted':False},'observed'),
            ('changelog',{'guid':f'synthetic-{n}'},{'title':f'Synthetic changelog {n}','published_at':date},
             {'ucp_scoped':True},'published'),
        ]:
            # PR event times deliberately tie; identity resolves the tie.
            time='2020-01-02T00:00:00Z' if family=='spec_pr' else date
            c=candidate(family,subject,material,facts,evidence('https://example.invalid/synthetic', 'synthetic@'+'a'*40, material),time,kind,'official_repo','S1')
            rows.append(revise(c,None,NOW,'synthetic'))
    for family,subject,material,facts in [
        ('spec_release',{'repo':SPEC,'version':'2020-01-01'},
         {'version':'2020-01-01','tag':'v2020-01-01','tag_commit':'a'*40,'branch_head':'b'*40,'published_at':'2020-01-01T00:00:00Z','amended':True},
         {'tagged':True,'release_published':True,'amended':True,'artifact_republished':False,'deleted':{'tag':False,'branch':False}}),
        ('sdk_tag',{'repo':SPEC.replace('/ucp','/python-sdk'),'tag':'v1.0.0'},
         {'tag':'v1.0.0','scheme':'semver','tag_commit':'c'*40}, {'tagged':True,'release_published':False}),
        ('registry_version',{'registry':'npm','package':'@ucp-js/sdk','version':'1.0.0'},
         {'version':'1.0.0','published_at':'2020-01-02T00:00:00Z','dist_tags':['latest']},
         {'package_published':True,'deleted':False,'yanked':False}),
    ]:
        c=candidate(family,subject,material,facts,evidence('https://example.invalid/synthetic','synthetic@'+'a'*40,material),
                    material.get('published_at',NOW),'published' if material.get('published_at') else 'observed','official_repo','S1')
        rows.append(revise(c,None,NOW,'synthetic'))
    return rows


def rendered():
    rows=synthetic_records()
    return render(rows,{}, {},seed(rows,'a'*40,NOW,PERIOD),draft=True)


def test_history_golden_and_byte_stability():
    md,js=rendered()
    assert md==GOLDEN.read_text()
    assert (md,js)==rendered()


def test_all_discovery_tables_show_event_and_observation_separately():
    md,js=rendered()
    ledger={r['citation']:r for r in json.loads(js)['source_ledger']}
    count=0
    for block in md.split('## ')[1:]:
        lines=[l for l in block.splitlines() if l.startswith('|')]
        if not lines or 'First seen' not in lines[0]: continue
        count+=1
        columns=[v.strip() for v in lines[0].split('|')[1:-1]]
        assert 'Event time (kind)' in columns
        order=[]
        for line in lines[2:]:
            values=[v.strip() for v in line.split('|')[1:-1]]
            row=ledger[values[-1].strip('[]')]
            kind='observed, not published' if row['event_time_kind']=='observed' else row['event_time_kind']
            assert values[columns.index('Event time (kind)')]==row['event_time']+' ('+kind+')'
            assert values[columns.index('First seen')]=='2020-02-10T00:00:00.000000Z'
            order.append((row['event_time'],row['key'].split('@')[0]))
        assert order==sorted(order)
    assert count==6
    notices=md.split('## Official notices')[1].split('## Governance')[0]
    assert '2020-01-01T00:00:00.000000Z (posted)' in notices
