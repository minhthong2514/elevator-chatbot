import cv2
import time
# from YoloPose_behavior_recognition import YOLOPoseTracker
from test_yolopose_ok import YOLOPoseTracker
from Mongodb_behavior_recognition import MongoDBLogger
# ===============================
# CONFIG
# ===============================
MONGO_URI = "mongodb+srv://buiminhtai1234:191104@cluster0.ydqe2ve.mongodb.net/?retryWrites=true&w=majority"
CAMERA_ID = "CAM_01"
DB_INTERVAL = 1.0
# ===============================
# INIT
# ===============================
tracker = YOLOPoseTracker("yolov8n-pose.pt")
db_logger = MongoDBLogger(MONGO_URI)

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

last_db_time = 0
prev_time = time.time()

print("🚀 System started. Press ESC to exit.")

# ===============================
# LOOP
# ===============================
while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)

    draw_data, people_data = tracker.process_frame(frame)

    for item in draw_data:
        x1, y1, x2, y2 = item["bbox"]
        cv2.rectangle(frame, (x1, y1), (x2, y2), item["color"], 2)
        cv2.putText(
            frame,
            item["text"],
            (x1, y1 - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            item["color"],
            2
        )

    now = time.time()
    if people_data and now - last_db_time > DB_INTERVAL:
        try:
            db_logger.insert_people_data(CAMERA_ID, people_data)
            last_db_time = now
        except:
            print("⚠️ MongoDB insert error")

    fps = 1 / (now - prev_time + 1e-6)
    prev_time = now
    cv2.putText(frame, f"FPS: {int(fps)}", (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)

    cv2.imshow("YOLOv8 Behavioral Tracking", frame)
    if cv2.waitKey(1) & 0xFF == 27:
        break

# ===============================
# CLEANUP
# ===============================
cap.release()
cv2.destroyAllWindows()
db_logger.close()
