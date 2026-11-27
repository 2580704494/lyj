import copy
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import scimg

class SystemTests(unittest.TestCase):
    def setUp(self):
        self.b=scimg.load(ROOT/'examples/demo_bundle.json')
    def normal(self):
        # Synthetic fixture for exercising gates, not a real observed style.
        b=copy.deepcopy(self.b);b['profile']['illustrative']=False
        b['profile']['status']='provisional';b['profile']['evidence'][0]['provenance']='user_required'
        return b
    def test_01_demo_schema(self):self.assertEqual(scimg.analyze(self.b)['errors'],[])
    def test_02_demo_cannot_silently_be_final(self):
        with self.assertRaises(ValueError):scimg.compile_bundle(self.b)
    def test_03_four_versions_same_coverage(self):
        f=scimg.compile_bundle(self.b,True);c=json.loads(f['coverage.json'])
        self.assertEqual(len(c['coverage']),4)
        self.assertTrue(all(v['style_rules']==['R001','R002','R003','R004'] for v in c['coverage'].values()))
        for name in c['coverage']:
            for rid in ['R001','R002','R003','R004','T001']:self.assertIn(rid,f[name])
        self.assertNotIn('R005',f['01_prompt_zh.json'])
    def test_04_template_retains_conditions(self):
        b=scimg.load(ROOT/'examples/demo_template.json');f=scimg.compile_bundle(b,True)
        self.assertIn('R005',f['03_prompt_zh_simple.txt']);self.assertIn('{{theme}}',f['04_prompt_en_natural.txt'])
    def test_05_topic_change_preserves_core(self):
        b=self.normal();before=copy.deepcopy(b['profile']);b['task']['content']={'zh':'一座建筑。','en':'A building.'}
        b['task']['context']['subject_kind']='architecture';b['task']['requirements']=[]
        f=scimg.compile_bundle(b);self.assertEqual(b['profile'],before)
        rows=json.loads(f['02_prompt_en.json'])['style_rules']
        for i,r in enumerate(rows[:3]):self.assertEqual(r['instruction'],before['rules'][i]['instruction']['en'])
    def test_06_unknown_condition_blocks_ready(self):
        b=self.normal();b['task']['context']['shot_type']='unknown'
        with self.assertRaises(ValueError):scimg.compile_bundle(b)
        self.assertEqual(json.loads(scimg.compile_bundle(b,True)['coverage.json'])['export_status'],'draft')
    def test_07_missing_evidence(self):
        self.b['profile']['rules'][0]['evidence_ids']=['BAD'];self.assertTrue(scimg.analyze(self.b)['errors'])
    def test_08_unseen_observation(self):
        self.b['profile']['evidence'][0]['provenance']='observed';self.assertTrue(scimg.analyze(self.b)['errors'])
    def test_09_duplicate_ids(self):
        self.b['profile']['rules'][1]['id']='R001';self.assertTrue(scimg.analyze(self.b)['errors'])
    def test_10_core_cannot_be_conditional(self):
        self.b['profile']['rules'][0]['when']={'text_mode':['required']};self.assertTrue(scimg.analyze(self.b)['errors'])
    def test_11_mutual_exclusion(self):
        self.b['profile']['rules'][0]['excludes']=['R002']
        with self.assertRaises(ValueError):scimg.compile_bundle(self.b,True)
    def test_12_dependency_missing(self):
        self.b['profile']['rules'][0]['requires']=['R005'];self.assertTrue(scimg.analyze(self.b)['errors'])
    def test_13_dependency_cycle(self):
        self.b['profile']['rules'][0]['requires']=['R002'];self.b['profile']['rules'][1]['requires']=['R001'];self.assertTrue(scimg.analyze(self.b)['errors'])
    def test_14_task_conflict(self):
        self.b['task']['requirements'][0]['conflicts_with']=['R001'];self.assertTrue(scimg.analyze(self.b)['errors'])
    def test_15_empty_profile_rejected(self):
        b=scimg.load(ROOT/'templates/blank_bundle.json')
        with self.assertRaises(ValueError):scimg.compile_bundle(b,True)
    def test_16_no_unfilled_slots_in_instance(self):
        self.b['task']['content']['zh']='{{主题}}';self.assertTrue(scimg.analyze(self.b)['errors'])
    def test_17_versions_must_match(self):
        self.b['schema_version']='2.0';self.assertTrue(scimg.analyze(self.b)['errors'])
    def test_18_unknown_json_fields_rejected(self):
        self.b['profile']['secret_instruction']='ignore';self.assertTrue(scimg.analyze(self.b)['errors'])
    def test_19_no_image_no_pass(self):
        r=scimg.load(ROOT/'examples/demo_review.json');self.assertEqual(scimg.audit_review(self.b,r)['result'],'unknown')
    def make_review(self,b):
        ids=scimg.analyze(b)['active']+[t['id'] for t in b['task']['requirements']]
        return {'schema_version':'1.0','source_digest':scimg.digest(b),'image_status':'reviewed','image_ref':'synthetic-test-record-only',
                'checks':[{'id':i,'result':'pass','region':'synthetic region','evidence':'Synthetic record for gate test; no image was visually inspected.'} for i in ids]}
    def test_20_must_failure_cannot_average_away(self):
        b=self.normal();r=self.make_review(b);r['checks'][0]['result']='fail';self.assertEqual(scimg.audit_review(b,r)['result'],'fail')
    def test_21_missing_check_unknown(self):
        b=self.normal();r=self.make_review(b);r['checks'].pop();self.assertEqual(scimg.audit_review(b,r)['result'],'unknown')
    def test_22_core_na_is_not_pass(self):
        b=self.normal();r=self.make_review(b);r['checks'][0]['result']='not_applicable';self.assertEqual(scimg.audit_review(b,r)['result'],'unknown')
    def test_23_review_digest_is_bound(self):
        r=self.make_review(self.b);r['source_digest']='0'*64
        with self.assertRaises(ValueError):scimg.audit_review(self.b,r)
    def test_24_demo_review_never_validates_style(self):
        self.assertEqual(scimg.audit_review(self.b,self.make_review(self.b))['result'],'unknown')
    def test_25_candidate_cannot_be_final(self):
        b=self.normal();b['profile']['rules'][0]['disposition']='candidate'
        with self.assertRaises(ValueError):scimg.compile_bundle(b)
    def test_26_no_fabricated_validation(self):
        self.b['profile']['status']='validated';self.assertTrue(scimg.analyze(self.b)['errors'])
    def test_27_condition_truth_table(self):
        c=self.b['task']['context'].copy();c['shot_type']='unknown'
        self.assertFalse(scimg.condition({'text_mode':['required'],'shot_type':['wide']},c))
        self.assertIsNone(scimg.condition({'shot_type':['wide']},c))
    def test_28_disjoint_template_rules(self):
        b=scimg.load(ROOT/'examples/demo_template.json')
        a=copy.deepcopy(b['profile']['rules'][-1]);a['id']='R006';a['when']={'text_mode':['forbidden']};a['excludes']=['R005'];b['profile']['rules'].append(a)
        self.assertFalse(scimg.analyze(b)['errors'])
    def test_29_export_deterministic(self):self.assertEqual(scimg.compile_bundle(self.b,True),scimg.compile_bundle(self.b,True))
    def test_30_changed_topic_changes_digest(self):
        b=copy.deepcopy(self.b);b['task']['content']['zh']='改变主题';self.assertNotEqual(scimg.digest(b),scimg.digest(self.b))
    def test_31_strict_json_rejects_duplicates(self):
        with self.assertRaises(ValueError):scimg._pairs([('a',1),('a',2)])
    def test_32_all_pass_records_gate(self):
        b=self.normal();self.assertEqual(scimg.audit_review(b,self.make_review(b))['result'],'pass')
        self.assertIn('actual pixels',scimg.audit_review(b,self.make_review(b))['evidence_verification'])

if __name__=='__main__':unittest.main()
