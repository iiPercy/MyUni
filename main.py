import sys
from pathlib import Path

from PySide6.QtCore import QStandardPaths
from PySide6.QtWidgets import QApplication

from libretto.db import apri
from libretto.ui import Finestra


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Libretto UniPi")
    directory = Path(QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation))
    directory.mkdir(parents=True, exist_ok=True)
    db = apri(directory / "libretto.sqlite")
    finestra = Finestra(db)
    finestra.show()
    try:
        return app.exec()
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
