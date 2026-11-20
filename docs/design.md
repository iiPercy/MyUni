# Design di Libretto UniPi

## Struttura proposta

main.py avvia QApplication, apre il database e mostra la finestra. ui.py contiene la finestra e i widget delle viste. carriera.py valida il piano e gli esiti e calcola media e progresso con funzioni verificabili senza GUI. db.py raccoglie schema, query parametrizzate, transazioni e copie del database. La finestra usa direttamente queste operazioni. L’avvio previsto usa il Python dell’ambiente virtuale nella repo e main.py.

## Piano personale in ingresso

File UTF-8, con chiavi in minuscolo. L’esempio ridotto contiene un’attività ancora da collocare nell’anno di corso.

```json
{
  "corso": "Ingegneria Informatica",
  "cfu_totali": 12,
  "attivita": [
    {"nome": "Analisi matematica", "cfu": 9, "anno": 1},
    {"nome": "Tirocinio", "cfu": 3, "anno": null}
  ]
}
```

corso e nome sono stringhe con testo. cfu_totali e cfu sono interi positivi, anno è un intero positivo oppure null, mostrato come cella vuota. I booleani JSON sono tipi errati. Per confrontare i nomi, uniformare gli spazi e applicare casefold. Un omonimo reale si distingue aggiungendo al nome il modulo o il codice. La finestra di anteprima permette di correggere anche corso e totale. Mostra insieme gli errori bloccanti e gli avvisi del requisito 2. Alla conferma valida di nuovo e inserisce tutto in una transazione, verificando che il piano sia ancora assente. Le modifiche successive avvengono per identificativo stabile dalla vista Piano.

## Dati SQLite

Database personale nella directory dati locale restituita da QStandardPaths.AppLocalDataLocation, con nome applicazione stabile. Attivare le chiavi esterne su ogni connessione. Usare user_version per riconoscere la versione dello schema.

| Tabella | Dati e vincoli essenziali |
| --- | --- |
| piano | Unica riga con id = 1, corso obbligatorio e cfu_totali intero positivo. |
| attivita | Chiave intera stabile, piano_id obbligatorio riferito a piano, nome e chiave normalizzata univoca nel piano, cfu positivo, anno positivo o NULL. Stato obbligatorio tra Da preparare, In preparazione e Superato. Tre indicatori per scritto, orale e progetto. Note, docente, appello in formato YYYY-MM-DD e riferimento alla cartella materiali. |
| esito in attivita | Colonne della stessa riga. Un vincolo CHECK ammette, per Superato, un voto intero 18–30 con lode solo sul 30 oppure idoneità con voto NULL e lode falsa. Per gli altri stati richiede voto NULL, lode e idoneità false. Indicatori obbligatori 0/1. |
| progetto | Chiave intera, attivita_id obbligatorio riferito ad attivita, titolo e cartella obbligatori, URL e riferimento al README facoltativi, riassunto testuale. Più righe possono riferirsi alla stessa attività. |
| preferenze | Unica riga per la radice materiali e la modalità di visualizzazione dell’anello. |

Salvare insieme stato ed esito. Dopo il commit rileggere le attività per aggiornare home e calcoli. Arrotondare solo per la visualizzazione. Se il piano personale porta oltre il 100%, saturare il tratto disegnato e mostrare al centro il valore effettivo.

## Percorsi e lettura locale

Per ogni cartella salvare percorso e base esplicita. Dentro la radice scelta salvare il percorso relativo, all’esterno quello assoluto. Risolvere con pathlib al momento dell’apertura. Il README segue la cartella progetto se interno, altrimenti conserva il percorso assoluto. Cambiare radice aggiorna una preferenza. Ricollegare una cartella aggiorna il suo riferimento. Nessuna delle due operazioni sposta file.

Creare il QFileSystemModel in sola lettura quando si apre Materiali e impostare la cartella come radice del QTreeView. Lasciare al modello il caricamento su espansione. Aprire file e cartelle con QDesktopServices e QUrl.fromLocalFile. Se il percorso è assente o l’apertura fallisce, mostrare un messaggio nella vista. Creare le sottocartelle standard solo su comando esplicito, segnalando eventuali conflitti con file omonimi.

