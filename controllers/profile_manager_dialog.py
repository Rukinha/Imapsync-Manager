"""Diálogo de gerenciamento de perfis (lista + adicionar/editar/remover).

Construído programaticamente (não via Qt Designer) por ser uma tela simples
de CRUD sobre a lista de perfis; o cadastro/edição em si usa o profile_dialog.ui.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QMessageBox,
)

from models.profile import Profile
from services.profiles import ProfileManager
from controllers.profile_dialog_controller import ProfileDialog


class ProfileManagerDialog(QDialog):
    def __init__(self, profile_manager: ProfileManager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gerenciar Perfis de Servidor")
        self.resize(420, 480)
        self.profile_manager = profile_manager

        layout = QVBoxLayout(self)
        self.listWidget = QListWidget(self)
        layout.addWidget(self.listWidget)

        botoes = QHBoxLayout()
        self.btnNovo = QPushButton("Novo")
        self.btnEditar = QPushButton("Editar")
        self.btnRemover = QPushButton("Remover")
        self.btnFechar = QPushButton("Fechar")
        for b in (self.btnNovo, self.btnEditar, self.btnRemover, self.btnFechar):
            botoes.addWidget(b)
        layout.addLayout(botoes)

        self.btnNovo.clicked.connect(self._novo)
        self.btnEditar.clicked.connect(self._editar)
        self.btnRemover.clicked.connect(self._remover)
        self.btnFechar.clicked.connect(self.accept)

        self._recarregar_lista()

    def _recarregar_lista(self) -> None:
        self.listWidget.clear()
        for p in self.profile_manager.list_profiles():
            item = QListWidgetItem(str(p))
            item.setData(1000, p.id)
            self.listWidget.addItem(item)

    def _perfil_selecionado(self) -> Profile | None:
        item = self.listWidget.currentItem()
        if not item:
            return None
        return self.profile_manager.get(item.data(1000))

    def _novo(self) -> None:
        dialog = ProfileDialog(profile=Profile(), parent=self)
        if dialog.exec():
            self.profile_manager.add(dialog.profile)
            self._recarregar_lista()

    def _editar(self) -> None:
        perfil = self._perfil_selecionado()
        if not perfil:
            QMessageBox.information(self, "Selecione um perfil", "Escolha um perfil na lista para editar.")
            return
        dialog = ProfileDialog(profile=perfil, parent=self)
        if dialog.exec():
            self.profile_manager.update(dialog.profile)
            self._recarregar_lista()

    def _remover(self) -> None:
        perfil = self._perfil_selecionado()
        if not perfil:
            return
        resposta = QMessageBox.question(
            self, "Remover perfil",
            f"Remover o perfil '{perfil.nome}'? Essa ação não pode ser desfeita.",
        )
        if resposta == QMessageBox.StandardButton.Yes:
            self.profile_manager.remove(perfil.id)
            self._recarregar_lista()
