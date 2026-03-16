import cv2
import time
from Face_recognition import FaceRecognition
from Mongodb_face_recognition import MongoDBHandler
from Yolo_pose import YOLOPoseTracker

# ===============================
# CONFIG
# ===============================
FACE_ROOT = "/home/tai/Ung_dung/Code/Python/Thuc_tap/Data_faces"
THRESHOLD = 0.45
DB_INTERVAL = 1
CAMERA_ID = "CAM_01"

MONGO_URI = "mongodb+srv://buiminhtai1234:191104@cluster0.ydqe2ve.mongodb.net/?retryWrites=true&w=majority"

# ===============================
# INIT OBJECTS
# ===============================
face_recog = FaceRecognition(FACE_ROOT, THRESHOLD)
pose_tracker = YOLOPoseTracker()

mongo_handler = MongoDBHandler(
    mongo_uri=MONGO_URI,
    db_name="iot_project",
    collection_name="Test",
    camera_id=CAMERA_ID,
    interval=DB_INTERVAL
)

# ===============================
# CAMERA
# ===============================
cap = cv2.VideoCapture(0)
previousTime = 0

while True:
    success, frame = cap.read()
    if not success:
        break

    frame = cv2.flip(frame, 1)

    # =========================================
    # FACE RECOGNITION
    # =========================================
    frame, detected_names = face_recog.recognize_faces(frame)

    # =========================================
    # YOLO POSE
    # =========================================
    draw_data, pose_people = pose_tracker.process_frame(frame)

    # =========================================
    # DRAW POSE BOX
    # =========================================
    for item in draw_data:
        x1, y1, x2, y2 = item["bbox"]
        text = item["text"]
        color = item["color"]

        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(
            frame,
            text,
            (x1, y1 - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            color,
            2
        )

    # =========================================
    # COMBINE FACE + POSE DATA
    # =========================================
    combined_people = []

    for name in detected_names:

        matched_pose = None

        # nếu có pose thì lấy pose gần nhất (tạm thời lấy người đầu tiên)
        if pose_people:
            matched_pose = pose_people[0]

        if matched_pose:
            combined_people.append({
                "person_id": name,
                "behavior": matched_pose["behavior"],
                "duration": matched_pose["duration"],
                "level": matched_pose["level"]
            })
        else:
            combined_people.append({
                "person_id": name
            })

    # =========================================
    # SEND TO MONGODB
    # =========================================
    if combined_people:
        mongo_handler.send_if_needed(combined_people)

    # =========================================
    # FPS
    # =========================================
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

    cv2.imshow("Face Recognition + YOLO Pose + MongoDB", frame)

    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()