## Composizione della finestra

La veste grafica usa un foglio di stile Qt locale, libretto.qss, caricato alla creazione della finestra. La barra blu scuro evidenzia la vista attiva. Tabelle a righe alternate e un riquadro per media e progresso distinguono le aree della home. I caratteri sono quelli di sistema.

QMainWindow con navigazione Home, Piano e Impostazioni e viste in QStackedWidget. In home la lista «In preparazione» occupa lo spazio principale. Ogni riga mostra nome, eventuale appello e azioni «Scheda» e «Materiali». A fianco, un riquadro compatto con media e anello disegnato con QPainter. Su finestre strette il riquadro passa sotto la lista. Prima dell’importazione l’azione principale è «Importa piano». Dopo l’importazione, una lista vuota rimanda al piano per scegliere un’attività.

Nel Piano un QGridLayout scorrevole ridistribuisce le schede su un massimo di tre colonne in base alla larghezza disponibile. Ogni pulsante contiene nome a capo, anno, CFU e stato. La dashboard mostra i dettagli salvati e apre materiali, progetti ed editor dell’attività. Il comando di ritorno ripristina lo scorrimento del Piano. Progetti usa una lista con dettaglio selezionabile, QTextBrowser con setMarkdown per la lettura locale e un editor di testo semplice per il riassunto.

Usare layout ridimensionabili, margini di circa 16 pixel logici, 8 tra controlli correlati e scorrimento nei dettagli. Riservare il blu all’azione principale e il verde al superamento, sempre accompagnato dal testo dello stato. Mantenere focus visibile, ordine di tabulazione coerente e testi leggibili con la scala Windows. Omettere le date mancanti e usare «Collega cartella» per un riferimento ancora vuoto.

## Backup e ripristino

In Impostazioni, accanto ai due comandi, mostrare «Il backup contiene il libretto e i collegamenti. Copia separatamente le cartelle di dispense e progetti». Per il backup usare sqlite3.Connection.backup verso un file temporaneo nella destinazione, chiuderlo e pubblicarlo solo a copia riuscita. Impedire di scegliere il database attivo come destinazione.

Per il ripristino la versione 3 apre il backup in sola lettura e lo copia in un database temporaneo in memoria. Confronta versione e schema con il libretto aperto, verifica integrità SQLite e chiavi esterne. Dopo la conferma e i controlli, salva una copia del libretto corrente nella sua directory e usa la transazione dell’API di backup SQLite per sostituire i dati sulla connessione aperta. La home rilegge il piano dopo il completamento.

La migrazione dalla versione 2 aggiunge la tabella progetto. Il dialogo Progetti nella scheda attività elenca le associazioni e apre il dettaglio per leggere il README in UTF-8 e modificare il riassunto. I riferimenti interni al progetto seguono la cartella quando viene ricollegata.

## Scelte attuate nella fase 1

La schermata di anteprima permette di correggere direttamente il JSON, con riepilogo CFU e validazione durante la digitazione. Il piano e la home condividono la finestra principale, la scheda è un dialogo e il selettore della radice è nella barra superiore. Lo schema iniziale conserva la radice e il totale nella riga piano (campi radice e totale). Gli esiti, le preferenze dell’anello e i progetti richiederanno un aggiornamento dello schema nelle fasi successive.

Il reset confermato elimina attività e piano in una sola transazione SQLite e riapre la home iniziale.

## Scelte attuate nella fase 2

All’apertura lo schema della fase 1 viene aggiornato in una transazione SQLite. La tabella attività viene ricostruita conservando ID, stati e percorsi per estendere il vincolo sugli stati. La versione 2 conserva esito e dettagli nella stessa riga dell’attività. La preferenza dell’anello è nella riga piano. La home presenta media e anello sotto gli esami in preparazione. Il calcolo usa i dati appena salvati e include la lode come 30.

Nel Piano la ricerca e il filtro per stato ridistribuiscono le schede già caricate. La dashboard conserva i criteri insieme alla posizione di scorrimento per applicarli ai dati aggiornati al ritorno. La cornice indica lo stato insieme alla relativa etichetta.
