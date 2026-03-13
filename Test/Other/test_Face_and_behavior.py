import cv2
import face_recognition
import os
import numpy as np
import time
import torch
import threading
from datetime import datetime
from pymongo import MongoClient
from ultralytics import YOLO

# ===============================
# CONFIG & DEVICE
# ===============================
device = 'cuda' if torch.cuda.is_available() else 'cpu'
print(f"[INFO] He thong dang chay tren: {device}")

FACE_ROOT = "Data_faces"
THRESHOLD = 0.45
DB_INTERVAL = 1
CAMERA_ID = "CAM_01"
TIMEOUT = 2  # Thoi gian xoa ID sau khi roi khung hinh

# ===============================
# MONGODB SETUP
# ===============================
MONGO_URI = "mongodb+srv://buiminhtai1234:191104@cluster0.ydqe2ve.mongodb.net/?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI)
db = client["iot_project"]
collection = db["Test_database"]

def save_to_db(data):
    try:
        collection.insert_one(data)
    except Exception as e:
        print(f"Loi MongoDB: {e}")

# ===============================
# LOAD FACE DATASET (KHOI TAO)
# ===============================
print("[INFO] Dang nap du lieu khuon mat...")
known_encodings = []
known_names = []

if not os.path.exists(FACE_ROOT):
    os.makedirs(FACE_ROOT)

for person_name in os.listdir(FACE_ROOT):
    person_dir = os.path.join(FACE_ROOT, person_name)
    if not os.path.isdir(person_dir): continue
    encs_temp = []
    for img_name in os.listdir(person_dir):
        if img_name.lower().endswith((".jpg", ".png", ".jpeg")):
            img = cv2.imread(os.path.join(person_dir, img_name))
            if img is None: continue
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            encs = face_recognition.face_encodings(rgb)
            if encs: encs_temp.append(encs[0])
    if encs_temp:
        known_encodings.append(np.mean(encs_temp, axis=0))
        known_names.append(person_name.upper())
        print(f"[SUCCESS] Da nap: {person_name}")

# ===============================
# LOAD YOLO POSE (TOI UU GPU)
# ===============================
model = YOLO("yolov8n-pose.pt")
model.to(device)

# ===============================
# BIEN QUAN LY TRACKING
# ===============================
track_id_to_name = {}      # ID -> Ten nguoi
person_start_time = {}    # Ten_ID -> Thoi gian bat dau behavior
person_behavior_state = {} # Ten_ID -> Trang thai behavior cu
person_last_seen = {}     # ID -> Thoi gian cuoi cung thay

last_db_time = 0
prev_time = 0

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# ===============================
# MAIN LOOP
# ===============================
while True:
    ret, frame = cap.read()
    if not ret: break
    
    frame = cv2.flip(frame, 1)
    current_time = time.time()
    
    # 1. Chay YOLO Tracking (GPU)
    # Su dung persist=True de giu ID giua cac frame
    results = model.track(frame, persist=True, device=device, verbose=False, tracker="bytetrack.yaml")
    
    # Ve khung xuong tu dong
    frame_draw = results[0].plot(boxes=False) 
    
    people_data_for_db = []

    if results[0].boxes.id is not None:
        boxes = results[0].boxes.xyxy.cpu().numpy().astype(int)
        track_ids = results[0].boxes.id.cpu().numpy().astype(int)
        kpts = results[0].keypoints.data.cpu().numpy() # Keypoints cho moi nguoi

        for i, track_id in enumerate(track_ids):
            x1, y1, x2, y2 = boxes[i]
            person_last_seen[track_id] = current_time
            
            # 2. NHAN DIEN KHUON MAT (Chi chay neu ID nay chua co ten)
            if track_id not in track_id_to_name or track_id_to_name[track_id] == "UNKNOWN":
                name = "UNKNOWN"
                # Trich xuat vung mat dua tren keypoints (Mui, mat) de tiet kiem CPU
                face_points = kpts[i][:5]
                if np.mean(face_points[:, 2]) > 0.5: # Do tin cay keypoints mat > 50%
                    fx1 = int(np.min(face_points[:, 0])) - 20
                    fy1 = int(np.min(face_points[:, 1])) - 40
                    fx2 = int(np.max(face_points[:, 0])) + 20
                    fy2 = int(np.max(face_points[:, 1])) + 20
                    
                    face_crop = frame[max(0,fy1):fy2, max(0,fx1):fx2]
                    if face_crop.size != 0:
                        rgb_face = cv2.cvtColor(face_crop, cv2.COLOR_BGR2RGB)
                        encs = face_recognition.face_encodings(rgb_face)
                        if encs:
                            dist = face_recognition.face_distance(known_encodings, encs[0])
                            if len(dist) > 0 and np.min(dist) < THRESHOLD:
                                name = known_names[np.argmin(dist)]
                track_id_to_name[track_id] = name
            
            final_name = track_id_to_name[track_id]
            unique_key = f"{final_name}_{track_id}"

            # 3. PHAN TICH HANH VI (Dua tren Keypoints Hip vs Knee)
            try:
                hip_y = (kpts[i][11][1] + kpts[i][12][1]) / 2
                knee_y = (kpts[i][13][1] + kpts[i][14][1]) / 2
                # Neu khoang cach Hip-Knee ngan (theo truc Y) -> Sitting
                behavior = "Sitting" if abs(hip_y - knee_y) < (y2 - y1) * 0.15 else "Standing"
            except:
                behavior = "Standing"

            # 4. TINH THOI GIAN (DURATION)
            if unique_key not in person_start_time or person_behavior_state.get(unique_key) != behavior:
                person_start_time[unique_key] = current_time
                person_behavior_state[unique_key] = behavior
            
            duration = int(current_time - person_start_time[unique_key])
            level = "normal" if behavior == "Standing" else "warning"

            # 5. VE GIAO DIEN
            color = (0, 255, 0) if behavior == "Standing" else (0, 0, 255)
            cv2.rectangle(frame_draw, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame_draw, f"ID:{track_id} {final_name} | {behavior} | {duration}s", 
                        (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

            people_data_for_db.append({
                "person_id": final_name,
                "track_id": int(track_id),
                "behavior": behavior,
                "duration": duration,
                "level": level
            })

    # --- DON DEP TRACKING (Xoa ID da bien mat) ---
    expired_ids = [tid for tid, lseen in person_last_seen.items() if current_time - lseen > TIMEOUT]
    for tid in expired_ids:
        name = track_id_to_name.get(tid, "UNKNOWN")
        unique_key = f"{name}_{tid}"
        track_id_to_name.pop(tid, None)
        person_start_time.pop(unique_key, None)
        person_behavior_state.pop(unique_key, None)
        person_last_seen.pop(tid, None)

    # --- GUI MONGODB (THREADING) ---
    if (current_time - last_db_time > DB_INTERVAL) and people_data_for_db:
        doc = {
            "camera_id": CAMERA_ID,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "people": people_data_for_db
        }
        threading.Thread(target=save_to_db, args=(doc,)).start()
        last_db_time = current_time

    # --- FPS ---
    fps = 1 / (time.time() - prev_time) if prev_time else 0
    prev_time = time.time()
    cv2.putText(frame_draw, f"FPS: {int(fps)}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)

    # --- DISPLAY ---
    cv2.imshow("Jetson GPU: AI Behavior Analysis", frame_draw)
    if cv2.waitKey(1) & 0xFF == 27: break

cap.release()
cv2.destroyAllWindows()