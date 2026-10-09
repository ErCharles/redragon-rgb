#!/bin/sh
HERE=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
APP="$HERE/programa"
cmd='cd "$1" && ./instalar.sh; echo; echo "Listo. Abre Teclado en el menú."; printf "Pulsa Enter para cerrar. "; read _'
if [ -t 1 ]; then
  exec sh -c "$cmd" sh "$APP"
fi
if command -v x-terminal-emulator >/dev/null 2>&1; then
  exec x-terminal-emulator -e sh -c "$cmd" sh "$APP"
fi
if command -v gnome-terminal >/dev/null 2>&1; then
  exec gnome-terminal -- sh -c "$cmd" sh "$APP"
fi
if command -v konsole >/dev/null 2>&1; then
  exec konsole -e sh -c "$cmd" sh "$APP"
fi
if command -v kitty >/dev/null 2>&1; then
  exec kitty sh -c "$cmd" sh "$APP"
fi
exec sh -c "$cmd" sh "$APP"
