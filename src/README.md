### Link cài torch cuda 12.6 cho orin nano
https://github.com/tekletics/Jetpack-6.1-pytorch-cuda-setup

### Install torch 
python3 -m pip install --no-cache-dir \
  "https://developer.download.nvidia.com/compute/redist/jp/v61/pytorch/torch-2.5.0a0+872d972e41.nv24.08.17622132-cp310-cp310-linux_aarch64.whl"

### Install torchvision
python3 -m pip install --no-cache-dir --no-deps \
  "https://github.com/ultralytics/assets/releases/download/v0.0.0/torchvision-0.20.0a0+afc54f7-cp310-cp310-linux_aarch64.whl"


### Export format .pt to .engine
Firstly, you have to install onnx using pip **install onnx**. After this, run:
+ yolo export model=yolov8n-pose.pt format=engine device=0 (For full FP32)
+ yolo export model=yolov8n-pose.pt format=engine half=True device=0 (For half FP16)

Optional: dynamic=true ==> For flexible size
