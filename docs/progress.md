# Avanzamento

| Fase | Stato | Risultato |
| --- | --- | --- |
| 0 · Specifica | Completata | README, istruzioni operative, requisiti, design e questo piano presenti e riletti insieme. |
| 1 · Dal piano alla dispensa | Implementata, collaudo personale aperto | Dopo un riavvio apro una dispensa dalla home dell’app su Windows. |
| 2 · Carriera e statistiche | Media, anello e voti verificati sul PC personale | Registro gli esiti e leggo media e CFU aggiornati. |
| 3 · Progetti e copie | Implementata, da provare sul PC personale | Consulto i progetti e recupero il libretto da un backup. |

## Fase 1 · Dal piano alla dispensa

Come primo passo preparare un ambiente virtuale e una finestra Qt minima, documentare il comando di avvio dai sorgenti e provarlo subito sul PC Windows con Smart App Control nella configurazione abituale. Dopo la prova, se pratico, creare un collegamento desktop a pythonw.exe dell’ambiente con il percorso di main.py come argomento. L’MVP si avvia senza creare un eseguibile personalizzato.

Completare anteprima, importazione, correzioni manuali, piano e home. Scegliere «In preparazione», inserire un appello, collegare una cartella e navigare i materiali. Includere cambio radice, ricollegamento e creazione esplicita delle sottocartelle.

- **Codex** verifica con dati temporanei JSON valido ed errato, avvisi, annullamento, secondo import bloccato, aggiornamento per ID e persistenza dopo chiusura e riapertura. Controlla che all’avvio non venga attraversato l’albero dei materiali.
- **Sul PC personale** importare un piccolo piano, scegliere un esame in preparazione e collegare una cartella con una dispensa. Chiudere e riaprire l’app, aprire «Materiali» dalla home e poi la dispensa con il programma predefinito. Verificare anche Esplora file, il collegamento desktop se creato e la leggibilità a 14 pollici. Misurare apertura e risposta all’espansione di una cartella reale.

**Prove eseguite.** Due test unittest superati su Windows con Python 3.12.14 e PySide6 6.12.0. Il test Qt usa il backend offscreen, un JSON sintetico e un database temporaneo. Verifica correzione del JSON, avvisi, annullamento, importazione unica, modifica della scheda, collegamento relativo, riapertura della home senza modello filesystem e invio del percorso della dispensa al servizio desktop simulato. Avvio desktop richiesto da pythonw.exe. Restano da confermare visibilità della finestra, Smart App Control, apertura reale tramite associazioni Windows e le prove sul portatile elencate sopra.

L’utente ha confermato importazione, funzionamento dei comandi della demo e reset del piano.

## Fase 2 · Carriera e statistiche

Completare i dettagli della scheda e la registrazione degli esami pregressi. Aggiungere media e anello interattivo.

**Verificato.** Cinque test automatici superati su database temporanei. Verificati aggiornamento dello schema precedente, media vuota, registrazione da scheda di voto, lode e idoneità, media 28 con 12 CFU su 60, preferenza al riavvio, annullamento e conferma della riapertura con conservazione di note e percorso materiali.

- **Codex** verifica gli stati, la riapertura di un esame, lode, idoneità, media vuota e l’esempio del requisito 8. Controlla che salvare un risultato aggiorni home e piano e conservi i materiali.
- **Sul PC personale** registrare un esame passato e un’idoneità, alternare i due valori dell’anello e riavviare per verificare la preferenza.

## Fase 3 · Progetti e copie

Completare i progetti per attività, la lettura locale del README, il riassunto e i comandi di backup e ripristino.

- **Codex** verifica due progetti sullo stesso esame prima e dopo il superamento, README assente e riassunto persistente. Su database temporanei verifica il ripristino di una copia valida, l’annullamento e il rifiuto di copie corrotte o incompatibili con conservazione dei dati correnti.
- **Sul PC personale** provare la lettura offline, il backup e il ripristino con dati di prova. Cambiare radice, ricollegare una cartella esterna mancante e riaprire un progetto. Verificare che il messaggio sul backup separato dei materiali sia visibile.

**Prove automatiche della fase 3.** Database temporanei e dialoghi Qt offscreen. Verificati migrazione dalla versione 2, due progetti, lettura Markdown, modifica con README mancante dopo il superamento, backup e ripristino con copia di sicurezza, annullamento, copie incompatibili o corrotte e protezione del file attivo.
