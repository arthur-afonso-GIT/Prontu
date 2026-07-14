import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPalette, QColor
from ui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    
    # Força estilo Fusion + paleta clara, para não herdar o modo escuro do Windows
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#f8fafc"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#0f172a"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#0f172a"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#f1f5f9"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#0f172a"))
    app.setPalette(palette)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()