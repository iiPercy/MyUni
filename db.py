import sqlite3
from pathlib import Path

from carriera import chiave, verifica


def apri(file):
    db = sqlite3.connect(file)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    db.executescript("""
        CREATE TABLE IF NOT EXISTS piano (
            id INTEGER PRIMARY KEY CHECK(id=1), corso TEXT NOT NULL,
            totale INTEGER NOT NULL CHECK(totale>0), radice TEXT);
        CREATE TABLE IF NOT EXISTS attivita (
            id INTEGER PRIMARY KEY, piano_id INTEGER DEFAULT 1 NOT NULL REFERENCES piano,
            nome TEXT NOT NULL, chiave TEXT UNIQUE NOT NULL, cfu INTEGER NOT NULL CHECK(cfu>0),
            anno INTEGER CHECK(anno>0), stato TEXT NOT NULL DEFAULT 'Da preparare'
            CHECK(stato IN ('Da preparare','In preparazione')), appello TEXT,
            percorso TEXT, relativo INTEGER NOT NULL DEFAULT 0);
    """)
    return db


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
