#!/usr/bin/env python3
"""Exercise a Vial preset through pinned QMK actions and captured host reports."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from command_mode_test import function

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from command_mode_assets import c_code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preset', type=Path, default=ROOT / 'presets/command-mode/baseline16.vil')
    args = parser.parse_args()
    preset = json.loads(args.preset.read_text())
    qmk = ROOT / 'src/vial-kb/vial-qmk'
    assert subprocess.check_output(['git', '-C', str(qmk), 'rev-parse', 'HEAD'], text=True).strip() == 'dd43959ae5c08d8a28d38a1acf7b04e86b14a344'
    assert {k:preset['settings'][k] for k in ('7','18','19','21','22','23','24','25','26','27')} == {'7':200,'18':0,'19':80,'21':0,'22':0,'23':0,'24':0,'25':200,'26':0,'27':0}
    quantum = qmk / 'quantum'
    keymap = ROOT / 'keyboards/crkbd/vial-kb/vial-qmk/keymaps/vial'
    action = (quantum / 'action.c').read_text().replace('__attribute__((weak)) ', '')
    tapping = (quantum / 'action_tapping.c').read_text()
    assert 'command_mode_pre_action(event)' in action
    assert 'command_mode_source_layer(key, &owned_layer)' in (quantum / 'action_layer.c').read_text()
    with tempfile.TemporaryDirectory(prefix='home-row-mods-') as tmp:
        work = Path(tmp)
        shutil.copy(ROOT / 'tests/command_mode_qmk_shim.h', work)
        with (work / 'command_mode_qmk_shim.h').open('a') as f:
            f.write((ROOT / 'tests/home_row_mods_shim.h').read_text())
        for name in ('action_code.h','modifiers.h','keycodes.h','action_tapping.h','quantum_keycodes.h','quantum_keycodes_legacy.h'):
            shutil.copy(quantum / name, work)
        shutil.copy(quantum / 'keymap_extras/keymap_us.h', work)
        shutil.copy(quantum / 'sequencer/sequencer.h', work)
        for name in ('usb_device_state.c','usb_device_state.h'):
            shutil.copy(qmk / 'tmk_core/protocol' / name, work)
        for name in ('action.h','action_layer.h','action_util.h','keycode.h','timer.h'):
            (work / name).write_text('#include "command_mode_qmk_shim.h"\n')
        matrix = 'const uint16_t preset_maps[16][8][7] = {\n'
        matrix += ',\n'.join('{'+','.join('{'+','.join(c_code(v) for v in row)+'}' for row in layer)+'}' for layer in preset['layout'])+'\n};\n'
        (work / 'preset.h').write_text(matrix)
        (work / 'qmk_tapping.c').write_text('#include "command_mode_qmk_shim.h"\n' + tapping)
        wrappers = '#include "command_mode_qmk_shim.h"\n#include "command_qmk.h"\n#include "action_tapping.h"\n'
        wrappers += 'bool disable_action_cache, swap_hands, swap_held;\nuint8_t source_layers_cache[7][MAX_LAYER_BITS], encoder_source_layers_cache[1][MAX_LAYER_BITS];\nstatic uint8_t real_mods, weak_mods;\n'
        for name in ('action_exec','should_swap_hands','set_swap_hands_state','process_hand_swap','swap_hands_on','swap_hands_off','is_swap_hands_on','process_record','process_record_handler','is_tap_record','is_tap_action','process_action','register_code','unregister_code','register_mods','unregister_mods','tap_code','tap_code_delay'):
            wrappers += function(action, name)
        for source,names in (
            ('action_layer.c', ('update_source_layers_cache_impl','read_source_layers_cache_impl','update_source_layers_cache','read_source_layers_cache','store_or_get_action','layer_switch_get_layer','layer_switch_get_action')),
            ('keymap_common.c', ('action_for_key','action_for_keycode')),
            ('quantum.c', ('get_record_keycode','get_event_keycode','pre_process_record_quantum','process_record_quantum','post_process_record_quantum')),
            ('action_util.c', ('get_mods','add_mods','del_mods','set_mods','clear_mods','get_weak_mods','add_weak_mods','del_weak_mods','clear_weak_mods'))):
            text = (quantum / source).read_text()
            for name in names:
                wrappers += function(text, name)
        for name in ('process_record_user','post_process_record_user'):
            wrappers += function((keymap / 'keymap.c').read_text(), name)
        (work / 'qmk_wrappers.c').write_text(wrappers)
        command = ['clang','-std=gnu11','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-Wno-unused-function','-Wno-missing-field-initializers','-fsanitize=undefined','-fno-sanitize-recover=all','-g','-I',str(work),'-I',str(keymap),'-include',str(work/'command_mode_qmk_shim.h'),str(work/'qmk_wrappers.c'),str(work/'qmk_tapping.c'),str(work/'usb_device_state.c'),str(keymap/'command_state.c'),str(keymap/'command_protocol.c'),str(keymap/'command_qmk.c'),str(ROOT/'tests/home_row_mods.c'),'-o',str(work/'test')]
        subprocess.run(command,check=True)
        print('Preset under test: '+str(args.preset),flush=True)
        subprocess.run([str(work/'test')],check=True)


if __name__ == '__main__':
    main()
