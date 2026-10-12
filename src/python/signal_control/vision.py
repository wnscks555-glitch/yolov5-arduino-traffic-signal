import sys
import time
from .config import configured_path, validate, ConfigurationError
from .roi import Detection, aggregate_presence


def run_vision(config, transport, preview=False):
    validate(config, vision=True)
    root = configured_path(config, config["vision"]["yolo_root"])
    required = ("models/common.py", "utils/dataloaders.py", "utils/general.py", "utils/torch_utils.py")
    if any(not (root/path).is_file() for path in required):
        raise ConfigurationError("yolo_root must be a compatible YOLOv5 checkout containing " + ", ".join(required))
    # Project modules are isolated from YOLOv5's utils and models packages.
    for name in ("utils", "models"):
        module = sys.modules.get(name)
        if module is not None and root not in __import__("pathlib").Path(module.__file__).resolve().parents:
            raise ConfigurationError(f"An unrelated {name} module is already imported")
    sys.path.insert(0, str(root))
    import numpy as np
    import torch
    from models.common import DetectMultiBackend
    from utils.dataloaders import LoadStreams
    from utils.general import cv2, check_img_size, non_max_suppression, scale_boxes
    from utils.torch_utils import select_device
    options = config["vision"]
    device = select_device(options["device"])
    model = DetectMultiBackend(str(configured_path(config, options["weights"])), device=device, fp16=False)
    ids = config["classes"]["vehicle_ids"] + config["classes"]["pedestrian_ids"]
    if any(i not in model.names if isinstance(model.names, dict) else i >= len(model.names) for i in ids):
        raise ConfigurationError("Configured class IDs do not exist in the loaded weights")
    size = check_img_size([options["image_size"], options["image_size"]], s=model.stride)
    dataset = LoadStreams(str(options["source"]), img_size=size, stride=model.stride, auto=model.pt, vid_stride=1)
    try:
        with torch.inference_mode():
            for _, im, originals, _, _ in dataset:
                captured_at = time.monotonic()
                tensor = torch.from_numpy(im).to(model.device).float() / 255.0
                if len(tensor.shape) == 3: tensor = tensor[None]
                prediction = model(tensor, augment=False, visualize=False)
                prediction = non_max_suppression(prediction, options["confidence"], options["iou"], classes=ids)
                frame = originals[0].copy()
                detected = prediction[0]
                if len(detected):
                    detected[:, :4] = scale_boxes(tensor.shape[2:], detected[:, :4], frame.shape).round()
                centers = []
                for x1, y1, x2, y2, confidence, class_id in detected.tolist():
                    centers.append(Detection(int(class_id), (x1+x2)/2, (y1+y2)/2))
                    if preview:
                        cv2.rectangle(frame, (int(x1),int(y1)), (int(x2),int(y2)), (0,255,0), 1)
                presence = aggregate_presence(centers, config)
                if time.monotonic() - captured_at < options["max_frame_age_seconds"]:
                    transport.send(presence, captured_at=captured_at)
                for status in transport.poll(): print(status)
                if preview:
                    for polygons in config["roi"].values():
                        for polygon in polygons or []:
                            cv2.polylines(frame,[np.array(polygon,dtype=np.int32)],True,(0,255,255),1)
                    cv2.imshow("Traffic signal",frame)
                    if cv2.waitKey(1) & 0xff in (27,ord('q')): break
    finally:
        for capture in getattr(dataset, "caps", []): capture.release()
        if hasattr(dataset, "running"): dataset.running = False
        if preview: cv2.destroyAllWindows()
