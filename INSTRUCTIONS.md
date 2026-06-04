Configurazione del Ruolo e Contesto
Sei un ingegnere del software esperto di sistemi Linux, Docker Compose e ROS (Robot Operating System). Hai accesso diretto alla macchina e al terminale per creare, configurare, scrivere codice e testare il software.

Il tuo obiettivo è sviluppare un'applicazione WEB di debugging e monitoraggio per un ecosistema misto. L'applicazione deve monitorare lo stato di nodi web (gestiti via Docker Compose con Nginx, servizi REST, ecc.) e, nello specifico, lo stato e le performance di nodi ROS.

Specifiche Tecniche dell'Applicazione
- Architettura: Web App (Backend in Python + Frontend Web leggero/reattivo).
- Backend (Python): Deve interfacciarsi con l'ambiente ROS (via SysCall) per raccogliere dati in tempo reale.
- Frontend: Una dashboard web accessibile tramite browser che mostri i dati in modo dinamico.

Requisiti Funzionali Core

1. Visualizzazione e Stato dei Nodi (Color Coding)
- La dashboard web deve mostrare l'elenco dei nodi ROS
- Ogni nodo deve avere un indicatore visivo di stato basato sui colori:
  * VERDE: Nodo attivo, responsivo e funzionante.
  * ROSSO: Nodo crashato, offline o non raggiungibile.

2. Ispezione Variabili d'Ambiente ROS
- Una sezione dedicata della dashboard deve mostrare chiaramente tutte le variabili d'ambiente di ROS attive sul sistema (es. ROS_MASTER_URI, ROS_DOMAIN_ID, ecc.) per facilitare il debug delle configurazioni di rete.

3. Log Parser
- Implementa un sistema di log parsing centralizzato nel backend Python che legga i log dei nodi ROS (dalla cartella .ros/log [dato da verificare] ), evidenziando nel frontend (es. tramite formattazione o alert) errori e warning critici.

4. Funzionalità Avanzate [Opzionali / Sperimentali]
- Rilevamento Spin Bloccato: Implementa una logica euristica nel backend Python per capire se un nodo ROS è in blocco (es. lo spin è bloccato, il nodo non pubblica su un topic atteso alla frequenza corretta o non risponde ai servizi).
- Bridge rqt: Permetti di lanciare o richiamare i tool di diagnostica grafici di ROS (rqt) direttamente dalla macchina tramite comandi avviabili (o segnalati) dall'interfaccia.

Requisiti Collaborativi:
- Quest'app sarà lasciata in eredità in un altro team per eventiali aggiunte che potranno essere fatte, deve quindi essere estremamente ben documentata. La documentazione all'interno di `docs/` 
  ci sarà un documento principale con la decrizione a grandi linee del app ma non estremamente specifica (più specifica del README, meno della documentazione) 
  poi ogni zona del progetto feature particolare verrà descritta da un file a se stante dal resto della documentazione
  La documentazione verrà espansa ad albero dal meno specifico (radice) al più specifico le foglie
- Adotta lo stile 1TBS (One True Brace Style), combinata con lo standard moderno PSR-12 per la tipizzazione del codice PHP.
- Commenta il codice sempre ogni funzione deve avere la sua JavaDoc (o rispettivo per linguaggio di programmazione), chiara ma descrittiva
- Deve adottare anche i dipici design pattern e scrivi il codice rispettando i principi SOLID

