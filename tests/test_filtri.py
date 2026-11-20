import unittest
from contextlib import closing

from tests.test_fase1 import clic
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QComboBox, QLabel, QLineEdit

from libretto.db import apri, importa
from libretto.ui import Finestra, PianoSchede


class FiltriPiano(unittest.TestCase):
    def test_ricerca_stato_ritorno_e_reset(self):
        app = QApplication.instance() or QApplication([])
        with closing(apri(":memory:")) as db:
            nomi = ["Reti di calcolatori", "Reti wireless", "Analisi"]
            importa(db, dict(corso="Prova", cfu_totali=18,
                             attivita=[dict(nome=n, cfu=6, anno=1) for n in nomi]))
            with db:
                db.execute("UPDATE attivita SET stato='Superato', voto=28 WHERE id=1")
                db.execute("UPDATE attivita SET stato='In preparazione' WHERE id=2")
            finestra = Finestra(db)
            finestra.home(False)
            finestra.show()
            self.addCleanup(finestra.close)
            pagina = finestra.centralWidget()
            cerca = pagina.findChild(QLineEdit)
            cerca.setText("RETI")
            griglia = pagina.findChild(PianoSchede)
            self.assertEqual([c.accessibleName() for c in griglia.visibili], nomi[:2])
            pagina.findChild(QComboBox).setCurrentText("In preparazione")
            self.assertEqual(len(griglia.visibili), 1)
            carta = griglia.visibili[0]
            self.assertEqual(carta.property("stato"), "In preparazione")
            carta.click()

            def modifica():
                dialog = app.activeModalWidget()
                dialog.findChild(QComboBox).setCurrentText("Da preparare")
                clic(dialog, "Salva")
            QTimer.singleShot(0, modifica)
            clic(finestra.centralWidget(), "Modifica dettagli")
            clic(finestra.centralWidget(), "←")
            app.processEvents()
            pagina = finestra.centralWidget()
            self.assertEqual(pagina.findChild(QLineEdit).text(), "RETI")
            self.assertEqual(pagina.findChild(QComboBox).currentText(), "In preparazione")
            self.assertTrue(any(l.isVisible() and l.text() == "Nessun esame trovato"
                                for l in pagina.findChildren(QLabel)))
            clic(pagina, "Azzera filtri")
            griglia = pagina.findChild(PianoSchede)
            self.assertEqual(len(griglia.visibili), 3)
            self.assertEqual(griglia.visibili[-1].property("stato"), "Da preparare")
