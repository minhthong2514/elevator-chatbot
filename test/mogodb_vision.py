from pymongo import MongoClient
from datetime import datetime


MONGO_URI = "mongodb+srv://buiminhtai1234:191104@cluster0.ydqe2ve.mongodb.net/?retryWrites=true&w=majority"

# 1️⃣ Kết nối MongoDB Cloud
client = MongoClient(MONGO_URI)

# 2️⃣ Chọn database
db = client["iot_project"]

# 3️⃣ Chọn collection
# collection = db["Human Resource Management"]
collection = db["Test"]

# 4️⃣ Dữ liệu cần đẩy
data = {
    "username": "Tai",
    "password": "tai123",
    "rank": "admin"
}

# 5️⃣ Insert
result = collection.insert_one(data)

print("✅ Đã đẩy dữ liệu, ID:", result.inserted_id)