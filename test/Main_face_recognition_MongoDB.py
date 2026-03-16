import cv2
import face_recognition
import os
import numpy as np
import time
from pymongo import MongoClient
from datetime import datetime


# ===============================
# CONFIG
# ===============================
FACE_ROOT = "/home/tai/Ung_dung/Code/Python/Thuc_tap/Data_faces"
THRESHOLD = 0.45
DB_INTERVAL = 1   # giây
CAMERA_ID = "CAM_01"

# ===============================
# MONGODB
# ===============================
MONGO_URI = "mongodb+srv://buiminhtai1234:191104@cluster0.ydqe2ve.mongodb.net/?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI)
db = client["iot_project"]
collection = db["Test_database"]

# ===============================
# LOAD & ENCODE FACES (MEAN)
# ===============================
print("[INFO] Loading & encoding faces...")

known_encodings = []
known_names = []

for person_name in os.listdir(FACE_ROOT):
    person_dir = os.path.join(FACE_ROOT, person_name)
    if not os.path.isdir(person_dir):
        continue

    enc_list = []

    for img_name in os.listdir(person_dir):
        if img_name.lower().endswith((".jpg", ".png", ".jpeg")):
            img_path = os.path.join(person_dir, img_name)
            img = cv2.imread(img_path)
            if img is None:
                continue

            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            encs = face_recognition.face_encodings(rgb)

            if encs:
                enc_list.append(encs[0])

    if len(enc_list) >= 3:
        mean_enc = np.mean(enc_list, axis=0)
        known_encodings.append(mean_enc)
        known_names.append(person_name.upper())
        print(f"  [+] {person_name}: {len(enc_list)} images")

print("[INFO] Loaded persons:", known_names)

# ===============================
# CAMERA
# ===============================
cap = cv2.VideoCapture(0)

previousTime = 0
last_db_time = 0

# ===============================
# REALTIME LOOP
# ===============================
while True:
    success, frame = cap.read()
    if not success:
        break

    frame = cv2.flip(frame, 1)
    small = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)

    face_locations = face_recognition.face_locations(
        small, number_of_times_to_upsample=1, model="hog"
    )
    face_encodings = face_recognition.face_encodings(small, face_locations)

    people_data_for_db = []
    detected_names = set()

    for face_encoding, face_loc in zip(face_encodings, face_locations):
        name = "UNKNOWN"

        if known_encodings:
            distances = face_recognition.face_distance(
                known_encodings, face_encoding
            )
            best_idx = np.argmin(distances)

            if distances[best_idx] < THRESHOLD:
                name = known_names[best_idx]
                detected_names.add(name)

        # Scale bounding box
        top, right, bottom, left = face_loc
        top *= 2
        right *= 2
        bottom *= 2
        left *= 2

        cv2.rectangle(frame, (left, top), (right, bottom), (255, 0, 255), 2)
        cv2.putText(
            frame,
            name,
            (left, top - 10),
            cv2.FONT_HERSHEY_COMPLEX,
            0.8,
            (255, 255, 255),
            2,
        )

    # ===============================
    # PREPARE DB DATA
    # ===============================
    for name in detected_names:
        people_data_for_db.append({
            "person_id": name
        })

    # ===============================
    # SEND MONGODB (INTERVAL)
    # ===============================
    now_time = time.time()
    if people_data_for_db and (now_time - last_db_time > DB_INTERVAL):
        try:
            collection.insert_one({
                "camera_id": CAMERA_ID,
                "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                "people": people_data_for_db
            })
            last_db_time = now_time
            print("✅ MongoDB inserted:", people_data_for_db)
        except Exception as e:
            print("⚠️ MongoDB insertion failed:", e)

    # ===============================
    # FPS
    # ===============================
    currentTime = time.time()
    fps = 1 / (currentTime - previousTime) if previousTime else 0
    previousTime = currentTime

    cv2.putText(
        frame,
        f"FPS: {int(fps)}",
        (10, 40),
        cv2.FONT_HERSHEY_COMPLEX,
        1,
        (0, 255, 0),
        2,
    )

    cv2.imshow("Face Recognition + MongoDB", frame)

    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()
