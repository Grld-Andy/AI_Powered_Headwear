import cv2


def handle_stop_mode(frame):
    resized_frame = cv2.resize(frame, (640, 480))
    cv2.imshow("Camera View", resized_frame)
    return resized_frame
