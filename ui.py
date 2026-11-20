import json
import sqlite3
from datetime import date
from pathlib import Path

from PySide6.QtCore import QTimer, QUrl, Qt
from PySide6.QtGui import QColor, QDesktopServices, QPainter, QPen
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFileDialog, QFileSystemModel, QFormLayout,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMainWindow, QMessageBox,
    QPlainTextEdit, QPushButton, QTableWidget, QTableWidgetItem, QTreeView,
    QGridLayout, QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)

from carriera import chiave, positivo, verifica, statistiche
from db import aggiungi, azzera_piano, backup, collega, importa, ripristina
from progetti import Progetti


def bottone(layout, nome, azione):
    b = QPushButton(nome)
    layout.addWidget(b)
    b.clicked.connect(lambda: azione())
    return b


class CartaEsame(QPushButton):
    def sizeHint(self):
        return self.layout().sizeHint()

    def minimumSizeHint(self):
        return self.layout().minimumSize()

    def heightForWidth(self, width):
        return self.layout().totalHeightForWidth(width)


class PianoSchede(QScrollArea):
    def __init__(self, righe, apri):
        super().__init__()
        self.setWidgetResizable(True)
        corpo = QWidget()
        self.griglia = QGridLayout(corpo)
        self.griglia.setAlignment(Qt.AlignTop)
        self.griglia.setSpacing(10)
        self.colonne = 0
        self.schede = []
        for r in righe:
            scheda = CartaEsame(corpo)
            scheda.setObjectName("esame")
            scheda.setProperty("stato", r["stato"])
            scheda.setAccessibleName(r["nome"])
            politica = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            politica.setHeightForWidth(True)
            scheda.setSizePolicy(politica)
            contenuto = QVBoxLayout(scheda)
            contenuto.setContentsMargins(14, 12, 14, 12)
            anno = f"Anno {r['anno']}" if r["anno"] else "Anno da definire"
            for testo, ruolo in [(f"{anno}   ·   {r['cfu']} CFU", "metadati"),
                                 (r["nome"], "nomeEsame"), (r["stato"], "statoEsame")]:
                label = QLabel(testo)
                label.setTextFormat(Qt.PlainText)
                label.setWordWrap(True)
                label.setObjectName(ruolo)
                label.setProperty("superato", r["stato"] == "Superato")
                label.setAttribute(Qt.WA_TransparentForMouseEvents)
                contenuto.addWidget(label)
            scheda.clicked.connect(lambda _, ident=r["id"]: apri(ident, self.verticalScrollBar().value()))
            self.schede.append(scheda)
        self.visibili = self.schede
        self.setWidget(corpo)
        self.disponi()

    def filtra(self, testo, stato):
        ricerca = chiave(testo)
        self.visibili = []
        for scheda in self.schede:
            corrisponde = (ricerca in chiave(scheda.accessibleName())
                           and (not stato or scheda.property("stato") == stato))
            self.griglia.removeWidget(scheda)
            scheda.setVisible(corrisponde)
            if corrisponde:
                self.visibili.append(scheda)
        self.colonne = 0
        self.disponi()
        self.verticalScrollBar().setValue(0)
        return bool(self.visibili)

    def disponi(self):
        colonne = max(1, min(3, self.viewport().width() // max(250, self.fontMetrics().averageCharWidth() * 28)))
        if colonne != self.colonne:
            self.colonne = colonne
            for i, scheda in enumerate(self.visibili):
                self.griglia.addWidget(scheda, i // colonne, i % colonne)
            for i in range(3):
                self.griglia.setColumnStretch(i, int(i < colonne))
        margini = self.griglia.contentsMargins()
        spazio = self.viewport().width() - margini.left() - margini.right()
        larghezza = max(1, (spazio - (colonne - 1) * self.griglia.spacing()) // colonne)
        for scheda in self.visibili:
            scheda.setMinimumHeight(scheda.heightForWidth(larghezza))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.disponi()


class Anello(QPushButton):
    def __init__(self, acquisiti, totale, mostra_cfu):
        super().__init__()
        self.percentuale = 100 * acquisiti / totale
        self.focus_tastiera = False
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

    def focusInEvent(self, event):
        self.focus_tastiera = event.reason() in (Qt.TabFocusReason, Qt.BacktabFocusReason, Qt.ShortcutFocusReason)
        super().focusInEvent(event)

    def mousePressEvent(self, event):
        self.focus_tastiera = False
        super().mousePressEvent(event)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        cerchio = self.rect().adjusted(6, 6, -6, -6)
        p.setPen(QPen(QColor("#bacfd4"), 6))
        p.drawEllipse(cerchio)
        p.setPen(QPen(QColor("#287783"), 6))
        p.drawArc(cerchio, 90 * 16, -round(min(self.percentuale, 100) * 57.6))
        p.setPen(QColor("#164a58"))
        p.drawText(self.rect(), Qt.AlignCenter, self.text())
        if self.hasFocus() and self.focus_tastiera:
            p.setPen(QPen(QColor("#945e08"), 2))
            p.drawEllipse(self.rect().adjusted(1, 1, -2, -2))


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
        self.salva.setObjectName("primario")
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
        self.setStyleSheet(Path(__file__).with_name("libretto.qss").read_text(encoding="utf-8"))
        self.resize(820, 540)
        self.home()

    def pagina(self, titolo, indietro=None):
        widget = QWidget()
        widget.setObjectName("pagina")
        self.setCentralWidget(widget)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)
        navigazione = QWidget()
        navigazione.setObjectName("navigazione")
        barra = QHBoxLayout(navigazione)
        barra.setContentsMargins(6, 5, 6, 5)
        layout.addWidget(navigazione)
        marca = QLabel("Libretto UniPi")
        marca.setObjectName("marca")
        barra.addWidget(marca)
        bottone(barra, "Home", self.home).setProperty("attivo", titolo == "In preparazione")
        bottone(barra, "Piano", lambda: self.home(False)).setProperty("attivo", titolo == "Piano di studi")
        barra.addStretch()
        bottone(barra, "Impostazioni", self.impostazioni).setProperty("attivo", titolo == "Impostazioni")
        self.piano = self.db.execute("SELECT * FROM piano").fetchone()
        if self.piano:
            bottone(barra, "Radice materiali…", self.radice)
        label = QLabel(titolo)
        label.setTextFormat(Qt.PlainText)
        label.setObjectName("titolo")
        label.setWordWrap(True)
        if indietro:
            intestazione = QHBoxLayout()
            layout.addLayout(intestazione)
            freccia = bottone(intestazione, "←", indietro)
            freccia.setObjectName("indietro")
            freccia.setAccessibleName("Torna indietro")
            freccia.setToolTip("Torna indietro")
            intestazione.addWidget(label, 1)
        else:
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

    def home(self, preparazione=True, posizione=0, ricerca="", stato=""):
        self.preparazione = preparazione
        layout = self.pagina("In preparazione" if preparazione else "Piano di studi")
        if not self.piano:
            bottone(layout, "Importa piano", self.importazione).setObjectName("primario")
            layout.addStretch()
            return
        corso = QLabel(self.piano["corso"])
        corso.setObjectName("corso")
        corso.setWordWrap(True)
        layout.addWidget(corso)
        query = "SELECT * FROM attivita"
        if preparazione:
            query += " WHERE stato='In preparazione'"
        righe = self.db.execute(query + " ORDER BY nome COLLATE NOCASE").fetchall()
        if not preparazione:
            controlli = QHBoxLayout()
            layout.addLayout(controlli)
            cerca = QLineEdit(ricerca)
            cerca.setPlaceholderText("Cerca esame")
            cerca.setAccessibleName("Cerca esame")
            cerca.setClearButtonEnabled(True)
            controlli.addWidget(cerca, 1)
            filtro = QComboBox()
            filtro.setAccessibleName("Filtra per stato")
            filtro.addItem("Tutti gli stati", "")
            for opzione in ("Da preparare", "In preparazione", "Superato"):
                filtro.addItem(opzione, opzione)
            filtro.setCurrentIndex(filtro.findData(stato))
            controlli.addWidget(filtro)
            def azzera():
                cerca.clear()
                filtro.setCurrentIndex(0)
                cerca.setFocus()
            reset = bottone(controlli, "Azzera filtri", azzera)
            def apri(ident, scroll):
                self.dashboard(ident, scroll, cerca.text(), filtro.currentData())
            piano = PianoSchede(righe, apri)
            layout.addWidget(piano)
            vuoto = QLabel("Nessun esame trovato")
            vuoto.setAlignment(Qt.AlignCenter)
            layout.addWidget(vuoto, 1)
            def aggiorna():
                trovati = piano.filtra(cerca.text(), filtro.currentData())
                piano.setVisible(trovati)
                vuoto.setVisible(not trovati)
                reset.setEnabled(bool(cerca.text() or filtro.currentData()))
            cerca.textChanged.connect(aggiorna)
            filtro.currentIndexChanged.connect(aggiorna)
            aggiorna()
            if posizione:
                QTimer.singleShot(0, piano, lambda: piano.verticalScrollBar().setValue(posizione))
        elif not righe:
            layout.addWidget(QLabel("Scegli dal piano un esame da preparare."))
            bottone(layout, "Apri piano", lambda: self.home(False)).setObjectName("primario")
            layout.addStretch()
        else:
            colonne = ["Attività", "Appello"]
            tab = QTableWidget(len(righe), len(colonne) + 2)
            tab.setHorizontalHeaderLabels(colonne + ["", ""])
            tab.setEditTriggers(QTableWidget.NoEditTriggers)
            tab.setAlternatingRowColors(True)
            tab.setShowGrid(False)
            tab.setSelectionBehavior(QTableWidget.SelectRows)
            tab.verticalHeader().setDefaultSectionSize(max(36, tab.fontMetrics().height() + 18))
            tab.verticalHeader().hide()
            tab.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            tab.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
            tab.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
            layout.addWidget(tab)
            for i, r in enumerate(righe):
                valori = [r["nome"], r["appello"]]
                for j, val in enumerate(valori):
                    cella = QTableWidgetItem(str(val or ""))
                    tab.setItem(i, j, cella)
                for j, (nome, azione) in enumerate([("Scheda", self.dashboard), ("Materiali", self.materiali)], len(valori)):
                    b = QPushButton(nome)
                    b.clicked.connect(lambda _, ident=r["id"], fn=azione: fn(ident))
                    tab.setCellWidget(i, j, b)
                    if i == 0:
                        b.ensurePolished()
                        tab.horizontalHeader().setSectionResizeMode(j, QHeaderView.Fixed)
                        tab.setColumnWidth(j, b.sizeHint().width() + b.fontMetrics().horizontalAdvance("  "))
        if preparazione:
            acquisiti, media = statistiche(self.db.execute("SELECT stato,cfu,voto FROM attivita"))
            pannello = QWidget()
            pannello.setObjectName("statistiche")
            riepilogo = QHBoxLayout(pannello)
            riepilogo.setContentsMargins(16, 6, 16, 6)
            layout.addWidget(pannello)
            valore = "—" if media is None else f"{media:.2f}".replace(".", ",")
            media_layout = QVBoxLayout()
            media_layout.addStretch()
            media_layout.addWidget(QLabel("Media ponderata"))
            numero = QLabel(valore)
            numero.setObjectName("media")
            media_layout.addWidget(numero)
            media_layout.addStretch()
            riepilogo.addLayout(media_layout)
            riepilogo.addStretch()
            riepilogo.addWidget(QLabel("Progresso CFU"))
            anello = Anello(acquisiti, self.piano["totale"], bool(self.piano["mostra_cfu"]))
            riepilogo.addWidget(anello)
            def memorizza(cfu):
                with self.db:
                    self.db.execute("UPDATE piano SET mostra_cfu=?", (cfu,))
            anello.toggled.connect(memorizza)
        else:
            azioni = QHBoxLayout()
            layout.addLayout(azioni)
            bottone(azioni, "Aggiungi attività", lambda: self.scheda(None)).setObjectName("primario")
            azioni.addStretch()
            bottone(azioni, "Azzera piano…", self.conferma_azzeramento)

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

    def dashboard(self, ident, posizione=None, ricerca="", stato=""):
        r = self.db.execute("SELECT * FROM attivita WHERE id=?", (ident,)).fetchone()
        def indietro():
            if posizione is None:
                self.home()
            else:
                self.home(False, posizione, ricerca, stato)
        layout = self.pagina(r["nome"], indietro)
        anno = f"Anno {r['anno']}" if r["anno"] else "Anno da definire"
        layout.addWidget(QLabel(f"{anno}   ·   {r['cfu']} CFU   ·   {r['stato']}"))
        if r["appello"] and r["stato"] != "Superato":
            layout.addWidget(QLabel(f"Prossimo appello   {r['appello']}"))
        if r["stato"] == "Superato":
            esito = "Idoneità" if r["idoneita"] else "30 e lode" if r["lode"] else f"{r['voto']}/30"
            layout.addWidget(QLabel(f"Risultato   {esito}"))
        def aggiorna():
            self.dashboard(ident, posizione, ricerca, stato)
        azioni = QHBoxLayout()
        layout.addLayout(azioni)
        bottone(azioni, "Materiali", lambda: self.materiali(ident, aggiorna)).setObjectName("primario")
        bottone(azioni, "Progetti…", lambda: Progetti(self.db, r, self.piano["radice"], self).exec())
        bottone(azioni, "Modifica dettagli", lambda: self.scheda(ident, aggiorna))
        azioni.addStretch()
        modalita = ", ".join(m for m in ("scritto", "orale", "progetto") if r[m])
        for campo, valore in [("Docente", r["docente"]), ("Modalità", modalita)]:
            if valore:
                label = QLabel(f"{campo}   {valore}")
                label.setTextFormat(Qt.PlainText)
                label.setWordWrap(True)
                layout.addWidget(label)
        if r["note"]:
            layout.addWidget(QLabel("Note"))
            note = QPlainTextEdit(r["note"])
            note.setReadOnly(True)
            layout.addWidget(note)
        else:
            layout.addStretch()

    def scheda(self, ident, dopo_salvataggio=None):
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

        bottone(form, "Salva", salva).setObjectName("primario")
        if dialog.exec():
            if dopo_salvataggio:
                dopo_salvataggio()
            else:
                self.home(self.preparazione)

    def materiali(self, ident, ritorno=None):
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
                self.materiali(ident, ritorno)

        barra = QHBoxLayout()
        layout.addLayout(barra)
        if ritorno:
            bottone(barra, "Torna all’esame", ritorno)
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
