import sys
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow

def main():
    # Inicializa o gerenciador de aplicação do PySide6
    app = QApplication(sys.argv)
    
    # Cria e exibe a janela principal do sistema
    window = MainWindow()
    window.show()
    
    # Executa o loop principal do sistema
    sys.exit(app.exec())

if __name__ == "__main__":
    main()