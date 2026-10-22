"""Check the optional preset's exact data boundary without keyboard I/O."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('preset', ROOT / 'tools/home_row_mods_preset.py')
preset = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preset)


class HomeRowPresetTests(unittest.TestCase):
    def setUp(self):
        self.source = preset.load_source(ROOT / preset.SOURCE)
        self.candidate, self.changes = preset.transform(self.source)

    def test_exact_allowlisted_changes_and_all_other_data_preserved(self):
        actual = {(layer, row, col) for layer in range(16) for row in range(8) for col in range(7)
                  if self.source['layout'][layer][row][col] != self.candidate['layout'][layer][row][col]}
        layers = (1, 2, 6, 7, 8, 9, 10, 12, 13)
        allowed = {(layer, row, col) for layer in layers for row in (1, 5) for col in range(1, 5)}
        allowed |= {(layer, row, col) for layer in layers for row, col in ((1, 0), (1, 6), (2, 0), (5, 6))
                    if self.source['layout'][layer][row][col] != self.source['layout'][0][row][col]}
        allowed |= {(layer, 6, 0) for layer in (6, 7, 8, 9, 10, 12, 13)}
        allowed |= {(7, 3, 4), (8, 3, 4)}
        self.assertEqual(actual, allowed)
        self.assertEqual(len(actual), 115)
        paths = {tuple(map(int, re.findall(r'\[(\d+)\]', change['path']))) for change in self.changes}
        self.assertEqual(actual, paths)
        self.assertEqual(len(self.changes), len(paths))
        for field in set(self.source) - {'layout'}:
            self.assertEqual(self.source[field], self.candidate[field], field)
        for layer in (0, 3, 4, 5, 11, 14, 15):
            self.assertEqual(self.source['layout'][layer], self.candidate['layout'][layer], layer)
        for layer in range(16):
            for row in range(8):
                for col in range(7):
                    self.assertEqual(self.source['layout'][layer][row][col] == -1,
                                     self.candidate['layout'][layer][row][col] == -1)

    def test_exact_hold_families_preserve_existing_taps(self):
        holds = {1: ('LGUI_T', 'LCTL_T', 'LALT_T', 'LGUI_T'),
                 5: ('RGUI_T', 'LCTL_T', 'RALT_T', 'RGUI_T')}
        plain = {'LGUI_T': 'KC_LGUI', 'LCTL_T': 'KC_LCTL', 'LALT_T': 'KC_LALT',
                 'RGUI_T': 'KC_RGUI', 'RALT_T': 'KC_RALT'}
        neutral = 0
        for layer in (1, 2, 6, 7, 8, 9, 10, 12, 13):
            for row, families in holds.items():
                for col, family in enumerate(families, 1):
                    old = self.source['layout'][layer][row][col]
                    new = self.candidate['layout'][layer][row][col]
                    if old == 'KC_NO':
                        self.assertEqual(new, plain[family])
                        self.assertNotIn('_T(', new)
                        neutral += 1
                    else:
                        self.assertEqual(new, family + '(' + old + ')')
        self.assertEqual(neutral, 9)
        self.assertEqual(self.candidate['settings'], self.source['settings'])
        self.assertEqual(self.candidate['settings']['7'], 200)
        self.assertEqual(self.candidate['settings']['25'], 200)
        for field in ('22', '23', '24', '26', '27'):
            self.assertEqual(self.candidate['settings'][field], 0)

    def test_tab_shift_voice_and_protected_controls(self):
        for layer in (0, 1, 2, 6, 7, 8, 9, 10, 12, 13):
            for row, col in ((1, 0), (1, 6), (2, 0), (5, 6)):
                self.assertEqual(self.candidate['layout'][layer][row][col], self.source['layout'][0][row][col])
        for layer in (6, 7, 8, 9, 10, 12, 13):
            self.assertEqual(self.candidate['layout'][layer][6][0], 'KC_LSHIFT')
        for layer, action in ((7, 'KC_F18'), (8, 'LCTL(LALT(LSFT(KC_D)))')):
            self.assertEqual(self.candidate['layout'][layer][3][4], action)
            self.assertEqual(sum(key == action for row in self.candidate['layout'][layer] for key in row), 1)
            self.assertEqual(self.candidate['layout'][layer][2][0], 'KC_LSHIFT')
            self.assertEqual(self.candidate['layout'][layer][6][0], 'KC_LSHIFT')
        for layer in range(16):
            for row, col in ((3, 3), (7, 3), (7, 4), (2, 5), (6, 5), (3, 5), (7, 5)):
                self.assertEqual(self.candidate['layout'][layer][row][col], self.source['layout'][layer][row][col])
        self.assertEqual(self.candidate['layout'][0][3][5], 'KC_SPACE')

    def test_basic_numeric_taps_match_pinned_qmk(self):
        qmk = Path(os.environ.get('QMK_SOURCE', ROOT / 'src/vial-kb/vial-qmk'))
        pin = subprocess.check_output(['git', '-C', str(qmk), 'rev-parse', 'HEAD'], text=True).strip()
        self.assertEqual(pin, 'dd43959ae5c08d8a28d38a1acf7b04e86b14a344')
        header = (qmk / 'quantum/keycodes.h').read_text()
        aliases = {'KC_LBRACKET': 'KC_LEFT_BRACKET', 'KC_RBRACKET': 'KC_RIGHT_BRACKET', 'KC_BSLASH': 'KC_BACKSLASH'}
        for name, expected in preset.BASIC_TAPS.items():
            match = re.search(r'\b' + aliases.get(name, name) + r'\s*=\s*(0x[0-9A-Fa-f]+)', header)
            self.assertIsNotNone(match, name)
            self.assertEqual(int(match[1], 16), expected, name)
            self.assertLessEqual(expected, 255)

    def test_invalid_source_shape_family_or_tap_rejected(self):
        for kind in ('layers', 'row', 'encoders', 'hole', 'family', 'chord', 'custom', 'mouse', 'number', 'voice'):
            changed = copy.deepcopy(self.source)
            if kind == 'layers': changed['layout'].pop()
            elif kind == 'row': changed['layout'][1][1].pop()
            elif kind == 'encoders': changed['encoder_layout'][1].pop()
            elif kind == 'hole': changed['layout'][1][0][0] = -1
            elif kind == 'family': changed['layout'][0][5][2] = 'RCTL_T(KC_L)'
            elif kind == 'voice': changed['layout'][7][3][4] = 'KC_A'
            else:
                changed['layout'][6][1][1] = {'chord': 'LGUI(KC_A)', 'custom': 'USER00',
                                             'mouse': 'KC_MS_L', 'number': 0x100}[kind]
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                preset.transform(changed)

    def test_current_comparison_ignores_formatting_and_rejects_every_field_drift(self):
        formatted = json.loads(json.dumps(self.source, sort_keys=True, separators=(',', ':')))
        self.assertEqual(preset.current_status(formatted, self.source, self.candidate), 'baseline')
        self.assertEqual(preset.current_status(self.candidate, self.source, self.candidate), 'candidate')
        for kind in ('matrix', 'encoder', 'setting', 'macro', 'type', 'field'):
            changed = copy.deepcopy(self.source)
            if kind == 'matrix': changed['layout'][0][0][0] = 'KC_A'
            elif kind == 'encoder': changed['encoder_layout'][0][0][0] = 'KC_A'
            elif kind == 'setting': changed['settings']['7'] += 1
            elif kind == 'macro': changed['macro'][0] = ['a']
            elif kind == 'type': changed['settings']['1'] = False
            else: changed['new_field'] = 1
            with self.subTest(kind=kind):
                self.assertEqual(preset.current_status(changed, self.source, self.candidate), 'drift')

    def test_generation_checksums_and_cli_no_write_drift_check(self):
        folder = ROOT / preset.OUTPUT
        for name, content in preset.generated_files(self.source).items():
            self.assertEqual((folder / name).read_text(), content)
        for line in (folder / 'SHA256SUMS').read_text().splitlines():
            expected, name = line.split(maxsplit=1)
            self.assertEqual(hashlib.sha256((folder / name).read_bytes()).hexdigest(), expected)
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            source = work / 'source.vil'
            source.write_bytes((ROOT / preset.SOURCE).read_bytes())
            output = work / 'output'
            output.mkdir()
            (output / 'README.md').write_bytes((folder / 'README.md').read_bytes())
            command = [sys.executable, str(ROOT / 'tools/home_row_mods_preset.py'), '--source', str(source), '--output', str(output)]
            subprocess.run([*command, 'generate'], check=True, capture_output=True)
            before = {p.name: p.read_bytes() for p in output.iterdir()}
            subprocess.run([*command, 'check'], check=True, capture_output=True)
            current = work / 'fresh.vil'
            current.write_text(json.dumps(self.source, sort_keys=True))
            match = subprocess.run([*command, '--compare-current', str(current)], capture_output=True, text=True)
            self.assertEqual(match.returncode, 0, match.stderr)
            self.assertIn('matches verified baseline16', match.stdout)
            drift = copy.deepcopy(self.source)
            drift['settings']['7'] += 1
            current.write_text(json.dumps(drift))
            mismatch = subprocess.run([*command, '--compare-current', str(current)], capture_output=True, text=True)
            self.assertEqual(mismatch.returncode, 1)
            self.assertIn('Do not import', mismatch.stdout)
            self.assertEqual(before, {p.name: p.read_bytes() for p in output.iterdir()})
            source.write_text(json.dumps(drift))
            reject = subprocess.run([*command, 'generate'], capture_output=True, text=True)
            self.assertEqual(reject.returncode, 1)
            self.assertIn('source SHA256 differs', reject.stderr)
            self.assertEqual(before, {p.name: p.read_bytes() for p in output.iterdir()})


if __name__ == '__main__':
    unittest.main()
