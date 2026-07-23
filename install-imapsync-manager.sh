#!/usr/bin/env bash
# Instala o IMAPSync Manager em Ubuntu ou Ubuntu no WSL.
# Uso: curl -fsSL https://raw.githubusercontent.com/Rukinha/Imapsync-Manager/main/install-imapsync-manager.sh | bash
set -Eeuo pipefail

REPO_URL="https://github.com/Rukinha/Imapsync-Manager.git"
INSTALL_DIR="${IMAPSYNC_MANAGER_DIR:-$HOME/Imapsync-Manager}"
VENV_DIR="$INSTALL_DIR/.venv"
LAUNCHER="$HOME/.local/bin/imapsync-manager"

info() { printf '\n\033[1;36m%s\033[0m\n' "$1"; }
ok() { printf '\033[0;32m✓ %s\033[0m\n' "$1"; }
fail() { printf '\033[0;31mErro: %s\033[0m\n' "$1" >&2; exit 1; }

command -v apt-get >/dev/null || fail "Este instalador é destinado ao Ubuntu/Debian (apt)."
command -v sudo >/dev/null || fail "O comando sudo é necessário para instalar os pacotes do sistema."

info "[1/4] Instalando dependências do sistema"
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

if apt-cache show imapsync >/dev/null 2>&1; then
    sudo apt-get install -y imapsync
else
    info "Pacote 'imapsync' não encontrado. Baixando a versão oficial..."

    sudo wget -qO /usr/local/bin/imapsync \
        https://raw.githubusercontent.com/imapsync/imapsync/master/imapsync

    sudo chmod +x /usr/local/bin/imapsync
fi

if ! command -v imapsync >/dev/null 2>&1; then
    fail "Falha ao instalar o imapsync."
fi

ok "Dependências do sistema e imapsync instalados"

info "[2/4] Baixando ou atualizando o aplicativo"
if [[ -d "$INSTALL_DIR/.git" ]]; then
  git -C "$INSTALL_DIR" fetch --all --prune
  git -C "$INSTALL_DIR" pull --ff-only origin main || git -C "$INSTALL_DIR" pull --ff-only origin master
elif [[ -e "$INSTALL_DIR" ]]; then
  fail "A pasta '$INSTALL_DIR' já existe e não é uma instalação Git. Mova-a ou escolha outra pasta com IMAPSYNC_MANAGER_DIR."
else
  git clone "$REPO_URL" "$INSTALL_DIR"
fi
ok "Código disponível em $INSTALL_DIR"

info "[3/4] Preparando ambiente Python"
python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/python" -m pip install -r "$INSTALL_DIR/requirements.txt"
ok "Dependências Python instaladas"

info "[4/4] Criando comando de execução"
mkdir -p "$(dirname "$LAUNCHER")"
cat > "$LAUNCHER" <<EOF
#!/usr/bin/env bash
exec "$VENV_DIR/bin/python" "$INSTALL_DIR/main.py" "\$@"
EOF
chmod +x "$LAUNCHER"

if [[ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]]; then
  mkdir -p "$HOME/.local/share/applications"
  cat > "$HOME/.local/share/applications/imapsync-manager.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=IMAPSync Manager
Comment=Gerenciador de migrações de e-mail com imapsync
Exec=$LAUNCHER
Terminal=false
Categories=Network;Utility;
EOF
  update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
  ok "Atalho de menu criado"
fi

printf '\n\033[1;32mInstalação concluída.\033[0m\n'
printf 'Execute com: \033[1;36m%s\033[0m\n' "$LAUNCHER"
printf 'Se ~/.local/bin estiver no PATH, basta usar: \033[1;36mimapsync-manager\033[0m\n'
printf 'Em WSL, use uma distribuição com interface gráfica (WSLg ou servidor X) para abrir a janela.\n'
