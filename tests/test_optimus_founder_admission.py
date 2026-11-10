"""Falsify the two independent root release receipts; no green from absence or fixtures."""
from __future__ import annotations

import datetime as dt
import importlib.machinery
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
loader = importlib.machinery.SourceFileLoader('gate', str(ROOT / 'bin' / 'idp-optimus-founder-admission'))
spec = importlib.util.spec_from_loader('gate', loader)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

SHA = 'a' * 40
NOW = dt.datetime(2026, 11, 10, 7, 12, 0, tzinfo=dt.timezone.utc)


def runs():
    entry = {'instruction_id': 'GEN-0001', 'permission': 'allowed', 'permission_receipt': 'receipt-7', 'yield_tracking': 'pending'}
    base = {'schema': gate.SCHEMA, 'subject_sha': SHA, 'observed_at': '2026-11-10T07:10:00Z', 'instructions': [entry]}
    metrics = dict(base, metrics={'required_events': 2, 'observed_events': 2, 'dropped_events': 0})
    surface = dict(base, founder_surface={'live': True, 'instructions_visible': True, 'permission_visible': True,
                                         'yield_tracking_visible': True, 'event_cursor': '1030',
                                         'url': 'https://founder.example.com'})
    return [
        {'name':'optimus-metrics','head_sha':SHA,'app':{'id':11},'status':'completed','conclusion':'success',
         'completed_at':'2026-11-10T07:11:00Z','id':1,'output':{'text':json.dumps(metrics)}},
        {'name':'founder-surface-visibility','head_sha':SHA,'app':{'id':22},'status':'completed','conclusion':'success',
         'completed_at':'2026-11-10T07:11:00Z','id':2,'output':{'text':json.dumps(surface)}}]


def admit(rs):
    return gate.verdict(rs, sha=SHA, optimus_app_id=11, founder_app_id=22, now=NOW)


