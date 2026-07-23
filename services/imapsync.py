"""Camada de integração com o binário `imapsync`.

Responsável por:
- Montar a linha de comando a partir de perfis + credenciais de uma conta.
- Executar o processo de forma assíncrona via QProcess (não bloqueia a UI).
- Fazer parsing básico da saída do imapsync para extrair progresso/velocidade.
"""
from __future__ import annotations

import re
import shutil
from dataclasses import dataclass

from PyQt6.QtCore import QObject, QProcess, pyqtSignal

from models.profile import Profile
from models.account import Account

IMAPSYNC_BIN = shutil.which("imapsync") or "imapsync"

# Parâmetros globais padrão (podem ser sobrescritos em Configurações)
DEFAULT_FLAGS = [
    "--automap",
    "--subscribe",
    "--syncinternaldates",
    "--skipsize",
    "--nofoldersizes",
    "--noauthmd5",
]

# Regex aproximada para extrair progresso/velocidade da saída do imapsync.
# Ex.: "... 1234/5678 messages transferred ... (12.3 KB/s)"
RE_PROGRESS = re.compile(r"(\d+)\s*/\s*(\d+)\s+messages")
RE_SPEED = re.compile(r"([\d.]+\s*[KMG]?B/s)")


def build_command(origem: Profile, destino: Profile, account: Account,
                   extra_flags: list[str] | None = None) -> list[str]:
    """Monta a lista de argumentos para o subprocess do imapsync."""
    flags = list(extra_flags if extra_flags is not None else DEFAULT_FLAGS)

    cmd = [
        IMAPSYNC_BIN,
        "--host1", origem.host,
        "--port1", str(origem.porta),
        "--user1", account.email,
        "--password1", account.senha_origem,
        "--host2", destino.host,
        "--port2", str(destino.porta),
        "--user2", account.email,
        "--password2", account.senha_destino,
    ]

    if origem.ssl:
        cmd.append("--ssl1")
    if destino.ssl:
        cmd.append("--ssl2")
    if origem.prefixo_imap:
        cmd += ["--prefix1", origem.prefixo_imap]
    if destino.prefixo_imap:
        cmd += ["--prefix2", destino.prefixo_imap]

    cmd += ["--timeout", str(max(origem.timeout, destino.timeout))]
    cmd += flags
    return cmd


@dataclass
class MigrationResult:
    account_email: str
    exit_code: int
    ok: bool
    raw_log: str


class ImapsyncProcess(QObject):
    """Executa uma migração de conta única via QProcess, sem travar a UI.

    Sinais:
        progress(email, percent)
        speed_updated(email, speed_str)
        log_line(email, line)
        finished(MigrationResult)
    """

    progress = pyqtSignal(str, int)
    speed_updated = pyqtSignal(str, str)
    log_line = pyqtSignal(str, str)
    finished = pyqtSignal(object)  # MigrationResult

    def __init__(self, origem: Profile, destino: Profile, account: Account,
                 extra_flags: list[str] | None = None, parent: QObject | None = None):
        super().__init__(parent)
        self.origem = origem
        self.destino = destino
        self.account = account
        self.extra_flags = extra_flags
        self._process: QProcess | None = None
        self._buffer = ""

    def start(self) -> None:
        cmd = build_command(self.origem, self.destino, self.account, self.extra_flags)

        self._process = QProcess(self)
        self._process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self._process.readyReadStandardOutput.connect(self._on_output)
        self._process.finished.connect(self._on_finished)

        program, *args = cmd
        self._process.start(program, args)

    def cancel(self) -> None:
        if self._process and self._process.state() != QProcess.ProcessState.NotRunning:
            self._process.kill()

    # ---------- internos ----------

    def _on_output(self) -> None:
        if not self._process:
            return
        chunk = bytes(self._process.readAllStandardOutput()).decode(errors="replace")
        self._buffer += chunk

        for line in chunk.splitlines():
            self.log_line.emit(self.account.email, line)

            match_progress = RE_PROGRESS.search(line)
            if match_progress:
                atual, total = int(match_progress.group(1)), int(match_progress.group(2))
                if total > 0:
                    pct = int((atual / total) * 100)
                    self.progress.emit(self.account.email, pct)

            match_speed = RE_SPEED.search(line)
            if match_speed:
                self.speed_updated.emit(self.account.email, match_speed.group(1))

    def _on_finished(self, exit_code: int, _status) -> None:
        result = MigrationResult(
            account_email=self.account.email,
            exit_code=exit_code,
            ok=(exit_code == 0),
            raw_log=self._buffer,
        )
        self.finished.emit(result)


def test_connection(profile: Profile) -> tuple[bool, str]:
    """Testa conectividade básica de um perfil abrindo um socket IMAP simples.

    Não faz autenticação (não requer credenciais de usuário) — apenas
    valida que host/porta/SSL respondem, o que já cobre a maioria dos
    problemas de configuração de perfil.
    """
    import socket
    import ssl as ssl_lib

    try:
        raw_sock = socket.create_connection((profile.host, profile.porta), timeout=profile.timeout)
        if profile.ssl:
            context = ssl_lib.create_default_context()
            sock = context.wrap_socket(raw_sock, server_hostname=profile.host)
        else:
            sock = raw_sock

        banner = sock.recv(200).decode(errors="replace").strip()
        sock.close()
        return True, banner or "Conexão estabelecida."
    except Exception as exc:  # noqa: BLE001 - queremos capturar e reportar qualquer falha
        return False, str(exc)
