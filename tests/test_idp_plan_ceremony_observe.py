"""Adversarial tests; no runtime state or production effect is manufactured."""
import importlib.util
from importlib.machinery import SourceFileLoader
import json
import pathlib
import tempfile
import unittest
from datetime import datetime, timezone

SRC = pathlib.Path(__file__).with_name('idp_plan_ceremony_observe.py')
if not SRC.is_file():
    SRC = pathlib.Path(__file__).resolve().parents[1] / 'bin' / 'idp-plan-ceremony-observe'
spec = importlib.util.spec_from_loader('ceremony_observer', SourceFileLoader('ceremony_observer', str(SRC)))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def put(path, records):
    path.write_text(''.join(json.dumps(x)+'\n' for x in records), encoding='utf-8')


class Observation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        self.now = datetime(2026,11,16,4,50,tzinfo=timezone.utc)

    def read(self):
        return mod.observe(self.root, self.now)

    def test_missing_ledger_is_blind(self):
        self.assertEqual(mod.observe(self.root/'not-there', self.now)['status'], 'PARTIAL_OR_BLIND')

    def test_empty_root_is_blind(self):
        self.assertEqual(self.read()['status'], 'BLIND_NO_SESSIONS')

    def test_lifecycle_counts_are_not_operational_yield(self):
        put(self.root/'pi-1.jsonl', [
            {'at': 1,'tool':'session_start'},
            {'at': 2,'tool':'declare_plan','args':{'goal':'sensitive founder private text'}},
            {'at': 3,'tool':'add_bdd','args':{'goal_id':'g1','given':'secret'}},
            {'at': 4,'tool':'address_edgecases','args':{'goal_id':'g1'}},
            {'at': 5,'tool':'address_2nd_order_effects','args':{'goal_id':'g1'}},
            {'at': 6,'tool':'complete_goal','args':{'goal_id':'g1'}},
        ])
        out = self.read()
        self.assertEqual(out['sessions_with_completion_claims'],1)
        self.assertEqual(out['sessions_with_out_of_order_calls'],0)
        self.assertEqual(out['independently_verified_operational_yield'], None)
        self.assertNotIn('sensitive founder',json.dumps(out))
        self.assertNotIn('secret',json.dumps(out))

    def test_repeated_per_goal_calls(self):
        put(self.root/'pi-2.jsonl', [
            {'at':1,'tool':'declare_plan'},
            {'at':2,'tool':'add_bdd','args':{'goal_id':'g1'}},
            {'at':3,'tool':'add_bdd','args':{'goal_id':'g1'}},
        ])
        self.assertEqual(self.read()['sessions_with_repeated_per_goal_calls'],1)

    def test_unplanned_and_refusals(self):
        put(self.root/'observe.jsonl',[{'at':1,'command':'my very sensitive command'}])
        put(self.root/'refusals.jsonl',[{'at':1,'reason':'plan_not_declared','fatal':True,'command':'TOKEN=secret'},{'at':2,'reason':'plan_complete','fatal':False}])
        put(self.root/'intents.jsonl',[{'at':1,'session':'anonymous','intent':'plan-less'}])
        r=self.read()
        self.assertEqual(r['event_counts']['unplanned_records'],1)
        self.assertEqual(r['event_counts']['refusal_plan_not_declared'],1)
        self.assertEqual(r['event_counts']['nonfatal_refusals'],1)
        self.assertEqual(r['event_counts']['anonymous_intents'],1)
        self.assertNotIn('TOKEN=secret',json.dumps(r))

    def test_malformed_json_is_partial_not_pass(self):
        (self.root/'pi-3.jsonl').write_text('{ garbage}\n')
        self.assertEqual(self.read()['status'], 'PARTIAL_OR_BLIND')

    def test_out_of_order_edgecase_flagged(self):
        put(self.root/'pi-4.jsonl', [{'at':1,'tool':'declare_plan'},{'at':2,'tool':'address_edgecases','args':{'goal_id':'g1'}}])
        self.assertEqual(self.read()['sessions_with_out_of_order_calls'],1)

    def test_plan_event_span_not_mislabeled_cost(self):
        put(self.root/'pi-5.jsonl',[{'at':1,'tool':'declare_plan'},{'at':101,'tool':'complete_goal','args':{'goal_id':'g1'}}])
        r=self.read()
        self.assertEqual(r['session_plan_event_span_seconds_sum'], 100)
        self.assertIsNone(r['ceremony_cost'])
        self.assertIsNone(r['tokens_spent_on_ceremony'])

    def test_symlink_ledger_ignored(self):
        target=self.root/'outside'
        put(target,[{'at':1,'tool':'declare_plan'}])
        (self.root/'linked.jsonl').symlink_to(target)
        self.assertEqual(self.read()['status'],'PARTIAL_OR_BLIND')

    def test_session_markers_not_counted_as_plans(self):
        put(self.root/'pi-6.jsonl',[{'at':1,'tool':'session_start'}])
        self.assertEqual(self.read()['sessions_with_plan_declaration'],0)

    def test_oversized_ledger_is_partial(self):
        (self.root/'huge.jsonl').write_bytes(b' '*(mod.MAX_BYTES+1))
        self.assertEqual(self.read()['status'],'PARTIAL_OR_BLIND')

    def test_session_id_not_emitted(self):
        put(self.root/'sensitive-session-ABC.jsonl',[{'at':1,'tool':'declare_plan'}])
        self.assertNotIn('sensitive-session-ABC',json.dumps(self.read()))


if __name__ == '__main__':
    unittest.main()
