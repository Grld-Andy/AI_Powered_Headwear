from config.settings import yolo_model


def run_object_detection(frame):
    results = yolo_model(frame, verbose=False)
    detections = []
    for r in results:
        for *box, conf, cls in r.boxes.data.tolist():
            detections.append({'bbox': tuple(map(int, box)), 'confidence': conf, 'class_id': int(cls)})
    return detections
