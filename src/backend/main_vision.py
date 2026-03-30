import cv2
import time
import numpy as np
from ultralytics import YOLO
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import uvicorn
import threading
import queue
import asyncio
from turbojpeg import TurboJPEG

jpeg = TurboJPEG()
app = FastAPI()

# --- CẤU HÌNH ---
MODEL_PATH = '/home/tai/Ung_dung/Code/Python/Thuc_tap/models-vision/yolov8n-pose.engine'
GST_STR = (
    "v4l2src device=/dev/video0 ! "
    "image/jpeg, width=1920, height=1080, framerate=60/1 ! "
    "jpegdec ! videoconvert ! video/x-raw, format=BGR ! appsink drop=1"
)

class VisionSystem:
    def __init__(self):
        self.stopped = False
        self.frame_queue = queue.Queue(maxsize=2)
        self.output_queue = queue.Queue(maxsize=2)
        
        # 1. Nạp Model TRƯỚC
        print(">>> Đang nạp Model...")
        self.model = YOLO(MODEL_PATH, task='pose')
        
        # 2. Mở Camera SAU
        print(">>> Đang mở Camera...")
        self.cap = cv2.VideoCapture(GST_STR, cv2.CAP_GSTREAMER)
        
        if not self.cap.isOpened():
            raise RuntimeError("Không thể mở Camera. Kiểm tra lại kết nối hoặc GStreamer.")

    def start_threads(self):
        t1 = threading.Thread(target=self._reader_thread, daemon=True)
        t2 = threading.Thread(target=self._worker_thread, daemon=True)
        t1.start()
        t2.start()

    def _reader_thread(self):
        while not self.stopped:
            ret, frame = self.cap.read()
            if not ret:
                print(">>> Camera mất tín hiệu!")
                self.stopped = True
                break
            
            # Giải phóng hàng đợi nếu đầy để tránh delay
            if self.frame_queue.full():
                try: self.frame_queue.get_nowait()
                except: pass
            
            self.frame_queue.put(frame)
        self.cap.release()

    def _worker_thread(self):
        prev_time = 0
        while not self.stopped:
            if not self.frame_queue.empty():
                full_frame = self.frame_queue.get()
                
                results = self.model.predict(full_frame, imgsz=640, half=True, conf=0.8, stream=True, verbose=False)
                
                annotated_frame = full_frame

                for r in results:
                    if r.boxes is not None and r.keypoints is not None:
                        boxes = r.boxes.xyxy.cpu().numpy()
                        kpts = r.keypoints.data.cpu().numpy()

                        for i in range(len(boxes)):
                            kp = kpts[i]
                            x1, y1, x2, y2 = boxes[i].astype(int)

                            # --- BƯỚC 1: LUÔN VẼ BBOX TRƯỚC ---
                            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 6)

                            try:
                                # --- BƯỚC 2: KIỂM TRA ĐIỂM KHỚP ĐỂ XỬ LÝ LABEL ---
                                required_points = [5, 6, 11, 12, 13, 14, 15, 16]
                                conf_threshold = 0.5
                                is_visible = all(kp[idx][2] > conf_threshold for idx in required_points)

                                # Nếu không đủ điểm thì chỉ vẽ Box (đã vẽ ở trên) và bỏ qua phần Label
                                if not is_visible: 
                                    continue 

                                # --- BƯỚC 3: LOGIC TÍNH TOÁN STATUS (Giữ nguyên của bạn) ---
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

                                if box_w > box_h * 0.9: 
                                    if torso_vertical_dist > (box_h * 0.3):
                                        status, color = "Sitting", (255, 165, 0)
                                    else:
                                        status, color = "Lying/Falling", (0, 0, 255)
                                else: 
                                    torso_ratio = torso_vertical_dist / (box_h + 1e-6)
                                    if torso_ratio < 0.2:
                                        status, color = "Lying", (0, 0, 255)
                                    else:
                                        if knee_angle > 160: status, color = "Standing", (0, 255, 0)
                                        elif knee_angle < 120: status, color = "Sitting", (255, 165, 0)
                                        else: status, color = "Bending", (0, 255, 255)

                                # --- BƯỚC 4: VẼ ĐÈ LÊN BOX CŨ VỚI MÀU CỦA STATUS ---
                                # Vẽ lại Box với màu theo status (để thay thế màu trắng ban đầu)
                                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
                                
                                # Vẽ nhãn hành vi
                                label = f"{status}"
                                (w_t, h_t), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
                                cv2.rectangle(annotated_frame, (int(x1), int(y1) - h_t - 10), (int(x1) + w_t, int(y1)), color, -1)
                                cv2.putText(annotated_frame, label, (int(x1), int(y1) - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
                            
                            except Exception: 
                                continue

                # Tính FPS hiển thị
                curr_time = time.time()
                fps = 1 / (curr_time - prev_time + 1e-6)
                prev_time = curr_time
                cv2.putText(annotated_frame, f"FPS: {int(fps)}", (40, 80), 
                            cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 255, 255), 4)

                if not self.output_queue.full():
                    self.output_queue.put(annotated_frame)

vision = VisionSystem()
vision.start_threads()

async def generate_frames():
    while not vision.stopped:
        frame = None
        # Xả sạch hàng đợi để lấy frame mới nhất, giảm độ trễ tích tụ (Latency)
        while not vision.output_queue.empty():
            frame = vision.output_queue.get_nowait()
        
        if frame is not None:
            try:
                # Nén Full HD bằng TurboJPEG cực nhanh
                buffer = jpeg.encode(frame, quality=70)
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer + b'\r\n')
            except: continue
        await asyncio.sleep(0.001)

@app.get("/video_feed")
async def video_feed():
    return StreamingResponse(generate_frames(), media_type="multipart/x-mixed-replace; boundary=frame")

if __name__ == "__main__":
    # Đừng quên chạy 'sudo jetson_clocks' trước khi chạy script này
    uvicorn.run(app, host="0.0.0.0", port=8000)