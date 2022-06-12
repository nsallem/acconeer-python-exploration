from __future__ import annotations

from typing import Any, Union

import attrs
from typing_extensions import Literal


StatusLiteral = Union[Literal["ok"], Literal["error"]]


@attrs.define
class Message:
    status: StatusLiteral
    command_name: str
    exception: Exception = attrs.field(default=None, init=False)
    data: Any = attrs.field(default=None, init=False)


@attrs.define
class OkMessage(Message):
    status: StatusLiteral = attrs.field(default="ok", init=False)


@attrs.define
class ErrorMessage(Message):
    exception: Exception
    status: StatusLiteral = attrs.field(default="error", init=False)


@attrs.define
class DataMessage(OkMessage):
    data: Any