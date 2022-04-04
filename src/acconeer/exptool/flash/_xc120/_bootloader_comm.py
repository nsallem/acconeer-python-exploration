# THIS FILE IS AUTOMATICALLY GENERATED - DO NOT EDIT
from __future__ import annotations

import logging
import queue
from typing import List

import serial

from acconeer.exptool.flash._xc120._uart_protocol import Packet, UartReader


_LOG = logging.getLogger(__name__)


class CommandFailed(Exception):
    pass


class BlCommandResponsePacket(Packet):
    packet_type = 0xF3

    def __init__(self, payload):
        self.command_id = int.from_bytes(payload[0:2], byteorder="little")
        self.command_payload = payload[2:]
        super().__init__(payload)

    def get_command_packet(self):
        return _command_packets.get(self.command_id)(self.command_payload)


class BlCommandRequestPacket(Packet):
    packet_type = 0xF3

    def __init__(self, command_payload):
        command_payload[0:0] = self.command_id.to_bytes(2, byteorder="little")
        super().__init__(command_payload)


class GetLastErrorRequestPacket(BlCommandRequestPacket):
    command_id = 0x0002

    def __init__(
        self,
    ):
        payload = bytearray()
        super().__init__(payload)


class GetLastErrorResponsePacket:
    command_id = 0x0002

    def __init__(self, payload):
        self.payload = payload

    def get_status(self):
        return self.payload[0]

    def get_response_data(self):
        return self.payload[1:].decode("ascii")


class GetAppSwVersionRequestPacket(BlCommandRequestPacket):
    command_id = 0x0101

    def __init__(
        self,
    ):
        payload = bytearray()
        super().__init__(payload)


class GetAppSwVersionResponsePacket:
    command_id = 0x0101

    def __init__(self, payload):
        self.payload = payload

    def get_status(self):
        return self.payload[0]

    def get_version(self):
        return self.payload[1:].decode("ascii")


class GetAppSwNameRequestPacket(BlCommandRequestPacket):
    command_id = 0x0102

    def __init__(
        self,
    ):
        payload = bytearray()
        super().__init__(payload)


class GetAppSwNameResponsePacket:
    command_id = 0x0102

    def __init__(self, payload):
        self.payload = payload

    def get_status(self):
        return self.payload[0]

    def get_name(self):
        return self.payload[1:].decode("ascii")


class IsImageErasedRequestPacket(BlCommandRequestPacket):
    command_id = 0xF000

    def __init__(self, image_size):
        payload = bytearray()
        payload.extend(image_size.to_bytes(4, byteorder="little", signed=True))
        super().__init__(payload)


class IsImageErasedResponsePacket:
    command_id = 0xF000

    def __init__(self, payload):
        self.payload = payload
        assert len(payload) == 2

    def get_status(self):
        return self.payload[0]

    def get_is_erased(self):
        return self.payload[1] != 0


class ImageEraseRequestPacket(BlCommandRequestPacket):
    command_id = 0xF001

    def __init__(self, image_size):
        payload = bytearray()
        payload.extend(image_size.to_bytes(4, byteorder="little", signed=True))
        super().__init__(payload)


class ImageEraseResponsePacket:
    command_id = 0xF001

    def __init__(self, payload):
        self.payload = payload
        assert len(payload) == 1

    def get_status(self):
        return self.payload[0]


class ImageWriteBlockRequestPacket(BlCommandRequestPacket):
    command_id = 0xF002

    def __init__(self, offset, data):
        payload = bytearray()
        payload.extend(offset.to_bytes(4, byteorder="little", signed=True))
        payload.extend(data)
        super().__init__(payload)


class ImageWriteBlockResponsePacket:
    command_id = 0xF002

    def __init__(self, payload):
        self.payload = payload
        assert len(payload) == 1

    def get_status(self):
        return self.payload[0]


class ResetRequestPacket(BlCommandRequestPacket):
    command_id = 0xFFFE

    def __init__(
        self,
    ):
        payload = bytearray()
        super().__init__(payload)


_command_packets = {
    0x0002: GetLastErrorResponsePacket,
    0x0101: GetAppSwVersionResponsePacket,
    0x0102: GetAppSwNameResponsePacket,
    0xF000: IsImageErasedResponsePacket,
    0xF001: ImageEraseResponsePacket,
    0xF002: ImageWriteBlockResponsePacket,
}


class BLCommunication:
    def __init__(self, port):
        self._ser = serial.Serial(port, exclusive=True)
        self._reader = UartReader(self._ser, [BlCommandResponsePacket])
        self._reader.start()
        self._timeout = UartReader.DEFAULT_READ_TIMEOUT
        self._reader_started = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def stop(self):
        if self._reader_started:
            self._reader.stop()
            self._reader_started = False

    def close(self):
        self.stop()
        self._ser.close()
        self._ser = None

    def _send_packet(self, packet):
        data = packet.get_byte_array()
        _LOG.debug("Sending packet %s", data)
        self._ser.write(data)

    def _execute_request(self, packet):
        try:
            self._send_packet(packet)
            response = self._reader.wait_packet(BlCommandResponsePacket.packet_type, self._timeout)
            return response.get_command_packet()
        except queue.Empty:
            _LOG.error("read timeout")
            raise TimeoutError("_execute_request timeout")

    def get_last_error(self):
        response = self._execute_request(GetLastErrorRequestPacket())
        status = response.get_status()
        response_data = response.get_response_data()
        if status != 0:
            error_msg = self.get_last_error()
            raise CommandFailed(f"Command failed with code {status} [{error_msg}]")
        return response_data

    def get_app_sw_version(self):
        response = self._execute_request(GetAppSwVersionRequestPacket())
        status = response.get_status()
        version = response.get_version()
        if status != 0:
            error_msg = self.get_last_error()
            raise CommandFailed(f"Command failed with code {status} [{error_msg}]")
        return version

    def get_app_sw_name(self):
        response = self._execute_request(GetAppSwNameRequestPacket())
        status = response.get_status()
        name = response.get_name()
        if status != 0:
            error_msg = self.get_last_error()
            raise CommandFailed(f"Command failed with code {status} [{error_msg}]")
        return name

    def is_image_erased(self, image_size: int):
        response = self._execute_request(IsImageErasedRequestPacket(image_size))
        status = response.get_status()
        is_erased = response.get_is_erased()
        if status != 0:
            error_msg = self.get_last_error()
            raise CommandFailed(f"Command failed with code {status} [{error_msg}]")
        return is_erased

    def image_erase(self, image_size: int):
        response = self._execute_request(ImageEraseRequestPacket(image_size))
        status = response.get_status()
        if status != 0:
            error_msg = self.get_last_error()
            raise CommandFailed(f"Command failed with code {status} [{error_msg}]")

    def image_write_block(self, offset: int, data: List[int]):
        response = self._execute_request(ImageWriteBlockRequestPacket(offset, data))
        status = response.get_status()
        if status != 0:
            error_msg = self.get_last_error()
            raise CommandFailed(f"Command failed with code {status} [{error_msg}]")

    def reset(self):
        self._send_packet(ResetRequestPacket())
