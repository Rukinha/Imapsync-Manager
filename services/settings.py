"""Configurações globais da aplicação, persistidas em config/settings.json.

Guarda preferências que fazem sentido continuarem entre sessões:
- Nome do operador (para identificar quem fez cada migração no log)
- Preferência de mostrar/ocultar senhas na tabela
- Preferência de reconexão automática
"""
from __future__ import annotations

import json
from pathlib import Path

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
SETTINGS_FILE = CONFIG_DIR / "settings.json"

_PADRAO = {
    "operador": "",
    "mostrar_senhas": False,
    "auto_retry": True,
    "retry_delay_seconds": 300,
    "desligar_ao_fim": False,
}


class Settings:
    def __init__(self, file_path: Path = SETTINGS_FILE):
        self.file_path = file_path
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self._dados = dict(_PADRAO)
        self.load()

    def load(self) -> None:
        if not self.file_path.exists():
            self.save()
            return
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                dados_salvos = json.load(f)
            self._dados.update(dados_salvos)
        except (json.JSONDecodeError, OSError):
            pass  # mantém padrão se o arquivo estiver corrompido

    def save(self) -> None:
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self._dados, f, indent=2, ensure_ascii=False)

    def get(self, chave: str, default=None):
        return self._dados.get(chave, default)

    def set(self, chave: str, valor) -> None:
        self._dados[chave] = valor
        self.save()
