import cv2
import torch

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

model = torch.hub.load(
    'ultralytics/yolov5',
    'yolov5n',
    pretrained=True
)

model.conf = 0.5
model.classes = [0]
model.to(device)
model.eval()
torch.set_grad_enabled(False)
detections = []

cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
cap.set(cv2.CAP_PROP_FPS, 60)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

frame_id = 0

while True:
    ret, frame = cap.read()
    frame = cv2.flip(frame, 1)
    if not ret:
        break
    
    frame_id += 1
    if frame_id % 3 == 0:
        # print(frame_id)
        results = model(frame, size=416)
        detections = results.xyxy[0]

    for det in detections:
        x1, y1, x2, y2, conf, cls = map(int, det[:6])
        cv2.rectangle(frame, (x1,y1),(x2,y2),(0,255,0),2)

    cv2.imshow("YOLOv5", frame)
    if cv2.waitKey(1) == 27:
        break

cap.release()
cv2.destroyAllWindows()
