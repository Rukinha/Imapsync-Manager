#!/usr/bin/env bash
set -Eeuo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"
PYTHON="${PYTHON:-python3}"
command -v pyuic6 >/dev/null || { echo "pyuic6 não encontrado. Ative o venv."; exit 1; }
declare -A UI_MAP=(
  ["ui/main_window.ui"]="controllers/ui_main_window.py"
  ["ui/profile_dialog.ui"]="controllers/ui_profile_dialog.py"
)
for ui_file in "${!UI_MAP[@]}"; do
    py_file="${UI_MAP[$ui_file]}"
    [[ -f "$ui_file" ]] || continue
    echo "Compilando $ui_file -> $py_file"
    pyuic6 "$ui_file" -o "$py_file"
    "$PYTHON" fix_pyuic6_bugs.py --ui "$ui_file" --py "$py_file"
done
