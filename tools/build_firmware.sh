#!/usr/bin/env bash
# Rebuild the web flasher's images (web/firmware/*.bin + web/manifest.json).
#
# PlatformIO runs from a throwaway venv and keeps its toolchain inside the
# gitignored .pio/ folder, so nothing is installed system-wide or into ~.
# Run it after changing src/ or data/clawd/, then commit web/firmware/ and
# web/manifest.json. The first run downloads the ESP32 toolchain (~1 GB).
set -euo pipefail

PIO_VERSION="6.2.0"
ENV_NAME="cyd"

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$REPO/.pio/pio-venv"
BUILD="$REPO/.pio/build/$ENV_NAME"
OUT="$REPO/web/firmware"
export PLATFORMIO_CORE_DIR="$REPO/.pio/core"

if ! "$VENV/bin/pio" --version 2>/dev/null | grep -q "version $PIO_VERSION\$"; then
  echo "==> PlatformIO $PIO_VERSION (venv in .pio/pio-venv)"
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install --quiet --upgrade "platformio==$PIO_VERSION"
fi
PIO="$VENV/bin/pio"

cd "$REPO"
echo "==> firmware"
"$PIO" run -e "$ENV_NAME"
echo "==> LittleFS image from data/clawd/"
"$PIO" run -e "$ENV_NAME" -t buildfs

mkdir -p "$OUT"
rm -f "$OUT"/*.bin
cp "$BUILD/bootloader.bin" "$BUILD/partitions.bin" "$BUILD/firmware.bin" \
   "$BUILD/littlefs.bin" "$OUT/"
cp "$PLATFORMIO_CORE_DIR/packages/framework-arduinoespressif32/tools/partitions/boot_app0.bin" "$OUT/"

# Manifest: the same flash map `pio run -t upload` + `-t uploadfs` write
# (bootloader / partitions / boot_app0 / app from PlatformIO's
# FLASH_EXTRA_IMAGES, the LittleFS image at its partitions.csv offset).
# Separate images on purpose: a merged one would fill the gaps with 0xFF and
# wipe NVS (0x9000), i.e. the token, calibration and stats, on every update.
VERSION="$(git -C "$REPO" describe --always --dirty --tags)"
python3 - "$REPO" "$VERSION" <<'EOF'
import csv, json, os, sys

repo, version = sys.argv[1], sys.argv[2]
parts = {}
with open(os.path.join(repo, "partitions.csv")) as f:
    for row in csv.reader(l for l in f if l.strip() and not l.startswith("#")):
        name, _type, _sub, off, size = (c.strip() for c in row[:5])
        parts[name] = (int(off, 0), int(size, 0))

fw = os.path.join(repo, "web", "firmware")
size = lambda n: os.path.getsize(os.path.join(fw, n))
app_off, app_max = parts["app0"]
fs_off, fs_size = parts["littlefs"]
assert app_off == 0x10000, "app0 moved: update the manifest map"
if size("firmware.bin") > app_max:
    sys.exit("firmware.bin (%d B) overflows app0 (%d B)" % (size("firmware.bin"), app_max))
if size("littlefs.bin") != fs_size:
    sys.exit("littlefs.bin is %d B, the partition is %d B" % (size("littlefs.bin"), fs_size))

manifest = {
    "name": "CYD Claude Buddy",
    "version": version,
    "new_install_prompt_erase": True,
    "new_install_improv_wait_time": 0,
    "builds": [{
        "chipFamily": "ESP32",
        "parts": [
            {"path": "firmware/bootloader.bin", "offset": 0x1000},
            {"path": "firmware/partitions.bin", "offset": 0x8000},
            {"path": "firmware/boot_app0.bin", "offset": 0xE000},
            {"path": "firmware/firmware.bin", "offset": app_off},
            {"path": "firmware/littlefs.bin", "offset": fs_off},
        ],
    }],
}
with open(os.path.join(repo, "web", "manifest.json"), "w") as f:
    json.dump(manifest, f, indent=2)
    f.write("\n")
print("firmware.bin %d / %d B of app0 (%.0f%%)" % (
    size("firmware.bin"), app_max, 100.0 * size("firmware.bin") / app_max))
EOF

(cd "$OUT" && sha256sum *.bin > SHA256SUMS)
echo "==> web/firmware/ + web/manifest.json updated ($VERSION)"
