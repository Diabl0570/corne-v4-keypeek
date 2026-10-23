#!/usr/bin/env python3
"""Generate/check the separate app-command trial or compare a local Vial export."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path('presets/command-mode/home-row-mods/home-row-mods16.vil')
SOURCE_SHA256 = '59c5c850fe0762d6756d9b98af08bfde1234e45ddc457679c846fb13447fd72d'
OUTPUT = Path('presets/command-mode/app-trial')
CANDIDATE = 'app-trial16.vil'
IMPORT_CANDIDATE = 'app-trial16-vial075.vil'
COMMAND_LAYERS = (6, 7, 8, 9, 10, 13)
SWAP_ROWS = ((0, 2), (4, 6))
SWAP_COLUMNS = (1, 2, 3, 4, 5)
OVERRIDES = {
    (7, 0, 1): ('LALT(LGUI(KC_LEFT))', 'previous sidebar item, Option-Command-Left'),
    (7, 4, 1): ('LALT(LGUI(KC_LEFT))', 'previous sidebar item, mirrored'),
    (7, 0, 2): ('LALT(LGUI(KC_RIGHT))', 'next sidebar item, Option-Command-Right'),
    (7, 4, 2): ('LALT(LGUI(KC_RIGHT))', 'next sidebar item, mirrored'),
    (7, 0, 6): ('LALT(LGUI(KC_SPACE))', 'one-tap dictation, Option-Command-Space'),
}
VIAL_GUI_COMMIT = 'e42622c352b69eff523a467718db487ab9c9cbf2'
SIMPLEEVAL_COMMIT = '41c99b8e224a7a0ae0ac59c773598fe79a4470db'
CODEC_PROVENANCE_SHA256 = '47bf02a0ee9db4f371a55840813f7e4a127df08ac5282e85c2831d02d2887465'
USER_ENCODINGS = {'USER16': '0x7e10', 'USER17': '0x7e11',
                  'USER18': '0x7e12', 'USER19': '0x7e13'}
# Exact exports observed with the pinned, original Vial 0.7.5 codec.
EXPORT_ALIASES = {
    'KC_LCTL': 'KC_LCTRL',
    'LCTL(LALT(LSFT(KC_D)))': 'MEH(KC_D)',
    'LALT(LGUI(KC_LEFT))': '0xc50',
    'LALT(LGUI(KC_RIGHT))': '0xc4f',
    'LALT(LGUI(KC_SPACE))': '0xc2c',
    **USER_ENCODINGS,
}


def dump(value):
    return json.dumps(value, indent=2, ensure_ascii=False) + '\n'


def sha256(content):
    return hashlib.sha256(content).hexdigest()


def reject_duplicate_fields(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON field: ' + key)
        result[key] = value
    return result


def read_json(raw):
    def reject_constant(value):
        raise ValueError('invalid JSON constant: ' + value)
    return json.loads(raw, object_pairs_hook=reject_duplicate_fields,
                      parse_constant=reject_constant)


def load_source(path):
    raw = path.read_bytes()
    if sha256(raw) != SOURCE_SHA256:
        raise ValueError('source SHA256 differs from verified home-row-mods16; no files written')
    return read_json(raw)


def transform(source):
    if sha256(dump(source).encode()) != SOURCE_SHA256:
        raise ValueError('source data differs from verified home-row-mods16')
    candidate = copy.deepcopy(source)
    changes = []
    for layer in COMMAND_LAYERS:
        for top, bottom in SWAP_ROWS:
            for column in SWAP_COLUMNS:
                candidate['layout'][layer][top][column] = source['layout'][layer][bottom][column]
                candidate['layout'][layer][bottom][column] = source['layout'][layer][top][column]
    for (layer, row, column), (binding, _) in OVERRIDES.items():
        candidate['layout'][layer][row][column] = binding
    for layer, matrix in enumerate(source['layout']):
        for row, keys in enumerate(matrix):
            for column, before in enumerate(keys):
                after = candidate['layout'][layer][row][column]
                if before != after:
                    reason = OVERRIDES.get((layer, row, column), (None, 'five-pair command row swap'))[1]
                    changes.append({'path': f'layout[{layer}][{row}][{column}]',
                                    'before': before, 'after': after, 'reason': reason})
    if len(changes) != 121:
        raise ValueError('expected exactly 121 changed layout cells')
    return candidate, changes


def vial075_import_document(document):
    result = copy.deepcopy(document)
    changes = []
    for field in ('layout', 'encoder_layout'):
        for layer, matrix in enumerate(result[field]):
            for row, keys in enumerate(matrix):
                for column, before in enumerate(keys):
                    if before in USER_ENCODINGS:
                        after = USER_ENCODINGS[before]
                        keys[column] = after
                        changes.append({'path': f'{field}[{layer}][{row}][{column}]',
                                        'before': before, 'after': after})
    return result, changes


def legacy_source_document(source):
    result = copy.deepcopy(source)
    changes = []
    for row in (2, 6):
        for column in range(4):
            before = source['layout'][15][row][column]
            if before != f'USER{16 + column:02}':
                raise ValueError('unexpected legacy-source Picker binding')
            result['layout'][15][row][column] = 'KC_NO'
            changes.append({'path': f'layout[15][{row}][{column}]',
                            'before': before, 'after': 'KC_NO'})
    return result, changes


def normalized_export(document):
    result = copy.deepcopy(document)
    if type(result) is dict:
        for field in ('layout', 'encoder_layout'):
            layers = result.get(field)
            if type(layers) is not list:
                continue
            for layer in layers:
                if type(layer) is not list:
                    continue
                for row in layer:
                    if type(row) is not list:
                        continue
                    for column, keycode in enumerate(row):
                        if type(keycode) is str:
                            row[column] = EXPORT_ALIASES.get(keycode, keycode)
    return json.dumps(result, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def current_status(current, source, candidate):
    current = normalized_export(current)
    if current == normalized_export(source):
        return 'source'
    if current == normalized_export(candidate):
        return 'candidate'
    legacy_source, _ = legacy_source_document(source)
    if current == normalized_export(legacy_source):
        return 'legacy-source'
    return 'drift'


def generated_files(source):
    candidate, changes = transform(source)
    import_candidate, encodings = vial075_import_document(candidate)
    _, legacy_loss = legacy_source_document(source)
    files = {CANDIDATE: dump(candidate), IMPORT_CANDIDATE: dump(import_candidate),
             'changes.json': dump(changes)}
    manifest = {
        'source': str(SOURCE), 'source_sha256': SOURCE_SHA256,
        'candidate_sha256': sha256(files[CANDIDATE].encode()),
        'import_candidate': IMPORT_CANDIDATE,
        'import_candidate_sha256': sha256(files[IMPORT_CANDIDATE].encode()),
        'changed_cells': len(changes), 'changed_layers': list(COMMAND_LAYERS),
        'changed_cells_reference': 'canonical trial versus pinned source',
        'import_variant_string_changed_cells': len(changes) + len(encodings),
        'canonical_unchanged_layers': [0, 1, 2, 3, 4, 5, 11, 12, 14, 15],
        'import_variant_literally_unchanged_layers': [0, 1, 2, 3, 4, 5, 11, 12, 14],
        'all_non_layout_fields_unchanged': True,
        'firmware_helper_registry_and_historical_assets_unchanged': True,
        'requires_flash': False, 'fresh_live_export_used': False,
        'new_preset_imported_or_physically_tested': False,
        'legacy_source': {
            'status': 'legacy-source',
            'fresh_live_state_confirmed': False,
            'lost_picker_cell_count': len(legacy_loss),
            'lost_picker_cells': legacy_loss,
            'trial_repairs_these_cells_only_if_exact_legacy_source_matches': True,
            'other_fields_and_cells_must_match_source_modulo_observed_export_aliases': True,
        },
        'codec': {'repository': 'https://github.com/vial-kb/vial-gui',
                  'ref': 'v0.7.5', 'commit': VIAL_GUI_COMMIT,
                  'simpleeval_commit': SIMPLEEVAL_COMMIT,
                  'fixture_provenance': 'tests/fixtures/vial075/provenance.json',
                  'fixture_provenance_sha256': CODEC_PROVENANCE_SHA256,
                  'canonical_direct_import_supported': False,
                  'canonical_import_blocker': 'Stock Vial 0.7.5 registers only USER00..USER15 without customKeycodes metadata.',
                  'import_representation_only_cells': len(encodings),
                  'import_representation_changes': encodings,
                  'comparison_aliases': EXPORT_ALIASES},
        'files': {name: sha256(content.encode()) for name, content in files.items()},
    }
    files['manifest.json'] = dump(manifest)
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('generate', 'check'), nargs='?', default='check')
    parser.add_argument('--source', type=Path, default=ROOT / SOURCE)
    parser.add_argument('--output', type=Path, default=ROOT / OUTPUT)
    parser.add_argument('--compare-current', type=Path, metavar='FRESH_EXPORT.vil')
    args = parser.parse_args()
    try:
        source = load_source(args.source)
        if args.compare_current:
            candidate, _ = transform(source)
            status = current_status(read_json(args.compare_current.read_bytes()), source, candidate)
            messages = {
                'source': 'source: Current export matches verified home-row-mods16. Use only app-trial16-vial075.vil for manual import.',
                'legacy-source': 'legacy-source: Exact stock Vial 0.7.5 source import recognized. Four duplicated Picker selectors are absent in eight cells. app-trial16-vial075.vil restores them plus the intended 121 changes.',
                'candidate': 'candidate: Current export already matches the app trial. No import needed.',
                'drift': 'drift: Current export differs from source and candidate. Do not import; reconcile the export first.',
            }
            print(messages[status])
            return int(status == 'drift')
        files = generated_files(source)
        readme = args.output / 'README.md'
        checksums = {**files, 'README.md': readme.read_text()}
        files['SHA256SUMS'] = ''.join(sha256(content.encode()) + '  ' + name + '\n'
                                    for name, content in sorted(checksums.items()))
        if args.action == 'generate':
            for name, content in files.items():
                (args.output / name).write_text(content)
            print('Generated separate app trial with 121 changed cells.')
        else:
            for name, content in files.items():
                if (args.output / name).read_text() != content:
                    raise ValueError('generated app-trial asset differs: ' + name)
            print('App-trial preset, exact 121-cell diff and checksums verified.')
        return 0
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.exit(1, str(error) + '\n')


if __name__ == '__main__':
    raise SystemExit(main())
