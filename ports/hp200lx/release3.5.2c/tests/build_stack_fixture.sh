#!/usr/bin/env bash
# Use the exact diagnostic object from a completed kernel build.
set -euo pipefail
KIT=$(cd "$(dirname "$0")/.." && pwd)
WORK=$(cd "$1" && pwd)
BIN="$WORK/cross/bin/ia16-elf"
"$BIN-ld" -T "$KIT/tests/stack.ld" -o "$KIT/build/stack.elf" "$WORK/elks/arch/i86/kernel/hp200lx-fw-asm.o"
"$BIN-objcopy" -O binary "$KIT/build/stack.elf" "$KIT/build/stack.bin"
"$BIN-nm" "$KIT/build/stack.elf" > "$KIT/build/stack.map"
cp "$WORK/elks/include/arch/asm-offsets.h" "$KIT/build/asm-offsets.h"
