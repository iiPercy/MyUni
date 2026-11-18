import sqlite3
from pathlib import Path

from carriera import chiave, verifica


def apri(file):
    db = sqlite3.connect(file)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    try:
        with db:
            db.execute("BEGIN IMMEDIATE")
            versione = db.execute("PRAGMA user_version").fetchone()[0]
            if versione == 0:
                prepara_schema(db)
            elif versione != 2:
                raise ValueError("Versione del libretto non supportata.")
    except Exception:
        db.close()
        raise
    return db


def prepara_schema(db):
    precedente = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='attivita'").fetchone()
    db.execute("""CREATE TABLE IF NOT EXISTS piano (
            id INTEGER PRIMARY KEY CHECK(id=1), corso TEXT NOT NULL,
            totale INTEGER NOT NULL CHECK(totale>0), radice TEXT)""")
    db.execute("ALTER TABLE piano ADD COLUMN mostra_cfu INTEGER NOT NULL DEFAULT 0")
    if precedente:
        db.execute("ALTER TABLE attivita RENAME TO attivita_precedenti")
    db.execute("""CREATE TABLE attivita (
            id INTEGER PRIMARY KEY, piano_id INTEGER DEFAULT 1 NOT NULL REFERENCES piano,
            nome TEXT NOT NULL, chiave TEXT UNIQUE NOT NULL, cfu INTEGER NOT NULL CHECK(cfu>0),
            anno INTEGER CHECK(anno>0), stato TEXT NOT NULL DEFAULT 'Da preparare'
            CHECK(stato IN ('Da preparare','In preparazione','Superato')), appello TEXT,
            percorso TEXT, relativo INTEGER NOT NULL DEFAULT 0,
            docente TEXT NOT NULL DEFAULT '', note TEXT NOT NULL DEFAULT '',
            scritto INTEGER NOT NULL DEFAULT 0, orale INTEGER NOT NULL DEFAULT 0,
            progetto INTEGER NOT NULL DEFAULT 0,
            voto INTEGER CHECK(voto IS NULL OR (typeof(voto)='integer' AND voto BETWEEN 18 AND 30)),
            lode INTEGER NOT NULL DEFAULT 0 CHECK(lode IN (0,1) AND (lode=0 OR voto IS 30)),
            idoneita INTEGER NOT NULL DEFAULT 0 CHECK(idoneita IN (0,1)),
            CHECK((stato='Superato' AND ((voto IS NOT NULL) + idoneita)=1)
               OR (stato!='Superato' AND voto IS NULL AND idoneita=0)))""")
    if precedente:
        colonne = "id,piano_id,nome,chiave,cfu,anno,stato,appello,percorso,relativo"
        db.execute(f"INSERT INTO attivita({colonne}) SELECT {colonne} FROM attivita_precedenti")
        db.execute("DROP TABLE attivita_precedenti")
    db.execute("PRAGMA user_version=2")


def aggiungi(db, riga):
    db.execute("INSERT INTO attivita(nome,chiave,cfu,anno) VALUES(?,?,?,?)",
               (riga["nome"].strip(), chiave(riga["nome"]), riga["cfu"], riga["anno"]))


def importa(db, piano):
    errori, _, _ = verifica(piano)
    if errori:
        raise ValueError("\n".join(errori))
    with db:
        db.execute("INSERT INTO piano(id,corso,totale) VALUES(1,?,?)",
                   (piano["corso"].strip(), piano["cfu_totali"]))
        for riga in piano["attivita"]:
            aggiungi(db, riga)


def azzera_piano(db):
    with db:
        db.execute("DELETE FROM attivita")
        db.execute("DELETE FROM piano")


def collega(db, ident, percorso, radice):
    percorso = Path(percorso)
    relativo = bool(radice and percorso.is_relative_to(radice))
    if relativo:
        percorso = percorso.relative_to(radice)
    with db:
        db.execute("UPDATE attivita SET percorso=?, relativo=? WHERE id=?",
                   (str(percorso), relativo, ident))
