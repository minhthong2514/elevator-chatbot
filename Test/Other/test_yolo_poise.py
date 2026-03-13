import cv2
from ultralytics import YOLO
import time
import numpy as np

# 1. Khởi tạo model
model = YOLO('yolov8n-pose.pt').to('cuda')
cap = cv2.VideoCapture(0)
prev_time = 0

while cap.isOpened():
    success, frame = cap.read()
    if not success: break

    # Tính FPS
    curr_time = time.time()
    fps = 1 / (curr_time - prev_time)
    prev_time = curr_time

    results = model.predict(frame, device=0, verbose=False)

    for r in results:
        annotated_frame = r.plot(labels=False, boxes=True) 
        
        if r.boxes is not None and r.keypoints is not None:
            for box, kp_data in zip(r.boxes.xyxy, r.keypoints.data):
                # kp[index] = [x, y, confidence]
                kp = kp_data.cpu().numpy()
                x1, y1, x2, y2 = box.cpu().numpy()

                try:
                    # --- KIỂM TRA ĐỦ ĐIỂM TRƯỚC KHI NHẬN DIỆN ---
                    # Danh sách các điểm quan trọng: Vai trái(5), Vai phải(6), Hông trái(11), Hông phải(12)
                    # Bạn có thể thêm Gối(13,14) và Cổ chân(15,16) nếu muốn bắt buộc phải thấy cả chân
                    required_points = [5, 6, 11, 12, 13, 14, 15, 16]
                    conf_threshold = 0.5
                    
                    # Kiểm tra xem tất cả các điểm quan trọng có đủ độ tin cậy không
                    is_visible = all(kp[idx][2] > conf_threshold for idx in required_points)

                    if not is_visible:
                        continue # Bỏ qua người này, không vẽ nhãn và không tính toán tiếp

                    # --- NẾU ĐỦ ĐIỂM THÌ MỚI CHẠY TIẾP PHẦN DƯỚI ---
                    
                    # 3. CHỌN CHÂN RÕ NHẤT ĐỂ TÍNH GÓC
                    l_conf = kp[13][2] + kp[15][2]
                    r_conf = kp[14][2] + kp[16][2]

                    if l_conf > r_conf:
                        hip, knee, ankle = kp[11], kp[13], kp[15]
                    else:
                        hip, knee, ankle = kp[12], kp[14], kp[16]

                    # [Giữ nguyên phần tính knee_angle của bạn ở đây...]
                    v1 = np.array([hip[0] - knee[0], hip[1] - knee[1]])
                    v2 = np.array([ankle[0] - knee[0], ankle[1] - knee[1]])
                    unit_v1 = v1 / (np.linalg.norm(v1) + 1e-6)
                    unit_v2 = v2 / (np.linalg.norm(v2) + 1e-6)
                    knee_angle = np.degrees(np.arccos(np.clip(np.dot(unit_v1, unit_v2), -1.0, 1.0)))

                    # 4. THUẬT TOÁN RA QUYẾT ĐỊNH (DECISION LOGIC)
                    status = "Unknown"
                    color = (255, 255, 255)

                    box_h = y2 - y1
                    box_w = x2 - x1
                    # 1. Tính trung bình tọa độ Y của 2 vai và 2 hông
                    avg_shoulder_y = (kp[5][1] + kp[6][1]) / 2
                    avg_hip_y = (kp[11][1] + kp[12][1]) / 2
                    
                    # Khoảng cách chiều dọc của thân trên (Thắt lưng đến vai)
                    torso_vertical_dist = abs(avg_hip_y - avg_shoulder_y)

                    # A. KIỂM TRA BOX NẰM NGANG (Dễ gây nhầm lẫn giữa Nằm và Ngồi chữ L)
                    if box_w > box_h * 0.9:
                        # Nếu thân trên (vai đến hông) vẫn có độ cao đáng kể -> Ngồi chữ L
                        # Ngưỡng 0.15 * box_h là khoảng cách an toàn để xác định thân đang dựng
                        if torso_vertical_dist > (box_h * 0.3):
                            status = "Sitting"
                            color = (255, 165, 0) # Màu cam
                        else:
                            status = "Lying/Falling"
                            color = (0, 0, 255) # Màu đỏ
                            
                    # B. KIỂM TRA BOX ĐỨNG
                    else:
                        # TÍNH TOÁN ĐỘ DÀI THÂN TRÊN SO VỚI CHIỀU CAO BOX
                        # Nếu đứng thật, torso_vertical_dist thường chiếm ~1/3 đến 1/2 chiều cao Box
                        # Nếu nằm dọc, torso_vertical_dist sẽ bị ép lại rất nhỏ
                        torso_ratio = torso_vertical_dist / (box_h + 1e-6)

                        # THUẬT TOÁN KIỂM TRA NẰM DỌC (Nằm hướng về Camera)
                        # Nếu tỷ lệ thân trên quá ngắn so với chiều cao tổng thể của Box
                        if torso_ratio < 0.2: 
                            status = "Lying"
                            color = (0, 0, 255) # Màu đỏ
                        
                        # Nếu không phải nằm dọc, xét tiếp Đứng/Ngồi/Cúi
                        else:
                            if knee_angle > 160: 
                                status = "Standing"
                                color = (0, 255, 0)
                            elif knee_angle < 120:
                                status = "Sitting"
                                color = (255, 165, 0)
                            else:
                                status = "Bending"
                                color = (0, 255, 255)

                    # 5. VẼ NHÃN TỰ CHỈNH
                    label = f"{status}"
                    (w_text, h_text), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
                    cv2.rectangle(annotated_frame, (int(x1), int(y1) - h_text - 10), (int(x1) + w_text, int(y1)), color, -1)
                    cv2.putText(annotated_frame, label, (int(x1), int(y1) - 5), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1, cv2.LINE_AA)
                                
                except Exception:
                    # Nếu không đủ điểm (ví dụ bị che khuất), bỏ qua người đó
                    continue

        # Hiển thị FPS và Kết quả
        cv2.putText(annotated_frame, f"FPS: {int(fps)}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
        cv2.imshow("Optimized Action Detection", annotated_frame)

    if cv2.waitKey(1) & 0xFF == 27: break # Nhấn ESC để thoát

cap.release()
cv2.destroyAllWindows()