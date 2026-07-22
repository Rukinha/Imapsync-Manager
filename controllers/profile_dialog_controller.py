"""Controller do ProfileDialog: cadastro/edição de perfis de servidor IMAP."""
from __future__ import annotations

from pathlib import Path

from PyQt6 import uic
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QDialog, QColorDialog, QMessageBox

from models.profile import Profile
from services.imapsync import test_connection

UI_PATH = Path(__file__).resolve().parent.parent / "ui" / "profile_dialog.ui"


class ProfileDialog(QDialog):
    def __init__(self, profile: Profile | None = None, parent=None):
        super().__init__(parent)
        uic.loadUi(str(UI_PATH), self)

        self.profile = profile or Profile()
        self._cor_atual = self.profile.cor

        self._popular_campos()

        self.btnPickColor.clicked.connect(self._escolher_cor)
        self.btnTestConnection.clicked.connect(self._testar_conexao)
        self.buttonBox.accepted.connect(self._salvar)
        self.buttonBox.rejected.connect(self.reject)

    def _popular_campos(self) -> None:
        p = self.profile
        self.editNome.setText(p.nome)
        self.editHost.setText(p.host)
        self.spinPorta.setValue(p.porta)
        self.checkSsl.setChecked(p.ssl)
        idx = self.comboAuthType.findText(p.auth_type)
        if idx >= 0:
            self.comboAuthType.setCurrentIndex(idx)
        self.spinTimeout.setValue(p.timeout)
        self.editPrefix.setText(p.prefixo_imap)
        self.editObs.setPlainText(p.observacoes)
        self._atualizar_preview_cor(p.cor)

    def _atualizar_preview_cor(self, hex_cor: str) -> None:
        self._cor_atual = hex_cor
        self.frameColorPreview.setStyleSheet(f"background-color: {hex_cor}; border: 1px solid #888;")

    def _escolher_cor(self) -> None:
        cor = QColorDialog.getColor(QColor(self._cor_atual), self, "Cor do perfil")
        if cor.isValid():
            self._atualizar_preview_cor(cor.name())

    def _testar_conexao(self) -> None:
        profile_temporario = self._montar_profile()
        ok, mensagem = test_connection(profile_temporario)
        cor = "green" if ok else "red"
        prefixo = "OK: " if ok else "Falhou: "
        self.labelTestResult.setText(f"<span style='color:{cor}'>{prefixo}{mensagem}</span>")

    def _montar_profile(self) -> Profile:
        self.profile.nome = self.editNome.text().strip()
        self.profile.host = self.editHost.text().strip()
        self.profile.porta = self.spinPorta.value()
        self.profile.ssl = self.checkSsl.isChecked()
        self.profile.auth_type = self.comboAuthType.currentText()
        self.profile.timeout = self.spinTimeout.value()
        self.profile.prefixo_imap = self.editPrefix.text().strip()
        self.profile.observacoes = self.editObs.toPlainText().strip()
        self.profile.cor = self._cor_atual
        return self.profile

    def _salvar(self) -> None:
        if not self.editNome.text().strip() or not self.editHost.text().strip():
            QMessageBox.warning(self, "Campos obrigatórios", "Informe ao menos Nome e Host.")
            return
        self._montar_profile()
        self.accept()
