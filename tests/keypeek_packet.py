#!/usr/bin/env python3
"""Exercise the pinned KeyPeek module with actual sixteen-bit layer packets."""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT/'modules/srwi/keypeek_layer_notify'
pin = subprocess.check_output(['git','-C',str(MODULE),'rev-parse','HEAD'],text=True).strip()
assert pin == '8f120e29fec27a0aeb63b4c4f63c6a70e3225fb3'
with tempfile.TemporaryDirectory() as temporary:
    base=Path(temporary)
    (base/'test_qmk.h').write_text('''#pragma once
#include <stdint.h>
#include <stdbool.h>
typedef uint16_t layer_state_t;
typedef struct { struct { struct { uint8_t row,col; } key; bool pressed; } event; } keyrecord_t;
extern layer_state_t layer_state, default_layer_state;
uint32_t timer_read32(void);
uint32_t timer_elapsed32(uint32_t);
void raw_hid_send(uint8_t *, uint8_t);
#define ASSERT_COMMUNITY_MODULES_MIN_API_VERSION(a,b,c)
#define RAW_EPSIZE 32
''')
    for name in ('raw_hid.h','usb_descriptor.h','timer.h'):
        (base/name).write_text('#include "test_qmk.h"\n')
    (base/'test.c').write_text('''#include "test_qmk.h"
#include "keypeek_layer_notify.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
layer_state_t layer_state=0x8000,default_layer_state=1;
static uint32_t now; static unsigned count; static uint8_t report[32];
uint32_t timer_read32(void){return now;}
uint32_t timer_elapsed32(uint32_t then){return now-then;}
void raw_hid_send(uint8_t *bytes,uint8_t length){assert(length==32);memcpy(report,bytes,32);count++;}
layer_state_t layer_state_set_keypeek_layer_notify(layer_state_t);
bool process_record_keypeek_layer_notify(uint16_t,keyrecord_t*);
int main(void){
 uint8_t subscribe[]={0xC0,0xA1};assert(keypeek_handle_command(subscribe,2));
 assert(count==1&&report[0]==0xFF&&report[1]==2&&report[2]==1&&report[3]==0&&report[4]==0&&report[5]==0x80);
 for(unsigned layer=0;layer<16;layer++){uint16_t mask=1u<<layer;assert(layer_state_set_keypeek_layer_notify(mask)==mask);assert(report[4]==(mask&255)&&report[5]==(mask>>8));for(unsigned i=6;i<32;i++)assert(report[i]==0);}
 keyrecord_t key={.event={.key={7,6},.pressed=true}};assert(process_record_keypeek_layer_notify(0,&key));assert(report[0]==0xF1&&report[1]==7&&report[2]==6&&report[3]==1);
 unsigned previous=count;now=3000;layer_state_set_keypeek_layer_notify(2);assert(count==previous);
 assert(keypeek_handle_command(subscribe,2));assert(count==previous+1);
 uint8_t unsubscribe[]={0xC0,0xA0};assert(keypeek_handle_command(unsubscribe,2));previous=count;layer_state_set_keypeek_layer_notify(4);assert(count==previous);
 puts("Pinned KeyPeek: all16 layer bits, two-byte masks, zero padding, key events and original subscription lease passed");
}
''')
    subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=undefined',
                    '-I',str(base),'-I',str(MODULE),'-DQMK_KEYBOARD_H="test_qmk.h"',
                    '-DKEYPEEK_DISABLE_RAW_HID_HANDLER','-DRAW_ENABLE',str(MODULE/'keypeek_layer_notify.c'),
                    str(base/'test.c'),'-o',str(base/'test')],check=True)
    subprocess.run([str(base/'test')],check=True)
