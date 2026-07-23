"""Diálogo simples para adicionar uma única conta manualmente."""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QDialogButtonBox, QVBoxLayout,
)

from models.account import Account


class AccountDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Adicionar Conta")
        self.resize(360, 160)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.editEmail = QLineEdit()
        self.editEmail.setPlaceholderText("usuario@dominio.com")
        self.editSenhaOrigem = QLineEdit()
        self.editSenhaOrigem.setEchoMode(QLineEdit.EchoMode.Password)
        self.editSenhaDestino = QLineEdit()
        self.editSenhaDestino.setEchoMode(QLineEdit.EchoMode.Password)

        form.addRow("Email", self.editEmail)
        form.addRow("Senha origem", self.editSenhaOrigem)
        form.addRow("Senha destino", self.editSenhaDestino)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_account(self) -> Account:
        return Account(
            email=self.editEmail.text().strip(),
            senha_origem=self.editSenhaOrigem.text(),
            senha_destino=self.editSenhaDestino.text(),
        )
