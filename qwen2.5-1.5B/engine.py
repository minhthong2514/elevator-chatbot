import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import json, re
from pymongo import MongoClient
import urllib.parse
from datetime import datetime

class ElevatorAI:
    def __init__(self):
        # 1. Khởi tạo Model
        self.model_name = "Qwen/Qwen2.5-1.5B-Instruct"
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name, torch_dtype="auto", device_map="auto"
        )
        
        # 2. Cấu hình MongoDB
        USER = "boybit2504_db_user"
        PASSWORD = "abc123456"
        CLUSTER_URL = "test-model.xawqqta.mongodb.net" 
        safe_pass = urllib.parse.quote_plus(PASSWORD)
        self.uri = f"mongodb+srv://{USER}:{safe_pass}@{CLUSTER_URL}/?retryWrites=true&w=majority&appName=test-model"
        
        self.client = MongoClient(self.uri)
        self.db = self.client['ElevatorDB']
        self.collection = self.db['elevator_logs']
        print("Trợ lý AI đã sẵn sàng kết nối cơ sở dữ liệu.")

    def _call_ai(self, messages):
        text = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.tokenizer([text], return_tensors="pt").to(self.model.device)
        ids = self.model.generate(**inputs, max_new_tokens=256, do_sample=False)
        return self.tokenizer.batch_decode(ids, skip_special_tokens=True)[0].split("assistant")[-1].strip()

    def _generate_query(self, user_question):
        # Chỉ dẫn tạo Query bằng tiếng Việt có dấu
        system_prompt = (
            "Bạn là chuyên gia về MongoDB. Nhiệm vụ của bạn là chuyển câu hỏi của người dùng thành một JSON query chính xác.\n"
            "QUY TẮC:\n"
            "1. Các trường dữ liệu gồm: 'device_id', 'floor', 'voltage', 'current', 'timestamp'.\n"
            "2. Nếu hỏi về thời gian, hãy sử dụng định dạng ISO (YYYY-MM-DDTHH:MM:SS).\n"
            "   Ví dụ hỏi lúc 18h ngày 2/1/2026: {'timestamp': {'$gte': '2026-01-02T18:00:00', '$lt': '2026-01-02T18:59:59'}}\n"
            "3. Chỉ trả về kết quả là mã JSON, tuyệt đối không giải thích gì thêm."
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_question}
        ]
        raw_res = self._call_ai(messages)
        try:
            json_str = re.search(r'\{.*\}', raw_res, re.DOTALL).group(0)
            return json.loads(json_str)
        except:
            return {}

    def _humanize_response(self, user_question, data):
        # Chỉ dẫn phản hồi bằng tiếng Việt có dấu
        system_prompt = (
            "Bạn là chuyên gia vận hành hệ thống thang máy thông minh. Dựa vào dữ liệu IoT thu được từ cơ sở dữ liệu, "
            "hãy trả lời câu hỏi của người dùng một cách chuyên nghiệp, lịch sự và ngắn gọn bằng tiếng Việt.\n"
            "Nếu dữ liệu trống hoặc không tìm thấy, hãy thông báo rằng không có thông tin trong hệ thống."
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Câu hỏi: {user_question}\nDữ liệu từ hệ thống: {data}"}
        ]
        return self._call_ai(messages)

    def ask(self, user_question):
        # BƯỚC 1: AI tạo Query
        raw_query = self._generate_query(user_question) 
        
        # BƯỚC 2: Xử lý và chuyển đổi kiểu dữ liệu thời gian
        query_dict = {}
        if isinstance(raw_query, dict):
            for k, v in raw_query.items():
                if k == 'timestamp' and isinstance(v, dict):
                    new_v = {}
                    for op, val in v.items():
                        try:
                            # Chuyển chuỗi ISO từ AI thành đối tượng datetime cho MongoDB
                            new_v[op] = datetime.fromisoformat(val)
                        except:
                            new_v[op] = val
                    query_dict[k] = new_v
                elif v is not None and v != "":
                    query_dict[k] = v

        print(f"Lệnh truy vấn thực tế: {query_dict}")
        
        # BƯỚC 3: Truy xuất dữ liệu từ MongoDB
        try:
            cursor = self.collection.find(query_dict).sort("timestamp", -1).limit(5)
            data_found = list(cursor)
            
            for d in data_found:
                d['_id'] = str(d['_id'])
                if 'timestamp' in d and isinstance(d['timestamp'], datetime):
                    d['timestamp'] = d['timestamp'].strftime("%Y-%m-%d %H:%M:%S")
            
            if not data_found:
                data_found = "Hệ thống không tìm thấy dữ liệu nào phù hợp với yêu cầu."
        except Exception as e:
            data_found = f"Lỗi xảy ra khi truy xuất dữ liệu: {e}"

        # BƯỚC 4: AI trả lời người dùng
        return self._humanize_response(user_question, data_found)