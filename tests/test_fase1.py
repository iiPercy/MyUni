import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QComboBox, QLineEdit, QPushButton, QTreeView

from libretto.carriera import verifica
from libretto.db import apri, importa
from libretto.ui import Anteprima, Finestra


PIANO = dict(corso="Prova", cfu_totali=9, attivita=[dict(nome="Reti", cfu=6, anno=None)])


def clic(widget, testo):
    next(b for b in widget.findChildren(QPushButton) if b.text() == testo).click()


class FaseUno(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_validazione(self):
        errori, avvisi, somma = verifica(PIANO)
        self.assertEqual((errori, len(avvisi), somma), ([], 2, 6))
        for riga in [dict(nome=" ", cfu=6, anno=None), dict(nome="X", cfu=True, anno=1),
                     dict(nome="X", cfu=6), dict(nome="X", cfu=6, anno=0),
                     dict(nome="  RETI ", cfu=6, anno=1)]:
            self.assertTrue(verifica(dict(PIANO, attivita=PIANO["attivita"] + [riga]))[0])
        anteprima = Anteprima("{", None)
        self.assertFalse(anteprima.salva.isEnabled())
        anteprima.editor.setPlainText(json.dumps(PIANO))
        self.assertTrue(anteprima.salva.isEnabled())

    def test_percorso_utente(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            db = apri(root / "test.sqlite")
            self.addCleanup(db.close)
            finestra = Finestra(db)
            file = root / "piano.json"
            file.write_text(json.dumps(PIANO))
            with patch("libretto.ui.QFileDialog.getOpenFileName", return_value=(str(file), "")):
                for azione, count in [("Annulla", 0), ("Conferma importazione", 1)]:
                    QTimer.singleShot(0, lambda: clic(self.app.activeModalWidget(), azione))
                    clic(finestra.centralWidget(), "Importa piano")
                    self.assertEqual(db.execute("SELECT count(*) FROM piano").fetchone()[0], count)
            with self.assertRaises(sqlite3.IntegrityError):
                importa(db, PIANO)

            def modifica():
                dialog = self.app.activeModalWidget()
                dialog.findChild(QComboBox).setCurrentText("In preparazione")
                dialog.findChildren(QLineEdit)[0].setText("Reti II")
                clic(dialog, "Salva")
            finestra.centralWidget().findChild(QPushButton, "esame").click()
            QTimer.singleShot(0, modifica)
            clic(finestra.centralWidget(), "Modifica dettagli")
            clic(finestra.centralWidget(), "Home")
            with patch("libretto.ui.QFileDialog.getExistingDirectory", return_value=str(root)):
                clic(finestra.centralWidget(), "Radice materiali…")
            cartella = root / "Reti"
            cartella.mkdir()
            dispensa = cartella / "dispensa.txt"
            dispensa.write_text("Prova")
            clic(finestra.centralWidget(), "Materiali")
            with patch("libretto.ui.QFileDialog.getExistingDirectory", return_value=str(cartella)):
                clic(finestra.centralWidget(), "Collega cartella")
            self.assertEqual(db.execute("SELECT percorso FROM attivita").fetchone()[0], "Reti")
            finestra.close()
            db.close()
            db = apri(root / "test.sqlite")
            try:
                with patch("libretto.ui.QFileSystemModel", side_effect=AssertionError):
                    finestra = Finestra(db)
                clic(finestra.centralWidget(), "Materiali")
                tree = finestra.centralWidget().findChild(QTreeView)
                with patch("libretto.ui.QDesktopServices.openUrl", return_value=True) as apertura:
                    tree.activated.emit(tree.model().index(str(dispensa)))
                    self.assertEqual(Path(apertura.call_args.args[0].toLocalFile()), dispensa)
                finestra.close()
            finally:
                db.close()

    def test_azzeramento_e_reimportazione(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            db = apri(root / "test.sqlite")
            try:
                importa(db, PIANO)
                dispensa = root / "dispensa.txt"
                dispensa.write_text("Appunti")
                with db:
                    db.execute("UPDATE attivita SET percorso=?", (directory,))
                finestra = Finestra(db)
                clic(finestra.centralWidget(), "Piano")
                for scelta, attesi in [("Annulla", 1), ("Azzera piano", 0)]:
                    QTimer.singleShot(0, lambda: clic(self.app.activeModalWidget(), scelta))
                    clic(finestra.centralWidget(), "Azzera piano…")
                    self.assertEqual(db.execute("SELECT count(*) FROM piano").fetchone()[0], attesi)
                    self.assertEqual(db.execute("SELECT count(*) FROM attivita").fetchone()[0], attesi)
                file = root / "nuovo.json"
                file.write_text(json.dumps(dict(PIANO, corso="Definitivo")))
                with patch("libretto.ui.QFileDialog.getOpenFileName", return_value=(str(file), "")):
                    QTimer.singleShot(0, lambda: clic(self.app.activeModalWidget(), "Conferma importazione"))
                    clic(finestra.centralWidget(), "Importa piano")
                self.assertEqual(finestra.piano["corso"], "Definitivo")
                self.assertIsNone(db.execute("SELECT percorso FROM attivita").fetchone()[0])
                self.assertEqual(dispensa.read_text(), "Appunti")
                finestra.close()
            finally:
                db.close()
