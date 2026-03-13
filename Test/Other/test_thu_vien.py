# import face_recognition
import cv2
import numpy    
import torch
import ultralytics
from ultralytics import YOLO

# print(face_recognition.__version__)
print(cv2.__version__)
print(numpy.__version__)
print(torch.__version__)
print(torch.cuda.is_available())
print(torch.cuda.get_device_name())
print(ultralytics.__version__)

# model = YOLO('/home/tai/Ung_dung/Code/Python/Thuc_tap/yolov5s.pt', device= 'cuda')