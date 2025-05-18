import sys
import os
from PyQt5.QtWidgets import QApplication
from ui.main_window import MainWindow

def main():
    if not os.path.exists("./data"):
        os.makedirs("./data/tables", exist_ok=True)
        os.makedirs("./data/indexes", exist_ok=True)
    
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()