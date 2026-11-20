import json
import sqlite3
from datetime import date
from pathlib import Path

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QDesktopServices, QPainter, QPen
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFileDialog, QFileSystemModel, QFormLayout,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMainWindow, QMessageBox,
    QPlainTextEdit, QPushButton, QTableWidget, QTableWidgetItem, QTreeView,
    QVBoxLayout, QWidget,
)

from carriera import chiave, positivo, verifica, statistiche
from db import aggiungi, azzera_piano, backup, collega, importa, ripristina
from progetti import Progetti


def bottone(layout, nome, azione):
    b = QPushButton(nome)
    layout.addWidget(b)
    b.clicked.connect(lambda: azione())
    return b


class Anello(QPushButton):
    def __init__(self, acquisiti, totale, mostra_cfu):
        super().__init__()
        self.percentuale = 100 * acquisiti / totale
        self.setCheckable(True)
        self.setChecked(mostra_cfu)
        self.setToolTip("Alterna percentuale e CFU acquisiti")
        self.setAccessibleName("Progresso CFU")
        def etichetta(cfu):
            self.setText(f"{acquisiti} / {totale}" if cfu else f"{self.percentuale:.0f}%")
            self.update()
        self.toggled.connect(etichetta)
        etichetta(mostra_cfu)
        lato = max(90, self.fontMetrics().horizontalAdvance(f"{acquisiti} / {totale}") + 24)
        self.setFixedSize(lato, lato)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        cerchio = self.rect().adjusted(6, 6, -6, -6)
        p.setPen(QPen(self.palette().mid().color(), 6))
        p.drawEllipse(cerchio)
        p.setPen(QPen(self.palette().highlight().color(), 6))
        p.drawArc(cerchio, 90 * 16, -round(min(self.percentuale, 100) * 57.6))
        p.setPen(self.palette().buttonText().color())
        p.drawText(self.rect(), Qt.AlignCenter, self.text())
        if self.hasFocus():
            p.drawRect(self.rect().adjusted(1, 1, -2, -2))


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
        bottone(barra, "Impostazioni", self.impostazioni)
        self.piano = self.db.execute("SELECT * FROM piano").fetchone()
        if self.piano:
            bottone(barra, "Radice materiali…", self.radice)
        label = QLabel(titolo)
        font = label.font()
        font.setPointSize(17)
        label.setFont(font)
        layout.addWidget(label)
        return layout

    def impostazioni(self):
        layout = self.pagina("Impostazioni")
        layout.addWidget(QLabel("Il backup contiene il libretto e i collegamenti.\n"
                                "Copia separatamente le cartelle di dispense e progetti."))
        bottone(layout, "Crea backup…", self.crea_backup)
        bottone(layout, "Ripristina backup…", self.ripristina_backup)
        layout.addStretch()

    def crea_backup(self):
        file, _ = QFileDialog.getSaveFileName(self, "Crea backup", "libretto-backup.sqlite", "Database (*.sqlite)")
        if file:
            try:
                backup(self.db, file)
                QMessageBox.information(self, "Backup completato", file)
            except (ValueError, sqlite3.Error, OSError) as exc:
                QMessageBox.warning(self, "Backup non riuscito", str(exc))

    def ripristina_backup(self):
        file, _ = QFileDialog.getOpenFileName(self, "Ripristina backup", "", "Database (*.sqlite);;Tutti i file (*)")
        if not file:
            return
        if QMessageBox.question(self, "Ripristina libretto", "Sostituire il libretto corrente con la copia scelta?",
                                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        try:
            sicurezza = ripristina(self.db, file)
            self.home()
            QMessageBox.information(self, "Ripristino completato", f"Copia del libretto precedente:\n{sicurezza}")
        except (ValueError, sqlite3.Error, OSError) as exc:
            QMessageBox.warning(self, "Ripristino non riuscito", str(exc))

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
        if preparazione:
            acquisiti, media = statistiche(self.db.execute("SELECT stato,cfu,voto FROM attivita"))
            riepilogo = QHBoxLayout()
            layout.addLayout(riepilogo)
            valore = "—" if media is None else f"{media:.2f}".replace(".", ",")
            riepilogo.addWidget(QLabel(f"Media ponderata   {valore}"))
            riepilogo.addStretch()
            riepilogo.addWidget(QLabel("Progresso CFU"))
            anello = Anello(acquisiti, self.piano["totale"], bool(self.piano["mostra_cfu"]))
            riepilogo.addWidget(anello)
            def memorizza(cfu):
                with self.db:
                    self.db.execute("UPDATE piano SET mostra_cfu=?", (cfu,))
            anello.toggled.connect(memorizza)
        else:
            bottone(layout, "Aggiungi attività", lambda: self.scheda(None))
            bottone(layout, "Azzera piano…", self.conferma_azzeramento)

    def conferma_azzeramento(self):
        dialog = QMessageBox(self)
        dialog.setWindowTitle("Azzera piano")
        dialog.setTextFormat(Qt.PlainText)
        dialog.setText(f"Eliminare definitivamente il piano «{self.piano['corso']}»?")
        dialog.setInformativeText(
            "Verranno eliminati attività, esiti, note, appelli, schede progetto e collegamenti ai materiali. "
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
        stato.addItems(["Da preparare", "In preparazione", "Superato"])
        if r:
            stato.setCurrentText(r["stato"])
        form.addRow("Stato", stato)
        esito = QComboBox()
        esito.addItems(["Scegli esito", "Idoneità", *map(str, range(18, 31)), "30 e lode"])
        if r and r["stato"] == "Superato":
            esito.setCurrentText("Idoneità" if r["idoneita"] else "30 e lode" if r["lode"] else str(r["voto"]))
        form.addRow("Risultato", esito)
        esito.setEnabled(stato.currentText() == "Superato")
        stato.currentTextChanged.connect(lambda testo: esito.setEnabled(testo == "Superato"))
        modalita = QHBoxLayout()
        caselle = []
        for nome in ("scritto", "orale", "progetto"):
            casella = QCheckBox(nome.capitalize())
            casella.setChecked(bool(r and r[nome]))
            modalita.addWidget(casella)
            caselle.append(casella)
        form.addRow("Modalità", modalita)
        docente = QLineEdit(r["docente"] if r else "")
        form.addRow("Docente", docente)
        note = QPlainTextEdit(r["note"] if r else "")
        form.addRow("Note", note)
        if r:
            bottone(form, "Progetti…", lambda: Progetti(self.db, r, self.piano["radice"], dialog).exec())

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
            risultato = esito.currentText() if stato.currentText() == "Superato" else ""
            if risultato == "Scegli esito":
                QMessageBox.warning(dialog, "Risultato", "Seleziona un voto o l’idoneità.")
                return
            if r and r["stato"] == "Superato" and not risultato:
                risposta = QMessageBox.question(dialog, "Riapri attività", "Rimuovere il risultato registrato?",
                                                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if risposta != QMessageBox.Yes:
                    return
            lode = risultato == "30 e lode"
            voto = 30 if lode else int(risultato) if risultato.isdigit() else None
            try:
                with self.db:
                    if r:
                        activity_id = ident
                        self.db.execute("UPDATE attivita SET nome=?,chiave=?,cfu=?,anno=? WHERE id=?",
                                        (nome, chiave(nome), cfu, anno, ident))
                    else:
                        aggiungi(self.db, dict(nome=nome, cfu=cfu, anno=anno))
                        activity_id = self.db.execute("SELECT last_insert_rowid()").fetchone()[0]
                    self.db.execute("""UPDATE attivita SET stato=?,appello=?,voto=?,lode=?,idoneita=?,
                                    scritto=?,orale=?,progetto=?,docente=?,note=? WHERE id=?""",
                                    (stato.currentText(), appello or None, voto, lode, risultato == "Idoneità",
                                     *(c.isChecked() for c in caselle), docente.text().strip(),
                                     note.toPlainText(), activity_id))
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
