import sys
import os

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from PyQt6.QtWidgets import QApplication
from ui import P2PHostWindow


def main() -> None:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = P2PHostWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
