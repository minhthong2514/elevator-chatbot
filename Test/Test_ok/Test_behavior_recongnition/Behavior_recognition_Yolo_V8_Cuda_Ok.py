import cv2
import time
import numpy as np
import torch
from ultralytics import YOLO
import os

os.environ['CUDA_LAUNCH_BLOCKING']="1"
os.environ['TORCH_USE_CUDA_DSA'] = "1"
# ===============================
# DEVICE
# ===============================
device = "cuda" if torch.cuda.is_available() else "cpu"
print("Running on:", device)

# ===============================
# LOAD YOLOv8 POSE
# ===============================
model = YOLO("/home/tai/Ung_dung/Code/Python/Thuc_tap/yolov8n-pose.pt")
model.to(device)

# ===============================
# CAMERA
# ===============================
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

# ===============================
# TIME TRACKING
# ===============================
sit_start_time = {}          # {pid: start_time}
SIT_TIME_THRESHOLD = 10      # seconds

prev_time = 0

# ===============================
# MAIN LOOP
# ===============================
while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)

    # ===== YOLO GPU INFERENCE =====
    results = model(frame, conf=0.5, device=0, verbose=False)

    for r in results:
        if r.keypoints is None:
            continue

        kps = r.keypoints.xy.cpu().numpy()      # (N, 17, 2)
        boxes = r.boxes.xyxy.cpu().numpy()      # (N, 4)

        for pid, person in enumerate(kps):
            x1, y1, x2, y2 = map(int, boxes[pid])

            # ===== KEYPOINTS =====
            LS, RS = person[5], person[6]
            LH, RH = person[11], person[12]
            LK, RK = person[13], person[14]

            xs = person[:, 0]
            ys = person[:, 1]

            pose_h = ys.max() - ys.min()
            pose_w = xs.max() - xs.min()
            aspect_ratio = pose_h / (pose_w + 1e-6)

            # ===== BODY ANGLE =====
            mid_shoulder = (LS + RS) / 2
            mid_hip = (LH + RH) / 2
            dx = mid_shoulder[0] - mid_hip[0]
            dy = mid_shoulder[1] - mid_hip[1]
            body_angle = abs(np.degrees(np.arctan2(dy, dx)))

            # ===== LEG BEND =====
            knee_y = (LK[1] + RK[1]) / 2
            hip_y = (LH[1] + RH[1]) / 2
            leg_ratio = abs(knee_y - hip_y) / (pose_h + 1e-6)

            # ===== BEHAVIOR CLASSIFICATION =====
            now = time.time()

            if aspect_ratio < 0.8 or body_angle < 30:
                state = "LYING"
                color = (0, 0, 255)
                sit_start_time.pop(pid, None)

            elif leg_ratio < 0.25:
                state = "SITTING"

                if pid not in sit_start_time:
                    sit_start_time[pid] = now

                sit_duration = now - sit_start_time[pid]

                if sit_duration > SIT_TIME_THRESHOLD:
                    state = "ABNORMAL SITTING"
                    color = (255, 0, 255)  # PURPLE
                    print(f"[WARNING] Person {pid} sitting too long: {int(sit_duration)}s")
                else:
                    color = (0, 255, 255)

            else:
                state = "STANDING"
                color = (0, 255, 0)
                sit_start_time.pop(pid, None)

            # ===== DRAW BOX =====
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

            # ===== DRAW LABEL =====
            cv2.putText(
                frame,
                state,
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                color,
                2
            )

            # ===== SHOW SITTING TIME =====
            if state.startswith("SITTING") or state.startswith("ABNORMAL"):
                cv2.putText(
                    frame,
                    f"{int(sit_duration)}s",
                    (x1, y2 + 20),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    color,
                    2
                )

    # ===============================
    # FPS
    # ===============================
    curr_time = time.time()
    fps = 1 / (curr_time - prev_time) if prev_time else 0
    prev_time = curr_time

    cv2.putText(
        frame,
        f"FPS: {int(fps)}",
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (255, 255, 0),
        2
    )

    cv2.imshow("YOLOv8 Pose - Abnormal Sitting Detection", frame)

    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()
