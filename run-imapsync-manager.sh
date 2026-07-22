#!/usr/bin/env bash
# Executa o aplicativo a partir do checkout atual.
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$ROOT_DIR/.venv/bin/python"

if [[ ! -x "$VENV_PYTHON" ]]; then
  echo "Ambiente não encontrado. Execute primeiro: ./install-imapsync-manager.sh" >&2
  exit 1
fi

exec "$VENV_PYTHON" "$ROOT_DIR/main.py" "$@"
