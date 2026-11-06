from pathlib import Path
import re
import yaml

ROOT=Path(__file__).parents[1]

def workflows():
    return [*ROOT.glob('.github/workflows/*.yml'),*ROOT.glob('templates/data-repo/.github/workflows/*.yml')]

def test_workflow_static_contract():
    paths=workflows(); assert len(paths)==5
    for path in paths:
        text=path.read_text(); value=yaml.safe_load(text)
        assert value['permissions']=={}
        assert 'pull_request_target' not in text
        assert '\u2014' not in text
        if path.name!='export.yml': assert 'UCP_PULSE_EXPORT_TOKEN' not in text
        for job in value['jobs'].values():
            assert job['runs-on']=='ubuntu-latest'
            assert job.get('permissions')
            for step in job['steps']:
                if 'uses' in step: assert re.fullmatch(r'[\w/-]+@[0-9a-f]{40}',step['uses'])
                if 'run' in step: assert '${{' not in step['run']
    private={p.stem:yaml.safe_load(p.read_text()) for p in paths if 'templates' in p.parts}
    assert private['collect']['concurrency']==private['draft']['concurrency']=={'group':'ucp-pulse-state','cancel-in-progress':False}
    assert private['collect']['jobs']['collect']['permissions']=={'contents':'write'}
    assert private['verify']['jobs']['verify']['permissions']=={'contents':'read'}
    assert 'pull-requests' not in yaml.safe_load((ROOT/'.github/workflows/ci.yml').read_text())['jobs']['verify']['permissions']


def test_collect_initial_bound_is_configuration_not_workflow_literal():
    template=ROOT/'templates/data-repo'
    workflow=(template/'.github/workflows/collect.yml').read_text()
    assert 'smoke-collect --data data' in workflow
    assert '--start' not in workflow and '2026-01-11' not in workflow
    assert yaml.safe_load((template/'config/collection.yaml').read_text())=={'history_start':'2026-01-11T00:00:00Z'}
