import time
import torch
from ultralytics import YOLO

class YOLOPoseTracker:
    def __init__(self, model_path="yolov8n-pose.pt", conf=0.5):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = YOLO(model_path)
        self.model.to(self.device)

        self.conf = conf
        self.tracked_people = {}

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

            hip_y = (kps[11, 1] + kps[12, 1]) / 2
            knee_y = (kps[13, 1] + kps[14, 1]) / 2
            leg_ratio = abs(knee_y - hip_y) / (pose_h + 1e-6)

            if aspect < 0.9:
                behavior = "lying"
            elif leg_ratio < 0.22:
                behavior = "sitting"
            else:
                behavior = "standing"

            if track_id not in self.tracked_people:
                self.tracked_people[track_id] = {
                    "behavior": behavior,
                    "start_time": now_time,
                    "last_seen": now_time
                }
            else:
                if behavior != self.tracked_people[track_id]["behavior"]:
                    self.tracked_people[track_id]["behavior"] = behavior
                    self.tracked_people[track_id]["start_time"] = now_time
                self.tracked_people[track_id]["last_seen"] = now_time

            duration = int(now_time - self.tracked_people[track_id]["start_time"])

            level = "normal"
            color = (0, 255, 0)
            if behavior == "lying":
                level = "warning"
                color = (0, 0, 255)
            elif behavior == "sitting" and duration >= 5:
                level = "warning"
                color = (0, 255, 255)

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