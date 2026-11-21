"""Contract tests for the shared, non-authorising Meridian decision reflex."""
import sys
import math
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULES = ROOT / 'platform' / 'estate' / 'governance'
if str(MODULES) not in sys.path:
    sys.path.insert(0, str(MODULES))
from founder_method import assess, decide
from decision_reflex import STAGES, seed, select, review


def candidate(name, mode='PROBE', **overrides):
    item = {
        'id': name, 'mode': mode, 'authority':'VERIFIED','budget':'VERIFIED',
        'custody':'UNKNOWN','capacity':'UNKNOWN','verifier':'UNKNOWN',
        'recoverable':'UNKNOWN','evidence':'UNKNOWN','cost':1,'risk':0,
        'unlocks':[],'learns':['deployment-state']
    }
    item.update(overrides)
    return item


class DecisionReflexContract(unittest.TestCase):
    def test_every_stage_has_usable_reflex(self):
        self.assertGreaterEqual(len(STAGES), 13)
        for stage in STAGES:
            self.assertEqual(seed(stage)['stage'],stage)
            self.assertEqual(len(seed(stage)['required_evidence']), 2)
            self.assertIn('QUAD/Greenlane',seed(stage)['effect_authority'])

    def test_zero_capacity_prefers_read_only_probe(self):
        action = candidate('unverified-worker','EFFECT')
        probe = candidate('inspect-source')
        verdict = select({'instruction_id':'task-1','candidates':[action,probe]})
        self.assertEqual(verdict['decision'],'SELECTED_FOR_PROBE')
        self.assertEqual(verdict['selected'],'inspect-source')

    def test_shared_capacity_outweighs_single_fix_where_dominance_is_proven(self):
        good = candidate('shared','EFFECT',cost=1,risk=1,
            unlocks=['custody','handoff'],learns=['cause'],
            custody='VERIFIED',capacity='VERIFIED',verifier='VERIFIED',
            recoverable='VERIFIED',evidence='VERIFIED')
        weak = dict(good,id='single',cost=2,unlocks=['custody'])
        verdict=select({'instruction_id':'task-2','candidates':[weak,good]})
        self.assertEqual(verdict['selected'],'shared')
        self.assertEqual(verdict['decision'],'PROPOSED_EFFECT_NOT_AUTHORISED')

    def test_model_verification_claim_does_not_authorise_effect(self):
        effect = candidate('merge','EFFECT', custody='VERIFIED',capacity='VERIFIED',
            verifier='VERIFIED',recoverable='VERIFIED',evidence='VERIFIED')
        self.assertNotEqual(select({'instruction_id':'task-3','candidates':[effect]})['decision'],
                            'SELECTED_FOR_EXECUTION')

    def test_unknown_authority_refuses(self):
        effect=candidate('unauthorized','EFFECT',authority='UNKNOWN')
        verdict=select({'instruction_id':'task-4','candidates':[effect]})
        self.assertEqual(verdict['decision'],'REFUSED')

    def test_unapproved_budget_refuses(self):
        probe = candidate('spend',budget='UNKNOWN')
        self.assertEqual(select({'instruction_id':'task-5','candidates':[probe]})['decision'],'REFUSED')

    def test_same_failure_same_action_prevented(self):
        e={'instruction_id':'task-6','failure_fingerprint':'groq-413',
            'candidates':[candidate('retry-groq')],
            'falsified':[{'candidate_id':'retry-groq','fingerprint':'groq-413',
                          'evidence_ref':'run:4487'}]}
        self.assertEqual(select(e)['held_against_recurrence'],['retry-groq'])
        self.assertEqual(select(e)['decision'],'REFUSED')
        e['failure_fingerprint']='different'
        self.assertEqual(select(e)['decision'],'SELECTED_FOR_PROBE')

    def test_misclassified_write_as_probe_is_refused(self):
        probe=candidate('fake-probe',external_effect=True)
        self.assertEqual(select({'instruction_id':'task-7','candidates':[probe]})['decision'],'REFUSED')

    def test_review_requires_independent_evidence(self):
        obj={'instruction_id':'task-8','decision_sha256':'abc',
             'predicted':['worker-online'],'observed':['worker-online'],
             'independent_receipt':''}
        self.assertEqual(review(obj)['verdict'],'UNVERIFIED')
        obj['independent_receipt']='claimed-proof'
        self.assertEqual(review(obj)['verdict'],
            'OBSERVED_MATCH_PENDING_RECEIPT_AUTHENTICATION')
        obj['observed']=[]
        self.assertEqual(review(obj)['verdict'],'PREDICTION_FALSIFIED')

    def test_no_mission_identity_is_refused(self):
        with self.assertRaisesRegex(ValueError,'instruction_id'):
            select({'candidates':[candidate('p')]})

    def test_nonfinite_cost_not_accepted(self):
        for value in (math.nan, math.inf, -1):
            with self.assertRaises(ValueError):
                assess(candidate('p',cost=value))

    def test_incomparable_options_remain_unresolved(self):
        v=select({'instruction_id':'task-9','candidates':[
            candidate('cheap-high-risk',cost=1,risk=5),
            candidate('expensive-low-risk',cost=5,risk=1)]})
        self.assertEqual(v['decision'],'UNRESOLVED')


if __name__=='__main__':unittest.main()