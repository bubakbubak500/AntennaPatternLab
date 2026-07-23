from __future__ import annotations

from dataclasses import dataclass
from ipaddress import ip_address
import socket
import struct
import threading
import time
from typing import Callable

MAGIC = 0xADBCCBDA


class PacketError(ValueError):
    pass


def parse_forward_targets(
    value: str, *, listener_host: str = "", listener_port: int | None = None
) -> tuple[tuple[str, int], ...]:
    """Parse comma/semicolon separated IPv4-or-hostname:port destinations."""
    targets = []
    for raw in value.replace(";", ",").split(","):
        raw = raw.strip()
        if not raw:
            continue
        try:
            host, port_text = raw.rsplit(":", 1)
            port = int(port_text)
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Invalid UDP forwarding target: {raw!r}") from exc
        host = host.strip()
        if not host or not 1 <= port <= 65535:
            raise ValueError(f"Invalid UDP forwarding target: {raw!r}")
        if listener_port == port and host.lower() == listener_host.lower():
            raise ValueError("Forwarding target must not equal the listener endpoint.")
        target = (host, port)
        if target not in targets:
            targets.append(target)
    return tuple(targets)


class Reader:
    def __init__(self, data: bytes):
        self.data = data
        self.offset = 0

    @property
    def remaining(self) -> int:
        return len(self.data) - self.offset

    def _read(self, size: int) -> bytes:
        if self.remaining < size:
            raise PacketError("Truncated WSJT-X packet")
        value = self.data[self.offset : self.offset + size]
        self.offset += size
        return value

    def u8(self) -> int:
        return self._read(1)[0]

    def boolean(self) -> bool:
        return bool(self.u8())

    def u32(self) -> int:
        return struct.unpack(">I", self._read(4))[0]

    def i32(self) -> int:
        return struct.unpack(">i", self._read(4))[0]

    def u64(self) -> int:
        return struct.unpack(">Q", self._read(8))[0]

    def f64(self) -> float:
        return struct.unpack(">d", self._read(8))[0]

    def utf8(self) -> str:
        size = self.u32()
        if size == 0xFFFFFFFF:
            return ""
        return self._read(size).decode("utf-8", errors="replace")


@dataclass(frozen=True, slots=True)
class Header:
    schema: int
    message_type: int
    instance_id: str


@dataclass(frozen=True, slots=True)
class Heartbeat:
    header: Header
    maximum_schema: int | None
    version: str
    revision: str


@dataclass(frozen=True, slots=True)
class Status:
    header: Header
    dial_frequency_hz: int
    mode: str
    dx_call: str
    report: str
    tx_mode: str
    tx_enabled: bool
    transmitting: bool
    decoding: bool
    rx_df_hz: int
    tx_df_hz: int
    de_call: str
    de_grid: str
    dx_grid: str
    tx_watchdog: bool
    sub_mode: str = ""
    fast_mode: bool = False
    special_operation_mode: int = 0
    frequency_tolerance_hz: int | None = None
    tr_period_seconds: int | None = None
    configuration_name: str = ""
    tx_message: str = ""


@dataclass(frozen=True, slots=True)
class Decode:
    header: Header
    is_new: bool
    milliseconds_since_midnight: int
    snr_db: int
    delta_time_seconds: float
    delta_frequency_hz: int
    mode: str
    message: str
    low_confidence: bool = False
    off_air: bool = False


@dataclass(frozen=True, slots=True)
class Close:
    header: Header


def parse_packet(data: bytes) -> Heartbeat | Status | Decode | Close | Header:
    reader = Reader(data)
    if reader.u32() != MAGIC:
        raise PacketError("Invalid WSJT-X magic number")
    schema = reader.u32()
    message_type = reader.u32()
    instance_id = reader.utf8()
    header = Header(schema, message_type, instance_id)
    if message_type == 0:
        maximum_schema = reader.u32() if reader.remaining >= 4 else None
        version = reader.utf8() if reader.remaining >= 4 else ""
        revision = reader.utf8() if reader.remaining >= 4 else ""
        return Heartbeat(header, maximum_schema, version, revision)
    if message_type == 1:
        return _parse_status(reader, header)
    if message_type == 2:
        return _parse_decode(reader, header)
    if message_type == 6:
        return Close(header)
    return header


