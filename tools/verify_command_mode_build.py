#!/usr/bin/env python3
"""Verify the actual RP2040 UF2, USB descriptor, layer storage and ELF symbols."""
import argparse
import hashlib
import json
from pathlib import Path
import struct


class Elf:
    def __init__(self, path):
        self.data = path.read_bytes()
        if self.data[:6] != b'\x7fELF\x01\x01':
            raise ValueError('expected little-endian ELF32')
        header = struct.unpack_from('<16sHHIIIIIHHHHHH', self.data)
        if header[2] != 40:
            raise ValueError('expected ARM ELF')
        self.sections = [struct.unpack_from('<IIIIIIIIII', self.data, header[6]+i*header[11]) for i in range(header[12])]
        names = self.sections[header[13]]
        string_table = self.data[names[4]:names[4]+names[5]]
        self.section_names = {string_table[s[0]:].split(b'\0',1)[0].decode():s for s in self.sections}
        self.symbols = {}
        for section in self.sections:
            if section[1] != 2: continue
            strings = self.sections[section[6]]
            table = self.data[strings[4]:strings[4]+strings[5]]
            for offset in range(section[4],section[4]+section[5],section[9]):
                name,value,size,info,_,index = struct.unpack_from('<IIIBBH',self.data,offset)
                name = table[name:].split(b'\0',1)[0].decode()
                if name and index < len(self.sections): self.symbols[name] = (value,size,index,info)

    def read(self, address, length):
        for section in self.sections:
            if section[1] != 8 and section[3] <= address and address+length <= section[3]+section[5]:
                offset = section[4]+address-section[3]
                return self.data[offset:offset+length]
        raise ValueError(f'address not backed by ELF bytes: {address:#x}')

    def symbol(self, name):
        address,size,_,info = self.symbols[name]
        return self.read(address & ~1 if info & 15 == 2 else address,size)


def verify(elf_path, uf2_path):
    elf = Elf(elf_path)
    expected_sizes = {'layer_state':2,'default_layer_state':2,'keymaps':1792,'encoder_map':256,
                      'hand_swap_config':112,'encoder_hand_swap_config':4}
    for symbol,size in expected_sizes.items():
        if elf.symbols[symbol][1] != size: raise ValueError(f'{symbol} expected {size} bytes')
    descriptor = elf.symbol('DeviceDescriptor')
    if len(descriptor)!=18 or descriptor[:2]!=b'\x12\x01' or struct.unpack_from('<HHH',descriptor,8)!=(0x4653,4,0x0411):
        raise ValueError('USB VID/PID/release descriptor mismatch')
    if 'Corne v4 CM1'.encode('utf-16le') not in elf.data:
        raise ValueError('supported product marker missing from built USB string')
    address = elf.symbols['nvm_dynamic_keymap_macro_size'][0] & ~1
    instruction = struct.unpack('<H',elf.read(address,2))[0]
    if instruction & 0xFF00 != 0x4800:
        raise ValueError('macro-size return instruction needs review for this compiler')
    literal = ((address+4)&~3)+(instruction&255)*4
    capacity = struct.unpack('<I',elf.read(literal,4))[0]
    if capacity!=815: raise ValueError(f'expected 815 macro bytes, found {capacity}')
    for symbol in ('keypeek_handle_command','keypeek_send_layer_state','command_mode_pre_action',
                   'command_mode_storage_bootstrap','command_mode_handle_report','action_tapping_is_idle'):
        if symbol not in elf.symbols: raise ValueError('required linked symbol missing: '+symbol)
    uf2 = uf2_path.read_bytes()
    if not uf2 or len(uf2)%512: raise ValueError('UF2 size is not full blocks')
    blocks = len(uf2)//512
    addresses = []
    for index in range(blocks):
        block=uf2[index*512:(index+1)*512]
        magic0,magic1,flags,address,length,number,total,family=struct.unpack_from('<8I',block)
        if (magic0,magic1,struct.unpack_from('<I',block,508)[0]) != (0x0A324655,0x9E5D5157,0x0AB16F30):
            raise ValueError('invalid UF2 magic')
        if flags != 0x2000 or family!=0xE48BFF56 or number!=index or total!=blocks or length!=256:
            raise ValueError('UF2 family, count, order or payload mismatch')
        if not 0x10000000<=address<=0x10200000-length: raise ValueError('UF2 outside RP2040 flash')
        addresses.append(address)
    if addresses != list(range(addresses[0],addresses[0]+blocks*256,256)):
        raise ValueError('UF2 addresses are not contiguous and unique')
    return {'uf2_sha256':hashlib.sha256(uf2).hexdigest(),'uf2_bytes':len(uf2),'uf2_blocks':blocks,
            'elf_sha256':hashlib.sha256(elf.data).hexdigest(),'linked_sizes':expected_sizes,
            'macro_bytes':capacity,'layer_count':16,'layer_mask_bytes':2,'usb_release':'0x0411',
            'product':'Corne v4 CM1','ram_bss_bytes':elf.section_names['.bss'][5],
            'ram_data_bytes':elf.section_names['.data'][5],'heap_available_bytes':elf.section_names['.heap'][5]}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--elf',type=Path,required=True)
    parser.add_argument('--uf2',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(verify(args.elf,args.uf2),indent=2))
