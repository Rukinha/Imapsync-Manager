"""Modelo de dados para perfis de servidor IMAP."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict


@dataclass
class Profile:
    """Representa um servidor IMAP cadastrado (origem ou destino)."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    nome: str = ""
    host: str = ""
    porta: int = 993
    ssl: bool = True
    auth_type: str = "LOGIN"
    timeout: int = 60
    prefixo_imap: str = ""
    observacoes: str = ""
    cor: str = "#3498db"

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> "Profile":
        campos_validos = Profile.__dataclass_fields__.keys()
        filtrado = {k: v for k, v in data.items() if k in campos_validos}
        return Profile(**filtrado)

    def __str__(self) -> str:
        return f"{self.nome} ({self.host}:{self.porta})"
