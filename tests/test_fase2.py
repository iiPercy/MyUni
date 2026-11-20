import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QComboBox, QMessageBox, QPlainTextEdit

from libretto.carriera import statistiche
from libretto.db import apri, importa
from tests.test_fase1 import clic
from libretto.ui import Anello, Finestra


class Carriera(unittest.TestCase):
    def test_migrazione(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "libretto.sqlite"
            db = sqlite3.connect(file)
            db.executescript("""
                CREATE TABLE piano(id INTEGER PRIMARY KEY, corso, totale, radice);
                INSERT INTO piano VALUES(1,'Prova',60,'C:/Materiali');
                CREATE TABLE attivita(id INTEGER PRIMARY KEY,piano_id,nome,chiave,cfu,anno,
                    stato,appello,percorso,relativo);
                INSERT INTO attivita VALUES(7,1,'Reti','reti',6,NULL,'In preparazione',
                    '2026-12-01','Reti',1);
            """)
            db.close()
            db = apri(file)
            try:
                r = db.execute("SELECT * FROM attivita WHERE id=7").fetchone()
                self.assertEqual((r["stato"], r["percorso"], r["appello"], r["voto"]),
                                 ("In preparazione", "Reti", "2026-12-01", None))
                with self.assertRaises(sqlite3.IntegrityError):
                    db.execute("UPDATE attivita SET stato='Superato'")
            finally:
                db.close()

    def test_carriera_da_scheda(self):
        app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "libretto.sqlite"
            db = apri(file)
            attivita = [dict(nome=n, cfu=c, anno=1) for n, c in [("A", 6), ("B", 3), ("C", 3)]]
            importa(db, dict(corso="Prova", cfu_totali=60, attivita=attivita))
            with db:
                db.execute("UPDATE attivita SET percorso='dispense' WHERE id=1")
            finestra = Finestra(db)
            def calcolo():
                return statistiche(db.execute("SELECT * FROM attivita"))
            self.assertEqual(calcolo(), (0, None))
            for ident, risultato in enumerate(("30 e lode", "24", "Idoneità"), 1):
                def registra():
                    dialog = app.activeModalWidget()
                    stato, esito = dialog.findChildren(QComboBox)
                    stato.setCurrentText("Superato")
                    esito.setCurrentText(risultato)
                    dialog.findChild(QPlainTextEdit).setPlainText("Appunti")
                    clic(dialog, "Salva")
                QTimer.singleShot(0, registra)
                finestra.scheda(ident)
            self.assertEqual(calcolo(), (12, 28))
            anello = finestra.centralWidget().findChild(Anello)
            self.assertEqual(anello.text(), "20%")
            anello.click()
            finestra.close()
            db.close()
            db = apri(file)
            finestra = Finestra(db)
            self.assertEqual(finestra.centralWidget().findChild(Anello).text(), "12 / 60")
            for risposta in (QMessageBox.No, QMessageBox.Yes):
                def riapri():
                    dialog = app.activeModalWidget()
                    dialog.findChild(QComboBox).setCurrentText("In preparazione")
                    clic(dialog, "Salva")
                    if risposta == QMessageBox.No:
                        dialog.reject()
                with patch("libretto.ui.QMessageBox.question", return_value=risposta):
                    QTimer.singleShot(0, riapri)
                    finestra.scheda(1)
                self.assertEqual(calcolo(), (12, 28) if risposta == QMessageBox.No else (6, 24))
            r = db.execute("SELECT * FROM attivita WHERE id=1").fetchone()
            self.assertEqual((r["voto"], r["lode"], r["note"], r["percorso"]), (None, 0, "Appunti", "dispense"))
            finestra.close()
            db.close()
