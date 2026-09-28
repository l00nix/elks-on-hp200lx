#!/usr/bin/env bash
# Exact upstream source + platform patch + separate socket compatibility.
set -euo pipefail
OVERLAY=$(cd "$(dirname "$0")" && pwd)
BASE=${BASE:-/home/arau/elks}
WORK=${WORK:-/home/arau/elks-hp200lx-release-3.5-rebuild}
REV=69dfd4f274139ef1f533c646711db84902b0cfe4
if [ -e "$WORK" ]; then
    echo "Refusing existing build directory: $WORK" >&2
    exit 1
fi
mkdir -p "$WORK"
if [ -f "$OVERLAY/upstream.tar" ]; then
    echo "f899555813310fbca73f012124d1057437a849e7c38acfaea2cd75147eeaeba9  $OVERLAY/upstream.tar" | sha256sum -c -
    tar -xf "$OVERLAY/upstream.tar" -C "$WORK"
else
    git -C "$BASE" archive "$REV" | tar -x -C "$WORK"
fi
ln -s "$(readlink -f "$BASE/cross")" "$WORK/cross"
cd "$WORK"
patch -p1 < "$OVERLAY/patches/0001-hp200lx-firmware-platform.patch"
patch -p1 < "$OVERLAY/patches/0002-hp200lx-pcmcia-cf.patch"
patch -p1 < "$OVERLAY/patches/0003-hp200lx-dos-load-base.patch"
cp "$OVERLAY/hp200lx.config" .config
export MAKEFLAGS=${MAKEFLAGS:-}
set +u
. ./env.sh
set -u
make elks/arch/i86/drivers/char/KeyMaps/config.in
make include/autoconf.h
make -C elks all
sha256sum elks/arch/i86/boot/Image
wc -c elks/arch/i86/boot/Image
