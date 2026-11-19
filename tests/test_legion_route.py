from importlib.machinery import SourceFileLoader
import importlib.util
from pathlib import Path
import pytest

loader = SourceFileLoader('legion_route', str(Path(__file__).resolve().parents[1] / 'bin' / 'legion-route'))
spec = importlib.util.spec_from_loader(loader.name, loader)
mod = importlib.util.module_from_spec(spec)
loader.exec_module(mod)

def routes(tmp_path):
    for p in ['newvendor','other']:
        (tmp_path/f'{p}.toml').write_text(f'id="{p}"\ndialect="openai"\nbase_url="https://{p}.example/v1"\n[auth]\nkey_env="{p.upper()}_KEY"\n[[models]]\nid="v1"\ncontext_window=100000\n')
    return mod.registry(tmp_path)

def offer(p='newvendor', **changes):
    return dict(dict(provider=p, model='v1', offer_id=p, account_id=p+'-account', failure_domain=p, mission_id='M1', credential_ref=p.upper()+'_KEY', state='AVAILABLE', adapter='pi', observed_at=99, expires_at=200, capabilities=['code'], available_tokens=20000, reserved_cost_usd=0.2, success_rate=0.9), **changes)

def choose(r,o,f=(),**kw):
    return mod.select(r,o,f,**dict(dict(mission_id='M1',capabilities=['code'],tokens=10000,budget=1,now=100),**kw))

def test_new_provider_without_defaults(tmp_path):
    assert choose(routes(tmp_path),[offer()])['provider']=='newvendor'

def test_no_capacity_is_not_success(tmp_path):
    with pytest.raises(mod.NoRoute): choose(routes(tmp_path),[])

@pytest.mark.parametrize('change',[dict(observed_at=-100),dict(observed_at=101),dict(expires_at=100),dict(available_tokens=1),dict(reserved_cost_usd=2),dict(success_rate=float('nan')),dict(mission_id='M2'),dict(credential_ref='OTHER_KEY'),dict(capabilities=[]),dict(state='UNKNOWN'),dict(adapter='wrong')])
def test_refuse_invalid_offer(tmp_path,change):
    with pytest.raises(mod.NoRoute): choose(routes(tmp_path),[offer(**change)])

def test_rate_limit_survives_new_task(tmp_path):
    f=[dict(provider='newvendor',account_id='newvendor-account',**{'class':'CAPACITY'},observed_at=98,retry_not_before=130)]
    assert choose(routes(tmp_path),[offer(),offer('other')],f)['provider']=='other'

def test_expired_cooldown_does_not_revive_old_offer(tmp_path):
    f=[dict(provider='newvendor',account_id='newvendor-account',**{'class':'CAPACITY'},observed_at=99,retry_not_before=100)]
    with pytest.raises(mod.NoRoute): choose(routes(tmp_path),[offer()],f)
    assert choose(routes(tmp_path),[offer(observed_at=100)],f)['provider']=='newvendor'

def test_fail_closed_unknown_cooldown(tmp_path):
    f=[dict(provider='newvendor',account_id='newvendor-account',**{'class':'AUTHENTICATION'},observed_at=80)]
    with pytest.raises(mod.NoRoute): choose(routes(tmp_path),[offer()],f)

def test_excluded_failure_domain_and_denied_provider(tmp_path):
    with pytest.raises(mod.NoRoute): choose(routes(tmp_path),[offer(),offer('other')],denied=['other'],excluded_domains=['newvendor'])

def test_duplicate_offer_refused(tmp_path):
    with pytest.raises(ValueError,match='duplicate'): choose(routes(tmp_path),[offer(),offer()])

def test_quality_then_cost_deterministic(tmp_path):
    assert choose(routes(tmp_path),[offer(),offer('other',reserved_cost_usd=0.1)])['provider']=='other'
    assert choose(routes(tmp_path),[offer(),offer('other',success_rate=0.8,reserved_cost_usd=0)])['provider']=='newvendor'
