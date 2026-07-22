"""Utilitário para desligar o computador (usado na opção 'Desligar ao final')."""
from __future__ import annotations

import platform
import subprocess


def desligar_computador() -> None:
    """Dispara o desligamento do sistema operacional.

    Em Linux, normalmente requer que o usuário tenha permissão (via polkit)
    para `systemctl poweroff` sem senha, ou que o programa rode com sudo.
    Caso falhe, o chamador deve capturar a exceção e avisar o usuário.
    """
    sistema = platform.system()

    if sistema == "Linux":
        subprocess.run(["systemctl", "poweroff"], check=True)
    elif sistema == "Windows":
        subprocess.run(["shutdown", "/s", "/t", "0"], check=True)
    elif sistema == "Darwin":
        subprocess.run(["osascript", "-e", 'tell app "System Events" to shut down'], check=True)
    else:
        raise RuntimeError(f"Desligamento automático não suportado neste sistema: {sistema}")
