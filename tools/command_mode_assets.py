#!/usr/bin/env python3
"""Generate/check the single registry, exact Vial presets and readable legend."""
import argparse
import copy
import hashlib
import json
import re
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
    if [x['id'] for x in layers if x.get('automatic')] != [0, *range(6, 11)]:
        raise ValueError('automatic allowlist must be0 and6..10')
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
    if set(bundles) & set(registry['transient_bundle_ids']):
        raise ValueError('mapped application cannot also be transient')
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
    # Vial exports legacy spellings; the pinned C headers use these aliases.
    aliases = {'FN_MO23':'TL_UPPR', 'KC_LBRACKET':'KC_LBRC', 'KC_RBRACKET':'KC_RBRC',
               'KC_LSHIFT':'KC_LSFT', 'KC_RSHIFT':'KC_RSFT', 'KC_BSPACE':'KC_BSPC',
               'KC_SCOLON':'KC_SCLN', 'KC_LCTRL':'KC_LCTL', 'KC_RCTRL':'KC_RCTL',
               'KC_BSLASH':'KC_BSLS', 'KC_PGDOWN':'KC_PGDN'}
    return re.sub(r'\b[A-Z][A-Z0-9_]*\b', lambda match: aliases.get(match[0], match[0]), value)


def keycap(value):
    match = re.search(r'KC_[A-Z0-9_]+', str(value))
    code = match[0] if match else str(value)
    names = {'KC_ESCAPE':'Esc', 'KC_BSPACE':'Bksp', 'KC_SPACE':'Space', 'KC_ENTER':'Enter',
             'KC_LSHIFT':'Shift', 'KC_RSHIFT':'Shift', 'KC_LCTRL':'Ctrl', 'KC_RCTRL':'Ctrl',
             'KC_LALT':'Option', 'KC_RALT':'Option', 'KC_LGUI':'Cmd', 'KC_RGUI':'Cmd',
             'KC_SCOLON':';', 'KC_QUOTE':"'", 'KC_COMMA':',', 'KC_DOT':'.',
             'KC_SLASH':'/', 'KC_LBRACKET':'[', 'KC_RBRACKET':']', 'KC_TAB':'Tab',
             'TG(1)':'Menu', 'FN_MO23':'Fn'}
    return names.get(code, code.removeprefix('KC_'))


