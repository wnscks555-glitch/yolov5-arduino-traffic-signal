import time
from .protocol import encode_presence, parse_status


class SerialTransport:
    def __init__(self, config, factory=None, clock=time.monotonic, report=print, max_frame_age_seconds=2.0):
        self.config, self.factory, self.clock, self.report = config, factory, clock, report
        self.connection = None
        self.next_retry = 0.0
        self.ready_at = 0.0
        self.last_sent = float("-inf")
        self.receive_buffer = bytearray()
        self.max_frame_age_seconds = max_frame_age_seconds

    def _open(self, now):
        if self.connection is not None: return now >= self.ready_at
        if now < self.next_retry: return False
        try:
            factory = self.factory
            if factory is None:
                import serial # The serial connection is opened only when sending data.
                factory = serial.Serial
            if not self.config.get("port"):
                raise ValueError("Set serial.port or --port for hardware output")
            self.connection = factory(self.config["port"], self.config["baud_rate"], timeout=0,
                                      write_timeout=self.config["write_timeout_seconds"])
            self.ready_at = now + self.config["settle_seconds"]
            self.receive_buffer.clear()
            self.report("SERIAL,CONNECTED")
            return now >= self.ready_at
        except (OSError, ValueError, ImportError) as error:
            self.report(f"SERIAL,UNAVAILABLE,{error}")
            self.next_retry = now + self.config["retry_seconds"]
            return False

    def _failed(self, error, now):
        self.report(f"SERIAL,DISCONNECTED,{error}")
        self.close()
        self.next_retry = now + self.config["retry_seconds"]

    def send(self, presence, captured_at=None):
        packet = encode_presence(presence)
        now = self.clock()
        if captured_at is not None and now - captured_at >= self.max_frame_age_seconds:
            return False # Missing/frozen detections are never replaced with all-zero presence.
        if not self._open(now) or now - self.last_sent < self.config["send_interval_seconds"]:
            return False
        try:
            if self.connection.write(packet) != len(packet):
                raise OSError("Incomplete serial write")
            self.last_sent = now
            return True
        except OSError as error:
            self._failed(error, now)
            return False

    def poll(self):
        if self.connection is None: return []
        try:
            data = self.connection.read(min(int(self.connection.in_waiting), 512))
        except OSError as error:
            self._failed(error, self.clock())
            return []
        statuses = []
        for byte in data:
            if byte == 10:
                status = parse_status(bytes(self.receive_buffer))
                if status is not None: statuses.append(status)
                self.receive_buffer.clear()
            elif len(self.receive_buffer) < 160:
                self.receive_buffer.append(byte)
            else:
                # Keep an overlong line invalid until LF, rather than parse its tail.
                self.receive_buffer[:] = b"?" * 160
        return statuses

    def close(self):
        if self.connection is not None:
            try: self.connection.close()
            except OSError: pass
        self.connection = None
        self.receive_buffer.clear()
