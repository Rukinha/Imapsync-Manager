"""Modelo de dados para contas de e-mail em migração."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class AccountStatus(str, Enum):
    AGUARDANDO = "aguardando"
    EXECUTANDO = "executando"
    CONCLUIDO = "concluído"
    ERRO = "erro"
    PAUSADO = "pausado"
    CANCELADO = "cancelado"
    REAGENDADO = "aguardando nova tentativa"


@dataclass
class Account:
    """Representa uma conta de e-mail a ser migrada de um servidor para outro."""

    email: str
    senha_origem: str
    senha_destino: str
    status: AccountStatus = AccountStatus.AGUARDANDO
    progresso: int = 0          # 0-100
    tempo_decorrido: str = "00:00:00"
    velocidade: str = "-"
    log: str = field(default_factory=str)
    tentativas: int = 0          # nº de vezes que já tentou migrar (para auto-retry)
    motivo_erro: str = ""        # mensagem de erro traduzida/resumida, se houver

    def resumo_linha(self, mostrar_senhas: bool = False) -> list[str]:
        """Retorna os valores formatados para exibição na QTableWidget.

        Quando `mostrar_senhas` é False, as senhas aparecem mascaradas.
        """
        if mostrar_senhas:
            senha_origem = self.senha_origem
            senha_destino = self.senha_destino
        else:
            senha_origem = "•" * len(self.senha_origem) if self.senha_origem else ""
            senha_destino = "•" * len(self.senha_destino) if self.senha_destino else ""

        return [
            self.email,
            senha_origem,
            senha_destino,
            self.status.value,
            f"{self.progresso}%",
            self.tempo_decorrido,
            self.velocidade,
            self.motivo_erro,
        ]
