import sqlite3
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog, QFileDialog, QFormLayout, QHBoxLayout, QLineEdit,
    QListWidget, QMessageBox, QPlainTextEdit, QPushButton, QTextBrowser, QVBoxLayout,
)


class Lettore(QTextBrowser):
    def loadResource(self, tipo, url):
        # Il testo Markdown è già in memoria. Le risorse incorporate sono facoltative.
        return None


class Progetti(QDialog):
    def __init__(self, db, attivita, radice, parent):
        super().__init__(parent)
        self.db = db
        self.ident = attivita["id"]
        self.radice = radice
        self.setWindowTitle("Progetti · " + attivita["nome"])
        layout = QVBoxLayout(self)
        self.lista = QListWidget()
        layout.addWidget(self.lista)
        apri = QPushButton("Apri progetto")
        nuovo = QPushButton("Nuovo progetto")
        layout.addWidget(apri)
        layout.addWidget(nuovo)
        self.lista.currentRowChanged.connect(lambda i: apri.setEnabled(i >= 0))
        apri.clicked.connect(lambda: self.modifica(self.righe[self.lista.currentRow()]))
        nuovo.clicked.connect(lambda: self.modifica(None))
        self.lista.itemDoubleClicked.connect(lambda _: apri.click())
        self.aggiorna()
        apri.setEnabled(bool(self.righe))

    def aggiorna(self):
        self.righe = self.db.execute("SELECT * FROM progetto WHERE attivita_id=? ORDER BY titolo,id",
                                     (self.ident,)).fetchall()
        self.lista.clear()
        self.lista.addItems([r["titolo"] for r in self.righe])
        self.lista.setCurrentRow(0)

    def modifica(self, r):
        dialog = QDialog(self)
        dialog.setWindowTitle("Dettagli progetto")
        dialog.resize(580, 560)
        form = QFormLayout(dialog)
        titolo = QLineEdit(r["titolo"] if r else "")
        cartella = QLineEdit()
        if r:
            percorso = Path(self.radice) / r["cartella"] if r["relativo"] else Path(r["cartella"])
            cartella.setText(str(percorso))
        url = QLineEdit(r["repository"] if r else "")
        readme = QLineEdit(r["readme"] if r else "README.md")
        riassunto = QPlainTextEdit(r["riassunto"] if r else "")
        form.addRow("Titolo", titolo)
        def percorso_con_scelta(label, campo, scegli):
            riga = QHBoxLayout()
            riga.addWidget(campo)
            b = QPushButton("Sfoglia…")
            riga.addWidget(b)
            def seleziona():
                valore = scegli()
                if valore:
                    campo.setText(valore)
                    campo.editingFinished.emit()
            b.clicked.connect(seleziona)
            form.addRow(label, riga)
        percorso_con_scelta("Cartella", cartella, lambda: QFileDialog.getExistingDirectory(
            dialog, "Cartella progetto", cartella.text() or self.radice or ""))
        form.addRow("URL repository", url)
        percorso_con_scelta("README locale", readme, lambda: QFileDialog.getOpenFileName(
            dialog, "Scegli README", cartella.text(), "Markdown (*.md);;Tutti i file (*)")[0])
        lettore = Lettore()
        lettore.setOpenLinks(False)
        form.addRow(lettore)
        def leggi():
            base = Path(cartella.text())
            if not base.is_absolute() or not base.is_dir():
                lettore.setPlainText("Scegli o ricollega la cartella del progetto.")
                return
            if not readme.text().strip():
                lettore.setPlainText("Nessun README collegato.")
                return
            try:
                testo = (base / readme.text()).read_text(encoding="utf-8-sig")
                lettore.setMarkdown(testo)
            except (OSError, UnicodeError):
                lettore.setPlainText("README non disponibile. Controlla il percorso e la codifica UTF-8.")
        cartella.editingFinished.connect(leggi)
        readme.editingFinished.connect(leggi)
        leggi()
        form.addRow("Riassunto", riassunto)
        azioni = QHBoxLayout()
        form.addRow(azioni)
        apri = QPushButton("Apri cartella")
        def esplora():
            base = Path(cartella.text())
            if not base.is_absolute() or not base.is_dir() or not QDesktopServices.openUrl(QUrl.fromLocalFile(str(base))):
                QMessageBox.warning(dialog, "Cartella", "Cartella non disponibile.")
        apri.clicked.connect(esplora)
        azioni.addWidget(apri)
        salva = QPushButton("Salva progetto")
        azioni.addWidget(salva)
        def registra():
            base = Path(cartella.text().strip())
            if not titolo.text().strip() or not base.is_absolute():
                QMessageBox.warning(dialog, "Progetto", "Inserisci un titolo e il percorso completo della cartella.")
                return
            relativo = bool(self.radice and base.is_relative_to(self.radice))
            riferimento = readme.text().strip()
            if riferimento and Path(riferimento).is_relative_to(base):
                riferimento = str(Path(riferimento).relative_to(base))
            dati = (titolo.text().strip(), str(base.relative_to(self.radice) if relativo else base),
                    relativo, url.text().strip(), riferimento, riassunto.toPlainText())
            try:
                with self.db:
                    if r:
                        self.db.execute("""UPDATE progetto SET titolo=?,cartella=?,relativo=?,repository=?,
                                        readme=?,riassunto=? WHERE id=?""", (*dati, r["id"]))
                    else:
                        self.db.execute("""INSERT INTO progetto(titolo,cartella,relativo,repository,readme,
                                        riassunto,attivita_id) VALUES(?,?,?,?,?,?,?)""", (*dati, self.ident))
                dialog.accept()
            except sqlite3.Error as exc:
                QMessageBox.warning(dialog, "Salvataggio progetto", str(exc))
        salva.clicked.connect(registra)
        if dialog.exec():
            self.aggiorna()
