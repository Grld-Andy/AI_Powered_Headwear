import cv2

def capture_and_save_image(save_path):
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    if ret:
        cv2.imwrite(save_path, frame)
    cap.release()
    return ret, save_path if ret else None
