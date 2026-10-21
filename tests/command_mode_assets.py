"""Public preset and registry-generator boundary checks."""
import copy
import importlib.util
import json
import re
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('assets', ROOT/'tools/command_mode_assets.py')
assets = importlib.util.module_from_spec(spec)
spec.loader.exec_module(assets)


class AssetTests(unittest.TestCase):
    def setUp(self):
        self.registry, self.source, self.physical, _, _ = assets.read_registry()

    def test_exact_preservation_and_only_reversible_space_change(self):
        baseline, experimental, _ = assets.make_presets(self.registry, self.source, self.physical)
        self.assertEqual(baseline['layout'][:6], self.source['layout'])
        self.assertEqual(baseline['encoder_layout'][:6], self.source['encoder_layout'])
        for key in set(self.source)-{'layout','encoder_layout'}:
            self.assertEqual(baseline[key], self.source[key], key)
            self.assertEqual(experimental[key], self.source[key], key)
        self.assertEqual(experimental['layout'][0][3][5], 'USER03')
        experimental['layout'][0][3][5] = 'KC_SPACE'
        self.assertEqual(experimental, baseline)

    def test_every_layer_and_auto_have_deliberate_picker_controls(self):
        baseline, _, _ = assets.make_presets(self.registry, self.source, self.physical)
        picker = baseline['layout'][15]
        for layer in self.registry['layers']:
            r,c = layer['selector']
            expected = f"USER{layer['id']+4:02}"
            self.assertEqual(picker[r][c], expected)
            self.assertEqual(picker[r+4][c], expected)
        self.assertEqual(picker[2][4], 'USER01')
        self.assertEqual(picker[2][5], 'USER00')
        self.assertEqual(len(self.physical), 46)

    def test_changes_to_settings_or_original_key_are_rejected(self):
        baseline, experiment, _ = assets.make_presets(self.registry, self.source, self.physical)
        for kind in ('settings','mapping','encoder'):
            changed = copy.deepcopy(baseline)
            if kind == 'settings': changed['settings']['7'] = 201
            elif kind == 'mapping': changed['layout'][0][0][1] = 'KC_Z'
            else: changed['encoder_layout'][0][0][0] = 'KC_NO'
            with self.assertRaises(AssertionError):
                assets.verify_presets(self.source, changed, experiment)

    def test_invalid_registry_or_capture_rejected_before_writing(self):
        for kind in ('selector','bundle','layer','matrix'):
            registry = copy.deepcopy(self.registry)
            source = copy.deepcopy(self.source)
            if kind == 'selector': registry['layers'][1]['selector'] = [0,0]
            elif kind == 'bundle': registry['layers'][8]['bundle_ids'] = ['com.openai.codex']
            elif kind == 'layer': registry['layers'][15]['id'] = 16
            else: source['layout'][0][0].pop()
            with tempfile.TemporaryDirectory() as temporary:
                base = Path(temporary)
                (base/'config').mkdir()
                (base/'config/command-mode.json').write_text(json.dumps(registry))
                source_file = base/registry['source']
                source_file.parent.mkdir(parents=True)
                source_file.write_text(json.dumps(source))
                original = assets.ROOT
                try:
                    assets.ROOT = base
                    with self.assertRaises(ValueError): assets.generate()
                    self.assertFalse((base/'presets').exists())
                finally: assets.ROOT = original

    def test_vial_user_range_and_named_app_identity(self):
        # Vial GUI v6 USER00 is QK_KB+0, independently verified upstream.
        self.assertEqual(assets.c_code('USER00'), 'QK_KB_0')
        self.assertEqual(assets.c_code('USER19'), 'QK_KB_19')
        # Match imported USERnn to actual pinned QMK enum values, not just names.
        keycodes = (ROOT/'src/vial-kb/vial-qmk/quantum/keycodes.h').read_text()
        for number in range(20):
            compiled_name = assets.c_code(f'USER{number:02}')
            match = re.search(r'\b'+compiled_name+r'\s*=\s*(0x[0-9A-Fa-f]+)', keycodes)
            self.assertIsNotNone(match)
            self.assertEqual(int(match.group(1), 16), 0x7E00+number)
        matching = [x for x in self.registry['layers'] if 'com.openai.codex' in x.get('bundle_ids',[])]
        self.assertEqual([x['id'] for x in matching], [7])


if __name__ == '__main__':
    unittest.main()
