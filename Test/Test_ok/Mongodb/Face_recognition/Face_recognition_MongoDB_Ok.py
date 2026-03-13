from pymongo import MongoClient
from datetime import datetime

# 🔑 THAY BẰNG URI CỦA BẠN
MONGO_URI = "mongodb+srv://buiminhtai1234:191104@cluster0.ydqe2ve.mongodb.net/?retryWrites=true&w=majority"

# 1️⃣ Kết nối MongoDB Cloud
client = MongoClient(MONGO_URI)

# 2️⃣ Chọn database
db = client["iot_project"]

# 3️⃣ Chọn collection
collection = db["sensor_data"]

# 4️⃣ Dữ liệu cần đẩy
data = {
    "device_id": "ESP32_01",
    "temperature": 30.5,
    "humidity": 70,
    "status": "running",
    "time": datetime.now()
}

# 5️⃣ Insert
result = collection.insert_one(data)

print("✅ Đã đẩy dữ liệu, ID:", result.inserted_id)
