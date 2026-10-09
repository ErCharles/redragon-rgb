#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
STAGE=$(mktemp -d)
trap 'rm -rf "$STAGE"' EXIT
OUT="$ROOT/dist"
mkdir -p "$OUT"

pack() {
  name=$1
  src=$STAGE/$name/Teclado
  mkdir -p "$src/programa"
  cp "$ROOT/kb.py" "$ROOT/presets.py" "$ROOT/win_hid.py" "$ROOT/LICENSE" "$src/programa/"
  if [ "$name" = windows ]; then
    cp "$ROOT/descarga/windows/1. Lee esto.txt" "$src/1. Lee esto.txt"
    cp "$ROOT/Instalar.bat" "$src/2. Instalar Teclado.bat"
    cp "$ROOT/Teclado.vbs" "$src/programa/"
    python3 - "$src/1. Lee esto.txt" "$src/2. Instalar Teclado.bat" << 'PY'
import pathlib, sys
for name in sys.argv[1:]:
    p = pathlib.Path(name)
    raw = p.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    if name.endswith(".txt") and not raw.startswith(b"\xef\xbb\xbf"):
        raw = b"\xef\xbb\xbf" + raw
    p.write_bytes(raw.replace(b"\n", b"\r\n"))
PY
  else
    cp "$ROOT/descarga/linux/1. Lee esto.txt" "$src/"
    cp "$ROOT/descarga/linux/2. Instalar Teclado.sh" "$src/"
    chmod +x "$src/2. Instalar Teclado.sh"
    cp "$ROOT/instalar.sh" "$src/programa/"
    chmod +x "$src/programa/instalar.sh" "$src/programa/kb.py"
    mkdir -p "$src/programa/linux" "$src/programa/assets"
    cp "$ROOT/linux/60-teclado-color.rules" "$src/programa/linux/"
    cp "$ROOT/assets/icon.png" "$src/programa/assets/"
  fi
  rm -f "$OUT/Teclado-$2.zip"
  (cd "$STAGE/$name" && zip -qrX "$OUT/Teclado-$2.zip" Teclado)
}

pack windows Windows
pack linux Linux
echo "$OUT"
