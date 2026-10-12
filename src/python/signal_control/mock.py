import json
import subprocess
from pathlib import Path
from .protocol import FIELDS, encode_presence


class FirmwareHarness:
    def __init__(self, executable):
        if not Path(executable).is_file():
            raise RuntimeError("Build the harness first: python tests/verify.py")
        self.process = subprocess.Popen([str(Path(executable).resolve())], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
        self.initial = json.loads(self.process.stdout.readline())

    def command(self, command):
        self.process.stdin.write(command + "\n"); self.process.stdin.flush()
        line = self.process.stdout.readline()
        if not line: raise RuntimeError("Firmware harness stopped: " + self.process.stderr.read())
        return json.loads(line)

    def close(self):
        if self.process.poll() is None:
            self.process.stdin.write("QUIT\n"); self.process.stdin.flush()
            self.process.communicate(timeout=5)


def run_mock(scenario_path, executable):
    with Path(scenario_path).open(encoding="utf-8-sig") as stream: scenario = json.load(stream)
    events = scenario["events"]
    if any(type(event["at_ms"]) is not int or event["at_ms"] < 0 for event in events):
        raise ValueError("Mock event times must be nonnegative integers")
    if events != sorted(events,key=lambda event:event["at_ms"]):
        raise ValueError("Mock events must be chronological")
    harness = FirmwareHarness(executable)
    now, index, sending = 0, 0, False
    presence = dict.fromkeys(FIELDS,False)
    previous = None
    try:
        for now in range(0,scenario["duration_ms"]+1,100):
            snapshot = harness.command("STEP,100") if now else harness.initial
            while index < len(events) and events[index]["at_ms"] <= now:
                event=events[index]; index+=1
                if "presence" in event:
                    unknown=set(event["presence"])-set(FIELDS)
                    if unknown:raise ValueError("Unknown mock fields: "+str(unknown))
                    presence=dict.fromkeys(FIELDS,False);presence.update(event["presence"])
                sending=event.get("send",True)
            if sending and now%500==0:
                snapshot=harness.command("FRAME,"+encode_presence(presence).hex())
            current=(snapshot["phase"],snapshot["state"],snapshot["ped_state"])
            if current != previous:
                print(json.dumps({"mock":True,**snapshot},ensure_ascii=False))
                previous=current
        print(json.dumps({"mock_complete":True,"duration_ms":now,"final":snapshot},ensure_ascii=False))
    finally:harness.close()
