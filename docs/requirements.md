# Comportamento atteso dell’MVP

## Preparare il piano

1. **Importazione guidata.** Al primo avvio posso scegliere un JSON con corso, cfu_totali e attivita. Ogni attività contiene nome, cfu e anno. Prima di confermare vedo le righe modificabili, la somma dei CFU e il totale richiesto. Correggere una riga ricalcola subito il riepilogo. Annullare lascia intatto il database.
2. **Validazione.** Un file illeggibile o un JSON malformato consente di scegliere un altro file. Campi obbligatori assenti, tipi errati, nomi vuoti, CFU diversi da interi positivi e attività con lo stesso nome dopo normalizzazione impediscono il salvataggio. Il piano deve contenere almeno un’attività. Un anno intero positivo o null è valido. Anno vuoto e somma diversa dal totale producono avvisi visibili che posso accettare.
3. **Manutenzione.** Posso aggiungere o correggere singole attività, compresi esami a scelta, idoneità, tirocinio e prova finale. Registro un insegnamento integrato come una sola attività con i suoi CFU complessivi e un solo esito. Correggere nome, CFU o anno conserva la carriera e i collegamenti. Con un piano già presente, un nuovo tentativo di importazione mi indirizza alla modifica manuale senza scrivere dati.

Dal piano posso scegliere «Azzera piano…». Annullando ritrovo i dati correnti. Confermando torno a «Importa piano» e posso caricare un altro JSON. I materiali sul disco restano disponibili.

## Preparare e registrare un esame


4. **Home.** All’apertura vedo per primi gli esami «In preparazione», ognuno con nome, eventuale prossimo appello e accessi diretti alla scheda e ai materiali. Se la lista è vuota posso aprire il piano. Il piano completo mostra anche «Da preparare» e «Superato» (gruppo «Superati»).
5. **Scheda.** Una nuova attività parte da «Da preparare». Posso cambiare stato, selezionare una o più modalità tra scritto, orale e progetto, salvare note, docente e data facoltativa del prossimo appello. Posso lasciare vuoti i dettagli. Una data non valida impedisce il salvataggio e identifica il campo da correggere.
6. **Esito.** Posso passare direttamente a «Superato», anche per attività precedenti all’installazione. Scelgo un voto intero da 18 a 30, con lode ammessa solo sul 30, oppure idoneità senza voto. Serve un esito valido per salvare il superamento. Se riapro un’attività superata, confermo la rimozione dell’esito. Dopo il salvataggio home e statistiche si aggiornano e la scheda conserva materiali e progetti.

## Leggere le statistiche

7. **Media.** Divido la somma di voto × CFU per la somma dei CFU delle sole attività superate con voto numerico. Senza voti compare «—». Per convenzione personale dell’MVP conto 30 e lode come 30 e mostro comunque la lode in scheda. Questa scelta non esprime una regola UniPi.
8. **Progresso.** Sommo i CFU di tutte le attività superate, comprese le idoneità, e divido per cfu_totali. Un clic al centro dell’anello alterna percentuale e «CFU acquisiti / CFU totali». Con 30 e lode da 6 CFU, 24 da 3 CFU e un’idoneità da 3 CFU su 60, la media è 252 / 9 = 28 e l’anello alterna 20% e «12 / 60». Un’attività ancora in preparazione lascia invariati entrambi i valori.

## Aprire materiali e progetti

9. **Materiali.** Posso collegare una cartella esistente senza alterarne la struttura. Dalla home apro il relativo albero, espando una sottocartella per caricarla, apro una dispensa con l’app predefinita o la cartella in Esplora file. Per un nuovo esame posso richiedere la creazione di Dispense, Esercizi, Esami passati e facoltativamente Progetto. Le cartelle già presenti conservano tutto il contenuto.
10. **Cambio PC.** Dopo un cambio della radice materiali ritrovo i collegamenti interni con la stessa struttura relativa. Una cartella assente mostra il percorso atteso e il comando «Ricollega». Posso continuare a usare la scheda e salvare note anche se il disco è scollegato.
11. **Progetti.** Prima e dopo il superamento posso associare più progetti, ciascuno con titolo, cartella locale, URL facoltativo della repository, riferimento al README.md locale e riassunto modificabile anche tramite incolla. Posso leggere il README nella scheda. Se manca, il riassunto rimane leggibile e modificabile.

## Ritrovare i dati

12. **Persistenza e copie.** Al riavvio ritrovo piano, carriera, preferenze e riferimenti locali. Posso creare un backup del database e ripristinarne uno valido dopo conferma. Una copia incompatibile o danneggiata lascia utilizzabile il libretto corrente. La schermata spiega che dispense e progetti restano nelle proprie cartelle e richiedono una copia separata.
13. **Uso quotidiano.** L’app si apre dai sorgenti in una finestra Windows senza connessione o abbonamento. Sul portatile da 14 pollici posso raggiungere scheda e materiali anche con ridimensionamento dello schermo. L’avvio evita scansioni delle cartelle collegate. Tempi di apertura e reattività sono da misurare sul PC reale.
