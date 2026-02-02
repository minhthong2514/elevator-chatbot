import urllib.parse
import threading
import time
from pymongo import MongoClient
from engine import ElevatorAI

# 1. Cau hinh MongoDB
USER = "boybit2504_db_user"
PASSWORD = "abc123456"
CLUSTER_URL = "test-model.xawqqta.mongodb.net"
safe_pass = urllib.parse.quote_plus(PASSWORD)
uri = f"mongodb+srv://{USER}:{safe_pass}@{CLUSTER_URL}/?retryWrites=true&w=majority"

class InteractiveAgent:
    def __init__(self):
        print("--- Dang khoi dong AI Agent. Vui long doi ---")
        self.agent = ElevatorAI()
        self.client = MongoClient(uri)
        self.db = self.client['ElevatorDB']
        self.collection = self.db['elevator_logs']
        self.last_seen_id = None
        self.running = True

    def monitor_stream(self):
        """Luong chay ngam de theo doi du lieu moi tu MongoDB"""
        print("--- Che do giam sat du lieu real-time da bat ---")
        while self.running:
            try:
                # Tim ban ghi moi nhat
                latest_doc = self.collection.find().sort("timestamp", -1).limit(1)
                doc_list = list(latest_doc)
                
                if doc_list:
                    current_id = doc_list[0]['_id']
                    if current_id != self.last_seen_id:
                        self.last_seen_id = current_id
                        # Tu dong in ra thong tin vua cap nhat
                        d = doc_list[0]
                        print(f"\n[STREAM MOI] Thang: {d.get('device_id')} | Tang: {d.get('floor')} | Dien ap: {d.get('voltage')}V")
                        print("Ban: ", end="", flush=True) # Giu nguyen prompt nhap lieu
                
                time.sleep(2) # Quet moi 2 giay
            except Exception as e:
                print(f"\n[LOI STREAM]: {e}")
                time.sleep(5)

    def start(self):
        # Chay luong giam sat
        stream_thread = threading.Thread(target=self.monitor_stream, daemon=True)
        stream_thread.start()

        print("\n" + "="*50)
        print("HE THONG GIAM SAT THANG MAY")
        print("Nhap cau hoi de tuong tac hoac doi du lieu stream...")
        print("Go 'exit' de thoat")
        print("="*50)

        while True:
            user_input = input("Ban: ")
            
            if user_input.lower() in ['exit', 'quit']:
                self.running = False
                print("Ket thuc chuong trinh.")
                break
                
            if not user_input.strip():
                continue

            try:
                print("AI dang phan tich...")
                response = self.agent.ask(user_input)
                print(f"AI Agent: {response}")
            except Exception as e:
                print(f"Loi: {e}")

if __name__ == "__main__":
    app = InteractiveAgent()
    app.start()