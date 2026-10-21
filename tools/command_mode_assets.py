#!/usr/bin/env python3
"""Generate/check the single registry, exact Vial presets and readable legend."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KEYMAP = Path('keyboards/crkbd/vial-kb/vial-qmk/keymaps/vial')
PRESETS = Path('presets/command-mode')
REGISTRY = Path('config/command-mode.json')


def dump(value):
    return json.dumps(value, indent=2, ensure_ascii=False) + '\n'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_registry():
    registry = json.loads((ROOT / REGISTRY).read_text())
    layers = registry['layers']
    if registry['version'] != 1 or [x['id'] for x in layers] != list(range(16)):
        raise ValueError('registry requires version1 and ordered IDs0..15')
    if [x['id'] for x in layers if x.get('automatic')] != list(range(6, 11)):
        raise ValueError('automatic allowlist must be6..10')
    source_bytes = (ROOT / registry['source']).read_bytes()
    source = json.loads(source_bytes)
    if len(source['layout']) != 6 or len(source['encoder_layout']) != 6:
        raise ValueError('expected captured six-layer source')
    for layer in source['layout']:
        if len(layer) != 8 or any(len(row) != 7 for row in layer):
            raise ValueError('matrix must be8x7')
    physical = {(r, c) for r in range(8) for c in range(7) if source['layout'][0][r][c] != -1}
    if len(physical) != 46 or any({(r,c) for r in range(8) for c in range(7) if layer[r][c] != -1} != physical for layer in source['layout']):
        raise ValueError('captured physical matrix mismatch')
    selectors = [tuple(x['selector']) for x in layers]
    if len(set(selectors)) != 16 or not set(selectors) <= physical:
        raise ValueError('selector collision or hole')
    if set(map(tuple, registry['controls'].values())) & set(selectors):
        raise ValueError('selector/control collision')
    bundles = [b for x in layers for b in x.get('bundle_ids', [])]
    if len(bundles) != len(set(bundles)):
        raise ValueError('bundle identity has competing profiles')
    canonical = json.dumps(registry, sort_keys=True, separators=(',', ':')).encode()
    return registry, source, physical, source_bytes, canonical


def make_presets(registry, source, physical):
    baseline = copy.deepcopy(source)
    labels = {}
    for entry in registry['layers'][6:]:
        matrix = [[-1 if (r,c) not in physical else 'KC_NO' for c in range(7)] for r in range(8)]
        layer_labels = {}
        def put(pos, code, label, mirror=True):
            r, c = pos
            if (r,c) not in physical:
                raise ValueError(f'binding into matrix hole: {pos}')
            matrix[r][c] = code
            layer_labels[f'{r},{c}'] = label
            if mirror and r < 4:
                matrix[r+4][c] = code
                layer_labels[f'{r+4},{c}'] = label
        bindings = registry['templates'].get(entry.get('template'), {}) | entry.get('bindings', {})
        for pos, (code, label) in bindings.items():
            put(tuple(map(int, pos.split(','))), code, label)
        if entry['id'] == 15:
            for selected in registry['layers']:
                put(selected['selector'], f"USER{selected['id']+4:02}", selected['name'])
            put(registry['controls']['auto'], 'USER01', 'Auto Command')
        put(registry['controls']['home'], 'USER00', 'Home: typing, Auto off')
        put((3,3), 'TG(1)', 'Menu: tap numbers / hold picker / double Home', mirror=False)
        put((7,3), 'KC_RGUI', 'Right Command', mirror=False)
        put((7,4), 'FN_MO23', 'Symbols, hold', mirror=False)
        put(registry['controls']['mirror_left'], 'USER02', 'Mirror, hold', mirror=False)
        put(registry['controls']['mirror_right'], 'USER02', 'Mirror, hold', mirror=False)
        baseline['layout'].append(matrix)
        baseline['encoder_layout'].append(copy.deepcopy(source['encoder_layout'][0]))
        labels[entry['id']] = layer_labels
    experimental = copy.deepcopy(baseline)
    experimental['layout'][0][3][5] = 'USER03'
    verify_presets(source, baseline, experimental)
    return baseline, experimental, labels


def verify_presets(source, baseline, experimental):
    for preset in (baseline, experimental):
        assert len(preset['layout']) == len(preset['encoder_layout']) == 16
        assert all(len(x) == 4 and all(len(pair) == 2 for pair in x) for x in preset['encoder_layout'])
        assert all(len(x) == 8 and all(len(row) == 7 for row in x) for x in preset['layout'])
        assert {k:v for k,v in preset.items() if k not in ('layout','encoder_layout')} == {k:v for k,v in source.items() if k not in ('layout','encoder_layout')}
        assert preset['encoder_layout'][:6] == source['encoder_layout']
    assert baseline['layout'][:6] == source['layout']
    restored = copy.deepcopy(experimental)
    restored['layout'][0][3][5] = source['layout'][0][3][5]
    assert restored == baseline
    # This captured source has empty macros; reject an unexpected later source.
    assert len(source['macro']) == 16 and not any(source['macro'])
    # Every picker selector survives; Home and both mirrors are explicit controls.
    for layer in range(16):
        code = f'USER{layer+4:02}'
        assert any(code == value for row in baseline['layout'][15] for value in row)
    assert baseline['layout'][15][2][4] == 'USER01'
    for layer in range(6, 16):
        assert baseline['layout'][layer][2][5] == 'USER00'
        assert baseline['layout'][layer][3][5] == baseline['layout'][layer][7][5] == 'USER02'


def c_code(value):
    if value == -1:
        return 'KC_NO'
    if value.startswith('USER') and value[4:].isdigit():
        return 'QK_KB_' + str(int(value[4:]))
    return value.replace('FN_MO23', 'TL_UPPR')


def generate():
    registry, source, physical, source_bytes, canonical = read_registry()
    baseline, experimental, labels = make_presets(registry, source, physical)
    hash32 = int.from_bytes(hashlib.sha256(canonical).digest()[:4], 'little')
    banner = '// Generated by tools/command_mode_assets.py; do not edit.\n'
    header = banner + '#pragma once\n#include <stdint.h>\n#include <stdbool.h>\n'
    header += f'#define CM_LAYER_COUNT 16\n#define CM_GENERIC_LAYER 6\n#define CM_PICKER_LAYER 15\n#define CM_REGISTRY_HASH UINT32_C(0x{hash32:08X})\n'
    header += 'static inline bool cm_auto_layer_valid(uint8_t layer) { return layer >= 6 && layer <= 10; }\n'
    header += '#define CM_LAYER_PALETTE { ' + ', '.join('{%d, %d, 0}' % (x['hue'], x['saturation']) for x in registry['layers']) + ' }\n'
    header += 'static const char *const cm_layer_names[16] = { ' + ', '.join(json.dumps(x['name']) for x in registry['layers']) + ' };\n'
    keymaps = banner + '#pragma once\nconst uint16_t PROGMEM keymaps[][MATRIX_ROWS][MATRIX_COLS] = {\n'
    for layer in baseline['layout']:
        keymaps += '    {\n' + ''.join('        { ' + ', '.join(c_code(x) for x in row) + ' },\n' for row in layer) + '    },\n'
    keymaps += '};\n#ifdef ENCODER_MAP_ENABLE\nconst uint16_t PROGMEM encoder_map[][NUM_ENCODERS][NUM_DIRECTIONS] = {\n'
    for layer in baseline['encoder_layout']:
        keymaps += '    { ' + ', '.join('{ ' + ', '.join(c_code(x) for x in pair) + ' }' for pair in layer) + ' },\n'
    keymaps += '};\n#endif\n'
    settings = banner + '#pragma once\nstatic const struct { uint16_t id; uint32_t value; } cm_initial_settings[] = {\n'
    settings += ''.join(f'    {{{int(k)}, {v}}},\n' for k,v in source['settings'].items()) + '};\n'
    swift = banner + 'import Foundation\n\npublic enum CommandRegistry {\n    public static let schemaVersion: UInt8 = 1\n'
    swift += f'    public static let hash: UInt32 = 0x{hash32:08X}\n    public static let entries: [CommandDefinition] = [\n'
    for x in registry['layers']:
        swift += '        .init(id: %d, name: %s, bundleIDs: %s, automatic: %s),\n' % (x['id'], json.dumps(x['name']), json.dumps(x.get('bundle_ids', [])), str(x.get('automatic',False)).lower())
    swift += '    ]\n    public static let transientBundleIDs: Set<String> = ' + json.dumps(registry['transient_bundle_ids']) + '\n'
    swift += '    public static let configuratorBundleID = ' + json.dumps(registry['configurator_bundle_id']) + '\n'
    swift += '    public static func layer(forBundleID bundleID: String) -> UInt8 {\n        entries.first { $0.bundleIDs.contains(bundleID) }?.id ?? 6\n    }\n}\n'
    legend = '# Corne command-mode legend\n\nGenerated from `config/command-mode.json`. Matrix coordinates are row,column, not keycap names. Both halves offer the same command clusters. The original six layers are preserved in baseline16.\n\n'
    legend += 'Menu is the left outer thumb. Tap toggles numbers after the 200ms double-tap window. Hold200ms opens Picker; release without selection cancels. Double tap performs Home immediately on the second press. In a command panel a single exits to numbers. Home disarms Auto and clears mirror.\n\n'
    legend += '| ID | Panel | Picker left position | Automatic application |\n|---|---|---|---|\n'
    for x in registry['layers']:
        legend += f"| {x['id']} | {x['name']} | {','.join(map(str,x['selector']))} | {', '.join(x.get('bundle_ids', [])) or 'Manual'} |\n"
    legend += '\nPicker2,4 selects Auto. Picker2,5 performs Home. Left/right inner thumbs3,5 and7,5 hold Mirror in command panels and Picker. The right middle thumb keeps its symbols role. Selecting an app panel manually pins it; Auto follows apps only after deliberate Auto selection. Picker15 can be latched deliberately and cancelled by Menu.\n'
    for x in registry['layers'][6:]:
        legend += f"\n## {x['id']}: {x['name']}\n\n| Left position | Action | Keycode |\n|---|---|---|\n"
        for pos,label in labels[x['id']].items():
            r,c = map(int,pos.split(','))
            if r < 4:
                legend += f"| {pos} | {label} | `{baseline['layout'][x['id']][r][c]}` |\n"
    legend += '\n' + '\n'.join('- '+x for x in registry['action_limits']) + '\n\nStandard shortcuts: [Apple keyboard shortcuts](https://support.apple.com/en-us/102650). No shortcut, microphone, dictation or typing action was executed during generation/tests.\n'
    diff = '# Exact preset migration\n\nInput: `' + registry['source'] + '`.\n\nBaseline16 appends layers6..15 and their encoders. Every original layer/encoder cell and every other JSON field is identical. Experimental16 differs from baseline16 at exactly one path:\n\n- `layout[0][3][5]`: `KC_SPACE` → `USER03`, tap Space / hold Mirror.\n\nNo home-row timing, Tap Dance, combo, macro, override or core setting changes. Sixteen layers leave815 macro bytes; this source has16 empty macro slots. Future flashing requires the explicit upgrade/import/readback procedure. These files have not been loaded onto the keyboard.\n'
    files = {KEYMAP/'command_registry.h': header, KEYMAP/'command_keymaps.h': keymaps, KEYMAP/'command_settings.h':settings,
             Path('tools/CommandModeHelper/Sources/CommandModeCore/Registry.generated.swift'):swift,
             PRESETS/'baseline16.vil':dump(baseline), PRESETS/'experimental16.vil':dump(experimental), PRESETS/'legend.md':legend, PRESETS/'migration.md':diff}
    manifest = {'registry_sha256':digest(canonical), 'registry_hash_u32':hash32, 'source_sha256':digest(source_bytes), 'source':registry['source'], 'baseline_preserves_first_six':True,
                'experimental_changes':[{'path':'layout[0][3][5]','before':'KC_SPACE','after':'USER03'}],
                'files':{str(path):digest(content.encode()) for path,content in files.items()}}
    files[PRESETS/'manifest.json'] = dump(manifest)
    files[PRESETS/'SHA256SUMS'] = ''.join(digest(content.encode())+'  '+path.name+'\n' for path,content in files.items() if path.parent==PRESETS)
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['generate','check'])
    args = parser.parse_args()
    failed = []
    for path,content in generate().items():
        target = ROOT/path
        if args.command == 'generate':
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
        elif not target.exists() or target.read_text()!=content:
            failed.append(str(path))
    if failed:
        parser.exit(1, 'Generated assets differ: '+', '.join(failed)+'\n')
    print('Command-mode registry, presets and generated assets '+('verified' if args.command=='check' else 'generated'))


if __name__ == '__main__':
    main()
