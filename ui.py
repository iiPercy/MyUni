import json
import sqlite3
from datetime import date
from pathlib import Path

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFileDialog, QFileSystemModel, QFormLayout,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMainWindow, QMessageBox,
    QPlainTextEdit, QPushButton, QTableWidget, QTableWidgetItem, QTreeView,
    QVBoxLayout, QWidget,
)

from carriera import chiave, positivo, verifica
from db import aggiungi, azzera_piano, collega, importa


def bottone(layout, nome, azione):
    b = QPushButton(nome)
    layout.addWidget(b)
    b.clicked.connect(lambda: azione())
    return b


class Anteprima(QDialog):
    def __init__(self, testo, parent):
        super().__init__(parent)
        self.setWindowTitle("Anteprima del piano")
        self.resize(660, 500)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Controlla le attività. Puoi correggere direttamente il JSON."))
        self.editor = QPlainTextEdit(testo)
        layout.addWidget(self.editor)
        self.info = QLabel()
        self.info.setWordWrap(True)
        layout.addWidget(self.info)
        azioni = QHBoxLayout()
        layout.addLayout(azioni)
        bottone(azioni, "Annulla", self.reject)
        self.salva = bottone(azioni, "Conferma importazione", self.accept)
        self.editor.textChanged.connect(self.aggiorna)
        self.aggiorna()

    def aggiorna(self):
        try:
            self.piano = json.loads(self.editor.toPlainText())
            errori, avvisi, somma = verifica(self.piano)
            totale = self.piano.get("cfu_totali", "—") if isinstance(self.piano, dict) else "—"
            righe = [f"CFU delle attività: {somma}   ·   Totale richiesto: {totale}"]
            righe.extend("Errore: " + e for e in errori[:3])
            righe.extend("Avviso: " + a for a in avvisi[:3])
            self.info.setText("\n".join(righe))
            self.salva.setEnabled(not errori)
        except ValueError as exc:
            self.info.setText(f"JSON non valido: {exc}")
            self.salva.setEnabled(False)


