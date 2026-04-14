import cv2
import time
import numpy as np
import threading
import queue
import asyncio
from ultralytics import YOLO
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import uvicorn
from turbojpeg import TurboJPEG
from pymongo import MongoClient
from datetime import datetime, timedelta
from collections import deque

# --- CONFIG ---
MONGO_URI = "mongodb+srv://buiminhtai1234:191104@cluster0.ydqe2ve.mongodb.net/?retryWrites=true&w=majority"
MODEL_PATH = '/home/tai/Ung_dung/Code/Python/Thuc_tap/models-vision/yolo26n-pose.engine'
# Dùng path file custom_tracker đã tạo để ID không nhảy
TRACKER_CONFIG = "/home/tai/Ung_dung/Code/Python/Thuc_tap/models-vision/custom_tracker.yaml"

GST_STR = (
    "v4l2src device=/dev/video0 ! "
    "image/jpeg, width=1920, height=1080, framerate=60/1 ! "
    "jpegdec ! videoconvert ! video/x-raw, format=BGR ! appsink drop=1 max-buffers=1"
)

class VisionSystem:
    def __init__(self):
        self.stopped = False
        self.raw_frame = deque(maxlen=1)
        self.processed_frame = deque(maxlen=1)
        self.db_queue = queue.Queue(maxsize=20)
        self.sitting_timers = {}
        self.jpeg = TurboJPEG()
        
        # --- BỘ ĐỆM DỮ LIỆU ---
        self.buffer_60s = {}        
        self.frame_counts = {}      
        self.last_record_time = {}  
        self.last_behavior_level = {} # Theo dõi trạng thái để ghi log tức thì
        self.start_time_60s = time.time()
        self.start_timestamp_str = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        
        print(">>> Khởi tạo Vision System (Jetson Orin Nano)...")
        self.model = YOLO(MODEL_PATH, task='pose')
        self.model(np.zeros((640, 640, 3), dtype=np.uint8), verbose=False)
        
        self.cap = cv2.VideoCapture(GST_STR, cv2.CAP_GSTREAMER)
        if not self.cap.isOpened():
            raise RuntimeError("Camera Error: Không thể kết nối GStreamer")

    def start(self):
        threading.Thread(target=self._reader, daemon=True).start()
        threading.Thread(target=self._worker, daemon=True).start()
        threading.Thread(target=self._mongo_worker, daemon=True).start()

    def _reader(self):
        while not self.stopped:
            ret, frame = self.cap.read()
            if ret:
                self.raw_frame.append(cv2.flip(frame, 1))
            else:
                time.sleep(0.01)

    def _worker(self):
        prev_time = 0
        # Đảm bảo current_minute được khởi tạo
        if not hasattr(self, 'current_minute'):
            self.current_minute = datetime.now().strftime("%Y-%m-%dT%H:%M")

        while not self.stopped:
            if not self.raw_frame:
                continue
                
            frame = self.raw_frame.pop()
            
            # --- 1. LẤY THỜI GIAN NGAY ĐẦU VÒNG LẶP ---
            now_dt = datetime.now()
            now_ts = time.time()
            minute_now = now_dt.strftime("%Y-%m-%dT%H:%M")
            sec_key = now_dt.strftime("%H:%M:%S")

            # 2. Chạy Tracking
            results = self.model.track(
                frame, persist=True, imgsz=640, half=True, 
                conf=0.6, iou=0.5, verbose=False, tracker=TRACKER_CONFIG
            )
            
            active_ids = []
            
            if results[0].boxes.id is not None:
                boxes = results[0].boxes.xyxy.cpu().numpy().astype(int)
                ids = results[0].boxes.id.int().cpu().tolist()
                kpts = results[0].keypoints.data.cpu().numpy()
                
                for i, p_id in enumerate(ids):
                    kp = kpts[i]    
                    x1, y1, x2, y2 = boxes[i]
                    
                    # --- KIỂM TRA ĐIỂM QUAN TRỌNG ---
                    required_points = [5, 6, 11, 12, 13, 14, 15, 16]
                    if not all(kp[idx][2] > 0.5 for idx in required_points):
                        continue

                    active_ids.append(p_id)

                    # --- TÍNH TOÁN GÓC GỐI ---
                    l_conf = kp[13][2] + kp[15][2]
                    r_conf = kp[14][2] + kp[16][2]
                    hip_pt, knee_pt, ankle_pt = (kp[11], kp[13], kp[15]) if l_conf > r_conf else (kp[12], kp[14], kp[16])
                    
                    v1_k = np.array([hip_pt[0] - knee_pt[0], hip_pt[1] - knee_pt[1]])
                    v2_k = np.array([ankle_pt[0] - knee_pt[0], ankle_pt[1] - knee_pt[1]])
                    knee_angle = np.degrees(np.arccos(np.clip(np.dot(v1_k, v2_k) / (np.linalg.norm(v1_k) * np.linalg.norm(v2_k) + 1e-6), -1.0, 1.0)))
                    
                    # --- TÍNH TOÁN GÓC HÔNG ---
                    shoulder_mid = (kp[5] + kp[6]) / 2
                    hip_mid = (kp[11] + kp[12]) / 2
                    knee_mid = (kp[13] + kp[14]) / 2
                    v1_h = np.array([shoulder_mid[0] - hip_mid[0], shoulder_mid[1] - hip_mid[1]])
                    v2_h = np.array([knee_mid[0] - hip_mid[0], knee_mid[1] - hip_mid[1]])
                    hip_angle = np.degrees(np.arccos(np.clip(np.dot(v1_h, v2_h) / (np.linalg.norm(v1_h) * np.linalg.norm(v2_h) + 1e-6), -1.0, 1.0)))

                    box_w, box_h = x2 - x1, y2 - y1
                    torso_dist = abs(((kp[5][1] + kp[6][1]) / 2) - ((kp[11][1] + kp[12][1]) / 2))

                    status, level, color = "Unknown", "normal", (255, 255, 255)

                    # --- LOGIC NHẬN DIỆN TƯ THẾ ---
                    if box_w > box_h * 1.5: 
                        if torso_dist > (box_h * 0.3):
                            status, color = "Sitting", (255, 165, 0)
                        else: 
                            status, level, color = "Lying", "warning", (0, 0, 255)
                    else: 
                        torso_ratio = torso_dist / (box_h + 1e-6)
                        if torso_ratio < 0.2: 
                            status, level, color = "Lying", "warning", (0, 0, 255)
                        else:
                            # Ngồi khi góc hông gập HOẶC góc gối gập
                            if hip_angle < 130 or knee_angle < 130: 
                                status, color = "Sitting", (255, 165, 0)
                            else:
                                status, color = "Standing", (0, 255, 0)
                    
                    # --- CẢNH BÁO NGỒI LÂU ---
                    if "Sitting" in status:
                        if p_id not in self.sitting_timers: self.sitting_timers[p_id] = now_ts
                        dur = now_ts - self.sitting_timers[p_id]
                        if dur >= 5.0:
                            status, level, color = f"WARNING: Sitting {int(dur)}s", "warning", (0, 0, 255)
                    else:
                        self.sitting_timers.pop(p_id, None)

                    # --- LƯU DỮ LIỆU VÀO BUFFER ---
                    if sec_key not in self.buffer_60s:
                        self.buffer_60s[sec_key] = []
                    
                    if not any(p['person_id'] == p_id for p in self.buffer_60s[sec_key]):
                        self.buffer_60s[sec_key].append({
                            "timestamp": sec_key,
                            "person_id": p_id,
                            "behavior": status,
                            "level": level
                        })

                    # Vẽ UI
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)
                    cv2.putText(frame, f"ID:{p_id} {status}", (x1, y1-10), 0, 0.7, color, 2)

            # Clean up timers cho những người đã rời khỏi khung hình
            self.sitting_timers = {k: v for k, v in self.sitting_timers.items() if k in active_ids}

            # --- 3. LOGIC ĐẨY DB KHI SANG PHÚT MỚI (00s -> 59s) ---
            if minute_now != self.current_minute and len(self.buffer_60s) > 0:
                old_analysis = {}
                new_analysis = {}
                # Tách dữ liệu: chỉ lấy những giây thuộc về phút cũ
                old_min_label = self.current_minute.split("T")[-1] 
                
                for ts, data in self.buffer_60s.items():
                    if ts.startswith(old_min_label):
                        old_analysis[ts] = data
                    else:
                        new_analysis[ts] = data

                if old_analysis:
                    all_ids = set()
                    warning_ids = set()
                    for sec in old_analysis:
                        for p in old_analysis[sec]:
                            all_ids.add(p["person_id"])
                            if p["level"] == "warning": warning_ids.add(p["person_id"])

                    payload = {
                        "camera_id": "CAM_01",
                        "start_time": f"{self.current_minute}:00",
                        "end_time": f"{self.current_minute}:59",
                        "total_person_count": len(all_ids),
                        "total_warning_count": len(warning_ids),
                        "analysis": old_analysis
                    }

                    if not self.db_queue.full():
                        self.db_queue.put(payload)
                        print(f"--- Đã đẩy dữ liệu phút {self.current_minute} (00-59) ---")
                
                # Chuyển sang phút mới và giữ lại dữ liệu giây 00 của phút mới
                self.buffer_60s = new_analysis
                self.current_minute = minute_now

            # Hiển thị FPS và số người
            fps = 1 / (time.time() - prev_time + 1e-6)
            prev_time = time.time()
            cv2.putText(frame, f"FPS: {int(fps)}  People: {len(active_ids)}", (20, 40), 0, 1, (0, 255, 255), 2)
            self.processed_frame.append(frame)
            
    def _mongo_worker(self):
        db = MongoClient(MONGO_URI)["iot_project"]["Test"]
        while not self.stopped:
            try:
                data = self.db_queue.get(timeout=1)
                db.insert_one(data)
                print(">>> MongoDB: Lưu thành công!")
            except: continue

vision = VisionSystem()
vision.start()
app = FastAPI()

@app.get("/video_feed")
async def video_feed():
    async def generate():
        while True:
            if vision.processed_frame:
                img = vision.jpeg.encode(vision.processed_frame.pop(), quality=60)
                yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + img + b'\r\n')
            await asyncio.sleep(0.01)
    return StreamingResponse(generate(), media_type="multipart/x-mixed-replace; boundary=frame")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="error")