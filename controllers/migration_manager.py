"""Orquestra a execução da fila de migrações (uma instância de ImapsyncProcess por conta),
limitando quantas rodam em paralelo para não sobrecarregar host/rede.

Também cuida de reconexão automática: se uma conta falha por um motivo
identificado como problema de rede/conexão (timeout, conexão recusada,
DNS, SSL, etc.), ela é recolocada na fila para uma nova tentativa depois
de um intervalo (5 minutos por padrão), até um número máximo de tentativas.
"""
from __future__ import annotations

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from models.account import Account, AccountStatus
from models.profile import Profile
from services.imapsync import ImapsyncProcess, MigrationResult
from services.error_translator import traduzir_erro

RETRY_DELAY_MS_PADRAO = 5 * 60 * 1000  # 5 minutos
MAX_TENTATIVAS_PADRAO = 3


class MigrationManager(QObject):
    """Gerencia o ciclo de vida da migração de várias contas.

    Sinais:
        account_status_changed(email, status)
        account_progress(email, percent)
        account_speed(email, speed)
        account_log(email, line)
        account_error(email, motivo_amigavel)
        overall_progress(percent)
        all_finished()
    """

    account_status_changed = pyqtSignal(str, str)
    account_progress = pyqtSignal(str, int)
    account_speed = pyqtSignal(str, str)
    account_log = pyqtSignal(str, str)
    account_error = pyqtSignal(str, str)
    overall_progress = pyqtSignal(int)
    all_finished = pyqtSignal()

    def __init__(self, max_parallel: int = 4, parent: QObject | None = None):
        super().__init__(parent)
        self.max_parallel = max_parallel
        self.auto_retry = True
        self.retry_delay_ms = RETRY_DELAY_MS_PADRAO
        self.max_tentativas = MAX_TENTATIVAS_PADRAO

        self._origem: Profile | None = None
        self._destino: Profile | None = None
        self._extra_flags: list[str] | None = None

        self._fila: list[Account] = []
        self._em_execucao: dict[str, ImapsyncProcess] = {}
        self._concluidas: list[Account] = []
        self._aguardando_retry: set[str] = set()  # emails com retry agendado (para contar no total)
        self._pausado = False
        self._cancelado = False

    def configurar(self, origem: Profile, destino: Profile,
                    contas: list[Account], extra_flags: list[str] | None = None) -> None:
        self._origem = origem
        self._destino = destino
        self._extra_flags = extra_flags
        self._fila = list(contas)
        self._concluidas = []
        self._aguardando_retry.clear()
        self._pausado = False
        self._cancelado = False
        for conta in self._fila:
            conta.tentativas = 0
            conta.motivo_erro = ""

    def iniciar(self) -> None:
        if not self._origem or not self._destino:
            raise RuntimeError("Servidores de origem/destino não configurados.")
        self._pausado = False
        self._cancelado = False
        self._preencher_slots()

    def pausar(self) -> None:
        """Pausa a fila: processos em execução terminam, mas novos não iniciam."""
        self._pausado = True

    def retomar(self) -> None:
        self._pausado = False
        self._preencher_slots()

    def cancelar(self) -> None:
        """Cancela tudo: mata processos em execução e esvazia a fila."""
        self._cancelado = True
        for proc in list(self._em_execucao.values()):
            proc.cancel()
        self._fila.clear()
        self._aguardando_retry.clear()

    # ---------- internos ----------

    def _preencher_slots(self) -> None:
        if self._pausado or self._cancelado:
            return
        while self._fila and len(self._em_execucao) < self.max_parallel:
            conta = self._fila.pop(0)
            self._iniciar_conta(conta)

    def _iniciar_conta(self, conta: Account) -> None:
        conta.status = AccountStatus.EXECUTANDO
        conta.tentativas += 1
        conta.motivo_erro = ""
        self.account_status_changed.emit(conta.email, conta.status.value)

        proc = ImapsyncProcess(self._origem, self._destino, conta, self._extra_flags, parent=self)
        proc.progress.connect(self._on_progress)
        proc.speed_updated.connect(self.account_speed)
        proc.log_line.connect(self.account_log)
        proc.finished.connect(lambda result, c=conta: self._on_conta_finalizada(c, result))

        self._em_execucao[conta.email] = proc
        proc.start()

    def _on_progress(self, email: str, pct: int) -> None:
        self.account_progress.emit(email, pct)
        self._emitir_progresso_geral()

    def _on_conta_finalizada(self, conta: Account, result: MigrationResult) -> None:
        self._em_execucao.pop(conta.email, None)

        if result.ok:
            conta.status = AccountStatus.CONCLUIDO
            conta.progresso = 100
            conta.motivo_erro = ""
            self.account_status_changed.emit(conta.email, conta.status.value)
            self._concluidas.append(conta)
            self._continuar_apos_conta(conta)
            return

        motivo, eh_erro_de_conexao = traduzir_erro(result.raw_log)
        conta.motivo_erro = motivo
        self.account_error.emit(conta.email, motivo)

        pode_tentar_de_novo = (
            self.auto_retry
            and eh_erro_de_conexao
            and conta.tentativas < self.max_tentativas
            and not self._cancelado
        )

        if pode_tentar_de_novo:
            conta.status = AccountStatus.REAGENDADO
            self.account_status_changed.emit(conta.email, conta.status.value)
            self._aguardando_retry.add(conta.email)
            self.account_log.emit(
                conta.email,
                f"Falha de conexão detectada ({motivo}). "
                f"Nova tentativa automática {self._descricao_intervalo_retry()} "
                f"(tentativa {conta.tentativas}/{self.max_tentativas})."
            )
            QTimer.singleShot(self.retry_delay_ms, lambda c=conta: self._reencaminhar_para_fila(c))
        else:
            conta.status = AccountStatus.ERRO
            self.account_status_changed.emit(conta.email, conta.status.value)
            self._concluidas.append(conta)
            self._continuar_apos_conta(conta)

    def _reencaminhar_para_fila(self, conta: Account) -> None:
        self._aguardando_retry.discard(conta.email)
        if self._cancelado:
            return
        conta.status = AccountStatus.AGUARDANDO
        self.account_status_changed.emit(conta.email, conta.status.value)
        self._fila.append(conta)
        self._preencher_slots()

    def _descricao_intervalo_retry(self) -> str:
        segundos = max(0, self.retry_delay_ms // 1000)
        if segundos == 0:
            return "imediatamente"
        if segundos < 60:
            return f"em {segundos} segundos"
        minutos = segundos // 60
        return f"em {minutos} minuto{'s' if minutos != 1 else ''}"

    def _continuar_apos_conta(self, conta: Account) -> None:
        self._emitir_progresso_geral()

        tudo_parado = not self._fila and not self._em_execucao and not self._aguardando_retry
        if tudo_parado:
            self.all_finished.emit()
        else:
            self._preencher_slots()

    def _emitir_progresso_geral(self) -> None:
        total = (
            len(self._fila) + len(self._em_execucao)
            + len(self._aguardando_retry) + len(self._concluidas)
        )
        if total == 0:
            self.overall_progress.emit(0)
            return
        feito = len(self._concluidas)
        pct = int((feito / total) * 100)
        self.overall_progress.emit(pct)
