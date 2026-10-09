#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname "$0")" && pwd)

if [ "$(id -u)" -eq 0 ]; then
  echo "Ábrelo con tu usuario, no como root."
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "Falta Python."
  echo "Arch: sudo pacman -S python tk"
  echo "Debian/Ubuntu: sudo apt install python3 python3-tk"
  echo "Fedora: sudo dnf install python3-tkinter"
  exit 1
fi

if ! python3 -c "import tkinter" >/dev/null 2>&1; then
  echo "Falta la ventana de Python."
  echo "Arch: sudo pacman -S tk"
  echo "Debian/Ubuntu: sudo apt install python3-tk"
  echo "Fedora: sudo dnf install python3-tkinter"
  exit 1
fi

RULE_SRC="$ROOT/linux/60-teclado-color.rules"
RULE_DST=/etc/udev/rules.d/60-teclado-color.rules
if [ ! -f "$RULE_DST" ] || ! cmp -s "$RULE_SRC" "$RULE_DST"; then
  if command -v pkexec >/dev/null 2>&1; then
    pkexec sh -c "cp '$RULE_SRC' '$RULE_DST' && udevadm control --reload && udevadm trigger --subsystem-match=hidraw"
  elif command -v sudo >/dev/null 2>&1; then
    sudo sh -c "cp '$RULE_SRC' '$RULE_DST' && udevadm control --reload && udevadm trigger --subsystem-match=hidraw"
  else
    echo "Copia linux/60-teclado-color.rules a /etc/udev/rules.d/ y vuelve a enchufar el teclado."
    exit 1
  fi
fi

PY=$(command -v python3)
mkdir -p "$HOME/.local/share/applications" "$HOME/.config/systemd/user"
rm -f "$HOME/.local/share/applications/teclado-color.desktop"

cat > "$HOME/.local/share/applications/teclado.desktop" <<EOF
[Desktop Entry]
Name=Teclado
GenericName=Color del teclado
Comment=Rueda, brillo y efectos. Sin el programa de la marca.
Exec=$PY $ROOT/kb.py
Icon=$ROOT/assets/icon.png
Terminal=false
Type=Application
Categories=Settings;Utility;
StartupNotify=true
EOF

cat > "$HOME/.config/systemd/user/teclado-color.service" <<EOF
[Unit]
Description=Color del teclado
After=default.target

[Service]
ExecStart=$PY $ROOT/kb.py --render
Restart=on-failure
RestartSec=2

[Install]
WantedBy=default.target
EOF

if command -v systemctl >/dev/null 2>&1; then
  systemctl --user daemon-reload
  systemctl --user enable --now teclado-color.service
fi

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$HOME/.local/share/applications" >/dev/null 2>&1 || true
fi

echo "Listo. Abre Teclado en el menú."
if [ -t 0 ]; then
  printf "Pulsa Enter para cerrar. "
  read _
fi
