#!/bin/sh
set -eu

tool_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
firmware_dir="$tool_dir/../software"

if command -v mpremote >/dev/null 2>&1; then
    mpremote_cmd=mpremote
elif [ -x "$tool_dir/../.venv-mpremote/bin/mpremote" ]; then
    mpremote_cmd="$tool_dir/../.venv-mpremote/bin/mpremote"
else
    echo "mpremote is not installed. Run: python3 -m pip install mpremote" >&2
    exit 1
fi

cd "$firmware_dir"

# mkdir reports an error when a directory already exists; that is harmless.
for remote_dir in :lib :lib/usb :lib/usb/device; do
    "$mpremote_cmd" connect auto fs mkdir "$remote_dir" >/dev/null 2>&1 || true
done

"$mpremote_cmd" connect auto fs cp ./*.py :
"$mpremote_cmd" connect auto fs cp ./lib/usb/__init__.py :lib/usb/__init__.py
"$mpremote_cmd" connect auto fs cp ./lib/usb/device/*.py :lib/usb/device/
"$mpremote_cmd" connect auto reset

echo "MK9 MicroPython firmware uploaded and reset."
