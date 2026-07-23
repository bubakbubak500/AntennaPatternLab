from __future__ import annotations

from dataclasses import dataclass
import socket
import threading
import time
from typing import Callable


class HamlibError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class RigState:
    frequency_hz: int
    mode: str
    passband_hz: int
    ptt: int
    power_fraction: float | None = None
    swr: float | None = None


@dataclass(frozen=True, slots=True)
class RotatorState:
    azimuth_deg: float
    elevation_deg: float


class RigctldClient:
    """Small read-only client for Hamlib's documented default TCP protocol."""

    def __init__(self, host: str = "127.0.0.1", port: int = 4532, timeout: float = 2.0):
        self.host = host
        self.port = port
        self.timeout = timeout

    def poll(self) -> RigState:
        frequency = int(self._query("f", 1)[0])
        mode_values = self._query("m", 2)
        ptt = int(self._query("t", 1)[0])
        power = self._optional_level("RFPOWER")
        swr = self._optional_level("SWR")
        return RigState(
            frequency_hz=frequency,
            mode=mode_values[0],
            passband_hz=int(mode_values[1]),
            ptt=ptt,
            power_fraction=power,
            swr=swr,
        )

    def _optional_level(self, name: str) -> float | None:
        try:
            return float(self._query(f"l {name}", 1)[0])
        except (HamlibError, ValueError):
            return None

    def _query(self, command: str, expected_lines: int) -> list[str]:
        try:
            with socket.create_connection((self.host, self.port), timeout=self.timeout) as sock:
                sock.settimeout(self.timeout)
                sock.sendall((command + "\n").encode("ascii"))
                stream = sock.makefile("r", encoding="ascii", newline="\n")
                values = []
                for _ in range(expected_lines):
                    line = stream.readline()
                    if not line:
                        raise HamlibError("rigctld closed the connection")
                    value = line.strip()
                    if value.startswith("RPRT "):
                        raise HamlibError(value)
                    values.append(value)
                return values
        except (OSError, ValueError) as exc:
            raise HamlibError(str(exc)) from exc


class RotctldClient:
    """Read the current position from Hamlib rotctld without sending movement commands."""

    def __init__(self, host: str = "127.0.0.1", port: int = 4533, timeout: float = 2.0):
        self.host = host
        self.port = port
        self.timeout = timeout

    def poll(self) -> RotatorState:
        try:
            with socket.create_connection((self.host, self.port), timeout=self.timeout) as sock:
                sock.settimeout(self.timeout)
                sock.sendall(b"p\n")
                stream = sock.makefile("r", encoding="ascii", newline="\n")
                values = []
                for _ in range(2):
                    line = stream.readline()
                    if not line:
                        raise HamlibError("rotctld closed the connection")
                    value = line.strip()
                    if value.startswith("RPRT "):
                        raise HamlibError(value)
                    values.append(float(value))
                return RotatorState(values[0] % 360.0, values[1])
        except (OSError, ValueError) as exc:
            raise HamlibError(str(exc)) from exc


class HamlibMonitor:
    def __init__(
        self,
        client: RigctldClient,
        on_rig_state: Callable[[RigState], None],
        on_connection: Callable[[str, str], None],
        poll_seconds: float = 2.0,
    ):
        self.client = client
        self.on_rig_state = on_rig_state
        self.on_connection = on_connection
        self.poll_seconds = poll_seconds
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self.on_connection("connecting", f"{self.client.host}:{self.client.port}")
        self._thread = threading.Thread(target=self._run, daemon=True, name="hamlib-monitor")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        thread, self._thread = self._thread, None
        if thread and thread is not threading.current_thread():
            thread.join(timeout=3)
        self.on_connection("disabled", "")

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                state = self.client.poll()
            except HamlibError as exc:
                self.on_connection("error", str(exc))
            else:
                self.on_connection("connected", f"{state.frequency_hz} {state.mode}")
                self.on_rig_state(state)
            self._stop.wait(self.poll_seconds)


class RotatorMonitor:
    def __init__(
        self,
        client: RotctldClient,
        on_position: Callable[[RotatorState], None],
        on_connection: Callable[[str, str], None],
        poll_seconds: float = 2.0,
    ):
        self.client = client
        self.on_position = on_position
        self.on_connection = on_connection
        self.poll_seconds = poll_seconds
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self.on_connection("connecting", f"{self.client.host}:{self.client.port}")
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="rotator-monitor"
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        thread, self._thread = self._thread, None
        if thread and thread is not threading.current_thread():
            thread.join(timeout=3)
        self.on_connection("disabled", "")

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                position = self.client.poll()
            except HamlibError as exc:
                self.on_connection("error", str(exc))
            else:
                detail = f"{position.azimuth_deg:.1f}° / {position.elevation_deg:.1f}°"
                self.on_connection("connected", detail)
                self.on_position(position)
            self._stop.wait(self.poll_seconds)
