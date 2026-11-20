import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from tests.test_fase1 import PIANO, clic
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QLineEdit, QMessageBox, QPlainTextEdit, QTextBrowser
from libretto.db import apri, backup, importa, ripristina
from libretto.progetti import Progetti
from libretto.ui import Finestra


class ProgettiECopie(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.file = self.root / "libretto.sqlite"
        self.db = apri(self.file)
        self.addCleanup(self.db.close)
        importa(self.db, PIANO)
        self.finestra = Finestra(self.db)
        self.addCleanup(self.finestra.close)

    def test_progetti_e_copia(self):
        directory = self.root / "Reti"
        directory.mkdir()
        readme = directory / "README.md"
        readme.write_text("# Laboratorio", encoding="utf-8")
        with self.db:
            self.db.execute("UPDATE piano SET radice=?", (str(self.root),))
        attivita = self.db.execute("SELECT * FROM attivita").fetchone()
        progetti = Progetti(self.db, attivita, str(self.root), self.finestra)
        letture = []
        def compila():
            dialog = self.app.activeModalWidget()
            titolo, cartella, repo, riferimento = dialog.findChildren(QLineEdit)
            titolo.setText("Laboratorio")
            cartella.setText(str(directory))
            cartella.editingFinished.emit()
            repo.setText("https://example.org/reti")
            letture.append(dialog.findChild(QTextBrowser).toPlainText())
            dialog.findChild(QPlainTextEdit).setPlainText("Appunti")
            clic(dialog, "Salva progetto")
        for _ in range(2):
            QTimer.singleShot(0, compila)
            clic(progetti, "Nuovo progetto")
        self.assertEqual(letture, ["Laboratorio"] * 2)
        readme.unlink()
        with self.db:
            self.db.execute("UPDATE attivita SET stato='Superato',voto=30")
        def modifica():
            dialog = self.app.activeModalWidget()
            letture.append(dialog.findChild(QTextBrowser).toPlainText())
            dialog.findChild(QPlainTextEdit).setPlainText("Nuovi appunti")
            clic(dialog, "Salva progetto")
        QTimer.singleShot(0, modifica)
        clic(progetti, "Apri progetto")
        self.assertIn("README non disponibile", letture[-1])
        copia = self.root / "copia.sqlite"
        backup(self.db, copia)
        with self.db:
            self.db.execute("DELETE FROM progetto")
        sicurezza = ripristina(self.db, copia)
        with closing(sqlite3.connect(sicurezza)) as precedente:
            self.assertEqual(precedente.execute("SELECT count(*) FROM progetto").fetchone()[0], 0)
        righe = self.db.execute("SELECT riassunto, cartella, relativo FROM progetto ORDER BY id").fetchall()
        self.assertEqual([tuple(r) for r in righe], [("Nuovi appunti","Reti",1), ("Appunti","Reti",1)])

    def test_rifiuto_e_annullamento(self):
        copia = self.root / "copia.sqlite"
        backup(self.db, copia)
        with patch("libretto.ui.QFileDialog.getOpenFileName", return_value=(str(copia), "")), \
             patch("libretto.ui.QMessageBox.question", return_value=QMessageBox.No), patch("libretto.ui.ripristina") as azione:
            self.finestra.ripristina_backup()
            azione.assert_not_called()
        with closing(sqlite3.connect(copia)) as db:
            db.execute("PRAGMA user_version=77")
        with self.assertRaises(ValueError):
            ripristina(self.db, copia)
        copia.write_bytes(b"Database danneggiato")
        with self.assertRaises(sqlite3.DatabaseError):
            ripristina(self.db, copia)
        for operazione in (backup, ripristina):
            with self.assertRaises(ValueError):
                operazione(self.db, self.file)
        self.assertEqual(self.db.execute("SELECT nome FROM attivita").fetchone()[0], "Reti")

    def test_aggiornamento_fase_due(self):
        copia = self.root / "fase-due.sqlite"
        backup(self.db, copia)
        with closing(sqlite3.connect(copia)) as precedente, precedente:
            precedente.execute("DROP TABLE progetto")
            precedente.execute("PRAGMA user_version=2")
            precedente.execute("UPDATE attivita SET stato='Superato', voto=30, lode=1")
        with closing(apri(copia)) as aggiornata:
            self.assertEqual(aggiornata.execute("PRAGMA user_version").fetchone()[0], 3)
            self.assertEqual(tuple(aggiornata.execute("SELECT nome,voto,lode FROM attivita").fetchone()),
                             ("Reti", 30, 1))
            self.assertEqual(aggiornata.execute("SELECT count(*) FROM progetto").fetchone()[0], 0)
