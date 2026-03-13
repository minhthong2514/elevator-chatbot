import cv2
import os

# ===============================
# ĐƯỜNG DẪN GỐC (CỐ ĐỊNH)
# ===============================
BASE_DIR = "/home/tai/Ung_dung/Code/Python/Thuc_tap/Data_faces"

# ===============================
# NHẬP TÊN NGƯỜI DÙNG
# ===============================
user_name = input("Nhập tên người dùng: ").strip()

user_dir = os.path.join(BASE_DIR, user_name)
os.makedirs(user_dir, exist_ok=True)

print(f"Lưu ảnh tại: {user_dir}")

# ===============================
# ĐẾM ẢNH ĐÃ CÓ
# ===============================
existing_imgs = [
    f for f in os.listdir(user_dir)
    if f.lower().endswith((".jpg", ".png"))
]
img_count = len(existing_imgs)

# ===============================
# LOAD FACE CASCADE
# ===============================
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

# ===============================
# MỞ CAMERA
# ===============================
cap = cv2.VideoCapture(0)

print("Nhấn 's' để chụp ảnh khuôn mặt, 'q' để thoát")

while True:
    ret, frame = cap.read()
    frame =cv2.flip(frame,1)
    if not ret:
        print("Không mở được camera")
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.3,
        minNeighbors=5,
        minSize=(100, 100)
    )

    for (x, y, w, h) in faces:
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

    cv2.imshow("Face Capture", frame)

    key = cv2.waitKey(1) & 0xFF

    # ===============================
    # NHẤN 's' ĐỂ LƯU ẢNH
    # ===============================
    if key == ord('s') and len(faces) > 0:
        for (x, y, w, h) in faces:
            face_img = frame[y:y + h, x:x + w]

            img_count += 1
            filename = f"{user_name}_{img_count:03d}.jpg"
            filepath = os.path.join(user_dir, filename)

            cv2.imwrite(filepath, face_img)
            print(f"Đã lưu: {filepath}")

    # ===============================
    # THOÁT
    # ===============================
    if key == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
