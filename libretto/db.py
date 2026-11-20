import sqlite3
from contextlib import closing
from pathlib import Path
from tempfile import NamedTemporaryFile

from .carriera import chiave, verifica


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
            if versione in (0, 2):
                db.execute("""CREATE TABLE progetto (
                    id INTEGER PRIMARY KEY, attivita_id INTEGER NOT NULL REFERENCES attivita ON DELETE CASCADE,
                    titolo TEXT NOT NULL CHECK(length(trim(titolo))>0), cartella TEXT NOT NULL CHECK(cartella!=''),
                    relativo INTEGER NOT NULL CHECK(relativo IN (0,1)), repository TEXT NOT NULL,
                    readme TEXT NOT NULL, riassunto TEXT NOT NULL)""")
                db.execute("PRAGMA user_version=3")
            elif versione != 3:
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


def file_distinto(db, file):
    attivo = Path(db.execute("PRAGMA database_list").fetchone()[2]).resolve()
    file = Path(file).resolve()
    if attivo == file or (file.exists() and file.samefile(attivo)):
        raise ValueError("Scegli un file diverso dal libretto aperto.")
    return file


def backup(db, destinazione):
    file = file_distinto(db, destinazione)
    with NamedTemporaryFile(dir=file.parent, delete=False) as tmp:
        temporaneo = Path(tmp.name)
    try:
        with closing(sqlite3.connect(temporaneo)) as copia:
            db.backup(copia)
        temporaneo.replace(file)
    finally:
        temporaneo.unlink(missing_ok=True)


def ripristina(db, sorgente):
    file = file_distinto(db, sorgente)
    schema = "SELECT type,name,sql FROM sqlite_master WHERE sql IS NOT NULL ORDER BY type,name"
    with closing(sqlite3.connect(":memory:")) as copia:
        with closing(sqlite3.connect(file.as_uri() + "?mode=ro", uri=True)) as origine:
            origine.backup(copia)
        copia.execute("PRAGMA trusted_schema=OFF")
        atteso = [tuple(riga) for riga in db.execute(schema)]
        if copia.execute("PRAGMA user_version").fetchone()[0] != 3 or copia.execute(schema).fetchall() != atteso:
            raise ValueError("Schema del backup incompatibile.")
        if copia.execute("PRAGMA integrity_check").fetchall() != [("ok",)] or copia.execute("PRAGMA foreign_key_check").fetchone():
            raise ValueError("Il backup contiene dati incoerenti.")
        directory = Path(db.execute("PRAGMA database_list").fetchone()[2]).parent
        with NamedTemporaryFile(dir=directory, prefix="prima-del-ripristino-", suffix=".sqlite", delete=False) as tmp:
            sicurezza = Path(tmp.name)
        try:
            backup(db, sicurezza)
        except Exception:
            sicurezza.unlink(missing_ok=True)
            raise
        copia.backup(db)
        return sicurezza
