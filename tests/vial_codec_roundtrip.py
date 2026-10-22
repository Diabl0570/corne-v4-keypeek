"""Exercise the original pinned Vial 0.7.5 keycode codec, entirely offline."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'tests/fixtures/vial075'
sys.path.insert(0, str(FIXTURE))
from keycodes.keycodes import Keycode, recreate_keyboard_keycodes
from simpleeval import FunctionNotDefined, NameNotDefined

spec = importlib.util.spec_from_file_location('app_trial', ROOT / 'tools/app_command_trial_preset.py')
preset = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preset)


def configure_codec(document):
    recreate_keyboard_keycodes(SimpleNamespace(
        vial_protocol=document['vial_protocol'], layers=len(document['layout']),
        macro_count=len(document['macro']), tap_dance_count=len(document['tap_dance']),
        custom_keycodes=None, midi=None, supported_features=[]))


def cells(document):
    for field in ('layout', 'encoder_layout'):
        for layer, matrix in enumerate(document[field]):
            for row, keys in enumerate(matrix):
                for column, value in enumerate(keys):
                    yield field, layer, row, column, value


def roundtrip_document(document, *, strict=True):
    configure_codec(document)
    exported = copy.deepcopy(document)
    count = 0
    for field, layer, row, column, value in cells(document):
        raw = Keycode.deserialize(value, reraise=strict)
        serialized = Keycode.serialize(raw)
        if Keycode.deserialize(serialized, reraise=True) != raw:
            raise AssertionError(f'codec value changed at {field}[{layer}][{row}][{column}]')
        # keyboard_comm.py save_layout uses -1 for coordinates absent from the physical map.
        exported[field][layer][row][column] = -1 if type(value) is int and value == -1 else serialized
        count += 1
    return exported, count


class VialCodecTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = preset.load_source(ROOT / preset.SOURCE)
        cls.candidate, _ = preset.transform(cls.source)

    def setUp(self):
        configure_codec(self.source)

    def test_original_source_hashes_and_immutable_provenance(self):
        self.assertEqual(hashlib.sha256((FIXTURE / 'provenance.json').read_bytes()).hexdigest(),
                         preset.CODEC_PROVENANCE_SHA256)
        provenance = json.loads((FIXTURE / 'provenance.json').read_text())
        self.assertEqual(provenance['vial_gui']['commit'], preset.VIAL_GUI_COMMIT)
        self.assertEqual(provenance['vial_gui']['ref'], 'v0.7.5')
        self.assertEqual(provenance['simpleeval']['commit'], preset.SIMPLEEVAL_COMMIT)
        for item in provenance['files']:
            with self.subTest(path=item['path']):
                self.assertEqual(hashlib.sha256((FIXTURE / item['path']).read_bytes()).hexdigest(), item['sha256'])
        self.assertEqual((FIXTURE / 'keycodes/__init__.py').read_bytes(), b'')

    def test_new_chords_and_existing_claude_chord_use_actual_codec(self):
        expected = {
            'LALT(LGUI(KC_LEFT))': (0x0C50, '0xc50'),
            'LALT(LGUI(KC_RIGHT))': (0x0C4F, '0xc4f'),
            'LALT(LGUI(KC_SPACE))': (0x0C2C, '0xc2c'),
            'LCTL(LALT(LSFT(KC_D)))': (0x0707, 'MEH(KC_D)'),
        }
        for expression, (raw, exported) in expected.items():
            with self.subTest(expression=expression):
                self.assertEqual(Keycode.deserialize(expression, reraise=True), raw)
                self.assertEqual(Keycode.serialize(raw), exported)
                self.assertEqual(Keycode.deserialize(exported, reraise=True), raw)
        for expression in ('LAG(KC_LEFT)', 'LAG(KC_RIGHT)', 'LAG(KC_SPACE)'):
            with self.subTest(expression=expression):
                with self.assertRaises(FunctionNotDefined):
                    Keycode.deserialize(expression, reraise=True)
                self.assertEqual(Keycode.deserialize(expression), 0)

    def test_default_user_registration_exposes_canonical_import_blocker(self):
        definition = json.loads((ROOT / 'keyboards/crkbd/vial-kb/vial-qmk/keymaps/vial/vial.json').read_text())
        self.assertFalse(definition.get('customKeycodes'))
        self.assertEqual(self.source['vial_protocol'], 6)
        for document in (self.source, self.candidate):
            failures = []
            count = 0
            for field, layer, row, column, value in cells(document):
                count += 1
                if value in preset.USER_ENCODINGS:
                    with self.assertRaises(NameNotDefined):
                        Keycode.deserialize(value, reraise=True)
                    self.assertEqual(Keycode.deserialize(value), 0)
                    failures.append((field, layer, row, column, value))
                else:
                    raw = Keycode.deserialize(value, reraise=True)
                    self.assertEqual(Keycode.deserialize(Keycode.serialize(raw), reraise=True), raw)
            self.assertEqual(count, 1024)
            self.assertEqual(failures, [
                ('layout', 15, row, column, f'USER{16 + column:02}')
                for row in (2, 6) for column in range(4)])

    def test_user_encoding_identity_comes_from_original_protocol_table(self):
        for name, exported in preset.USER_ENCODINGS.items():
            with self.subTest(name=name):
                # resolve reads the original protocol-6 constants, without registering invented keyboard metadata.
                raw = Keycode.resolve(name)
                self.assertEqual(raw, 0x7E00 + int(name[4:]))
                self.assertEqual(Keycode.serialize(raw), exported)
                self.assertEqual(Keycode.deserialize(exported, reraise=True), raw)
                self.assertIsNone(Keycode.find_by_qmk_id(name))

    def test_default_lossy_source_roundtrip_matches_only_exact_legacy_profile(self):
        exported, count = roundtrip_document(self.source, strict=False)
        self.assertEqual(count, 1024)
        legacy, changes = preset.legacy_source_document(self.source)
        self.assertEqual(len(changes), 8)
        self.assertEqual(preset.normalized_export(exported), preset.normalized_export(legacy))
        self.assertNotEqual(preset.normalized_export(exported), preset.normalized_export(self.source))
        self.assertEqual(preset.current_status(exported, self.source, self.candidate), 'legacy-source')
        for row in (2, 6):
            self.assertEqual(exported['layout'][15][row][:4], ['KC_NO'] * 4)

    def test_every_source_and_candidate_cell_roundtrips_with_safe_encoding(self):
        observed_aliases = {}
        for name, document in (('source', self.source), ('candidate', self.candidate)):
            import_document, encoding_changes = preset.vial075_import_document(document)
            self.assertEqual(len(encoding_changes), 8)
            exported, count = roundtrip_document(import_document)
            self.assertEqual(count, 1024)
            self.assertEqual(preset.current_status(exported, self.source, self.candidate), name)
            for field, layer, row, column, original in cells(document):
                after = exported[field][layer][row][column]
                if type(original) is str and original != after:
                    observed_aliases[original] = after
            for field in set(document) - {'layout', 'encoder_layout'}:
                self.assertEqual(document[field], exported[field], field)
        self.assertEqual(observed_aliases, preset.EXPORT_ALIASES)

    def test_mouse_encoders_user_and_custom_control_identities_survive(self):
        expected = {
            'KC_MS_LEFT': 0x00CF, 'KC_MS_RIGHT': 0x00D0,
            'RGB_MOD': 0x7821, 'RGB_RMOD': 0x7822,
            'USER00': 0x7E00, 'USER01': 0x7E01, 'USER02': 0x7E02,
            '0x7e10': 0x7E10, '0x7e13': 0x7E13,
        }
        for value, raw in expected.items():
            with self.subTest(value=value):
                self.assertEqual(Keycode.deserialize(value, reraise=True), raw)
                self.assertEqual(Keycode.deserialize(Keycode.serialize(raw), reraise=True), raw)
        self.assertNotEqual(Keycode.deserialize('KC_NO'), Keycode.deserialize('0x7e13'))

    def test_wrong_chords_and_lost_picker_bindings_remain_drift(self):
        safe, _ = preset.vial075_import_document(self.candidate)
        exported, _ = roundtrip_document(safe)
        for position, value in (((7, 0, 6), '0x82c'), ((7, 0, 1), '0xc4f'),
                                ((7, 0, 2), 'LAG(KC_RIGHT)'), ((15, 2, 0), 'KC_NO'),
                                ((15, 6, 3), 'KC_NO'), ((8, 0, 6), 'LALT(LSFT(KC_D))')):
            changed = copy.deepcopy(exported)
            layer, row, column = position
            changed['layout'][layer][row][column] = value
            with self.subTest(position=position, value=value):
                self.assertEqual(preset.current_status(changed, self.source, self.candidate), 'drift')


if __name__ == '__main__':
    unittest.main()
