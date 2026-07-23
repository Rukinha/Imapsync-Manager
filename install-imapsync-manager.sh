#!/usr/bin/env bash
# Instala o IMAPSync Manager em Ubuntu ou Ubuntu no WSL.
# Uso:
# curl -fsSL https://raw.githubusercontent.com/Rukinha/Imapsync-Manager/main/install-imapsync-manager.sh | bash

set -Eeuo pipefail

info() { printf '\n\033[1;36m%s\033[0m\n' "$1"; }
ok() { printf '\033[0;32m✓ %s\033[0m\n' "$1"; }
fail() { printf '\033[0;31mErro: %s\033[0m\n' "$1" >&2; exit 1; }

REPO="https://github.com/Rukinha/Imapsync-Manager.git"
INSTALL_BASE="$HOME/.local/share"
INSTALL_DIR="$INSTALL_BASE/Imapsync-Manager"

VENV_DIR="$INSTALL_DIR/.venv"
LAUNCHER="/usr/local/bin/imapsync-manager"


info "Verificando instalação"

if [[ ! -f "$INSTALL_DIR/main.py" ]]; then

    info "Clonando projeto..."

    mkdir -p "$INSTALL_BASE"

    if [[ -d "$INSTALL_DIR" ]]; then
        rm -rf "$INSTALL_DIR"
    fi

    git clone "$REPO" "$INSTALL_DIR"

fi


[[ -f "$INSTALL_DIR/main.py" ]] || fail "main.py não encontrado."
[[ -f "$INSTALL_DIR/requirements.txt" ]] || fail "requirements.txt não encontrado."


command -v apt-get >/dev/null || fail "Ubuntu/Debian necessário."
command -v sudo >/dev/null || fail "sudo não encontrado."


info "[1/4] Instalando dependências"

sudo apt-get update

sudo apt-get install -y \
    git \
    python3 \
    python3-venv \
    python3-pip \
    wget \
    cpanminus \
    libmail-imapclient-perl \
    libio-socket-ssl-perl \
    libdigest-hmac-perl \
    libauthen-ntlm-perl \
    libencode-imaputf7-perl \
    libgl1 \
    libegl1 \
    libxkbcommon-x11-0 \
    libdbus-1-3 \
    libxcb-cursor0 \
    desktop-file-utils


if ! command -v imapsync >/dev/null; then

    info "Instalando imapsync..."

    sudo wget -qO /usr/local/bin/imapsync \
    https://raw.githubusercontent.com/imapsync/imapsync/master/imapsync

    sudo chmod +x /usr/local/bin/imapsync

fi


command -v imapsync >/dev/null || fail "imapsync falhou."


ok "Dependências instaladas"


info "[2/4] Configurando Python"
if command -v python3.12 >/dev/null; then
    PYTHON_BIN=python3.12
else
    PYTHON_BIN=python3
fi
"$PYTHON_BIN" -m venv "$VENV_DIR"

"$VENV_DIR/bin/python" -m pip install --upgrade pip

"$VENV_DIR/bin/python" -m pip install \
-r "$INSTALL_DIR/requirements.txt"


ok "Python configurado"


info "[3/4] Criando comando"

sudo tee "$LAUNCHER" >/dev/null <<EOF
#!/usr/bin/env bash
exec "$VENV_DIR/bin/python" "$INSTALL_DIR/main.py" "\$@"
EOF

sudo chmod +x "$LAUNCHER"


ok "Comando criado"


info "[4/4] Criando atalho"

mkdir -p "$HOME/.local/share/applications"

cat > "$HOME/.local/share/applications/imapsync-manager.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=IMAPSync Manager
Comment=Gerenciador de migração de emails
Exec=$LAUNCHER
Terminal=false
Categories=Network;Utility;
EOF


update-desktop-database \
"$HOME/.local/share/applications" \
2>/dev/null || true


ok "Atalho criado"


printf '\n\033[1;32mInstalação concluída!\033[0m\n'
printf 'Execute:\n\n'
printf '  \033[1;36mimapsync-manager\033[0m\n\n'


if grep -qi microsoft /proc/version 2>/dev/null; then
    printf 'WSL detectado: use WSLg para abrir a interface gráfica.\n'
fi
