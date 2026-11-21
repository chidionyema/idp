import copy
import json
import pathlib
import unittest
from recovery_model import (evaluate_probe, unlocked, closure, Capability, feasibility,
                            custody_transition, run_model)

CONFIG = json.loads((pathlib.Path(__file__).parent / 'example_config.json').read_text())


class TestRecoveryModel(unittest.TestCase):
    def test_one_step_value_of_information_can_beat_guessing(self):
        result = evaluate_probe(CONFIG['decision'])
        self.assertEqual(result['choice'], 'PROBE')
        self.assertGreater(result['probe']['net_expected_value'], result['direct']['expected_net'])
        self.assertAlmostEqual(sum(x['probability'] for x in result['probe']['observations']), 1.0)
        for row in result['probe']['observations']:
            self.assertAlmostEqual(sum(row['posterior'].values()), 1.0)

    def test_never_forces_a_negative_value_guess(self):
        model = copy.deepcopy(CONFIG['decision'])
        model['repair_costs'] = {k: 100.0 for k in model['repair_costs']}
        model['probe_cost'] = 50.0
        self.assertEqual(evaluate_probe(model)['choice'], 'ABSTAIN')

    def test_zero_signal_expensive_probe_is_rejected(self):
        model = copy.deepcopy(CONFIG['decision'])
        model['probe_accuracy'] = 1 / len(model['fault_priors'])
        model['probe_cost'] = 1
        self.assertEqual(evaluate_probe(model)['choice'], 'DIRECT_REPAIR')

    def test_unbounded_cost_is_rejected(self):
        model = copy.deepcopy(CONFIG['decision'])
        model['repair_costs']['receiver_route'] = float('nan')
        with self.assertRaises(ValueError):
            evaluate_probe(model)

    def test_dependency_closure_is_not_wishful_thinking(self):
        rules = [Capability('capture', frozenset({'ai_studio','intake'}),1),
                 Capability('custody', frozenset({'capture','git_authority'}),2)]
        self.assertEqual(closure({'ai_studio'}, rules), {'ai_studio'})
        self.assertEqual(unlocked({'ai_studio'}, {'intake'}, rules)['gained'], ['capture'])
        self.assertEqual(unlocked({'ai_studio','git_authority'}, {'intake'}, rules)['gained'], ['capture','custody'])

    def test_effect_never_authorised_by_selection(self):
        c = CONFIG['candidate_actions']
        self.assertTrue(feasibility(c[0])[0])
        self.assertFalse(feasibility(c[1])[0])
        self.assertFalse(feasibility(c[2])[0])

    def test_zero_worker_cannot_erase_obligation(self):
        s={'workers':1,'open_obligations':2,'checkpoint_epoch':0,'independent_receipt':False}
        lost=custody_transition(s,'WORKER_LOST')
        self.assertEqual(lost['open_obligations'],2)
        with self.assertRaises(ValueError):
            custody_transition(lost,'CHECKPOINT')
        with self.assertRaises(ValueError):
            custody_transition(lost,'VERIFY_AND_SETTLE')
        restored=custody_transition(lost,'WORKER_RETURNED')
        self.assertEqual(restored['workers'],1)
        self.assertEqual(restored['open_obligations'],2)

    def test_no_free_agents_unlocked_without_authentication(self):
        out = run_model(CONFIG)
        self.assertNotIn('free_web_delivery', out['capability_effect']['repair_intake']['gained'])
        self.assertIn('recovery', out['capability_effect']['repair_intake']['gained'])
        self.assertNotIn('custody', out['capability_effect']['repair_intake_but_no_git_authority']['gained'])

if __name__ == '__main__':
    unittest.main()