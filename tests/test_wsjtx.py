import struct
import socket
import time

import pytest

from antenna_pattern_lab.wsjtx import (
    Heartbeat,
    MAGIC,
    PacketError,
    Status,
    WsjtxListener,
    parse_forward_targets,
    parse_packet,
)


def u32(value):
    return struct.pack(">I", value)


def u64(value):
    return struct.pack(">Q", value)


def text(value):
    encoded = value.encode()
    return u32(len(encoded)) + encoded


def header(message_type):
    return u32(MAGIC) + u32(3) + u32(message_type) + text("WSJT-X")


def test_parses_heartbeat():
    packet = header(0) + u32(3) + text("2.7.0") + text("r123")
    message = parse_packet(packet)
    assert isinstance(message, Heartbeat)
    assert message.maximum_schema == 3
    assert message.version == "2.7.0"


def test_parses_status_with_tx_context():
    packet = b"".join(
        (
            header(1),
            u64(14_074_000),
            text("FT8"),
            text("W1AW"),
            text("-10"),
            text("FT8"),
            b"\x01\x01\x00",
            u32(1200),
            u32(1500),
            text("OK7PS"),
            text("JN79"),
            text("FN31"),
            b"\x00",
            text(""),
            b"\x00\x00",
            u32(0xFFFFFFFF),
            u32(15),
            text("Default"),
            text("CQ OK7PS JN79"),
        )
    )
    message = parse_packet(packet)
    assert isinstance(message, Status)
    assert message.transmitting is True
    assert message.de_call == "OK7PS"
    assert message.tx_message == "CQ OK7PS JN79"
    assert message.dial_frequency_hz + message.tx_df_hz == 14_075_500


def test_rejects_invalid_or_truncated_packets():
    with pytest.raises(PacketError):
        parse_packet(b"bad")
    with pytest.raises(PacketError):
        parse_packet(u32(0) + u32(3) + u32(0) + text("WSJT-X"))


def test_parses_forward_targets_and_rejects_loop():
    assert parse_forward_targets("127.0.0.1:2238; localhost:2239") == (
        ("127.0.0.1", 2238),
        ("localhost", 2239),
    )
    with pytest.raises(ValueError):
        parse_forward_targets(
            "127.0.0.1:2237", listener_host="127.0.0.1", listener_port=2237
        )


def test_listener_forwards_valid_raw_packet():
    consumer = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    consumer.bind(("127.0.0.1", 0))
    consumer.settimeout(2)
    listener = WsjtxListener(
        lambda _message: None,
        lambda _state, _detail: None,
        port=0,
        forward_targets=(("127.0.0.1", consumer.getsockname()[1]),),
    )
    listener.start()
    deadline = time.monotonic() + 2
    while listener.bound_port == 0 and time.monotonic() < deadline:
        time.sleep(0.01)
    packet = header(0) + u32(3) + text("2.7.0") + text("r123")
    sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sender.sendto(packet, ("127.0.0.1", listener.bound_port))
    forwarded, _address = consumer.recvfrom(65535)
    listener.stop()
    sender.close()
    consumer.close()
    assert forwarded == packet
