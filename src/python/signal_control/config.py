import json
import math
from pathlib import Path
from .protocol import FIELDS


class ConfigurationError(ValueError):
    pass


def load_config(path):
    path = Path(path).resolve()
    with path.open(encoding="utf-8-sig") as stream:
        config = json.load(stream)
    config["_directory"] = str(path.parent)
    validate(config, vision=False)
    return config


def configured_path(config, value):
    if not value:
        return None
    path = Path(value).expanduser()
    return (Path(config["_directory"]) / path).resolve() if not path.is_absolute() else path.resolve()


def validate(config, vision=False):
    serial = config["serial"]
    for name in ("baud_rate", "send_interval_seconds", "write_timeout_seconds", "retry_seconds", "settle_seconds"):
        value = serial[name]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ConfigurationError(f"Invalid serial.{name}")
    if serial["baud_rate"] != 9600:
        raise ConfigurationError("Firmware currently uses 9600; change both ends together")
    if not 0 < serial["send_interval_seconds"] < 3 or serial["retry_seconds"] <= 0 or serial["write_timeout_seconds"] <= 0:
        raise ConfigurationError("Send interval must be greater than 0 and less than 3 seconds; retries and write timeouts must be positive")
    if not vision:
        return
    if not isinstance(serial.get("port"), str) or not serial["port"].strip():
        raise ConfigurationError("YOLO hardware output requires serial.port or --port")
    missing = []
    for key in ("weights", "yolo_root"):
        path = configured_path(config, config["vision"].get(key))
        if path is None or not path.exists(): missing.append(f"vision.{key}")
    categories = config["classes"]
    for key in ("vehicle_ids", "pedestrian_ids"):
        ids = categories.get(key)
        if not isinstance(ids, list) or not ids or any(type(i) is not int or i < 0 for i in ids):
            missing.append(f"classes.{key}")
    if missing:
        raise ConfigurationError("Missing required model files or class IDs: " + ", ".join(missing))
    if set(categories["vehicle_ids"]) & set(categories["pedestrian_ids"]):
        raise ConfigurationError("Vehicle and pedestrian class IDs must be disjoint")
    for field in FIELDS:
        polygons = config["roi"].get(field)
        if not isinstance(polygons, list) or not polygons:
            missing.append(f"roi.{field}")
            continue
        for polygon in polygons:
            if not isinstance(polygon, list) or len(polygon) < 3:
                raise ConfigurationError(f"Invalid polygon for {field}")
            if any(not isinstance(p, list) or len(p) != 2 or any(type(n) not in (int, float) or not math.isfinite(n) for n in p) for p in polygon):
                raise ConfigurationError(f"Invalid polygon coordinates for {field}")
            area = sum(polygon[i][0]*polygon[(i+1)%len(polygon)][1] - polygon[(i+1)%len(polygon)][0]*polygon[i][1] for i in range(len(polygon)))
            if abs(area) < 1e-9: raise ConfigurationError(f"Zero-area polygon for {field}")
    if missing:
        raise ConfigurationError("Missing ROI settings: " + ", ".join(missing))
    vision_cfg = config["vision"]
    if type(vision_cfg["source"]) is not int or vision_cfg["source"] < 0:
        raise ConfigurationError("vision.source must be a webcam index")
    if not 0 < vision_cfg["confidence"] <= 1 or not 0 < vision_cfg["iou"] <= 1:
        raise ConfigurationError("Invalid confidence/IoU settings")
    if vision_cfg["max_frame_age_seconds"] <= 0:
        raise ConfigurationError("Frame age limit must be positive")
    if type(vision_cfg["image_size"]) is not int or vision_cfg["image_size"] <= 0:
        raise ConfigurationError("Image size must be a positive integer")
