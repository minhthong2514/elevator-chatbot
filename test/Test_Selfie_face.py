import cv2
import os

# ===============================
# ĐƯỜNG DẪN GỐC (CỐ ĐỊNH)
# ===============================
BASE_DIR = "/home/tai/Ung_dung/Code/Python/Data_faces"

# ===============================
# CẤU HÌNH
# ===============================
MAX_IMAGES = 10
MAX_SHOT_PER_PRESS = 1

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

print("Phím điều khiển:")
print("  S : Chụp tối đa 10 ảnh")
print("  Z : Xóa ảnh vừa chụp")
print("  Q : Thoát")

while True:
    ret, frame = cap.read()
    frame = cv2.flip(frame, 1)

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

    # ===============================
    # HIỂN THỊ SỐ ẢNH
    # ===============================
    cv2.putText(
        frame,
        f"Images: {img_count}/{MAX_IMAGES}",
        (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0, 255, 255),
        2
    )

    cv2.imshow("Face Capture", frame)

    key = cv2.waitKey(1) & 0xFF

    # ===============================
    # NHẤN 'S' → CHỤP 1 ẢNH / TỐI ĐA 10
    # ===============================
    if key == ord('s') and len(faces) > 0 and img_count < MAX_IMAGES:
        shot_count = 0

        for (x, y, w, h) in faces:
            while shot_count < MAX_SHOT_PER_PRESS and img_count < MAX_IMAGES:
                face_img = frame[y:y + h, x:x + w]

                img_count += 1
                shot_count += 1

                filename = f"{user_name}_{img_count:03d}.jpg"
                filepath = os.path.join(user_dir, filename)

                cv2.imwrite(filepath, face_img)
                print(f"Đã lưu: {filepath}")

                cv2.waitKey(80)

    # ===============================
    # NHẤN 'Z' → XÓA ẢNH CUỐI
    # ===============================
    if key == ord('z') and img_count > 0:
        imgs = sorted([
            f for f in os.listdir(user_dir)
            if f.lower().endswith((".jpg", ".png"))
        ])

        if imgs:
            last_img = imgs[-1]
            os.remove(os.path.join(user_dir, last_img))
            img_count -= 1
            print(f"Đã xóa ảnh: {last_img}")

    # ===============================
    # THOÁT
    # ===============================
    if key == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