class Finestra(QMainWindow):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.setWindowTitle("Libretto UniPi")
        self.resize(820, 540)
        self.home()

    def pagina(self, titolo):
        widget = QWidget()
        self.setCentralWidget(widget)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        barra = QHBoxLayout()
        layout.addLayout(barra)
        bottone(barra, "Home", self.home)
        bottone(barra, "Piano", lambda: self.home(False))
        barra.addStretch()
        self.piano = self.db.execute("SELECT * FROM piano").fetchone()
        if self.piano:
            bottone(barra, "Radice materiali…", self.radice)
        label = QLabel(titolo)
        font = label.font()
        font.setPointSize(17)
        label.setFont(font)
        layout.addWidget(label)
        return layout

    def radice(self):
        path = QFileDialog.getExistingDirectory(self, "Scegli radice materiali", self.piano["radice"] or "")
        if path:
            with self.db:
                self.db.execute("UPDATE piano SET radice=?", (path,))
            self.home()

    def home(self, preparazione=True):
        self.preparazione = preparazione
        layout = self.pagina("In preparazione" if preparazione else "Piano di studi")
        if not self.piano:
            bottone(layout, "Importa piano", self.importazione)
            layout.addStretch()
            return
        layout.addWidget(QLabel(self.piano["corso"]))
        query = "SELECT * FROM attivita"
        if preparazione:
            query += " WHERE stato='In preparazione'"
        righe = self.db.execute(query + " ORDER BY nome COLLATE NOCASE").fetchall()
        if not righe and preparazione:
            layout.addWidget(QLabel("Scegli dal piano un esame da preparare."))
            bottone(layout, "Apri piano", lambda: self.home(False))
        else:
            colonne = ["Attività", "Appello"] if preparazione else ["Attività", "Anno", "CFU", "Stato"]
            tab = QTableWidget(len(righe), len(colonne) + 2)
            tab.setHorizontalHeaderLabels(colonne + ["", ""])
            tab.setEditTriggers(QTableWidget.NoEditTriggers)
            tab.verticalHeader().hide()
            tab.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
            tab.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
            layout.addWidget(tab)
            for i, r in enumerate(righe):
                valori = [r["nome"], r["appello"]] if preparazione else [r[k] for k in ("nome","anno","cfu","stato")]
                for j, val in enumerate(valori):
                    tab.setItem(i, j, QTableWidgetItem(str(val or "")))
                for j, (nome, azione) in enumerate([("Scheda", self.scheda), ("Materiali", self.materiali)], len(valori)):
                    b = QPushButton(nome)
                    b.clicked.connect(lambda _, ident=r["id"], fn=azione: fn(ident))
                    tab.setCellWidget(i, j, b)
        if not preparazione:
            bottone(layout, "Aggiungi attività", lambda: self.scheda(None))
            bottone(layout, "Azzera piano…", self.conferma_azzeramento)

    def conferma_azzeramento(self):
        dialog = QMessageBox(self)
        dialog.setWindowTitle("Azzera piano")
        dialog.setTextFormat(Qt.PlainText)
        dialog.setText(f"Eliminare definitivamente il piano «{self.piano['corso']}»?")
        dialog.setInformativeText(
            "Verranno eliminati attività, stati, appelli, radice materiali e collegamenti. "
            "I file sul disco restano disponibili. Potrai importare un nuovo piano dalla home."
        )
        annulla = dialog.addButton("Annulla", QMessageBox.RejectRole)
        conferma = dialog.addButton("Azzera piano", QMessageBox.DestructiveRole)
        dialog.setDefaultButton(annulla)
        dialog.setEscapeButton(annulla)
        dialog.exec()
        if dialog.clickedButton() != conferma:
            return
        try:
            azzera_piano(self.db)
        except sqlite3.Error as exc:
            QMessageBox.warning(self, "Azzeramento non riuscito", str(exc))
            return
        self.home()

    def importazione(self):
        file, _ = QFileDialog.getOpenFileName(self, "Apri piano", "", "Piani JSON (*.json)")
        if not file:
            return
        try:
            anteprima = Anteprima(Path(file).read_text(encoding="utf-8-sig"), self)
            if anteprima.exec():
                importa(self.db, anteprima.piano)
                self.home(False)
        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "Piano presente", "Modifica le attività dal piano.")
            self.home(False)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Importazione", str(exc))

    def scheda(self, ident):
        r = self.db.execute("SELECT * FROM attivita WHERE id=?", (ident,)).fetchone()
        dialog = QDialog(self)
        dialog.setWindowTitle("Scheda attività")
        form = QFormLayout(dialog)
        campi = {}
        for key, label in [("nome","Nome"), ("cfu","CFU"), ("anno","Anno"), ("appello","Appello (AAAA-MM-GG)")]:
            campo = QLineEdit(str(r[key] or "") if r else "")
            form.addRow(label, campo)
            campi[key] = campo
        stato = QComboBox()
        stato.addItems(["Da preparare", "In preparazione"])
        if r:
            stato.setCurrentText(r["stato"])
        form.addRow("Stato", stato)

        def salva():
            try:
                nome = campi["nome"].text().strip()
                cfu = int(campi["cfu"].text())
                anno = int(campi["anno"].text()) if campi["anno"].text().strip() else None
                if not nome or not positivo(cfu) or (anno is not None and not positivo(anno)):
                    raise ValueError
            except ValueError:
                QMessageBox.warning(dialog, "Controlla i dati", "Inserisci nome, CFU positivi e anno positivo o vuoto.")
                return
            appello = campi["appello"].text().strip()
            try:
                if appello and date.fromisoformat(appello).isoformat() != appello:
                    raise ValueError
            except ValueError:
                QMessageBox.warning(dialog, "Appello", "Inserisci una data valida nel formato AAAA-MM-GG.")
                return
            try:
                with self.db:
                    if r:
                        activity_id = ident
                        self.db.execute("UPDATE attivita SET nome=?,chiave=?,cfu=?,anno=? WHERE id=?",
                                        (nome, chiave(nome), cfu, anno, ident))
                    else:
                        aggiungi(self.db, dict(nome=nome, cfu=cfu, anno=anno))
                        activity_id = self.db.execute("SELECT last_insert_rowid()").fetchone()[0]
                    self.db.execute("UPDATE attivita SET stato=?, appello=? WHERE id=?",
                                    (stato.currentText(), appello or None, activity_id))
                dialog.accept()
            except sqlite3.IntegrityError:
                QMessageBox.warning(dialog, "Nome duplicato", "Esiste già una attività con questo nome.")

        bottone(form, "Salva", salva)
        if dialog.exec():
            self.home(self.preparazione)

    def materiali(self, ident):
        r = self.db.execute("SELECT * FROM attivita WHERE id=?", (ident,)).fetchone()
        layout = self.pagina("Materiali · " + r["nome"])
        radice = self.piano["radice"]
        percorso = Path(r["percorso"]) if r["percorso"] else None
        if r["relativo"]:
            percorso = Path(radice) / percorso

        def scegli():
            path = QFileDialog.getExistingDirectory(self, "Collega cartella", radice or "")
            if path:
                collega(self.db, ident, path, radice)
                self.materiali(ident)

        barra = QHBoxLayout()
        layout.addLayout(barra)
        bottone(barra, "Ricollega" if percorso else "Collega cartella", scegli)
        if percorso:
            layout.addWidget(QLabel(str(percorso)))
        if not percorso or not percorso.is_dir():
            layout.addWidget(QLabel("Cartella non disponibile." if percorso else "Scegli la cartella di questa attività."))
            layout.addStretch()
            return

        def apri_locale(file):
            if not file.exists() or not QDesktopServices.openUrl(QUrl.fromLocalFile(str(file))):
                QMessageBox.warning(self, "Materiali", "Impossibile aprire il percorso selezionato.")

        bottone(barra, "Apri in Esplora file", lambda: apri_locale(percorso))
        tree = QTreeView()
        model = QFileSystemModel(tree)
        model.setReadOnly(True)
        tree.setModel(model)
        tree.setRootIndex(model.setRootPath(str(percorso)))
        tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        def apri_file(index):
            file = Path(model.filePath(index))
            if file.is_file():
                apri_locale(file)
        tree.activated.connect(apri_file)
        layout.addWidget(tree)
        progetto = QCheckBox("Includi Progetto")
        layout.addWidget(progetto)

        def crea():
            nomi = ["Dispense", "Esercizi", "Esami passati"]
            if progetto.isChecked():
                nomi.append("Progetto")
            try:
                for nome in nomi:
                    (percorso / nome).mkdir(exist_ok=True)
            except OSError as exc:
                QMessageBox.warning(self, "Creazione cartelle", str(exc))
        bottone(layout, "Crea sottocartelle standard", crea)