def _parse_status(reader: Reader, header: Header) -> Status:
    required = dict(
        dial_frequency_hz=reader.u64(),
        mode=reader.utf8(),
        dx_call=reader.utf8(),
        report=reader.utf8(),
        tx_mode=reader.utf8(),
        tx_enabled=reader.boolean(),
        transmitting=reader.boolean(),
        decoding=reader.boolean(),
        rx_df_hz=reader.u32(),
        tx_df_hz=reader.u32(),
        de_call=reader.utf8(),
        de_grid=reader.utf8(),
        dx_grid=reader.utf8(),
        tx_watchdog=reader.boolean(),
    )
    optional = {
        "sub_mode": reader.utf8() if reader.remaining >= 4 else "",
        "fast_mode": reader.boolean() if reader.remaining >= 1 else False,
        "special_operation_mode": reader.u8() if reader.remaining >= 1 else 0,
        "frequency_tolerance_hz": reader.u32() if reader.remaining >= 4 else None,
        "tr_period_seconds": reader.u32() if reader.remaining >= 4 else None,
        "configuration_name": reader.utf8() if reader.remaining >= 4 else "",
        "tx_message": reader.utf8() if reader.remaining >= 4 else "",
    }
    return Status(header=header, **required, **optional)


def _parse_decode(reader: Reader, header: Header) -> Decode:
    result = Decode(
        header=header,
        is_new=reader.boolean(),
        milliseconds_since_midnight=reader.u32(),
        snr_db=reader.i32(),
        delta_time_seconds=reader.f64(),
        delta_frequency_hz=reader.u32(),
        mode=reader.utf8(),
        message=reader.utf8(),
        low_confidence=reader.boolean() if reader.remaining >= 1 else False,
        off_air=reader.boolean() if reader.remaining >= 1 else False,
    )
    return result


class WsjtxListener:
    def __init__(
        self,
        on_message: Callable[[object], None],
        on_state: Callable[[str, str], None],
        host: str = "127.0.0.1",
        port: int = 2237,
        forward_targets: tuple[tuple[str, int], ...] = (),
        multicast_interface: str = "0.0.0.0",
    ):
        self.on_message = on_message
        self.on_state = on_state
        self.host = host
        self.port = port
        self.forward_targets = forward_targets
        self.multicast_interface = multicast_interface
        self.bound_port = port
        self._socket: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self.on_state("waiting", f"{self.host}:{self.port}")
        self._thread = threading.Thread(target=self._run, daemon=True, name="wsjtx-udp")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        sock, self._socket = self._socket, None
        if sock is not None:
            sock.close()
        thread, self._thread = self._thread, None
        if thread and thread is not threading.current_thread():
            thread.join(timeout=2)
        self.on_state("disconnected", "")

    def _run(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket = sock
        try:
            try:
                is_multicast = ip_address(self.host).is_multicast
            except ValueError:
                is_multicast = False
            if is_multicast:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind(("", self.port))
                membership = socket.inet_aton(self.host) + socket.inet_aton(
                    self.multicast_interface
                )
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, membership)
            else:
                sock.bind((self.host, self.port))
            self.bound_port = int(sock.getsockname()[1])
            sock.settimeout(1.0)
        except (OSError, ValueError) as exc:
            self.on_state("error", str(exc))
            sock.close()
            return
        last_valid: float | None = None
        while not self._stop.is_set():
            try:
                payload, _address = sock.recvfrom(65535)
            except socket.timeout:
                if last_valid is not None and time.monotonic() - last_valid > 45:
                    self.on_state("stale", "No heartbeat for 45 seconds")
                    last_valid = None
                continue
            except OSError:
                break
            try:
                message = parse_packet(payload)
            except (PacketError, UnicodeError):
                continue
            for target in self.forward_targets:
                try:
                    sock.sendto(payload, target)
                except OSError:
                    # A failed optional consumer must not interrupt primary capture.
                    continue
            last_valid = time.monotonic()
            self.on_state("connected", message.header.instance_id)
            self.on_message(message)
