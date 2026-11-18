"""Launch the Flood Alert simulator:  python main.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from flood_alert.ui.main_window import MainWindow  # noqa: E402


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
