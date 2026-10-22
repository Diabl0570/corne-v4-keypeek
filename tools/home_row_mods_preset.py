#!/usr/bin/env python3
"""Generate/check the optional home-row preset without changing firmware assets."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path('presets/command-mode/baseline16.vil')
SOURCE_SHA256 = '34c9215bfecb4149c21ac5300639ea38abd2f3ec6110a81294824a3d6df5b3d0'
OUTPUT = Path('presets/command-mode/home-row-mods')
LAYERS = (1, 2, 6, 7, 8, 9, 10, 12, 13)
COMMAND_LAYERS = (6, 7, 8, 9, 10, 12, 13)
BASE_KEYS = {
    (1, 1): 'LGUI_T(KC_A)', (1, 2): 'LCTL_T(KC_S)',
    (1, 3): 'LALT_T(KC_D)', (1, 4): 'LGUI_T(KC_F)',
    (5, 1): 'RGUI_T(KC_SCOLON)', (5, 2): 'LCTL_T(KC_L)',
    (5, 3): 'RALT_T(KC_K)', (5, 4): 'RGUI_T(KC_J)',
}
PLAIN_MODIFIERS = {'LGUI_T': 'KC_LGUI', 'LCTL_T': 'KC_LCTL',
                   'LALT_T': 'KC_LALT', 'RGUI_T': 'KC_RGUI', 'RALT_T': 'KC_RALT'}
BASIC_TAPS = {'KC_NO': 0x00, 'KC_EQUAL': 0x2E, 'KC_LBRACKET': 0x2F,
              'KC_RBRACKET': 0x30, 'KC_BSLASH': 0x31, 'KC_RIGHT': 0x4F,
              'KC_LEFT': 0x50, 'KC_DOWN': 0x51, 'KC_UP': 0x52}
RESTORED_KEYS = ((1, 0), (1, 6), (2, 0), (5, 6))
VOICE_KEYS = {7: 'KC_F18', 8: 'LCTL(LALT(LSFT(KC_D)))'}


def dump(value):
    return json.dumps(value, indent=2, ensure_ascii=False) + '\n'


def sha256(content):
    return hashlib.sha256(content).hexdigest()


def validate_source(source):
    layout, encoders = source['layout'], source['encoder_layout']
    if len(layout) != 16 or any(len(layer) != 8 or any(len(row) != 7 for row in layer) for layer in layout):
        raise ValueError('expected sixteen 8x7 matrices')
    if len(encoders) != 16 or any(len(layer) != 4 or any(len(pair) != 2 for pair in layer) for layer in encoders):
        raise ValueError('expected sixteen layers of four encoder pairs')
    holes = {(r, c) for r in range(8) for c in range(7) if layout[0][r][c] == -1}
    if len(holes) != 10 or any({(r, c) for r in range(8) for c in range(7) if layer[r][c] == -1} != holes for layer in layout):
        raise ValueError('physical matrix holes changed')
    for (r, c), expected in BASE_KEYS.items():
        if layout[0][r][c] != expected:
            raise ValueError(f'unexpected base hold family at layout[0][{r}][{c}]')
    for layer, voice in VOICE_KEYS.items():
        if layout[layer][2][0] != voice or layout[layer][6][0] != voice or layout[layer][3][4] != 'KC_NO':
            raise ValueError(f'unexpected voice source or occupied destination in layer{layer}')


def transform(source):
    validate_source(source)
    candidate = copy.deepcopy(source)
    changes = []

    def put(layer, row, column, after, reason):
        before = source['layout'][layer][row][column]
        candidate['layout'][layer][row][column] = after
        if before != after:
            changes.append({'path': f'layout[{layer}][{row}][{column}]', 'before': before,
                            'after': after, 'reason': reason})

    for layer in LAYERS:
        for row, column in BASE_KEYS:
            family = re.fullmatch(r'([A-Z]+_T)\(KC_[A-Z]+\)', source['layout'][0][row][column])[1]
            tap = source['layout'][layer][row][column]
            if not isinstance(tap, str) or tap not in BASIC_TAPS or not 0 <= BASIC_TAPS[tap] <= 0xFF:
                raise ValueError(f'unsupported 8-bit tap at layout[{layer}][{row}][{column}]')
            # MT(mod, KC_NO) aliases QMK's one-shot action, so blank taps use a plain modifier.
            binding = PLAIN_MODIFIERS[family] if tap == 'KC_NO' else f'{family}({tap})'
            put(layer, row, column, binding, 'base hold family, existing tap')
        for row, column in RESTORED_KEYS:
            put(layer, row, column, source['layout'][0][row][column], 'restore familiar Tab or Shift')
        if layer in COMMAND_LAYERS:
            put(layer, 6, 0, 'KC_LSHIFT', 'mirrored left Shift, no voice action')
        if layer in VOICE_KEYS:
            put(layer, 3, 4, VOICE_KEYS[layer], 'explicit voice action, left Backspace thumb only')
    changes.sort(key=lambda change: tuple(map(int, re.findall(r'\[(\d+)\]', change['path']))))
    return candidate, changes


def load_source(path):
    raw = path.read_bytes()
    if sha256(raw) != SOURCE_SHA256:
        raise ValueError('source SHA256 differs from the verified baseline16; no files written')
    source = json.loads(raw)
    validate_source(source)
    return source


def current_status(current, source, candidate):
    def canonical(value):
        return json.dumps(value, sort_keys=True, separators=(',', ':'))
    if canonical(current) == canonical(source):
        return 'baseline'
    if canonical(current) == canonical(candidate):
        return 'candidate'
    return 'drift'


def generated_files(source):
    candidate, changes = transform(source)
    files = {'home-row-mods16.vil': dump(candidate), 'changes.json': dump(changes)}
    manifest = {
        'source': str(SOURCE), 'source_sha256': SOURCE_SHA256,
        'candidate_sha256': sha256(files['home-row-mods16.vil'].encode()),
        'changed_cells': len(changes), 'covered_layers': [0, *LAYERS],
        'unchanged_layers': [0, 3, 4, 5, 11, 14, 15],
        'all_non_layout_fields_unchanged': True,
        'compiled_firmware_helper_and_registry_unchanged': True,
        'requires_flash': False, 'fresh_live_export_used': False,
        'new_preset_imported_or_physically_tested': False,
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
            status = current_status(json.loads(args.compare_current.read_text()), source, candidate)
            messages = {
                'baseline': 'Current export matches verified baseline16. Ready for manual home-row preset import.',
                'candidate': 'Current export already matches home-row-mods16. No import needed.',
                'drift': 'Current export differs from baseline16 and home-row-mods16. Do not import; reconcile the export first.',
            }
            print(messages[status])
            return int(status == 'drift')
        files = generated_files(source)
        readme = args.output / 'README.md'
        if not readme.is_file():
            raise ValueError('output README.md is missing')
        checksums = {**files, 'README.md': readme.read_text()}
        files['SHA256SUMS'] = ''.join(sha256(content.encode()) + '  ' + name + '\n' for name, content in sorted(checksums.items()))
        if args.action == 'generate':
            for name, content in files.items():
                (args.output / name).write_text(content)
            print('Generated home-row-mods16 with 115 changed cells. Firmware and registry are unchanged.')
        else:
            for name, content in files.items():
                if not (args.output / name).is_file() or (args.output / name).read_text() != content:
                    raise ValueError('generated preset asset differs: ' + name)
            print('Home-row preset, 115 changed cells and checksums verified.')
        return 0
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.exit(1, str(error) + '\n')


if __name__ == '__main__':
    raise SystemExit(main())
