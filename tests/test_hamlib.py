import socketserver
import threading

from antenna_pattern_lab.hamlib import RigctldClient, RotctldClient


class RigHandler(socketserver.StreamRequestHandler):
    def handle(self):
        command = self.rfile.readline().decode().strip()
        responses = {
            "f": "14074000\n",
            "m": "PKTUSB\n3000\n",
            "t": "1\n",
            "l RFPOWER": "0.25\n",
            "l SWR": "1.4\n",
        }
        self.wfile.write(responses[command].encode())


def test_rigctld_client_reads_frequency_mode_and_ptt():
    server = socketserver.ThreadingTCPServer(("127.0.0.1", 0), RigHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        state = RigctldClient(port=server.server_address[1]).poll()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
    assert state.frequency_hz == 14_074_000
    assert state.mode == "PKTUSB"
    assert state.passband_hz == 3000
    assert state.ptt == 1
    assert state.power_fraction == 0.25
    assert state.swr == 1.4


class RotatorHandler(socketserver.StreamRequestHandler):
    def handle(self):
        command = self.rfile.readline().decode().strip()
        assert command == "p"
        self.wfile.write(b"372.5\n4.25\n")


def test_rotctld_client_only_reads_and_normalizes_position():
    server = socketserver.ThreadingTCPServer(("127.0.0.1", 0), RotatorHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        state = RotctldClient(port=server.server_address[1]).poll()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert state.azimuth_deg == 12.5
    assert state.elevation_deg == 4.25
