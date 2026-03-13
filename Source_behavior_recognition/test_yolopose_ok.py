import time
import torch
import numpy as np
from ultralytics import YOLO


class YOLOPoseTracker:
    def __init__(self, model_path="yolov8n-pose.pt", conf=0.5):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = YOLO(model_path)
        self.model.to(self.device)

        self.conf = conf
        self.tracked_people = {}
        self.previous_positions = {}  # dùng để tính vận tốc

    def process_frame(self, frame):
        now_time = time.time()

        results = self.model.track(
            frame,
            persist=True,
            conf=self.conf,
            verbose=False,
            device=self.device
        )

        people_for_db = []
        draw_data = []

        if results[0].boxes.id is None:
            return draw_data, people_for_db

        boxes = results[0].boxes.xyxy.cpu().numpy()
        track_ids = results[0].boxes.id.int().cpu().tolist()
        keypoints = results[0].keypoints.xy.cpu().numpy()

        for i, track_id in enumerate(track_ids):

            x1, y1, x2, y2 = map(int, boxes[i])
            kps = keypoints[i]

            pose_h = kps[:, 1].max() - kps[:, 1].min()
            pose_w = kps[:, 0].max() - kps[:, 0].min()

            if pose_h < 10:
                continue

            aspect = pose_h / (pose_w + 1e-6)

            # ===============================
            # BASE POSTURE (standing/sitting/lying)
            # ===============================
            hip_y = (kps[11, 1] + kps[12, 1]) / 2
            knee_y = (kps[13, 1] + kps[14, 1]) / 2
            leg_ratio = abs(knee_y - hip_y) / (pose_h + 1e-6)

            if aspect < 0.9:
                behavior = "lying"
            elif leg_ratio < 0.22:
                behavior = "sitting"
            else:
                behavior = "standing"

            # ===============================
            # WALKING / RUNNING
            # ===============================
            center_x = (x1 + x2) / 2

            speed = 0
            if track_id in self.previous_positions:
                speed = abs(center_x - self.previous_positions[track_id])
            self.previous_positions[track_id] = center_x

            if behavior == "standing":
                if speed > 25:
                    behavior = "running"
                elif speed > 8:
                    behavior = "walking"

            # ===============================
            # RAISING HAND
            # ===============================
            left_wrist_y = kps[9, 1]
            right_wrist_y = kps[10, 1]
            left_shoulder_y = kps[5, 1]
            right_shoulder_y = kps[6, 1]

            if left_wrist_y < left_shoulder_y or right_wrist_y < right_shoulder_y:
                behavior = "raising_hand"

            # ===============================
            # BENDING
            # ===============================
            shoulder_center = (kps[5] + kps[6]) / 2
            hip_center = (kps[11] + kps[12]) / 2

            dx = shoulder_center[0] - hip_center[0]
            dy = shoulder_center[1] - hip_center[1]

            angle_ratio = abs(dx) / (abs(dy) + 1e-6)

            if behavior == "standing" and angle_ratio > 0.5:
                behavior = "bending"

            # ===============================
            # TRACKING TIME & FALLING DETECTION
            # ===============================
            if track_id not in self.tracked_people:
                self.tracked_people[track_id] = {
                    "behavior": behavior,
                    "start_time": now_time,
                    "last_seen": now_time
                }
            else:
                previous_behavior = self.tracked_people[track_id]["behavior"]
                time_diff = now_time - self.tracked_people[track_id]["start_time"]

                # FALLING: standing -> lying nhanh
                if previous_behavior == "standing" and behavior == "lying" and time_diff < 1:
                    behavior = "falling"

                if behavior != previous_behavior:
                    self.tracked_people[track_id]["behavior"] = behavior
                    self.tracked_people[track_id]["start_time"] = now_time

                self.tracked_people[track_id]["last_seen"] = now_time

            duration = int(now_time - self.tracked_people[track_id]["start_time"])

            # ===============================
            # ALERT LEVEL
            # ===============================
            level = "normal"
            color = (0, 255, 0)

            if behavior in ["lying", "falling"]:
                level = "danger"
                color = (0, 0, 255)

            elif behavior == "sitting" and duration >= 5:
                level = "warning"
                color = (0, 255, 255)

            elif behavior == "running":
                level = "warning"
                color = (255, 0, 255)

            draw_data.append({
                "bbox": (x1, y1, x2, y2),
                "text": f"ID:{track_id} {behavior} {duration}s",
                "color": color
            })

            people_for_db.append({
                "person_id": track_id,
                "behavior": behavior,
                "duration": duration,
                "level": level
            })

        self.cleanup(now_time)
        return draw_data, people_for_db

    def cleanup(self, now_time, timeout=5):
        remove_ids = [
            pid for pid, data in self.tracked_people.items()
            if now_time - data["last_seen"] > timeout
        ]

        for pid in remove_ids:
            del self.tracked_people[pid]
            if pid in self.previous_positions:
                del self.previous_positions[pid]