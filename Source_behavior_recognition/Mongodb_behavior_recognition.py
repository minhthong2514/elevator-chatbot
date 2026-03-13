from pymongo import MongoClient
from datetime import datetime

class MongoDBLogger:
    def __init__(self, uri, db_name="iot_project", collection_name="Test"):
        self.client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        self.db = self.client[db_name]
        self.collection = self.db[collection_name]
        print("✅ Connected to MongoDB")
        
    def insert_people_data(self, camera_id, people_data):
        if not people_data:
            return

        doc = {
            "camera_id": camera_id,
            "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "people": people_data
        }
        self.collection.insert_one(doc)

    def close(self):
        self.client.close()
