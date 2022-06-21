from __future__ import annotations

import abc
from pathlib import Path
from typing import Any, Callable, Generic, Optional, TypeVar

from ._message import BackendPluginStateMessage, DataMessage, Message
from ._types import Task


StateT = TypeVar("StateT")


class BackendPlugin(abc.ABC, Generic[StateT]):
    shared_state: StateT

    def __init__(self, callback: Callable[[Message], None], key: str) -> None:
        self.callback = callback
        self.key = key

    @abc.abstractmethod
    def idle(self) -> bool:
        pass

    @abc.abstractmethod
    def attach_client(self, *, client: Any) -> None:
        pass

    @abc.abstractmethod
    def detach_client(self) -> None:
        pass

    @abc.abstractmethod
    def execute_task(self, *, task: Task) -> None:
        pass

    @abc.abstractmethod
    def teardown(self) -> None:
        pass

    @abc.abstractmethod
    def load_from_file(self, *, path: Path) -> None:
        pass

    def broadcast(self) -> None:
        self.callback(BackendPluginStateMessage(self.shared_state))

    def send_status_message(self, message: Optional[str]) -> None:
        self.callback(DataMessage("status", message))
