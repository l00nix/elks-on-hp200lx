#!/usr/bin/env bash
# Compile the production bridge with diagnostics disabled and compare its bytes.
set -euo pipefail
KIT=$(cd "$(dirname "$0")/.." && pwd)
WORK=$(cd "$1" && pwd)
BIN="$WORK/cross/bin/ia16-elf"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
sed '/#define CONFIG_HP200LX_STACK_DIAG /d' "$WORK/include/autoconf.h" > "$TMP/autoconf.h"
"$BIN-gcc" -E -traditional -I"$TMP" -I"$WORK/include" -I"$WORK/elks/include" -I"$WORK/libc/include" -D__KERNEL__ "$WORK/elks/arch/i86/kernel/hp200lx-fw-asm.S" > "$TMP/bridge.s"
"$BIN-as" -mtune=i8086 --32-segelf -o "$TMP/bridge.o" "$TMP/bridge.s"
"$BIN-ld" -T "$KIT/tests/abi.ld" -o "$TMP/bridge.elf" "$TMP/bridge.o"
"$BIN-objcopy" -O binary "$TMP/bridge.elf" "$TMP/bridge.bin"
cmp "$TMP/bridge.bin" "$KIT/build/abi.bin"
"$BIN-gcc" -ffreestanding -fno-inline -melks -mcmodel=small -msegment-relocation-stuff -mtune=i8086 -Os -I"$TMP" -I"$WORK/include" -I"$WORK/elks/include" -I"$WORK/libc/include" -D__KERNEL__ -c "$WORK/elks/arch/i86/kernel/hp200lx-fw.c" -o "$TMP/platform.o"
echo 'PASS: diagnostic-off bridge matches 3.5.1; platform C compiles.'
