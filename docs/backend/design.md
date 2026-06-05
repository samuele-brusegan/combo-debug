# Design pattern e principi SOLID

Documento foglia: spiega le scelte di design del backend e come estenderlo.

## Diagramma delle classi (UML)

```mermaid
classDiagram
    direction LR

    class RosCommandRunner {
        <<interface>>
        +run(args, timeout) CommandResult
    }
    class SubprocessRosCommandRunner {
        +run(args, timeout) CommandResult
        +is_available() bool
    }
    class CommandResult {
        +list~str~ args
        +int returncode
        +str stdout
        +str stderr
        +bool timed_out
        +ok() bool
    }

    class LevelStrategy {
        <<interface>>
        +matches(line) bool
    }
    class RegexLevelStrategy {
        +matches(line) bool
    }

    class NodeService {
        +get_nodes() list~RosNode~
    }
    class GraphService {
        +get_snapshot() GraphSnapshot
    }
    class LogService {
        +parse() list~LogEntry~
        +classify(line) LogLevel
    }

    RosCommandRunner <|.. SubprocessRosCommandRunner
    SubprocessRosCommandRunner ..> CommandResult : crea
    LevelStrategy <|.. RegexLevelStrategy

    NodeService "1" o--> "1" RosCommandRunner : usa
    GraphService "1" o--> "1" RosCommandRunner : usa
    LogService "1" o--> "*" LevelStrategy : usa
```

I service dipendono dalle **interfacce** (`RosCommandRunner`, `LevelStrategy`),
mai dalle implementazioni concrete: e' questo che rende il sistema testabile
(fake runner) ed estendibile (nuove strategie).

## Design pattern adottati

### Adapter — `app/adapters/ros_cli.py`
La comunicazione con ROS 2 avviene tramite SysCall alla CLI `ros2`. Tutta questa
logica e' incapsulata nell'Adapter `SubprocessRosCommandRunner`, che implementa
l'interfaccia `RosCommandRunner`. Il resto del codice non sa "come" si parla con
ROS: dipende solo dall'astrazione. Per passare in futuro a un client `rclpy`
nativo basta scrivere un nuovo adapter, senza toccare i service.

### Strategy — log
- **Log** (`log_service.py`): la classificazione di ogni riga e' delegata a una
  lista di `LevelStrategy`. Aggiungere o riordinare le regole non richiede di
  modificare il motore di parsing.

### Aggregazione del grafo — `graph_service.py`
`GraphService` ricostruisce il grafo (topic/servizi/azioni) aggregando
`ros2 node info` sui nodi attivi e incrociandolo con gli elenchi `ros2 ... list`.
Da questo incrocio deriva lo stato di ogni entita', incluso il rilevamento
**zombie** (presente nel grafo ma senza alcun nodo attivo associato).

### Application Factory — `main.py`
`create_app()` costruisce l'istanza FastAPI. Facilita i test con configurazioni
alternative e tiene la configurazione fuori dall'import globale.

### Composition Root — `api/deps.py`
Tutta la costruzione dei service (e delle loro dipendenze) e' centralizzata nei
provider di dependency injection. I router dichiarano `Depends(get_xxx_service)`
e ignorano i dettagli di costruzione.

### Singleton leggero — `Settings` e runner
`get_settings()` e `get_runner()` usano `lru_cache` per condividere un'unica
istanza in tutta l'applicazione.

## Principi SOLID

- **S**ingle Responsibility — un file per area (nodi, env, log, grafo);
  la configurazione e' isolata in `Settings`.
- **O**pen/Closed — Strategy per i log permette di estendere senza
  modificare il codice esistente.
- **L**iskov — qualsiasi `RosCommandRunner` (reale o fake) e' interscambiabile;
  i test lo dimostrano usando `FakeRosCommandRunner`.
- **I**nterface Segregation — protocolli minimali (`RosCommandRunner`,
  `LevelStrategy`) espongono solo cio' che serve.
- **D**ependency Inversion — i service dipendono da astrazioni, non da
  `subprocess`; le concrezioni sono iniettate dalla composition root.

## Come estendere

| Obiettivo                          | Dove intervenire                                              |
| ---------------------------------- | ------------------------------------------------------------- |
| Nuovo endpoint                     | Aggiungi un router in `app/api/routes/` e includilo in `routes/__init__.py`. |
| Nuova regola di classificazione log | Aggiungi una `RegexLevelStrategy` in `log_service.py`.        |
| Backend ROS alternativo (rclpy)    | Implementa `RosCommandRunner` e cambialo in `get_runner`.     |
| Nuovo dato esposto                 | Aggiungi un modello in `models/schemas.py`.                   |
