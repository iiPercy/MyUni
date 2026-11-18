# Lavorare su Libretto UniPi

- Prima di modificare file, ispeziona la cartella e le modifiche presenti. Leggi requirements.md per il comportamento, docs/design.md per le scelte tecniche e docs/progress.md per il traguardo corrente.
- Completa una fase alla volta, con interfaccia e documentazione in italiano. Mantieni pochi moduli per UI, calcoli e persistenza. Usa Python, PySide6 con Qt Widgets e sqlite3. PySide6 è l’unica dipendenza applicativa diretta esterna.
- Usa la libreria standard per JSON, percorsi, date, backup e test. Evita webview, server, ORM, cloud, AI, librerie grafiche aggiuntive, plugin e livelli di semplice inoltro.
- Usa dati sintetici e cartelle temporanee per le prove. Tieni fuori dalla repo database personali, materiali e backup. Preserva i file dell’utente anche quando cambia un collegamento. Crea cartelle dei materiali solo su richiesta esplicita.
- Verifica i flussi modificati dai normali punti di ingresso. Usa unittest per le regole e SQLite temporaneo per persistenza e transazioni. Registra in docs/progress.md le prove eseguite e quelle da fare sul PC reale. Aggiorna README e design quando cambiano l’avvio o le decisioni documentate.
