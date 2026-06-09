"""Servizio di ispezione e modifica dei parametri dei nodi ROS 2.

Permette di elencare i parametri di un nodo, leggerne il valore e (con conferma
esplicita) modificarli a caldo. Come gli altri service dipende dall'astrazione
`RosCommandRunner`, quindi e' testabile senza un'installazione ROS reale.

La scrittura di un parametro puo' alterare il comportamento di un robot in
esecuzione: il metodo `set_param` la esegue solo se la conferma e' esplicita,
replicando lato backend la protezione dello switch presente nella UI.
"""

from __future__ import annotations

from app.adapters.ros_cli import RosCommandRunner
from app.core.config import Settings
from app.models.schemas import NodeParams, ParamSetResult, ParamValue


class ParamWriteNotConfirmedError(Exception):
    """Sollevata quando si tenta una scrittura di parametro senza conferma."""


class ParamService:
    """Legge ed (opzionalmente) modifica i parametri dei nodi ROS 2."""

    def __init__(self, runner: RosCommandRunner, settings: Settings) -> None:
        """Inizializza il servizio.

        Args:
            runner: Adapter usato per eseguire i comandi ros2.
            settings: Configurazione applicativa.
        """
        self._runner = runner
        self._settings = settings

    def list_params(self, node: str) -> NodeParams:
        """Elenca i parametri dichiarati da un nodo.

        Args:
            node: Nome del nodo (es. ``/talker``).

        Returns:
            I nomi dei parametri del nodo e l'esito dell'interrogazione.
        """
        result = self._runner.run(
            ["param", "list", node], timeout=self._settings.ros_command_timeout
        )
        if not result.ok:
            return NodeParams(
                node=node,
                available=False,
                detail=result.stderr.strip() or "Impossibile elencare i parametri.",
            )
        params = sorted(
            {line.strip() for line in result.stdout.splitlines() if line.strip()}
        )
        return NodeParams(node=node, params=params, available=True)

    def get_param(self, node: str, name: str) -> ParamValue:
        """Legge il valore corrente di un parametro.

        Args:
            node: Nome del nodo proprietario del parametro.
            name: Nome del parametro.

        Returns:
            Il valore del parametro e l'esito della lettura.
        """
        result = self._runner.run(
            ["param", "get", node, name],
            timeout=self._settings.ros_command_timeout,
        )
        if not result.ok:
            return ParamValue(
                node=node,
                name=name,
                available=False,
                detail=result.stderr.strip() or "Impossibile leggere il parametro.",
            )
        return ParamValue(
            node=node, name=name, value=self._extract_value(result.stdout)
        )

    def set_param(
        self, node: str, name: str, value: str, confirm: bool
    ) -> ParamSetResult:
        """Modifica un parametro, ma solo se la scrittura e' confermata.

        Args:
            node: Nome del nodo proprietario del parametro.
            name: Nome del parametro da modificare.
            value: Nuovo valore (serializzato come stringa).
            confirm: Conferma esplicita richiesta per eseguire la scrittura.

        Returns:
            L'esito della scrittura.

        Raises:
            ParamWriteNotConfirmedError: Se ``confirm`` non e' ``True``. La
                scrittura non viene eseguita: e' la protezione server-side che
                impedisce di alterare il robot senza conferma esplicita.
        """
        if not confirm:
            raise ParamWriteNotConfirmedError(
                "Scrittura non confermata: la modifica dei parametri puo' "
                "cambiare lo stato del robot e richiede una conferma esplicita."
            )
        result = self._runner.run(
            ["param", "set", node, name, value],
            timeout=self._settings.ros_command_timeout,
        )
        if not result.ok:
            return ParamSetResult(
                node=node,
                name=name,
                value=value,
                success=False,
                detail=result.stderr.strip()
                or result.stdout.strip()
                or "Impossibile impostare il parametro.",
            )
        return ParamSetResult(
            node=node,
            name=name,
            value=value,
            success=True,
            detail=result.stdout.strip() or "Parametro impostato.",
        )

    @staticmethod
    def _extract_value(stdout: str) -> str:
        """Estrae il valore da una risposta di ``ros2 param get``.

        L'output ha tipicamente la forma ``<Tipo> value is: <valore>``; in tal
        caso viene restituito solo ``<valore>``, altrimenti l'output ripulito.

        Args:
            stdout: Standard output di ``ros2 param get``.

        Returns:
            Il valore del parametro come stringa.
        """
        text = stdout.strip()
        marker = "value is:"
        if marker in text:
            return text.split(marker, 1)[1].strip()
        return text