def legend_html(registry, baseline, labels):
    payload = json.dumps({'registry':registry, 'layout':baseline['layout'], 'labels':labels}, ensure_ascii=False).replace('<', '\\u003c')
    return '''<!doctype html>
<html lang="en" data-theme="luxury"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Corne command map</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/daisyui@5.5.19/daisyui.css">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/daisyui@5.5.19/themes.css">
<script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4.2.4/dist/index.global.js"></script>
<style>
*{box-sizing:border-box}html,body{margin:0;background:var(--color-base-100,#111);color:var(--color-base-content,#eee);font-family:system-ui,sans-serif}main{max-width:1220px;margin:auto;padding:40px 24px}h1{font-size:clamp(30px,5vw,56px);line-height:1.1;letter-spacing:-.04em;margin:8px 0 18px}p{line-height:1.6;overflow-wrap:anywhere}.toolbar{display:flex;gap:20px;align-items:center;flex-wrap:wrap;margin:30px 0 18px}.toolbar>*{min-width:0}select{max-width:100%}.keyboard{background:var(--color-base-200,#181818);border:1px solid var(--color-base-300,#333);border-radius:20px;padding:20px}svg{width:100%;height:auto;display:block}svg text{fill:var(--color-base-content,#eee);text-anchor:middle;font-size:12px;font-family:system-ui,sans-serif}svg .base{opacity:.55;font-size:10px}svg rect{fill:var(--color-base-100,#111);stroke:var(--color-base-300,#444);stroke-width:1.5}svg .control{stroke:var(--color-primary,#cfae72);stroke-width:2.5}.notes{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px;margin-top:24px}.notes>*{min-width:0}.note{padding:20px;border-top:2px solid var(--color-primary,#cfae72);background:var(--color-base-200,#181818);border-radius:0 0 12px 12px}.note h2{font-size:18px;margin:0 0 8px}.note p{font-size:14px;margin:0}.muted{opacity:.65;font-size:13px}.details{min-height:54px;padding-top:14px}button{cursor:pointer}a{color:var(--color-primary,#cfae72)}@media(max-width:680px){main{padding:24px 12px}.keyboard{padding:8px}.notes{grid-template-columns:minmax(0,1fr)}svg text{font-size:12px}.muted{font-size:12px}}
</style></head><body><main>
<div class="badge badge-outline">REFERENCE · PRE-FLASH CANDIDATE</div>
<h1>Your Corne command map</h1>
<p>Hold the left <strong>Menu thumb</strong>, choose a panel, then release. Double-tap Menu to return Home.</p>
<div class="toolbar"><label for="layer">Show panel <select id="layer" class="select select-bordered"></select></label><button id="theme" class="btn btn-sm btn-ghost">Light / dark</button><span id="mode" class="badge badge-outline"></span></div>
<div class="keyboard"><svg id="keyboard" viewBox="-12 -15 1100 365" role="img" aria-label="Corne physical keyboard command legend"><title>Physical key positions, with base keycaps above their selected actions</title></svg></div>
<p class="details" id="detail" aria-live="polite">Hover or focus a key to read its full action. Small labels show your usual base keycap.</p>
<div class="notes">
<section class="note" id="menu-note"><h2>One reliable way Home</h2><p>Menu taps toggle numbers after the 200ms double-tap window. Hold 200ms for Picker. Release without choosing to cancel. Double-tap performs Home immediately on the second press.</p></section>
<section class="note" id="auto-note"><h2>Auto is deliberate</h2><p>In Picker, left V selects Auto. App focus then chooses a panel. Left B selects Home, which disarms Auto. Manual Mouse, Review and other panels stay pinned.</p></section>
<section class="note" id="mirror-note"><h2>Both hands have controls</h2><p>Command clusters are duplicated on both halves. The inner thumbs hold Mirror in command panels. Normal Space stays Space; only experimental16 adds tap Space / hold Mirror while typing.</p></section>
</div>
<p class="muted">Preview only. This page never connects to your keyboard. The first six layers match your saved configuration. New physical behavior and KeyPeek high-layer display remain pending a later flash test.</p>
<p class="muted">Source: config/command-mode.json and the fresh Vial backup. <a href="legend.md">Text legend</a> · <a href="migration.md">Exact preset changes</a></p>
</main><script id="data" type="application/json">''' + payload + '''</script><script>
const data=JSON.parse(document.getElementById('data').textContent),ns='http://www.w3.org/2000/svg';
const select=document.getElementById('layer'),svg=document.getElementById('keyboard'),detail=document.getElementById('detail');
const names={KC_ESCAPE:'Esc',KC_BSPACE:'Bksp',KC_SPACE:'Space',KC_ENTER:'Enter',KC_LSHIFT:'Shift',KC_RSHIFT:'Shift',KC_LCTRL:'Ctrl',KC_RCTRL:'Ctrl',KC_LALT:'Opt',KC_RALT:'Opt',KC_LGUI:'Cmd',KC_RGUI:'Cmd',KC_SCOLON:';',KC_QUOTE:"'",KC_COMMA:',',KC_DOT:'.',KC_SLASH:'/',KC_LBRACKET:'[',KC_RBRACKET:']','TG(1)':'Menu',FN_MO23:'Fn'};
function cap(code){const m=String(code).match(/KC_[A-Z0-9_]+/);const k=m?m[0]:String(code);return names[k]??k.replace(/^KC_/,'')}
function el(tag,attrs,text){const e=document.createElementNS(ns,tag);for(const[k,v]of Object.entries(attrs))e.setAttribute(k,v);if(text)e.textContent=text;return e}
data.registry.layers.forEach(x=>{const o=document.createElement('option');o.value=x.id;o.textContent=x.id+' · '+x.name;select.append(o)});select.value=15;
function render(){svg.replaceChildren(el('title',{},'Corne keycaps and command actions'));const id=Number(select.value),entry=data.registry.layers[id];document.getElementById('mode').textContent=id===15?'Picker':id===0?'Typing / Raycast in Auto':entry.automatic?'Manual or Auto panel':id<6?'Original saved layer':'Manual panel';
for(let r=0;r<8;r++)for(let c=0;c<7;c++){const code=data.layout[id][r][c];if(code===-1)continue;const side=r>=4,local=r%4;let x=side?600+(5-c)*72:c*72,y=local*74+[35,35,18,0,18,28,0][c];if(c===6){x=side?514:442;y=local*74+112}if(local===3){x=side?600+(5-c)*72:c*72;y=280}
const base=cap(data.layout[0][r][c]);let label=data.labels[id]?.[r+','+c]??(code==='KC_NO'?'Unused':cap(code));if(r===3&&c===3)label='Menu';const control=String(code).startsWith('USER')||(r===3&&c===3);const g=el('g',{id:'key-'+r+'-'+c,tabindex:'0',role:'button','aria-label':base+': '+label});g.append(el('title',{},base+': '+label+' · '+code+' · matrix '+r+','+c));const rect=el('rect',{x,y,width:62,height:62,rx:10,class:control?'control':''});if(id>=6&&code!=='KC_NO')rect.style.fill='color-mix(in srgb,var(--color-base-100) 82%,hsl('+Math.round(entry.hue*360/255)+' 85% 55%))';g.append(rect,el('text',{x:x+31,y:y+16,class:'base'},base));
const words=label.split(' '),lines=[];let line='';for(const w of words){if((line+' '+w).trim().length>9&&line){lines.push(line);line=w}else line=(line+' '+w).trim()}if(line)lines.push(line);lines.slice(0,2).forEach((t,i)=>g.append(el('text',{x:x+31,y:y+35+i*15},t.length>9?t.slice(0,8)+'…':t)));
const show=()=>detail.textContent=base+' · '+label+' · '+code+' · matrix '+r+','+c;g.addEventListener('mouseenter',show);g.addEventListener('focus',show);svg.append(g)}
}
select.addEventListener('change',render);document.getElementById('theme').onclick=()=>document.documentElement.dataset.theme=document.documentElement.dataset.theme==='luxury'?'light':'luxury';render();
</script></body></html>
'''


