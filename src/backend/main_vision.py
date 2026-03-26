import cv2
import time
import numpy as np
from ultralytics import YOLO
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import uvicorn

app = FastAPI()

# 1. Khởi tạo Model YOLOv8 Pose (Sử dụng GPU CUDA trên Jetson)
model = YOLO('/home/tai/Ung_dung/Code/Python/Thuc_tap/models-vision/yolov8n-pose.pt').to('cpu')

# 2. Khởi tạo Camera
cap = cv2.VideoCapture(0)

def generate_frames():
    prev_time = 0
    while True:
        success, frame = cap.read()
        if not success:
            break
        
        # Lật ảnh gương (tùy chọn)
        frame = cv2.flip(frame, 1)
        frame = cv2.resize(frame, (1920,1080))

        # --- PHẦN LOGIC NHẬN DIỆN HÀNH VI ---
        # Chạy inference với YOLO
        results = model.predict(frame,verbose=False)
        
        annotated_frame = frame.copy() # Mặc định là frame gốc

        for r in results:
            # Vẽ các điểm xương (plot)
            annotated_frame = r.plot(labels=False, boxes=True) 
            
            if r.boxes is not None and r.keypoints is not None:
                for box, kp_data in zip(r.boxes.xyxy, r.keypoints.data):
                    kp = kp_data.cpu().numpy()
                    x1, y1, x2, y2 = box.cpu().numpy()

                    try:
                        # Kiểm tra đủ 8 điểm quan trọng
                        required_points = [5, 6, 11, 12, 13, 14, 15, 16]
                        conf_threshold = 0.5
                        is_visible = all(kp[idx][2] > conf_threshold for idx in required_points)

                        if not is_visible: continue 

                        # Chọn chân rõ nhất tính góc
                        l_conf = kp[13][2] + kp[15][2]
                        r_conf = kp[14][2] + kp[16][2]
                        hip, knee, ankle = (kp[11], kp[13], kp[15]) if l_conf > r_conf else (kp[12], kp[14], kp[16])

                        # Tính góc đầu gối
                        v1 = np.array([hip[0] - knee[0], hip[1] - knee[1]])
                        v2 = np.array([ankle[0] - knee[0], ankle[1] - knee[1]])
                        unit_v1 = v1 / (np.linalg.norm(v1) + 1e-6)
                        unit_v2 = v2 / (np.linalg.norm(v2) + 1e-6)
                        knee_angle = np.degrees(np.arccos(np.clip(np.dot(unit_v1, unit_v2), -1.0, 1.0)))

                        # LOGIC QUYẾT ĐỊNH HÀNH VI
                        status, color = "Unknown", (255, 255, 255)
                        box_h, box_w = y2 - y1, x2 - x1
                        avg_shoulder_y = (kp[5][1] + kp[6][1]) / 2
                        avg_hip_y = (kp[11][1] + kp[12][1]) / 2
                        torso_vertical_dist = abs(avg_hip_y - avg_shoulder_y)

                        if box_w > box_h * 0.9: # Box nằm ngang
                            if torso_vertical_dist > (box_h * 0.3):
                                status, color = "Sitting", (255, 165, 0)
                            else:
                                status, color = "Lying/Falling", (0, 0, 255)
                        else: # Box đứng
                            torso_ratio = torso_vertical_dist / (box_h + 1e-6)
                            if torso_ratio < 0.2:
                                status, color = "Lying", (0, 0, 255)
                            else:
                                if knee_angle > 160: status, color = "Standing", (0, 255, 0)
                                elif knee_angle < 120: status, color = "Sitting", (255, 165, 0)
                                else: status, color = "Bending", (0, 255, 255)

                        # Vẽ nhãn hành vi
                        label = f"{status}"
                        (w_t, h_t), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
                        cv2.rectangle(annotated_frame, (int(x1), int(y1) - h_t - 10), (int(x1) + w_t, int(y1)), color, -1)
                        cv2.putText(annotated_frame, label, (int(x1), int(y1) - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
                    
                    except Exception: continue

        # Tính toán FPS hiển thị trên web
        curr_time = time.time()
        fps = 1 / (curr_time - prev_time + 1e-6)
        prev_time = curr_time
        cv2.putText(annotated_frame, f"FPS: {int(fps)}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

        # MÃ HÓA JPEG TRUYỀN ĐI
        # Quality 40 giúp giảm lag cực mạnh trên web
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 200]
        ret, buffer = cv2.imencode('.jpg', annotated_frame, encode_param)
        frame_bytes = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.get("/video_feed")
async def video_feed():
    return StreamingResponse(generate_frames(), media_type="multipart/x-mixed-replace; boundary=frame")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)