VIA_ENABLE         = yes
VIAL_ENABLE        = yes
VIALRGB_ENABLE     = yes
ENCODER_MAP_ENABLE = yes
RAW_ENABLE        = yes

# Preserve effect buffers while applying the layer indicator at output time.
RGB_MATRIX_DRIVER = custom
WS2812_DRIVER_REQUIRED = yes

ifeq ($(KEYBOARD),tmp/crkbd/rev4_1/standard)
OPT_DEFS += -DCOMMAND_MODE_ENABLE
SWAP_HANDS_ENABLE = yes
SRC += command_state.c command_protocol.c command_qmk.c storage_bootstrap.c
endif
