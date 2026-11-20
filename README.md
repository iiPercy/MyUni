# Libretto UniPi

Un libretto personale per seguire Ingegneria Informatica all’Università di Pisa. La home darà accesso agli esami in preparazione e alle dispense sul PC. L’app si aprirà in una finestra Windows, funzionerà offline e sarà utilizzabile e manutenibile dai sorgenti anche senza Codex o abbonamenti.

Puoi importare il piano da JSON, correggerlo in anteprima e aprire i materiali degli esami in preparazione. In **Piano → Scheda** puoi salvare modalità, docente e note. Per registrare anche un esame pregresso, scegli **Superato**, seleziona il voto o l’idoneità e salva. La home aggiorna la media ponderata e l’anello di progresso. Un clic sull’anello alterna percentuale e CFU. Da **Scheda → Progetti…** puoi associare più progetti, leggere il README locale e aggiornare il riassunto anche dopo il superamento.

## Avvio su Windows

Dalla cartella del progetto in PowerShell:

```powershell
.\.venv\Scripts\python.exe main.py
```

Su questo PC l’ambiente è già predisposto. Per ricrearlo su un altro PC con Python 3.12 installato:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install PySide6==6.12.0
```

Solo l’installazione iniziale richiede il download dei pacchetti. Per i test eseguire `.\.venv\Scripts\python.exe -m unittest -v`. L’ambiente predisposto usa il Python 3.12 disponibile nel runtime locale di Codex. Per renderlo indipendente da quel runtime, ricrearlo con una propria installazione Python.

## Prima dispensa

Da **Importa piano** scegliere un file UTF-8 come quello nel design e confermare l’anteprima. Nel piano aprire **Scheda**, scegliere **In preparazione** e salvare. Se si desiderano percorsi portabili, scegliere **Radice materiali…** prima di collegare le cartelle. Dalla home aprire **Materiali**, scegliere **Collega cartella** e indicare la directory dell’esame. Dopo il riavvio aprire **Materiali** e fare doppio clic sulla dispensa.

## Backup e ripristino

In **Impostazioni** scegli **Crea backup…** per salvare una copia SQLite di piano, carriera, preferenze e schede progetto. Le dispense e i file dei progetti richiedono una copia separata. Per recuperare il libretto scegli **Ripristina backup…** e conferma. A ripristino riuscito viene indicato il percorso di una copia del libretto precedente.

## Gestione del piano

Per sostituire un piano demo, scegli **Piano → Azzera piano…** e conferma. Dalla home scegli **Importa piano** per caricare il nuovo JSON. Il reset elimina i dati del piano e i collegamenti salvati nel libretto. Le dispense restano nelle loro cartelle.

## Dove leggere

- [Requisiti MVP](requirements.md) per i flussi e i risultati attesi.
- [Design](docs/design.md) per il JSON, i dati locali e le schermate.
- [Avanzamento](docs/progress.md) per il prossimo traguardo e le prove su Windows.
- [Istruzioni operative](AGENTS.md) per chi modifica la repository.
