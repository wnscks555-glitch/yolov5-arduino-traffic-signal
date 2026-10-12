from dataclasses import dataclass
import math
from .protocol import FIELDS


@dataclass(frozen=True)
class Detection:
    class_id: int
    cx: float
    cy: float


def inside_polygon(point, polygon):
    # Only points strictly inside a polygon are included; edge points are excluded.
    x, y = point
    inside = False
    for i, (x1, y1) in enumerate(polygon):
        x2, y2 = polygon[(i + 1) % len(polygon)]
        cross = (x - x1) * (y2 - y1) - (y - y1) * (x2 - x1)
        if abs(cross) <= 1e-9 and min(x1, x2) <= x <= max(x1, x2) and min(y1, y2) <= y <= max(y1, y2):
            return False
        if (y1 > y) != (y2 > y) and x < (x2-x1) * (y-y1) / (y2-y1) + x1:
            inside = not inside
    return inside


def aggregate_presence(detections, config):
    result = dict.fromkeys(FIELDS, False)
    for detection in detections:
        if not math.isfinite(detection.cx) or not math.isfinite(detection.cy):
            continue
        if detection.class_id in config["classes"]["vehicle_ids"]:
            fields = FIELDS[:8]
        elif detection.class_id in config["classes"]["pedestrian_ids"]:
            fields = FIELDS[8:]
        else:
            continue
        for field in fields:
            polygons = config["roi"].get(field) or []
            if any(inside_polygon((detection.cx, detection.cy), polygon) for polygon in polygons):
                result[field] = True
                break # Deterministic protocol-order priority for overlapping regions.
    return result
