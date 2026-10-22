"""Check the separate app trial's exact preset boundary and local-only CLI."""
import copy
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('app_trial', ROOT / 'tools/app_command_trial_preset.py')
preset = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preset)


def leaves(value, path=()):
    if type(value) is dict and value:
        for key, item in value.items():
            yield from leaves(item, (*path, key))
    elif type(value) is list and value:
        for index, item in enumerate(value):
            yield from leaves(item, (*path, index))
    else:
        yield path, value


def replace(document, path, value):
    target = document
    for part in path[:-1]:
        target = target[part]
    target[path[-1]] = value


class AppTrialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = preset.load_source(ROOT / preset.SOURCE)
        cls.candidate, cls.changes = preset.transform(cls.source)
        cls.import_candidate, cls.encodings = preset.vial075_import_document(cls.candidate)

    def test_exact_121_unique_changes_and_explicit_row_swap(self):
        expected = {}
        for layer in (6, 7, 8, 9, 10, 13):
            for first, second in ((0, 2), (4, 6)):
                for column in (1, 2, 3, 4, 5):
                    expected[layer, first, column] = self.source['layout'][layer][second][column]
                    expected[layer, second, column] = self.source['layout'][layer][first][column]
        expected.update({
            (7, 0, 1): 'LALT(LGUI(KC_LEFT))', (7, 4, 1): 'LALT(LGUI(KC_LEFT))',
            (7, 0, 2): 'LALT(LGUI(KC_RIGHT))', (7, 4, 2): 'LALT(LGUI(KC_RIGHT))',
            (7, 0, 6): 'LALT(LGUI(KC_SPACE))',
        })
        actual = {}
        for layer in range(16):
            for row in range(8):
                for column in range(7):
                    old = self.source['layout'][layer][row][column]
                    new = self.candidate['layout'][layer][row][column]
                    if old != new:
                        actual[layer, row, column] = new
        self.assertEqual(actual, expected)
        self.assertEqual(len(actual), 121)
        paths = [tuple(map(int, re.findall(r'\[(\d+)\]', item['path']))) for item in self.changes]
        self.assertEqual(paths, sorted(expected))
        self.assertEqual(len(set(paths)), len(paths))
        for item, (layer, row, column) in zip(self.changes, paths):
            self.assertEqual(item['before'], self.source['layout'][layer][row][column])
            self.assertEqual(item['after'], actual[layer, row, column])

    def test_all_other_cells_and_non_layout_fields_preserved(self):
        for field in set(self.source) - {'layout'}:
            self.assertEqual(preset.dump(self.source[field]), preset.dump(self.candidate[field]), field)
        for layer in (0, 1, 2, 3, 4, 5, 11, 12, 14, 15):
            self.assertEqual(self.source['layout'][layer], self.candidate['layout'][layer], layer)
        protected = ((1, 0), (1, 1), (1, 2), (1, 3), (1, 4), (1, 6), (2, 0),
                     (5, 1), (5, 2), (5, 3), (5, 4), (5, 6), (6, 0),
                     (3, 3), (7, 3), (3, 4), (7, 4), (3, 5), (7, 5))
        for layer in range(16):
            for row, column in protected:
                self.assertEqual(self.source['layout'][layer][row][column],
                                 self.candidate['layout'][layer][row][column], (layer, row, column))
        self.assertEqual(self.candidate['layout'][0][3][5], 'KC_SPACE')
        self.assertEqual(self.candidate['layout'][8][0][6], 'LCTL(LALT(LSFT(KC_D)))')
        self.assertEqual(self.candidate['layout'][7][4][6], 'KC_NO')
        for layer in (6, 7, 8, 9, 10, 13):
            for row in (0, 4):
                self.assertEqual(self.candidate['layout'][layer][row][5], 'USER00')
                self.assertEqual(self.candidate['layout'][layer][row + 2][5], 'LGUI(KC_F)')
            for row in (2, 6):
                self.assertEqual(self.candidate['layout'][layer][row][1:5],
                                 ['LGUI(KC_Z)', 'LGUI(KC_X)', 'LGUI(KC_C)', 'LGUI(KC_V)'])

    def test_import_variant_has_exactly_eight_representation_changes(self):
        expected = [{'path': f'layout[15][{row}][{column}]',
                     'before': f'USER{16 + column:02}', 'after': f'0x7e{16 + column:02x}'}
                    for row in (2, 6) for column in range(4)]
        self.assertEqual(self.encodings, expected)
        restored = copy.deepcopy(self.import_candidate)
        for item in self.encodings:
            layer, row, column = map(int, re.findall(r'\[(\d+)\]', item['path']))
            restored['layout'][layer][row][column] = item['before']
        self.assertEqual(restored, self.candidate)
        self.assertEqual(preset.current_status(self.import_candidate, self.source, self.candidate), 'candidate')
        source_import, _ = preset.vial075_import_document(self.source)
        self.assertEqual(preset.current_status(source_import, self.source, self.candidate), 'source')

    def test_only_exact_legacy_source_with_all_eight_missing_picker_cells_is_recognized(self):
        legacy, changes = preset.legacy_source_document(self.source)
        self.assertEqual(len(changes), 8)
        self.assertEqual(preset.current_status(legacy, self.source, self.candidate), 'legacy-source')
        positions = [(15, row, column) for row in (2, 6) for column in range(4)]
        for count in range(1, 8):
            for partial_loss in itertools.combinations(positions, count):
                changed = copy.deepcopy(self.source)
                for layer, row, column in partial_loss:
                    changed['layout'][layer][row][column] = 'KC_NO'
                self.assertEqual(preset.current_status(changed, self.source, self.candidate), 'drift', partial_loss)
        for path, value in ((('layout', 15, 2, 4), 'KC_NO'),
                            (('layout', 0, 0, 1), 'KC_NO'), (('settings', '1'), False),
                            (('encoder_layout', 0, 0, 0), 'KC_NO'), (('extra_field',), 1)):
            changed = copy.deepcopy(legacy)
            replace(changed, path, value)
            self.assertEqual(preset.current_status(changed, self.source, self.candidate), 'drift', path)
        wrong_cell = copy.deepcopy(self.source)
        wrong_cell['layout'][15][2][4] = 'KC_NO'
        self.assertEqual(preset.current_status(wrong_cell, self.source, self.candidate), 'drift')
        lossy_trial, _ = preset.legacy_source_document(self.candidate)
        self.assertEqual(preset.current_status(lossy_trial, self.source, self.candidate), 'drift')

    def test_comparison_accepts_only_exact_observed_layout_encoder_aliases(self):
        for status, document in (('source', self.source), ('candidate', self.candidate)):
            reordered = json.loads(json.dumps(document, sort_keys=True, separators=(',', ':')))
            self.assertEqual(preset.current_status(reordered, self.source, self.candidate), status)
            for alias, exported in preset.EXPORT_ALIASES.items():
                for field in ('layout', 'encoder_layout'):
                    changed = copy.deepcopy(document)
                    for matrix in changed[field]:
                        for row in matrix:
                            for column, key in enumerate(row):
                                if key == alias:
                                    row[column] = exported
                    self.assertEqual(preset.current_status(changed, self.source, self.candidate), status)
        for value in ('0xC2C', '0x0c2c', 0xC2C, 'LGUI(LALT(KC_SPACE))', 'LAG(KC_SPACE)', '0xc2d'):
            changed = copy.deepcopy(self.candidate)
            changed['layout'][7][0][6] = value
            self.assertEqual(preset.current_status(changed, self.source, self.candidate), 'drift', value)
        for field, value in (('settings', {'1': False}), ('macro', [['MEH(KC_D)']]),
                             ('new_field', 1), ('version', True), ('version', 1.0),
                             ('vial_protocol', '6'), ('uid', str(self.source['uid']))):
            changed = copy.deepcopy(self.source)
            changed[field] = value
            self.assertEqual(preset.current_status(changed, self.source, self.candidate), 'drift', field)
        for path, value in ((('settings', '1'), False), (('settings', '1'), 0.0),
                            (('layout', 0, 0, 0), True), (('layout_options',), False)):
            changed = copy.deepcopy(self.source)
            replace(changed, path, value)
            self.assertEqual(preset.current_status(changed, self.source, self.candidate), 'drift', path)
        changed = copy.deepcopy(self.source)
        changed['macro'][0] = ['LCTL(LALT(LSFT(KC_D)))']
        other = copy.deepcopy(changed)
        other['macro'][0] = ['MEH(KC_D)']
        self.assertNotEqual(preset.normalized_export(changed), preset.normalized_export(other))

    def test_every_layout_encoder_cell_and_non_layout_leaf_rejects_drift(self):
        checked = 0
        for status, document in (('source', self.source), ('candidate', self.candidate)):
            for field in document:
                for path, value in leaves(document[field], (field,)):
                    changed = copy.deepcopy(document)
                    replacement = 'KC_A' if value != 'KC_A' else 'KC_B'
                    replace(changed, path, replacement)
                    self.assertEqual(preset.current_status(changed, self.source, self.candidate), 'drift', (status, path))
                    checked += 1
        self.assertGreater(checked, 2048)
        for field in self.source:
            changed = copy.deepcopy(self.source)
            del changed[field]
            self.assertEqual(preset.current_status(changed, self.source, self.candidate), 'drift', field)
        for value in (False, None, 0, [], {}, 'source'):
            self.assertEqual(preset.current_status(value, self.source, self.candidate), 'drift')

    def test_generated_assets_and_checksums(self):
        output = ROOT / preset.OUTPUT
        for name, content in preset.generated_files(self.source).items():
            self.assertEqual((output / name).read_text(), content, name)
        manifest = json.loads((output / 'manifest.json').read_text())
        self.assertEqual(manifest['changed_cells'], 121)
        self.assertEqual(manifest['codec']['import_representation_only_cells'], 8)
        self.assertFalse(manifest['codec']['canonical_direct_import_supported'])
        for line in (output / 'SHA256SUMS').read_text().splitlines():
            expected, name = line.split(maxsplit=1)
            self.assertEqual(hashlib.sha256((output / name).read_bytes()).hexdigest(), expected, name)

    def test_source_hash_gate_and_transform_reject_mutations(self):
        for path in (('layout', 6, 0, 1), ('settings', '1'), ('macro', 0), ('version',)):
            changed = copy.deepcopy(self.source)
            replace(changed, path, False)
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, 'source data differs'):
                preset.transform(changed)
        with self.assertRaisesRegex(ValueError, 'duplicate JSON field'):
            preset.read_json('{"version": 1, "version": 2}')
        with self.assertRaisesRegex(ValueError, 'invalid JSON constant'):
            preset.read_json('{"version": NaN}')

    def test_cli_generation_comparison_and_checks_never_write_current_or_source(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            source = work / 'source.vil'
            original_source = (ROOT / preset.SOURCE).read_bytes()
            source.write_bytes(original_source)
            output = work / 'output'
            output.mkdir()
            (output / 'README.md').write_bytes((ROOT / preset.OUTPUT / 'README.md').read_bytes())
            cli = [sys.executable, str(ROOT / 'tools/app_command_trial_preset.py'),
                   '--source', str(source), '--output', str(output)]
            subprocess.run([*cli, 'generate'], check=True, capture_output=True)
            before = {path.name: path.read_bytes() for path in output.iterdir()}
            subprocess.run([*cli, 'check'], check=True, capture_output=True)
            current = work / 'fresh.vil'
            for status, document in (('source', self.source), ('candidate', self.candidate),
                                     ('candidate', self.import_candidate),
                                     ('legacy-source', preset.legacy_source_document(self.source)[0])):
                current.write_text(json.dumps(document, sort_keys=True))
                original_current = current.read_bytes()
                result = subprocess.run([*cli, '--compare-current', str(current)], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue(result.stdout.startswith(status + ':'), result.stdout)
                self.assertEqual(current.read_bytes(), original_current)
            drift = copy.deepcopy(self.source)
            drift['settings']['7'] += 1
            for raw in (json.dumps(drift), '{"version":true}', '{broken',
                        '{"version":1,"version":1}', '{"version":NaN}'):
                current.write_text(raw)
                result = subprocess.run([*cli, '--compare-current', str(current)], capture_output=True, text=True)
                self.assertEqual(result.returncode, 1)
                if raw == json.dumps(drift):
                    self.assertIn('Do not import', result.stdout)
                self.assertEqual(current.read_text(), raw)
            self.assertEqual(source.read_bytes(), original_source)
            self.assertEqual(before, {path.name: path.read_bytes() for path in output.iterdir()})
            source.write_text(json.dumps(drift))
            for action in ('check', 'generate'):
                result = subprocess.run([*cli, action], capture_output=True, text=True)
                self.assertEqual(result.returncode, 1)
                self.assertIn('source SHA256 differs', result.stderr)
            self.assertEqual(before, {path.name: path.read_bytes() for path in output.iterdir()})
            (output / preset.CANDIDATE).write_text('{}\n')
            source.write_bytes(original_source)
            result = subprocess.run([*cli, 'check'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn('generated app-trial asset differs', result.stderr)
            self.assertEqual((output / preset.CANDIDATE).read_text(), '{}\n')


if __name__ == '__main__':
    unittest.main()
