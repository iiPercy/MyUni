def positivo(valore):
    return type(valore) is int and 0 < valore < 2**63


def statistiche(attivita):
    acquisiti = pesi = punti = 0
    for riga in attivita:
        if riga["stato"] == "Superato":
            acquisiti += riga["cfu"]
            if riga["voto"] is not None:
                pesi += riga["cfu"]
                punti += riga["cfu"] * riga["voto"]
    return acquisiti, punti / pesi if pesi else None


def chiave(nome):
    return " ".join(nome.split()).casefold()


def verifica(piano):
    errori, avvisi = [], []
    somma = 0
    if not isinstance(piano, dict):
        return ["Serve un oggetto JSON."], [], 0
    corso = piano.get("corso")
    if not isinstance(corso, str) or not corso.strip():
        errori.append("Inserire il nome del corso.")
    if not positivo(piano.get("cfu_totali")):
        errori.append("Il totale richiesto deve essere un intero positivo.")
    righe = piano.get("attivita")
    if not isinstance(righe, list) or not righe:
        return errori + ["Serve almeno una attività nell’elenco attivita."], [], 0
    nomi = set()
    for i, riga in enumerate(righe, 1):
        prefisso = f"Attività {i} · "
        if not isinstance(riga, dict):
            errori.append(prefisso + "serve un oggetto.")
            continue
        nome = riga.get("nome")
        if not isinstance(nome, str) or not nome.strip():
            errori.append(prefisso + "nome mancante o non valido.")
        elif chiave(nome) in nomi:
            errori.append(prefisso + "nome duplicato.")
        else:
            nomi.add(chiave(nome))
        if positivo(riga.get("cfu")):
            somma += riga["cfu"]
        else:
            errori.append(prefisso + "CFU non validi.")
        if "anno" in riga and riga["anno"] is None:
            avvisi.append(prefisso + "anno da definire.")
        elif not positivo(riga.get("anno")):
            errori.append(prefisso + "inserire anno positivo o null.")
    if somma != piano.get("cfu_totali"):
        avvisi.append("La somma differisce dal totale richiesto.")
    return errori, avvisi, somma
