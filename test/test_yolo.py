from ultralytics import YOLO

# Tải bản Nano Pose - Tối ưu nhất cho tốc độ trên Orin Nano
model = YOLO("yolo26n-pose.pt")