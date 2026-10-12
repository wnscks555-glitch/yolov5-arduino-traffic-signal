import argparse
import sys
from pathlib import Path
from signal_control.config import ConfigurationError, load_config

PROJECT = Path(__file__).resolve().parents[2]


def main():
    parser=argparse.ArgumentParser(description="YOLOv5 traffic signal control")
    parser.add_argument("--mode",choices=("mock","yolo"),default="mock")
    parser.add_argument("--config",type=Path,default=PROJECT/"src/config/signal.json")
    parser.add_argument("--scenario",type=Path,default=PROJECT/"src/config/mock_scenario.json")
    parser.add_argument("--firmware-harness",type=Path,default=PROJECT/"build/firmware_harness.exe")
    parser.add_argument("--port",help="Explicit hardware serial port (YOLO mode only)")
    parser.add_argument("--preview",action="store_true")
    options=parser.parse_args()
    try:
        if options.mode=="mock":
            from signal_control.mock import run_mock
            run_mock(options.scenario,options.firmware_harness)
        else:
            config=load_config(options.config)
            if options.port:config["serial"]["port"]=options.port
            from signal_control.transport import SerialTransport
            from signal_control.vision import run_vision
            transport=SerialTransport(config["serial"],max_frame_age_seconds=config["vision"]["max_frame_age_seconds"])
            try:run_vision(config,transport,preview=options.preview)
            finally:transport.close()
        return 0
    except (ConfigurationError,RuntimeError,ValueError,ImportError,OSError) as error:
        print(f"Traffic signal: {error}",file=sys.stderr)
        return 2
    except KeyboardInterrupt:return 130


if __name__=="__main__":sys.exit(main())
