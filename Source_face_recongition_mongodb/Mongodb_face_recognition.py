from pymongo import MongoClient
from datetime import datetime
import time


class MongoDBHandler:

    def __init__(self, mongo_uri, db_name, collection_name,
                 camera_id="CAM_01", interval=1):

        self.client = MongoClient(mongo_uri)

        self.db = self.client[db_name]
        self.collection = self.db[collection_name]

        self.camera_id = camera_id
        self.interval = interval

        self.last_db_time = 0


    # ==========================================
    # SEND DATA TO MONGODB WITH TIME INTERVAL
    # ==========================================
    def send_if_needed(self, people_data):

        now_time = time.time()

        # Không có dữ liệu
        if not people_data:
            return

        # chưa tới interval
        if now_time - self.last_db_time < self.interval:
            return

        # Chuẩn hóa dữ liệu trước khi insert
        formatted_people = []

        for person in people_data:

            data = {
                "person_id": person.get("person_id", "unknown"),
                "behavior": person.get("behavior", "unknown"),
                "duration": int(person.get("duration", 0)),
                "level": person.get("level", "normal")
            }

            formatted_people.append(data)

        document = {
            "camera_id": self.camera_id,
            "timestamp": datetime.now(),
            "people": formatted_people
        }

        try:

            self.collection.insert_one(document)

            self.last_db_time = now_time

            print("✅ MongoDB inserted:")
            print(formatted_people)

        except Exception as e:

            print("⚠️ MongoDB insertion failed:", e)