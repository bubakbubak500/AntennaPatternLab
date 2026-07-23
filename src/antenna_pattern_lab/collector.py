from __future__ import annotations

import logging
import ssl
from typing import Callable

import paho.mqtt.client as mqtt

from .domain import Spot

LOGGER = logging.getLogger(__name__)


class PskReporterCollector:
    HOST = "mqtt.pskreporter.info"
    TLS_PORT = 1884

    def __init__(
        self,
        on_spot: Callable[[Spot], None],
        on_status: Callable[[str], None] | None = None,
        on_connection: Callable[[str, str], None] | None = None,
        on_activity: Callable[[Spot], None] | None = None,
    ):
        self._on_spot = on_spot
        self._on_status = on_status or (lambda _message: None)
        self._on_connection = on_connection or (lambda _state, _detail: None)
        self._on_activity = on_activity or (lambda _spot: None)
        self._client: mqtt.Client | None = None
        self._topic = ""
        self._activity_topics: set[str] = set()

    @staticmethod
    def topic(callsign: str, band: str = "+", mode: str = "FT8") -> str:
        safe_call = callsign.strip().upper()
        if not safe_call or any(char in safe_call for char in "/+#"):
            raise ValueError("Zadejte platnou vlastní volací značku bez /, + nebo #.")
        safe_band = band.strip().lower() or "+"
        safe_mode = mode.strip().upper() or "+"
        return f"pskr/filter/v2/{safe_band}/{safe_mode}/{safe_call}/#"

    def start(
        self,
        callsign: str,
        band: str = "+",
        mode: str = "FT8",
        activity_fields: list[str] | tuple[str, ...] = (),
    ) -> None:
        self.stop()
        self._topic = self.topic(callsign, band, mode)
        safe_band = band.strip().lower() or "+"
        safe_mode = mode.strip().upper() or "+"
        self._activity_topics = {
            f"pskr/filter/v2_field/{safe_band}/{safe_mode}/+/{field[:2].upper()}"
            for field in activity_fields[:12]
            if len(field.strip()) >= 2
        }
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        client.tls_set(cert_reqs=ssl.CERT_REQUIRED)
        client.on_connect = self._handle_connect
        client.on_connect_fail = self._handle_connect_fail
        client.on_disconnect = self._handle_disconnect
        client.on_message = self._handle_message
        self._client = client
        self._on_connection("connecting", f"{self.HOST}:{self.TLS_PORT}")
        self._on_status(f"Připojuji {self.HOST}:{self.TLS_PORT}…")
        client.connect_async(self.HOST, self.TLS_PORT, keepalive=60)
        client.loop_start()

    def stop(self) -> None:
        client, self._client = self._client, None
        if client is not None:
            client.disconnect()
            client.loop_stop()
            self._on_connection("disconnected", "")
            self._on_status("Sběr zastaven.")

    def _handle_connect(self, client, _userdata, _flags, reason_code, _properties) -> None:
        if reason_code == 0:
            client.subscribe(self._topic, qos=0)
            for topic in sorted(self._activity_topics):
                client.subscribe(topic, qos=0)
            self._on_connection("connected", self._topic)
            self._on_status(f"Živý sběr aktivní: {self._topic}")
        else:
            self._on_connection("error", str(reason_code))
            self._on_status(f"MQTT připojení selhalo: {reason_code}")

    def _handle_connect_fail(self, _client, _userdata) -> None:
        self._on_connection("error", "connect failed")
        self._on_status("MQTT server není dosažitelný; klient připojení zopakuje.")

    def _handle_disconnect(self, _client, _userdata, _flags, reason_code, _properties) -> None:
        if self._client is not None and reason_code != 0:
            self._on_connection("error", str(reason_code))
            self._on_status(f"MQTT odpojeno ({reason_code}), klient se pokusí obnovit spojení.")

    def _handle_message(self, _client, _userdata, message) -> None:
        try:
            spot = Spot.from_pskr_payload(message.payload)
            if message.topic in self._activity_topics:
                self._on_activity(spot)
            else:
                self._on_spot(spot)
        except (KeyError, TypeError, ValueError) as exc:
            LOGGER.warning("Ignoring malformed PSK Reporter message: %s", exc)
