# Libretto UniPi

Un libretto personale per seguire Ingegneria Informatica all’Università di Pisa. La home darà accesso agli esami in preparazione e alle dispense sul PC. L’app si aprirà in una finestra Windows, funzionerà offline e sarà utilizzabile e manutenibile dai sorgenti anche senza Codex o abbonamenti.

**Stato attuale.** La repository contiene la specifica dell’MVP. Oggi si possono consultare i documenti e preparare il JSON del proprio piano seguendo l’esempio nel design.

**Uso previsto dopo l’implementazione.** Si avvierà l’app dai sorgenti in un ambiente virtuale Python con PySide6, unica dipendenza applicativa diretta esterna. Qt Widgets gestirà l’interfaccia e il modulo standard sqlite3 conserverà i dati. Dal piano importato si potranno registrare risultati, consultare media e CFU, aprire materiali e progetti locali e salvare un backup del libretto.

## Dove leggere

- [Requisiti MVP](requirements.md) per i flussi e i risultati attesi.
- [Design](docs/design.md) per il JSON, i dati locali e le schermate.
- [Avanzamento](docs/progress.md) per il prossimo traguardo e le prove su Windows.
- [Istruzioni operative](AGENTS.md) per chi modifica la repository.
