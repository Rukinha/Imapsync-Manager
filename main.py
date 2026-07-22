"""IMAPSync Manager — ponto de entrada da aplicação.

Uso:
    python main.py
"""
import sys
from pathlib import Path

# Garante que os pacotes controllers/models/services sejam importáveis
# quando o script é executado a partir de outro diretório.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from PyQt6.QtWidgets import QApplication

from controllers.main_controller import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("IMAPSync Manager")

    janela = MainWindow()
    janela.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