def generate():
    registry, source, physical, source_bytes, canonical = read_registry()
    baseline, experimental, labels = make_presets(registry, source, physical)
    hash32 = int.from_bytes(hashlib.sha256(canonical).digest()[:4], 'little')
    banner = '// Generated by tools/command_mode_assets.py; do not edit.\n'
    header = banner + '#pragma once\n#include <stdint.h>\n#include <stdbool.h>\n'
    header += f'#define CM_LAYER_COUNT 16\n#define CM_GENERIC_LAYER 6\n#define CM_PICKER_LAYER 15\n#define CM_REGISTRY_HASH UINT32_C(0x{hash32:08X})\n'
    automatic_mask = sum(1 << x['id'] for x in registry['layers'] if x.get('automatic'))
    header += f'#define CM_AUTOMATIC_LAYER_MASK UINT16_C(0x{automatic_mask:04X})\n'
    header += 'static inline bool cm_auto_layer_valid(uint8_t layer) { return layer < CM_LAYER_COUNT && (CM_AUTOMATIC_LAYER_MASK & (UINT16_C(1) << layer)); }\n'
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
    swift += f'    public static let automaticLayerMask: UInt16 = 0x{automatic_mask:04X}\n'
    swift += '    public static func allowsAutomaticLayer(_ layer: UInt8) -> Bool {\n        layer < 16 && automaticLayerMask & (UInt16(1) << layer) != 0\n    }\n'
    swift += '    public static func layer(forBundleID bundleID: String) -> UInt8 {\n        entries.first { $0.bundleIDs.contains(bundleID) }?.id ?? 6\n    }\n}\n'
    legend = '# Corne command-mode legend\n\nGenerated from `config/command-mode.json`. Matrix coordinates are row,column, not keycap names. Both halves offer the same command clusters. The original six layers are preserved in baseline16.\n\n'
    legend += 'Menu is the left outer thumb. Tap toggles numbers after the 200ms double-tap window. Hold 200ms opens Picker; release without selection cancels. Double tap performs Home immediately on the second press. In a command panel a single exits to numbers. Home disarms Auto and clears mirror.\n\n'
    legend += '| ID | Panel | Left keycap in Picker | Matrix | Automatic application |\n|---|---|---|---|---|\n'
    for x in registry['layers']:
        r,c=x['selector']
        legend += f"| {x['id']} | {x['name']} | {keycap(source['layout'][0][r][c])} | {r},{c} | {', '.join(x.get('bundle_ids', [])) or 'Manual'} |\n"
    legend += '\nIn Picker, left V selects Auto and left B performs Home. The inner thumbs hold Mirror in command panels and Picker. The right middle thumb keeps its symbols role. Command clusters are duplicated on both halves, so Mouse provides pointer, scroll, buttons and speed without the right hand. Normal Space stays Space; experimental16 alone changes typing Space to tap Space / hold Mirror. Selecting an app panel manually pins it; Auto follows apps only after deliberate Auto selection. Raycast temporarily uses the existing Typing layer while Auto stays armed; leaving Raycast follows the next foreground app. Picker15 can be latched deliberately and cancelled by Menu.\n'
    for x in registry['layers'][6:]:
        legend += f"\n## {x['id']}: {x['name']}\n\n| Left keycap | Matrix | Action | Keycode |\n|---|---|---|---|\n"
        for pos,label in labels[x['id']].items():
            r,c = map(int,pos.split(','))
            if r < 4:
                legend += f"| {keycap(source['layout'][0][r][c])} | {pos} | {label} | `{baseline['layout'][x['id']][r][c]}` |\n"
    legend += '\n' + '\n'.join('- '+x for x in registry['action_limits']) + '\n\nStandard shortcuts: [Apple keyboard shortcuts](https://support.apple.com/en-us/102650). No shortcut, microphone, dictation or typing action was executed during generation/tests.\n'
    diff = '# Exact preset migration\n\nInput: `' + registry['source'] + '`.\n\nBaseline16 appends layers6..15 and their encoders. Every original layer/encoder cell and every other JSON field is identical. Experimental16 differs from baseline16 at exactly one path:\n\n- `layout[0][3][5]`: `KC_SPACE` → `USER03`, tap Space / hold Mirror.\n\nNo home-row timing, Tap Dance, combo, macro, override or core setting changes. Sixteen layers leave815 macro bytes; this source has16 empty macro slots. Future flashing requires the explicit upgrade/import/readback procedure. These files have not been loaded onto the keyboard.\n'
    files = {KEYMAP/'command_registry.h': header, KEYMAP/'command_keymaps.h': keymaps, KEYMAP/'command_settings.h':settings,
             Path('tools/CommandModeHelper/Sources/CommandModeCore/Registry.generated.swift'):swift,
             PRESETS/'baseline16.vil':dump(baseline), PRESETS/'experimental16.vil':dump(experimental), PRESETS/'legend.md':legend, PRESETS/'legend.html':legend_html(registry,baseline,labels), PRESETS/'migration.md':diff}
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
