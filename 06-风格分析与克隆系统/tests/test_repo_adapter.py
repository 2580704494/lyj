import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import repo_adapter
import scimg


class RepositoryHandoffTests(unittest.TestCase):
    def setUp(self):
        self.bundle = scimg.load(ROOT / 'examples/demo_bundle.json')
        self.handoff = scimg.load(ROOT / 'examples/repo_handoff.json')
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        for module in self.handoff['modules']:
            path = self.repo / module['source']
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('Synthetic source for unit test', encoding='utf-8')

    def merge(self):
        return repo_adapter.merge(self.handoff, self.bundle, self.repo)

    def test_profile_preserved_and_old_subject_removed(self):
        original = copy.deepcopy(self.bundle)
        result, trace = self.merge()
        self.assertEqual(result['profile'], original['profile'])
        self.assertEqual(self.bundle, original)
        self.assertNotIn('T001', [r['id'] for r in result['task']['requirements']])
        self.assertNotIn('fox', result['task']['content']['en'])
        self.assertEqual(trace['output_bundle_digest'], scimg.digest(result))

    def test_every_constraint_reaches_all_four_outputs(self):
        result, _ = self.merge()
        files = scimg.compile_bundle(result, draft=True)
        self.assertEqual(len([n for n in files if n != 'coverage.json']), 4)
        for name, content in files.items():
            for constraint in self.handoff['constraints']:
                self.assertIn(constraint['id'], content, name)
            if name != 'coverage.json':
                self.assertNotIn('red fox', content)
                self.assertNotIn('红狐狸', content)

    def test_explicit_active_style_conflict_blocks(self):
        self.handoff['constraints'][0]['conflicts_with'] = ['R001']
        with self.assertRaisesRegex(ValueError, 'conflicts with active style'):
            self.merge()

    def test_unknown_conflict_target_blocks(self):
        self.handoff['constraints'][0]['conflicts_with'] = ['R999']
        with self.assertRaisesRegex(ValueError, 'unknown conflict target'):
            self.merge()

    def test_duplicate_constraint_id_blocks(self):
        self.handoff['constraints'][1]['id'] = self.handoff['constraints'][0]['id']
        with self.assertRaisesRegex(ValueError, 'duplicate IDs'):
            self.merge()

    def test_wrong_module_path_blocks(self):
        self.handoff['constraints'][0]['source'] = self.handoff['modules'][1]['source']
        with self.assertRaisesRegex(ValueError, 'Invalid source path'):
            self.merge()

    def test_missing_source_blocks(self):
        self.handoff['constraints'][0]['source'] = '01-信息图形数据逻辑/missing.md'
        with self.assertRaisesRegex(ValueError, 'source missing'):
            self.merge()

    def test_path_escape_blocks(self):
        self.handoff['constraints'][0]['source'] = '01-信息图形数据逻辑/../../outside.md'
        with self.assertRaisesRegex(ValueError, 'Invalid source path'):
            self.merge()

    def test_undeclared_module_blocks(self):
        self.handoff['modules'] = self.handoff['modules'][1:]
        with self.assertRaisesRegex(ValueError, 'undeclared module'):
            self.merge()

    def test_missing_translation_blocks(self):
        del self.handoff['constraints'][0]['instruction']['en']
        with self.assertRaisesRegex(ValueError, 'missing'):
            self.merge()

    def test_unresolved_carried_into_compiler(self):
        self.handoff['unresolved'].append('CHECK-DATA-SOURCE')
        result, trace = self.merge()
        self.assertIn('CHECK-DATA-SOURCE', result['task']['unresolved'])
        self.assertIn('CHECK-DATA-SOURCE', trace['pending'])
        with self.assertRaises(ValueError):
            scimg.compile_bundle(result)

    def test_existing_output_is_not_overwritten(self):
        result, trace = self.merge()
        output = self.repo / 'output'
        repo_adapter.write_output(output, self.handoff, result, trace)
        before = (output / 'bundle.json').read_bytes()
        with self.assertRaisesRegex(ValueError, 'new or empty'):
            repo_adapter.write_output(output, self.handoff, result, trace)
        self.assertEqual((output / 'bundle.json').read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
