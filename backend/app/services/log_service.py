"""Log parser centralizzato dei nodi ROS 2 (requisito 3).

Legge i file di log dalla cartella ``~/.ros/log`` (configurabile), classifica
ogni riga per livello di severita' ed evidenzia warning ed errori critici.

La classificazione e' realizzata con il pattern Strategy: ogni livello ha la
propria strategia di riconoscimento. Aggiungere/riordinare le regole non
richiede di modificare il motore di parsing (Open/Closed Principle).
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import Protocol

from app.core.config import Settings
from app.models.schemas import LogEntry, LogLevel


class LevelStrategy(Protocol):
    """Strategia di riconoscimento del livello di una riga di log."""

    level: LogLevel

    def matches(self, line: str) -> bool:
        """Indica se la riga appartiene al livello della strategia.

        Args:
            line: Riga di log grezza.

        Returns:
            ``True`` se la riga corrisponde al livello.
        """
        ...


class RegexLevelStrategy:
    """Strategia basata su espressione regolare (case-insensitive).

    Riconosce sia i marker testuali tipici di ROS/rcutils (es. ``[ERROR]``)
    sia parole chiave libere presenti nel messaggio.
    """

    def __init__(self, level: LogLevel, pattern: str) -> None:
        """Inizializza la strategia.

        Args:
            level: Livello associato alla strategia.
            pattern: Pattern regex usato per il riconoscimento.
        """
        self.level = level
        self._regex = re.compile(pattern, re.IGNORECASE)

    def matches(self, line: str) -> bool:
        """Verifica la corrispondenza della riga con il pattern.

        Args:
            line: Riga di log grezza.

        Returns:
            ``True`` se il pattern e' presente nella riga.
        """
        return self._regex.search(line) is not None


# Ordine significativo: dalle severita' piu' alte alle piu' basse.
_DEFAULT_STRATEGIES: tuple[RegexLevelStrategy, ...] = (
    RegexLevelStrategy(LogLevel.FATAL, r"\bfatal\b|\[fatal\]"),
    RegexLevelStrategy(LogLevel.ERROR, r"\berror\b|\[error\]|traceback|exception"),
    RegexLevelStrategy(LogLevel.WARN, r"\bwarn(ing)?\b|\[warn\]"),
    RegexLevelStrategy(LogLevel.DEBUG, r"\bdebug\b|\[debug\]"),
)


class LogService:
    """Analizza e classifica i log dei nodi ROS 2."""

    def __init__(
        self,
        settings: Settings,
        strategies: tuple[LevelStrategy, ...] | None = None,
    ) -> None:
        """Inizializza il servizio.

        Args:
            settings: Configurazione applicativa (fornisce la cartella dei log).
            strategies: Strategie di classificazione. Se ``None`` usa quelle di
                default. Iniettarle permette di estendere/testare le regole.
        """
        self._settings = settings
        self._strategies: tuple[LevelStrategy, ...] = strategies or _DEFAULT_STRATEGIES

    def classify(self, line: str) -> LogLevel:
        """Classifica una singola riga di log.

        Args:
            line: Riga di log grezza.

        Returns:
            Il primo livello la cui strategia corrisponde, altrimenti
            ``LogLevel.INFO``.
        """
        for strategy in self._strategies:
            if strategy.matches(line):
                return strategy.level
        return LogLevel.INFO

    def _iter_log_files(self) -> list[Path]:
        """Elenca i file di log disponibili sotto la cartella configurata.

        Returns:
            Lista dei file ``*.log`` ordinata per data di modifica decrescente.
            Vuota se la cartella non esiste.
        """
        root = self._settings.ros_log_dir
        if not root.exists():
            return []
        files = [path for path in root.rglob("*.log") if path.is_file()]
        files.sort(key=lambda path: path.stat().st_mtime, reverse=True)
        return files

    def parse(
        self,
        levels: set[LogLevel] | None = None,
        max_entries: int = 500,
    ) -> list[LogEntry]:
        """Analizza i file di log e restituisce le righe classificate.

        Args:
            levels: Se valorizzato, filtra le righe mantenendo solo i livelli
                indicati (es. solo warning/errori).
            max_entries: Numero massimo di voci restituite.

        Returns:
            Lista di `LogEntry`, dalla piu' recente alla piu' vecchia.
        """
        entries: list[LogEntry] = []
        for path in self._iter_log_files():
            source = self._relative_source(path)
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for line_number, raw_line in enumerate(content.splitlines(), start=1):
                line = raw_line.rstrip()
                if not line:
                    continue
                level = self.classify(line)
                if levels is not None and level not in levels:
                    continue
                entries.append(
                    LogEntry(
                        level=level,
                        message=line,
                        source=source,
                        line_number=line_number,
                    )
                )
                if len(entries) >= max_entries:
                    return entries
        return entries

    def summary(self) -> dict[str, int]:
        """Conteggia le righe di log per livello.

        Returns:
            Dizionario livello -> numero di righe. Utile per i badge di sintesi
            del frontend.
        """
        counter: Counter[str] = Counter()
        for entry in self.parse(max_entries=10_000):
            counter[entry.level.value] += 1
        return dict(counter)

    def _relative_source(self, path: Path) -> str:
        """Calcola il nome sorgente relativo alla cartella dei log.

        Args:
            path: Percorso assoluto del file di log.

        Returns:
            Percorso relativo alla cartella dei log, o il nome file se il
            calcolo relativo non e' possibile.
        """
        try:
            return str(path.relative_to(self._settings.ros_log_dir))
        except ValueError:
            return path.name
