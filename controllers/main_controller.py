"""Controller da janela principal: liga a UI (main_window.ui) à lógica de negócio."""
from __future__ import annotations

import csv
import io
from datetime import datetime
from pathlib import Path

from PyQt6 import uic
from PyQt6.QtWidgets import QMainWindow, QFileDialog, QMessageBox, QTableWidgetItem
from PyQt6.QtCore import QDateTime, QTimer, Qt
from PyQt6.QtGui import QColor

from models.account import Account, AccountStatus
from services.profiles import ProfileManager
from services.imapsync import test_connection, DEFAULT_FLAGS
from services.settings import Settings
from services.power import desligar_computador
from controllers.migration_manager import MigrationManager
from controllers.profile_manager_dialog import ProfileManagerDialog
from controllers.account_dialog import AccountDialog

UI_PATH = Path(__file__).resolve().parent.parent / "ui" / "main_window.ui"
LOGS_DIR = Path(__file__).resolve().parent.parent / "logs"

(COL_EMAIL, COL_SENHA_ORIGEM, COL_SENHA_DESTINO, COL_STATUS,
 COL_PROGRESSO, COL_TEMPO, COL_VELOCIDADE, COL_MOTIVO) = range(8)

COR_ERRO = QColor("#ffdddd")
COR_REAGENDADO = QColor("#fff6d5")
COR_CONCLUIDO = QColor("#e2f7e2")
COR_PADRAO = QColor("#ffffff")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi(str(UI_PATH), self)

        self.profile_manager = ProfileManager()
        self.settings = Settings()
        self.migration_manager = MigrationManager(max_parallel=4)
        self.accounts: list[Account] = []
        self.extra_flags: list[str] = list(DEFAULT_FLAGS)

        self._timer_agendamento: QTimer | None = None

        LOGS_DIR.mkdir(exist_ok=True)

        self._popular_combos_servidores()
        self._carregar_preferencias()
        self._conectar_sinais_ui()
        self._conectar_sinais_migration_manager()
        self._atualizar_contador_contas()

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _popular_combos_servidores(self) -> None:
        self.comboOrigin.clear()
        self.comboDest.clear()
        for perfil in self.profile_manager.list_profiles():
            self.comboOrigin.addItem(str(perfil), perfil.id)
            self.comboDest.addItem(str(perfil), perfil.id)

    def _carregar_preferencias(self) -> None:
        self.editOperador.setText(self.settings.get("operador", ""))
        self.checkShowPasswords.setChecked(bool(self.settings.get("mostrar_senhas", False)))
        self.checkAutoRetry.setChecked(bool(self.settings.get("auto_retry", True)))
        self.checkShutdownAfter.setChecked(bool(self.settings.get("desligar_ao_fim", False)))
        self.dateTimeSchedule.setDateTime(QDateTime.currentDateTime().addSecs(3600))
        self.migration_manager.auto_retry = self.checkAutoRetry.isChecked()

    def _conectar_sinais_ui(self) -> None:
        self.btnManageProfiles.clicked.connect(self._abrir_gerenciar_perfis)
        self.actionGerenciarPerfis.triggered.connect(self._abrir_gerenciar_perfis)

        self.btnTestConnections.clicked.connect(self._testar_conexoes_selecionadas)
        self.actionTestarConexoes.triggered.connect(self._testar_conexoes_selecionadas)

        self.btnImportCsv.clicked.connect(self._importar_arquivo_contas)
        self.actionImportarCsv.triggered.connect(self._importar_arquivo_contas)

        self.btnAddAccount.clicked.connect(self._adicionar_conta)
        self.btnRemoveAccount.clicked.connect(self._remover_contas_selecionadas)

        self.btnStart.clicked.connect(self._botao_iniciar_clicado)
        self.btnPause.clicked.connect(self._pausar_migracao)
        self.btnCancel.clicked.connect(self._cancelar_migracao)

        self.btnExportLogs.clicked.connect(self._exportar_logs)
        self.actionExportarLogs.triggered.connect(self._exportar_logs)

        self.actionSair.triggered.connect(self.close)

        self.tableAccounts.itemSelectionChanged.connect(self._exibir_log_conta_selecionada)

        self.checkShowPasswords.toggled.connect(self._on_toggle_show_passwords)
        self.checkAutoRetry.toggled.connect(self._on_toggle_auto_retry)
        self.checkSchedule.toggled.connect(self.dateTimeSchedule.setEnabled)

        self.editOperador.editingFinished.connect(
            lambda: self.settings.set("operador", self.editOperador.text().strip())
        )
        self.checkShutdownAfter.toggled.connect(
            lambda v: self.settings.set("desligar_ao_fim", v)
        )

    def _conectar_sinais_migration_manager(self) -> None:
        mm = self.migration_manager
        mm.account_status_changed.connect(self._on_account_status_changed)
        mm.account_progress.connect(self._on_account_progress)
        mm.account_speed.connect(self._on_account_speed)
        mm.account_log.connect(self._on_account_log)
        mm.account_error.connect(self._on_account_error)
        mm.overall_progress.connect(self.progressGeneral.setValue)
        mm.all_finished.connect(self._on_all_finished)

    # ------------------------------------------------------------------
    # Preferências (toggles)
    # ------------------------------------------------------------------

    def _on_toggle_show_passwords(self, marcado: bool) -> None:
        self.settings.set("mostrar_senhas", marcado)
        self._redesenhar_tabela()

    def _on_toggle_auto_retry(self, marcado: bool) -> None:
        self.settings.set("auto_retry", marcado)
        self.migration_manager.auto_retry = marcado

    def _operador_atual(self) -> str:
        return self.editOperador.text().strip() or "Operador não identificado"

    # ------------------------------------------------------------------
    # Perfis / conexões
    # ------------------------------------------------------------------

    def _abrir_gerenciar_perfis(self) -> None:
        dialog = ProfileManagerDialog(self.profile_manager, parent=self)
        dialog.exec()
        self._popular_combos_servidores()

    def _perfil_por_combo(self, combo):
        profile_id = combo.currentData()
        return self.profile_manager.get(profile_id) if profile_id else None

    def _testar_conexoes_selecionadas(self) -> None:
        origem = self._perfil_por_combo(self.comboOrigin)
        destino = self._perfil_por_combo(self.comboDest)

        if not origem or not destino:
            QMessageBox.warning(self, "Selecione os servidores", "Escolha origem e destino antes de testar.")
            return

        resultados = []
        for rotulo, perfil in (("Origem", origem), ("Destino", destino)):
            ok, msg = test_connection(perfil)
            resultados.append(f"{rotulo} ({perfil.nome}): {'OK' if ok else 'FALHOU'} — {msg}")
            self._log_geral(resultados[-1])

        QMessageBox.information(self, "Resultado do teste de conexão", "\n\n".join(resultados))

    # ------------------------------------------------------------------
    # Contas
    # ------------------------------------------------------------------

    def _adicionar_conta(self) -> None:
        dialog = AccountDialog(parent=self)
        if dialog.exec():
            conta = dialog.get_account()
            if not conta.email:
                QMessageBox.warning(self, "Email obrigatório", "Informe um endereço de e-mail válido.")
                return
            self.accounts.append(conta)
            self._adicionar_linha_tabela(conta)
            self._atualizar_contador_contas()

    def _importar_arquivo_contas(self) -> None:
        caminho, _ = QFileDialog.getOpenFileName(
            self, "Importar contas (CSV ou TXT)", "",
            "Arquivos de contas (*.csv *.txt);;CSV (*.csv);;Texto (*.txt);;Todos os arquivos (*)",
        )
        if not caminho:
            return

        try:
            with open(caminho, "r", encoding="utf-8-sig") as f:
                conteudo = f.read()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Erro ao abrir arquivo", str(exc))
            return

        try:
            novas_contas = self._parsear_contas(conteudo)
        except ValueError as exc:
            QMessageBox.warning(self, "Formato não reconhecido", str(exc))
            return

        if not novas_contas:
            QMessageBox.information(self, "Nenhuma conta encontrada", "O arquivo não continha contas válidas.")
            return

        for conta in novas_contas:
            self.accounts.append(conta)
            self._adicionar_linha_tabela(conta)

        self._atualizar_contador_contas()
        self._log_geral(f"Importadas {len(novas_contas)} contas de '{Path(caminho).name}'.")

    @staticmethod
    def _parsear_contas(conteudo: str) -> list[Account]:
        """Aceita dois formatos de arquivo (CSV/TXT):

        1) Com cabeçalho, separado por vírgula ou ponto e vírgula:
           email,senha_origem,senha_destino

        2) Sem cabeçalho, no padrão pedido pela equipe (separado por ';'):
           conta;senha-origem;senha-destino
        """
        linhas = [linha for linha in conteudo.splitlines() if linha.strip()]
        if not linhas:
            return []

        primeira_linha = linhas[0].lower()
        tem_cabecalho = "email" in primeira_linha or "conta" in primeira_linha

        # Detecta o delimitador mais provável olhando a primeira linha.
        delimitador = ";" if linhas[0].count(";") >= linhas[0].count(",") else ","

        contas: list[Account] = []

        if tem_cabecalho:
            leitor = csv.reader(io.StringIO(conteudo), delimiter=delimitador)
            cabecalho = [c.strip().lower() for c in next(leitor)]

            colunas_aceitas = {"email", "conta"}
            if not colunas_aceitas.intersection(cabecalho):
                raise ValueError(
                    "Cabeçalho não reconhecido. Use 'email;senha_origem;senha_destino' "
                    "ou remova o cabeçalho e use o padrão 'conta;senha-origem;senha-destino'."
                )

            idx_email = next((i for i, c in enumerate(cabecalho) if c in ("email", "conta")), None)
            idx_senha_origem = next((i for i, c in enumerate(cabecalho) if "origem" in c), None)
            idx_senha_destino = next((i for i, c in enumerate(cabecalho) if "destino" in c), None)

            for linha in leitor:
                if idx_email is None or idx_email >= len(linha):
                    continue
                email = linha[idx_email].strip()
                if not email:
                    continue
                senha_origem = linha[idx_senha_origem].strip() if idx_senha_origem is not None and idx_senha_origem < len(linha) else ""
                senha_destino = linha[idx_senha_destino].strip() if idx_senha_destino is not None and idx_senha_destino < len(linha) else ""
                contas.append(Account(email=email, senha_origem=senha_origem, senha_destino=senha_destino))
        else:
            # Sem cabeçalho: conta;senha-origem;senha-destino (ou com vírgula)
            for linha in linhas:
                partes = [p.strip() for p in linha.split(delimitador)]
                if len(partes) < 3 or not partes[0]:
                    continue
                email, senha_origem, senha_destino = partes[0], partes[1], partes[2]
                contas.append(Account(email=email, senha_origem=senha_origem, senha_destino=senha_destino))

        return contas

    def _remover_contas_selecionadas(self) -> None:
        linhas = sorted({idx.row() for idx in self.tableAccounts.selectedIndexes()}, reverse=True)
        for linha in linhas:
            del self.accounts[linha]
            self.tableAccounts.removeRow(linha)
        self._atualizar_contador_contas()

    def _adicionar_linha_tabela(self, conta: Account) -> None:
        linha = self.tableAccounts.rowCount()
        self.tableAccounts.insertRow(linha)
        mostrar_senhas = self.checkShowPasswords.isChecked()
        for col, valor in enumerate(conta.resumo_linha(mostrar_senhas)):
            self.tableAccounts.setItem(linha, col, QTableWidgetItem(valor))

    def _redesenhar_tabela(self) -> None:
        mostrar_senhas = self.checkShowPasswords.isChecked()
        for linha, conta in enumerate(self.accounts):
            for col, valor in enumerate(conta.resumo_linha(mostrar_senhas)):
                item = self.tableAccounts.item(linha, col)
                if item is None:
                    item = QTableWidgetItem()
                    self.tableAccounts.setItem(linha, col, item)
                item.setText(valor)

    def _atualizar_contador_contas(self) -> None:
        self.labelAccountCount.setText(f"{len(self.accounts)} contas")

    def _linha_da_conta(self, email: str) -> int | None:
        for linha in range(self.tableAccounts.rowCount()):
            item = self.tableAccounts.item(linha, COL_EMAIL)
            if item and item.text() == email:
                return linha
        return None

    def _colorir_linha(self, linha: int, cor: QColor) -> None:
        for col in range(self.tableAccounts.columnCount()):
            item = self.tableAccounts.item(linha, col)
            if item:
                item.setBackground(cor)

    # ------------------------------------------------------------------
    # Início da migração (imediato ou agendado)
    # ------------------------------------------------------------------

    def _botao_iniciar_clicado(self) -> None:
        if self.checkSchedule.isChecked():
            self._agendar_inicio()
        else:
            self._iniciar_migracao()

    def _agendar_inicio(self) -> None:
        origem = self._perfil_por_combo(self.comboOrigin)
        destino = self._perfil_por_combo(self.comboDest)
        if not origem or not destino:
            QMessageBox.warning(self, "Selecione os servidores", "Escolha origem e destino antes de agendar.")
            return
        if not self.accounts:
            QMessageBox.warning(self, "Nenhuma conta", "Adicione ao menos uma conta antes de agendar.")
            return

        alvo = self.dateTimeSchedule.dateTime()
        agora = QDateTime.currentDateTime()
        if alvo <= agora:
            QMessageBox.warning(self, "Data inválida", "Escolha um horário no futuro para o agendamento.")
            return

        self._timer_agendamento = QTimer(self)
        self._timer_agendamento.setSingleShot(True)
        self._timer_agendamento.timeout.connect(self._disparar_migracao_agendada)
        self._timer_agendamento.start(agora.msecsTo(alvo))

        self.btnStart.setEnabled(False)
        self.checkSchedule.setEnabled(False)
        self.dateTimeSchedule.setEnabled(False)
        self.labelScheduleStatus.setText(
            f"Agendado para {alvo.toString('dd/MM/yyyy HH:mm')} — clique em Cancelar para desistir."
        )
        self.btnCancel.setEnabled(True)
        self._log_geral(f"Migração agendada para {alvo.toString('dd/MM/yyyy HH:mm')} por {self._operador_atual()}.")

    def _disparar_migracao_agendada(self) -> None:
        self.labelScheduleStatus.setText("")
        self.checkSchedule.setChecked(False)
        self.checkSchedule.setEnabled(True)
        self._iniciar_migracao()

    def _iniciar_migracao(self) -> None:
        origem = self._perfil_por_combo(self.comboOrigin)
        destino = self._perfil_por_combo(self.comboDest)

        if not origem or not destino:
            QMessageBox.warning(self, "Selecione os servidores", "Escolha origem e destino antes de iniciar.")
            return
        if not self.accounts:
            QMessageBox.warning(self, "Nenhuma conta", "Adicione ao menos uma conta antes de iniciar.")
            return

        for conta in self.accounts:
            conta.status = AccountStatus.AGUARDANDO
            conta.progresso = 0
            conta.motivo_erro = ""

        self.migration_manager.auto_retry = self.checkAutoRetry.isChecked()
        self.migration_manager.configurar(origem, destino, self.accounts, self.extra_flags)
        self.migration_manager.iniciar()

        self.btnStart.setEnabled(False)
        self.btnPause.setEnabled(True)
        self.btnCancel.setEnabled(True)
        self._log_geral(
            f"Migração iniciada por {self._operador_atual()}: "
            f"{origem.nome} → {destino.nome} ({len(self.accounts)} contas)."
        )

    def _pausar_migracao(self) -> None:
        self.migration_manager.pausar()
        self.btnPause.setEnabled(False)
        self.btnStart.setEnabled(True)
        self._log_geral(f"Migração pausada por {self._operador_atual()}. Contas em execução serão concluídas.")

    def _cancelar_migracao(self) -> None:
        if self._timer_agendamento and self._timer_agendamento.isActive():
            self._timer_agendamento.stop()
            self.labelScheduleStatus.setText("")
            self.checkSchedule.setChecked(False)
            self.checkSchedule.setEnabled(True)
            self._log_geral(f"Agendamento cancelado por {self._operador_atual()}.")

        self.migration_manager.cancelar()
        self.btnStart.setEnabled(True)
        self.btnPause.setEnabled(False)
        self.btnCancel.setEnabled(False)
        self._log_geral(f"Migração cancelada por {self._operador_atual()}.")

    def _on_all_finished(self) -> None:
        self.btnStart.setEnabled(True)
        self.btnPause.setEnabled(False)
        self.btnCancel.setEnabled(False)
        self._log_geral(f"Migração concluída (encerrada com sessão de {self._operador_atual()}).")

        if self.checkShutdownAfter.isChecked():
            self._confirmar_e_desligar()

    def _confirmar_e_desligar(self) -> None:
        resposta = QMessageBox.question(
            self, "Desligar computador",
            "A migração terminou e a opção 'Desligar ao final' está marcada.\n\n"
            "O computador será desligado em 30 segundos.\n"
            "Clique em 'No' para cancelar o desligamento.",
            defaultButton=QMessageBox.StandardButton.No,
        )
        if resposta != QMessageBox.StandardButton.Yes:
            self._log_geral("Desligamento automático cancelado pelo usuário.")
            return

        self._log_geral("Desligando o computador em 30 segundos...")
        QTimer.singleShot(30_000, self._executar_desligamento)

    def _executar_desligamento(self) -> None:
        try:
            desligar_computador()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Falha ao desligar", str(exc))

    # ------------------------------------------------------------------
    # Callbacks de progresso/status por conta
    # ------------------------------------------------------------------

    def _on_account_status_changed(self, email: str, status: str) -> None:
        linha = self._linha_da_conta(email)
        if linha is None:
            return
        self.tableAccounts.setItem(linha, COL_STATUS, QTableWidgetItem(status))

        if status == AccountStatus.ERRO.value:
            self._colorir_linha(linha, COR_ERRO)
        elif status == AccountStatus.REAGENDADO.value:
            self._colorir_linha(linha, COR_REAGENDADO)
        elif status == AccountStatus.CONCLUIDO.value:
            self._colorir_linha(linha, COR_CONCLUIDO)
        else:
            self._colorir_linha(linha, COR_PADRAO)

    def _on_account_progress(self, email: str, pct: int) -> None:
        linha = self._linha_da_conta(email)
        if linha is not None:
            self.tableAccounts.setItem(linha, COL_PROGRESSO, QTableWidgetItem(f"{pct}%"))

    def _on_account_speed(self, email: str, speed: str) -> None:
        linha = self._linha_da_conta(email)
        if linha is not None:
            self.tableAccounts.setItem(linha, COL_VELOCIDADE, QTableWidgetItem(speed))

    def _on_account_error(self, email: str, motivo: str) -> None:
        linha = self._linha_da_conta(email)
        if linha is not None:
            self.tableAccounts.setItem(linha, COL_MOTIVO, QTableWidgetItem(motivo))

        carimbo = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        self.textGeneralLog.appendPlainText(
            f"[{carimbo}] [{self._operador_atual()}] [{email}] ERRO: {motivo}"
        )

    def _on_account_log(self, email: str, line: str) -> None:
        carimbo = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        self.textGeneralLog.appendPlainText(f"[{carimbo}] [{self._operador_atual()}] [{email}] {line}")

        conta = next((c for c in self.accounts if c.email == email), None)
        if conta:
            conta.log += line + "\n"

        item_selecionado = self.tableAccounts.currentItem()
        if item_selecionado:
            linha_sel = item_selecionado.row()
            email_sel_item = self.tableAccounts.item(linha_sel, COL_EMAIL)
            if email_sel_item and email_sel_item.text() == email:
                self.textAccountLog.appendPlainText(line)

    def _exibir_log_conta_selecionada(self) -> None:
        item = self.tableAccounts.currentItem()
        if not item:
            return
        email = self.tableAccounts.item(item.row(), COL_EMAIL).text()
        conta = next((c for c in self.accounts if c.email == email), None)
        self.textAccountLog.setPlainText(conta.log if conta else "")

    def _log_geral(self, mensagem: str) -> None:
        carimbo = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        self.textGeneralLog.appendPlainText(f"[{carimbo}] {mensagem}")

    # ------------------------------------------------------------------
    # Logs / exportação
    # ------------------------------------------------------------------

    def _exportar_logs(self) -> None:
        sugestao = LOGS_DIR / f"migracao_{datetime.now():%Y%m%d_%H%M%S}.log"
        caminho, _ = QFileDialog.getSaveFileName(self, "Exportar log geral", str(sugestao), "Log (*.log)")
        if not caminho:
            return
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(self.textGeneralLog.toPlainText())
        QMessageBox.information(self, "Log exportado", f"Log salvo em:\n{caminho}")
