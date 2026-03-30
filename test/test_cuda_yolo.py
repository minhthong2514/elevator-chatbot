import cv2
from ultralytics import YOLO
import time
import numpy as np
import threading
import queue

# --- CẤU HÌNH ---
MODEL_PATH = '/home/tai/Ung_dung/Code/Python/Thuc_tap/models-vision/yolov8n-pose.engine'
# MODEL_PATH = '/home/tai/Ung_dung/Code/Python/Thuc_tap/models-vision/yolov8n-pose.pt' # Comment lại pt

class PoseEstimationApp:
    def __init__(self, video_source=0):
        # 1. Khởi tạo Camera
        # self.cap = cv2.VideoCapture(video_source)
        gst_str = (
            "v4l2src device=/dev/video0 ! "
            "image/jpeg, width=1920, height=1080, framerate=60/1 ! "
            "jpegdec ! "
            "videoconvert ! "
            "video/x-raw, format=BGR ! "
            "appsink drop=1"
        )
        self.cap = cv2.VideoCapture(gst_str, cv2.CAP_GSTREAMER)
        # self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        # self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        
        # 2. Khởi tạo Model (Dùng .engine với task='pose')
        self.model = YOLO(MODEL_PATH, task='pose')
        
        # 3. Quản lý luồng và hàng đợi
        self.frame_queue = queue.Queue(maxsize=2)
        self.result_queue = queue.Queue(maxsize=2)
        self.stopped = False
        
        self.fps = 0
        self.prev_time = 0

    def start(self):
        # Chạy luồng đọc camera và luồng xử lý AI
        threading.Thread(target=self.video_capture_thread, daemon=True).start()
        threading.Thread(target=self.inference_thread, daemon=True).start()
        self.display_thread()

    def video_capture_thread(self):
        """Luồng 1: Chuyên đọc frame từ Camera"""
        while not self.stopped:
            success, frame = self.cap.read()
            if success:
                if not self.frame_queue.full():
                    self.frame_queue.put(frame)
            else:
                self.stopped = True

    def inference_thread(self):
        """Luồng 2: Chuyên chạy AI TensorRT và Logic tính toán"""
        while not self.stopped:
            if not self.frame_queue.empty():
                frame = self.frame_queue.get()
                
                # Chạy Predict (Sử dụng half=True cho engine FP16)
                results = self.model.predict(frame, imgsz=640, half=True, conf=0.7, stream=True, verbose=False)
                
                annotated_frame = frame.copy()
                
                for r in results:
                    # Vẽ xương mặc định
                    annotated_frame = r.plot(labels=False, boxes=True)
                    
                    if r.boxes is not None and r.keypoints is not None:
                        # TRÍCH XUẤT DATA RA CPU 1 LẦN DUY NHẤT
                        all_boxes = r.boxes.xyxy.cpu().numpy()
                        all_kpts = r.keypoints.data.cpu().numpy()

                        for i in range(len(all_boxes)):
                            box = all_boxes[i]
                            kp = all_kpts[i]
                            x1, y1, x2, y2 = box.astype(int)

                            try:
                                # Logic tính toán góc (Chân trái: 11, 13, 15)
                                l_hip, l_knee, l_ankle = kp[11], kp[13], kp[15]
                                
                                if l_hip[2] < 0.5 or l_knee[2] < 0.5 or l_ankle[2] < 0.5:
                                    continue

                                v1 = np.array([l_hip[0] - l_knee[0], l_hip[1] - l_knee[1]])
                                v2 = np.array([l_ankle[0] - l_knee[0], l_ankle[1] - l_knee[1]])
                                
                                unit_v1 = v1 / (np.linalg.norm(v1) + 1e-6)
                                unit_v2 = v2 / (np.linalg.norm(v2) + 1e-6)
                                angle = np.degrees(np.arccos(np.clip(np.dot(unit_v1, unit_v2), -1.0, 1.0)))

                                # Phân loại trạng thái
                                status, color = "Standing", (0, 255, 0)
                                box_h, box_w = (y2 - y1), (x2 - x1)

                                if box_w > box_h:
                                    status, color = "Falling/Lying", (0, 0, 255)
                                elif angle < 130:
                                    status, color = "Sitting", (255, 165, 0)
                                elif angle < 155:
                                    status, color = "Bending", (0, 255, 255)

                                # Vẽ nhãn tự chỉnh
                                label = f"{status} {int(angle)}deg"
                                cv2.rectangle(annotated_frame, (x1, y1 - 25), (x1 + 180, y1), color, -1)
                                cv2.putText(annotated_frame, label, (x1, y1 - 5), 
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,0), 1)
                            except:
                                continue
                
                # Đưa kết quả vào hàng đợi hiển thị
                if not self.result_queue.full():
                    self.result_queue.put(annotated_frame)

    def display_thread(self):
        """Luồng 3 (Main): Hiển thị hình ảnh ra màn hình"""
        while not self.stopped:
            if not self.result_queue.empty():
                result_frame = self.result_queue.get()
                
                # Tính FPS thực tế
                curr_time = time.time()
                self.fps = 1 / (curr_time - self.prev_time) if (curr_time - self.prev_time) > 0 else 0
                self.prev_time = curr_time

                cv2.putText(result_frame, f"Real-time FPS: {int(self.fps)}", (20, 40), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
                
                cv2.imshow("Orin Nano - Multi-threaded Pose Engine", result_frame)

            if cv2.waitKey(1) & 0xFF == 27: # ESC để thoát
                self.stopped = True
                break
        
        self.cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    # Đừng quên chạy 'sudo jetson_clocks' trước khi bắt đầu!
    app = PoseEstimationApp(video_source=0)
    app.start()