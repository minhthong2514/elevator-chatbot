import cv2
import time
import numpy as np
import torch
from datetime import datetime
from pymongo import MongoClient
from ultralytics import YOLO

# ===============================
# MONGODB CONFIG
# ===============================
MONGO_URI = "mongodb+srv://buiminhtai1234:191104@cluster0.ydqe2ve.mongodb.net/?retryWrites=true&w=majority"
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client["iot_project"]
    collection = db["test_database"]
    print("✅ Connected to MongoDB")
except Exception as e:
    print(f"❌ MongoDB Connection Error: {e}")

# ===============================
# DEVICE & MODEL
# ===============================
device = "cuda" if torch.cuda.is_available() else "cpu"
model = YOLO("yolov8n-pose.pt") # Đảm bảo file này có sẵexn
model.to(device)

# ===============================
# CAMERA
# ===============================
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# ===============================
# TRACKING STATE
# ===============================
# Cấu trúc: { track_id: {"behavior": str, "start_time": float, "last_seen": float} }
tracked_people = {}
DB_INTERVAL = 1.0
last_db_time = 0
prev_time = 0

print(f"🚀 Running on: {device}. Press 'ESC' to stop.")

# ===============================
# MAIN LOOP
# ===============================
while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)
    now_time = time.time()
    
    # ===== YOLO TRACKING (Sử dụng persist=True để tự động quản lý ID) =====
    results = model.track(frame, persist=True, conf=0.5, verbose=False, device=device)
    
    people_data_for_db = []

    # Kiểm tra xem có kết quả không
    if results[0].boxes.id is not None:
        boxes = results[0].boxes.xyxy.cpu().numpy()
        track_ids = results[0].boxes.id.int().cpu().tolist()
        keypoints = results[0].keypoints.xy.cpu().numpy()

        for i, track_id in enumerate(track_ids):
            # Lấy thông tin tọa độ và keypoints
            x1, y1, x2, y2 = map(int, boxes[i])
            person_kps = keypoints[i]

            # 1. Tính toán tư thế (Pose Analysis)
            # pose_h = max_y - min_y
            pose_h = person_kps[:, 1].max() - person_kps[:, 1].min()
            pose_w = person_kps[:, 0].max() - person_kps[:, 0].min()
            if pose_h < 10: continue

            # Keypoints quan trọng: Vai(5,6), Hông(11,12), Gối(13,14)
            # Tính tỷ lệ và góc để đoán hành vi
            aspect = pose_h / (pose_w + 1e-6)
            
            # Tính khoảng cách từ hông đến gối để nhận diện ngồi
            hip_y = (person_kps[11, 1] + person_kps[12, 1]) / 2
            knee_y = (person_kps[13, 1] + person_kps[14, 1]) / 2
            leg_ratio = abs(knee_y - hip_y) / (pose_h + 1e-6)

            # Phân loại hành vi
            if aspect < 0.9: # Người nằm ngang
                current_behavior = "lying"
            elif leg_ratio < 0.22: # Gối gần hông theo trục dọc
                current_behavior = "sitting"
            else:
                current_behavior = "standing"

            # 2. Quản lý Duration và Trạng thái ID
            if track_id not in tracked_people:
                # Nếu là ID mới hoàn toàn: Khởi tạo
                tracked_people[track_id] = {
                    "behavior": current_behavior,
                    "start_time": now_time,
                    "last_seen": now_time
                }
            else:
                # Nếu ID đã tồn tại: Kiểm tra xem họ có đổi tư thế không
                if current_behavior != tracked_people[track_id]["behavior"]:
                    tracked_people[track_id]["behavior"] = current_behavior
                    tracked_people[track_id]["start_time"] = now_time # RESET DURATION
                
                tracked_people[track_id]["last_seen"] = now_time

            # Tính thời gian đã duy trì hành vi
            duration = int(now_time - tracked_people[track_id]["start_time"])

            # 3. Xác định mức độ cảnh báo (Level & Color)
            level = "normal"
            color = (0, 255, 0) # Green

            if current_behavior == "lying":
                level = "warning"
                color = (0, 0, 255) # Red
            elif current_behavior == "sitting" and duration >= 5:
                level = "warning"
                color = (0, 255, 255) # Yellow

            # 4. Vẽ Debug lên màn hình
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, f"ID:{track_id} {current_behavior} {duration}s", 
                        (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

            # 5. Chuẩn bị dữ liệu gửi DB
            people_data_for_db.append({
                "person_id": track_id,
                "behavior": current_behavior,
                "duration": duration,
                "level": level
            })

    # ===== DỌN DẸP BỘ NHỚ (Xóa ID đã biến mất > 5 giây) =====
    ids_to_clean = [pid for pid, data in tracked_people.items() if now_time - data["last_seen"] > 5]
    for pid in ids_to_clean:
        del tracked_people[pid]

    # ===== GỬI MONGODB THEO CHU KỲ =====
    if people_data_for_db and (now_time - last_db_time > DB_INTERVAL):
        try:
            collection.insert_one({
                "camera_id": "CAM_01",
                "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                "people": people_data_for_db
            })
            last_db_time = now_time
        except:
            print("⚠️ MongoDB insertion failed")

    # ===== HIỂN THỊ FPS =====
    fps = 1 / (now_time - prev_time + 1e-6)
    prev_time = now_time
    cv2.putText(frame, f"FPS: {int(fps)}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)

    cv2.imshow("YOLOv8 Behavioral Tracking", frame)
    if cv2.waitKey(1) & 0xFF == 27: # Nhấn ESC để thoát
        break

# Cleanup
cap.release()
cv2.destroyAllWindows()
client.close()