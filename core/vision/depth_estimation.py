import cv2


def load_depth_model(path="./models/Midas-V2.onnx"):
    midas_net = cv2.dnn.readNet(path)
    midas_net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
    midas_net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
    return midas_net


def run_depth_estimation(frame, net):
    input_size = (256, 256)
    blob = cv2.dnn.blobFromImage(frame, 1 / 255.0, input_size, (0, 0, 0), swapRB=True, crop=False)
    net.setInput(blob)
    output = net.forward()
    depth = output.squeeze()
    depth = cv2.resize(depth, (frame.shape[1], frame.shape[0]))
    norm_depth = cv2.normalize(depth, None, 255, 0, cv2.NORM_MINMAX, cv2.CV_8U)
    color_depth = cv2.applyColorMap(norm_depth, cv2.COLORMAP_JET)
    return color_depth, depth
