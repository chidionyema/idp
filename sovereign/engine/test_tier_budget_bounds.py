from fractions import Fraction
import pytest
from sovereign.engine.tier_budget import resolve_candidate_volume, TierBudgetError
LADDER={"rungs":[{"name":"local","hardware_class":"local"},{"name":"metal","hardware_class":"apple_silicon"},{"name":"router","hardware_class":"router"},{"name":"gpu","hardware_class":"gpu"}]}
def decide(tier='router', time=60, step=60, usd=1, pct=100, cost=1):
    return resolve_candidate_volume(tier,time_box_s=time,step_s=step,budget_usd=usd,budget_pct=pct,cost_per_candidate_usd=cost,ladder=LADDER).candidate_volume
@pytest.mark.parametrize('tier',['router','gpu'])
@pytest.mark.parametrize('usd,pct,cost',[(0,100,1),(1,0,1),(0.01,100,0.02),(1,10,0.11),(1,100,1),(0.3,100,0.1),(0.3,50,0.05)])
def test_metered_never_exceeds_budget(tier,usd,pct,cost):
    funds=Fraction(str(usd))*Fraction(pct,100)
    n=decide(tier,usd=usd,pct=pct,cost=cost)
    assert n == funds//Fraction(str(cost))
    assert n*Fraction(str(cost)) <= funds
@pytest.mark.parametrize('tier',['local','metal'])
@pytest.mark.parametrize('time,step',[(0,60),(59,60),(60,60),(120,60),(0.3,0.1),(86400,600)])
def test_flat_rate_never_exceeds_time_box(tier,time,step):
    n=decide(tier,time=time,step=step,usd=0,pct=0)
    assert n==Fraction(str(time))//Fraction(str(step))
    assert n*Fraction(str(step))<=Fraction(str(time))
@pytest.mark.parametrize('field,value',[('usd',-1),('usd',float('nan')),('usd',float('inf')),('pct',-1),('pct',101),('pct',float('nan')),('cost',0),('cost',-1),('cost',float('inf')),('cost',float('nan')),('cost',True)])
def test_invalid_metered_terms_refused(field,value):
    with pytest.raises(TierBudgetError): decide(**{field:value})
@pytest.mark.parametrize('field,value',[('time',-1),('time',float('inf')),('time',float('nan')),('step',0),('step',-1),('step',float('nan')),('step',float('inf')),('step',True)])
def test_invalid_flat_terms_refused(field,value):
    with pytest.raises(TierBudgetError): decide('local',**{field:value})
def test_flat_ignores_dollar_terms():
    assert decide('local',time=120,step=60,usd=float('nan'),pct=-99,cost=0)==2
def test_metered_ignores_time_terms():
    assert decide('router',time=-1,step=float('nan'),usd=4,pct=50,cost=1)==2
