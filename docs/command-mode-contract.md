# Selected implementation contract

Root selects candidate A's compact firmware reducer, with B's explicit picker suspension, release collision tests, and quiescence guard. No generic policy stack or automatic legacy EEPROM migration. The independent judge may identify corrections before integration.

## Registry and ownership

Root owns `config/command-mode.json`, `tools/command_mode_assets.py`, generated assets, exact presets, source boot/admission patches and build integration. Firmware worker owns `keyboards/crkbd/vial-kb/vial-qmk/keymaps/vial/command_*.[ch]`, integration changes to that keymap's keymap.c/config.h/rules.mk, and `tests/command_mode*`. Swift worker owns `tools/CommandModeHelper/` except generated `Sources/CommandModeCore/Registry.generated.swift` owned by root. No worker writes another owner's files, the original checkout, or any device.

IDs: 0 Typing, 1 Numbers, 2 Symbols, 3 Maintenance, 4 Reserved 4, 5 Reserved 5, 6 Generic, 7 OpenAI desktop, 8 Claude, 9 Browser, 10 Editor, 11 Mouse, 12 Review, 13 Experiments, 14 Spare, 15 Picker. Auto Command is a selector action, not a layer. Only IDs6..10 are valid host contexts. Root-generated `command_registry.h` supplies `CM_LAYER_COUNT=16`, `CM_GENERIC_LAYER=6`, `CM_PICKER_LAYER=15`, `CM_REGISTRY_HASH` uint32, `cm_auto_layer_valid(uint8_t)`, palette/table names. Generated Swift `CommandRegistry` supplies the same IDs/hash, bundle lookup and transient/configurator IDs. All first six saved matrices/encoders and all non-layout fields are exact in baseline16.

Custom keycode values: `CM_HOME=QK_KB_0` (0x7E00), `CM_AUTO=QK_KB_1`, `CM_MIRROR=QK_KB_2` hold only, `CM_SPACE_MIRROR=QK_KB_3` experimental tap Space/hold mirror. `CM_SELECT_0` starts at QK_USER_4 (0x7E44), followed by all16 IDs. Generated preset uses USER00..USER19 names; generated C maps to QK_KB_0 etc. Mirror is present on left and right command/picker controls. Menu is physical[3,3], paired[7,3] stays fixed in full swap involution.

## Firmware behavior

The reducer alone owns mode0 Typing,1 Manual,2 Auto; selected layer, picker return, epoch/revision, host lease, pending context and gesture. A separate QMK adapter translates roles and applies complete valid masks and swap state before KeyPeek notifications. Preserve QMK ordinary release/source/swap caches; custom consumed keys keep paired release ownership. Handle overlap of an old mirrored hold and a fresh unmirrored key resolving to the same logical position explicitly. Auto changes wait for all physical keys up and the actual QMK tapping pipeline idle; an invented fixed delay is not a proof.

Menu hold200ms opens15; release with no selection cancels. Single tap waits200ms after release for a possible double, toggles numbers in typing, or exits command mode into explicit numbers. Interruption before hold resolves the single before the ordinary press is finally looked up. Second Menu down inside the gap immediately performs absolute Home and consumes its release. Home disarms Auto, invalidates context, cancels picker, clears numbers/FN overlays and mirror; an already held control cannot re-enable until released and pressed again. FN_MO23 preserves symbols alone and maintenance with numbers; from a command panel it temporarily presents symbols. Source-layer cache refresh on a gesture-triggered change must use pinned QMK's actual cache functions.

Every keyboard selection, Home and picker boundary advances a32-bit epoch. Host contexts cannot arm Auto. Session restart/close/timeout pins last panel and disarms; picker freezes updates; cancel restores semantic parent with a fresh epoch. Hold/gesture clock arithmetic is wrap-safe. Lease=2000ms. Helper state polls every250ms. No focus/session operation writes EEPROM.

## Wire v1, 32-byte little-endian reports

Request bytes0..3 = D3 43 01 opcode. Bytes4..7 requestID nonzero u32,8..11 session u32,12..15 epoch u32,16..19 observation sequence u32,20 layer u8,21..31 zero. Exact32-byte size only. Opcodes1 CAPABILITIES,2 OPEN,3 STATE,4 CONTEXT,5 CLOSE. CAPABILITIES has no effects. OPEN requires random nonzero session from helper, disarms on a new session, retries are idempotent. STATE renews the current session lease without arming. CONTEXT requires current session/epoch and strictly newer sequence; valid IDs6..10 only. CLOSE disarms/releases this session.

Response bytes0..3 = D3 AC 01 opcode;4..7 requestID. CAPABILITIES:8 status,9 layer count16,10 caps0x0F,11 layer mask bytes2,12..19 exactVial UID89 36 2A C7 FA D8 89 45,20..23 registry hash,24..27 schema0x434D0001,28..31 zero.

Other replies:8 status,9 mode,10 selected layer,11 flags(bit0 picker,1 mirror,2 deferred,3 session active),12..15 current session,16..19 epoch,20..23 revision,24..25 applied layer mask,26 count16,27 caps0x0F,28..31 registry hash. Status0 OK,1 DEFERRED,2 DISARMED,3 STALE_EPOCH,4 STALE_SEQUENCE,5 INVALID_LAYER,6 BAD_REQUEST,7 WRONG_SESSION,8 BUSY_CONFIGURATION,9 UNSUPPORTED_VERSION. Malformed frames must not mutate authority. Ignore unrelated report families; reject unchanged request echoes. Firmware fills the existing via.c buffer, never sends a duplicate ACK. Cache last session request+response for harmless retry. Counter wrap requires renegotiation/disarm.

Only supported descriptors permit a capability request. Target build product marker `Corne v4 CM1`, device release0x0411, existingVID/PID/UID. Old descriptor produces zero output reports. Swift opens native nonseizing IOHID with none options, never C0 subscribes/unsubscribes, filters other families, serializes one request, bounded timeout/readback and visible status. Dry-run constructs only mock transport. Native Vial process presence proactively pauses/closes; explicit pause covers browser configurators. A checked pre-dispatch Vial hook revokes authority on non-helper/non-KeyPeek configuration traffic and returns busy during2s quiet period. No auto-rearm after pause/restart/reconnect. No autorun.

## Upgrade boundary

16 layers relocate settings/encoders/TD/macros. Do not implement transparent in-place migration. Root supplies a narrowly checked source patch before initial qmk_settings_init that validates the new fixed schema/build marker and initializes incompatible dynamic EEPROM before relocated settings can be read. Seed compiled personal baseline16 keymaps and captured QMK settings. Mark validity only after initialization completes, and re-run after interruption. Stable explicit build/schema ID avoids random-build resets. Later physical flash session must import reviewed baseline16/experimental16 in Vial and verify full settings. No reset/import/flash occurs now. Preserve old firmware and fresh6-layer export for rollback.

## Evidence

Actual reducer, protocol, QMK adapter/tapping/cache/release and lighting tests; mock old-device/no-HID-output tests; Swift test/build and real foreground observation with mock transport. 16-layer v4.1standard Vial build, storage/ELF/UF2 checks and relevant unchanged regressions. Root's passive nonseizing probe opened currentRawHID while KeyPeek stayed running and received C0 keepalive echoes, with zero output reports. This establishes read coexistence for that launch order only, not postflash mixed-write compatibility. Physical gesture, mirror, high-layer KeyPeek and mixed-client tests remain pending a later user flash.
