# Copyright (c) Acconeer AB, 2022
# All rights reserved

from __future__ import annotations

from typing import Any

from typing_extensions import Protocol

from acconeer.exptool.a121._core.entities import SessionConfig

from .message import Message


class CommunicationProtocol(Protocol):
    end_sequence: bytes

    @classmethod
    def get_system_info_command(cls) -> bytes:
        """The `get_system_info` command."""
        ...

    @classmethod
    def get_sensor_info_command(cls) -> bytes:
        """The `get_sensor_info` command."""
        ...

    @classmethod
    def setup_command(cls, session_config: SessionConfig) -> bytes:
        """The `setup` command."""
        ...

    @classmethod
    def start_streaming_command(cls) -> bytes:
        """The `start_streaming` command."""
        ...

    @classmethod
    def stop_streaming_command(cls) -> bytes:
        """The `stop_streaming` command"""
        ...

    @classmethod
    def parse_message(cls, header: dict[str, Any], payload: bytes) -> Message:
        """Parses any supported Message given a header and a payload"""
        ...
