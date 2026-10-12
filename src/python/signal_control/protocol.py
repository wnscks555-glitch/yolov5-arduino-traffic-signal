from dataclasses import dataclass

FIELDS = ("B_st", "D_st", "B_left", "D_left", "C_left", "C_st", "A_left", "A_st",
          "C_ped", "A_ped", "B_ped", "D_ped")
STATES = {"WAITING", "RUNNING", "YELLOW", "FAULT"}


def encode_presence(values):
    if set(values) != set(FIELDS):
        raise ValueError("Presence must contain exactly the 12 protocol fields")
    if any(type(values[field]) not in (bool, int) or values[field] not in (0, 1) for field in FIELDS):
        raise ValueError("Presence values must be boolean or 0/1")
    return (",".join(str(int(values[field])) for field in FIELDS) + "\n").encode("ascii")


def decode_presence(packet):
    if packet.endswith(b"\r\n"):
        body = packet[:-2]
    elif packet.endswith(b"\n"):
        body = packet[:-1]
    else:
        raise ValueError("Packet must end with LF or CRLF")
    if len(body) != 23 or any(ch != 44 if i % 2 else ch not in (48, 49) for i, ch in enumerate(body)):
        raise ValueError("Expected 12 binary fields separated by commas")
    return {field: body[2*i] == 49 for i, field in enumerate(FIELDS)}


@dataclass(frozen=True)
class Status:
    phase: int
    state: str
    freshness: str
    ticks: int
    since_decision_ms: int


def parse_status(line):
    """Ignore diagnostic text; never interpret a whole log line as a phase integer."""
    try:
        parts = line.decode("ascii").strip().split(",")
        if len(parts) != 6 or parts[0] != "STATUS":
            return None
        phase, ticks, elapsed = int(parts[1]), int(parts[4]), int(parts[5])
        if phase not in (1, 2, 3, 4) or parts[2] not in STATES or parts[3] not in ("FRESH", "MISSING"):
            return None
        if ticks < 0 or elapsed < 0:
            return None
        return Status(phase, parts[2], parts[3], ticks, elapsed)
    except (UnicodeError, ValueError):
        return None
