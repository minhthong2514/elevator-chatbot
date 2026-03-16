import cv2
from ultralytics import YOLO
import time
import numpy as np
import face_recognition
import os

# --- 1. SETUP DỮ LIỆU MẶT ---
path_to_faces = "Data_faces" 
known_face_encodings = []
known_face_names = []

print("🔄 Đang nạp dữ liệu khuôn mặt...")
for person_name in os.listdir(path_to_faces):
    person_dir = os.path.join(path_to_faces, person_name)
    if os.path.isdir(person_dir):
        for img_name in os.listdir(person_dir):
            img_path = os.path.join(person_dir, img_name)
            try:
                face_img = face_recognition.load_image_file(img_path)
                encodings = face_recognition.face_encodings(face_img)
                if len(encodings) > 0:
                    known_face_encodings.append(encodings[0])
                    known_face_names.append(person_name)
            except Exception as e:
                print(f"Lỗi nạp ảnh {img_path}: {e}")
print(f"✅ Đã nạp xong {len(known_face_names)} ảnh khuôn mặt.")

# --- 2. KHỞI TẠO MODEL ---
model = YOLO('yolov8n-pose.pt').to('cuda')
cap = cv2.VideoCapture(0)
prev_time = 0
frame_count = 0
current_names = [] # Lưu tên để hiển thị giữa các quãng nghỉ nhận diện

while cap.isOpened():
    success, frame = cap.read()
    frame = cv2.flip(frame,1)

    if not success: break
    frame_count += 1

    # Tính FPS
    curr_time = time.time()
    fps = 1 / (curr_time - prev_time)
    prev_time = curr_time

    # Nhận diện Pose
    results = model.predict(frame, device=0, verbose=False)

    # TỐI ƯU: Chỉ nhận diện mặt mỗi 10 frame để không bị lag
    if frame_count % 10 == 0 or frame_count == 1:
        current_names = []
        # Resize nhỏ lại để nhận diện mặt nhanh hơn 4 lần
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        
        face_locations = face_recognition.face_locations(rgb_small_frame)
        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

        for face_encoding in face_encodings:
            matches = face_recognition.compare_faces(known_face_encodings, face_encoding, tolerance=0.6)
            name = "Unknown"
            face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
            if len(face_distances) > 0:
                best_match_index = np.argmin(face_distances)
                if matches[best_match_index]:
                    name = known_face_names[best_match_index]
            current_names.append(name)

    for r in results:
        annotated_frame = r.plot(labels=False, boxes=True) 
        
        if r.boxes is not None and r.keypoints is not None:
            # Lấy danh sách boxes để khớp với tên
            boxes = r.boxes.xyxy.cpu().numpy()
            
            for i, (box, kp_data) in enumerate(zip(boxes, r.keypoints.data)):
                kp = kp_data.cpu().numpy()
                x1, y1, x2, y2 = map(int, box)

                # Lấy tên tương ứng (nếu có)
                person_name = current_names[i] if i < len(current_names) else "Detecting..."

                try:
                    # --- [GIỮ NGUYÊN LOGIC TÍNH STATUS CỦA BẠN ĐỂ LẤY BIẾN 'color'] ---
                    # (Phần code tính Standing/Sitting/Lying của bạn ở đây...)
                    # Giả sử đã có biến 'status' và 'color'
                    
                    # --- 5. VẼ NHÃN CHỈ HIỂN THỊ TÊN ---
                    label = f"{person_name}" # Chỉ giữ lại tên người
                    
                    (w_text, h_text), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
                    
                    # Vẽ nền nhãn dựa trên màu của status (color)
                    cv2.rectangle(annotated_frame, (x1, y1 - h_text - 15), (x1 + w_text, y1), color, -1)
                    
                    # Ghi tên lên frame
                    cv2.putText(annotated_frame, label, (x1, y1 - 10), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1, cv2.LINE_AA)
                                
                except Exception: continue

    cv2.putText(annotated_frame, f"FPS: {int(fps)}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
    cv2.imshow("Multi-Person ID & Behavior", annotated_frame)
    if cv2.waitKey(1) & 0xFF == 27: break

cap.release()
cv2.destroyAllWindows()