class OperationalReleaseProofTests(unittest.TestCase):
    def test_complete_correlation_is_only_admission_not_yield(self):
        value=admit(runs())
        self.assertEqual(value['instruction_count'], 1)
        self.assertEqual(value['state'], 'ADMITTED_TO_GREENLANE_CI_NOT_YIELD')

    def test_absent_optimus_or_founder_blocks(self):
        for i in (0,1):
            with self.subTest(i=i), self.assertRaisesRegex(ValueError, 'absent'):
                admit([x for j,x in enumerate(runs()) if j != i])

    def test_untrusted_apps_or_wrong_sha_block(self):
        for field, value in (('app',{'id':33}), ('head_sha', 'b'*40)):
            rs=runs();rs[0][field]=value
            with self.subTest(field=field), self.assertRaisesRegex(ValueError,'wrong source SHA or untrusted'):
                admit(rs)

    def test_skipped_neutral_or_failed_check_never_proves(self):
        for conclusion in ('neutral','skipped','failure',None):
            rs=runs();rs[0]['conclusion']=conclusion
            with self.subTest(conclusion=conclusion), self.assertRaisesRegex(ValueError,'not successful'):
                admit(rs)

    def test_stale_observation_and_future_timestamp_block(self):
        for at in ('2026-11-10T06:50:00Z','2026-11-10T07:40:00Z'):
            rs=runs();x=json.loads(rs[0]['output']['text']);x['observed_at']=at;rs[0]['output']['text']=json.dumps(x)
            with self.subTest(at=at), self.assertRaisesRegex(ValueError,'wrong or stale'):
                admit(rs)

    def test_newer_failure_supersedes_old_success(self):
        rs=runs();failed=dict(rs[0],id=3,conclusion='failure');rs.append(failed)
        with self.assertRaisesRegex(ValueError,'not successful'):
            admit(rs)

    def test_missing_permission_linkage_blocks(self):
        rs=runs();x=json.loads(rs[0]['output']['text']);del x['instructions'][0]['permission_receipt'];rs[0]['output']['text']=json.dumps(x)
        with self.assertRaisesRegex(ValueError,'permission receipt'):
            admit(rs)

    def test_different_instruction_or_yield_status_blocks(self):
        for field,value in (('instruction_id','GEN-0002'),('yield_tracking','verified')):
            rs=runs();x=json.loads(rs[1]['output']['text']);x['instructions'][0][field]=value;rs[1]['output']['text']=json.dumps(x)
            with self.subTest(field=field),self.assertRaisesRegex(ValueError,'disagree'):
                admit(rs)

    def test_missing_metric_coverage_blocks(self):
        for change in ({'required_events':2,'observed_events':1,'dropped_events':0},
                       {'required_events':2,'observed_events':2,'dropped_events':1},
                       {'required_events':'2','observed_events':2,'dropped_events':0}):
            rs=runs();x=json.loads(rs[0]['output']['text']);x['metrics']=change;rs[0]['output']['text']=json.dumps(x)
            with self.subTest(change=change),self.assertRaisesRegex(ValueError,'Optimus'):
                admit(rs)

    def test_fake_static_surface_or_missing_cursor_blocks(self):
        for field,value in (('live',False),('instructions_visible',False),('event_cursor',''),('yield_tracking_visible',False)):
            rs=runs();x=json.loads(rs[1]['output']['text']);x['founder_surface'][field]=value;rs[1]['output']['text']=json.dumps(x)
            with self.subTest(field=field),self.assertRaises(ValueError):
                admit(rs)

    def test_missing_check_app_issuer_configuration_blocks(self):
        with self.assertRaisesRegex(ValueError,'not configured'):
            gate.verdict(runs(),sha=SHA,optimus_app_id=0,founder_app_id=22,now=NOW)

    def test_candidate_commit_without_instruction_is_refused(self):
        class Result:
            returncode = 0
            stdout = "Claim: chidionyema/idp#7771\x00"
        with self.assertRaisesRegex(ValueError, 'no Genesis-Instruction-Id'):
            gate.candidate_instructions(SHA, run=lambda *a, **kw: Result())

    def test_telemetry_must_cover_every_candidate_instruction(self):
        with self.assertRaisesRegex(ValueError, 'different instructions'):
            gate.verdict(runs(), sha=SHA, optimus_app_id=11, founder_app_id=22, now=NOW,
                         candidate_instruction_ids={'GEN-0001', 'GEN-0002'})

    def test_candidate_history_extracts_exact_instruction_ids(self):
        class Result:
            returncode = 0
            stdout = "Subject\n\nGenesis-Instruction-Id: GEN-0001\x00"
        self.assertEqual(gate.candidate_instructions(SHA, run=lambda *a, **kw: Result()), {'GEN-0001'})

    def test_pagination_and_unreadable_checks_block(self):
        data=[{'total_count':101,'check_runs':[{'name':'x'}]*100},
              {'total_count':101,'check_runs':[{'name':'last'}]}]
        calls=[]
        result=gate.list_check_runs('chidionyema/idp',SHA,'token',fetch=lambda u:(calls.append(u) or data[len(calls)-1]))
        self.assertEqual(len(result), 101)
        self.assertEqual(len(calls), 2)
        with self.assertRaisesRegex(ValueError,'unreadable'):
            gate.list_check_runs('chidionyema/idp',SHA,'token',fetch=lambda _:{})
        with self.assertRaisesRegex(ValueError,'count is missing'):
            gate.list_check_runs('chidionyema/idp',SHA,'token',fetch=lambda _:{'check_runs':[]})

    def test_ci_success_is_bound_to_observability_job(self):
        workflow = (ROOT / '.github/workflows/ci.yml').read_text()
        self.assertIn('  operational-visibility:', workflow)
        self.assertIn('operational-visibility]', workflow)
        self.assertIn('python3 bin/idp-optimus-founder-admission', workflow)
        self.assertIn('checks: read', workflow)
        self.assertIn('ESTATE_CANDIDATE_SHA:', workflow)
        self.assertNotIn('continue-on-error: true   # Optimus', workflow)


if __name__ == '__main__':
    unittest.main()
