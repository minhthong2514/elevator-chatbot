import cv2
import os

# ===============================
# CẤU HÌNH
# ===============================
BASE_DIR = "Data_faces"
MAX_SAMPLES = 10  # Số lượng ảnh cần quét (tăng lên để quét kỹ hơn)
user_name = input("Nhập tên người dùng: ").strip()

user_dir = os.path.join(BASE_DIR, user_name)
os.makedirs(user_dir, exist_ok=True)

face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

cap = cv2.VideoCapture(0)
count = 0  # Biến đếm số ảnh đã quét trong phiên này

print(f"Bắt đầu quét FaceID cho: {user_name}...")

while True:
    ret, frame = cap.read()
    if not ret: break
    frame = cv2.flip(frame, 1)
    height, width, _ = frame.shape
    
    # Chuyển xám để xử lý
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.3, 5, minSize=(150, 150))

    # Vẽ khung hướng dẫn (Vùng an toàn để đặt mặt vào)
    cv2.rectangle(frame, (width//4, height//6), (3*width//4, 5*height//6), (255, 255, 255), 1)

    for (x, y, w, h) in faces:
        # 1. Vẽ khung nhận diện
        color = (0, 255, 0) # Xanh lá khi đang quét
        cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
        
        # 2. Tự động lưu ảnh (FaceID style)
        if count < MAX_SAMPLES:
            count += 1
            face_img = frame[y:y + h, x:x + w]
            # Resize về kích thước chuẩn để đồng bộ database
            face_img = cv2.resize(face_img, (200, 200))
            
            filename = f"{user_name}_{count:03d}.jpg"
            cv2.imwrite(os.path.join(user_dir, filename), face_img)
            
            # Hiệu ứng quét: Vẽ thanh tiến trình
            progress = int((count / MAX_SAMPLES) * 100)
            cv2.putText(frame, f"Scanning: {progress}%", (x, y - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    # Hiển thị thông tin tổng quát
    cv2.putText(frame, f"User: {user_name}", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
    cv2.putText(frame, "Giu nguyen mat trong khung hinh...", (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

    cv2.imshow("FaceID Enrollment", frame)

    # Thoát khi đủ ảnh hoặc nhấn 'q'
    if cv2.waitKey(1) & 0xFF == ord('q') or count >= MAX_SAMPLES:
        break

print(f"Quá trình hoàn tất! Đã lưu {count} mẫu khuôn mặt.")
cap.release()
cv2.destroyAllWindows()