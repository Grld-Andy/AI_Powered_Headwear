from ultralytics import YOLO
from tensorflow.keras.models import load_model

# Load models
LANG_MODEL = load_model('./models/language_selector.keras')
yolo_model = YOLO("./models/yolov5n.pt")