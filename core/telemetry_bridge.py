import socket
import json
import time

class DroneTelemetryBridge:
    """
    Protocol-agnostic Ground Datalink Ingestion Bridge.
    Listens on UDP (default: 14550 / MAVLink Datalink port) for JSON/FADEC frames.
    """
    def __init__(self, host="0.0.0.0", port=14550):
        self.host = host
        self.port = port
        self.sock = None
        self.is_connected = False

    def bind_socket(self):
        if self.sock is not None:
            return True
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind((self.host, self.port))
            self.sock.setblocking(False)
            self.is_connected = True
            return True
        except Exception as e:
            self.is_connected = False
            return False

    def receive_latest_frame(self):
        """Non-blocking fetch of the newest packet in UDP buffer."""
        if not self.sock:
            if not self.bind_socket():
                return None

        latest_packet = None
        try:
            # Drain buffer to always process latest telemetry frame
            while True:
                data, addr = self.sock.recvfrom(2048)
                latest_packet = json.loads(data.decode('utf-8'))
        except (BlockingIOError, socket.error):
            pass
        except Exception:
            pass

        return latest_packet

    def close(self):
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None
            self.is_connected = False
