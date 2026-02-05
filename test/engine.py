import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, TextStreamer
import json, re
from pymongo import MongoClient
import urllib.parse
from datetime import datetime
import os
import warnings

# --- TẮT CẢNH BÁO ---
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
warnings.filterwarnings("ignore", category=UserWarning)

class ElevatorAI:
    def __init__(self):
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"--- Đang khởi động AI trên thiết bị: {device.upper()} ---")

        # 1. Khởi tạo Model
        self.model_path = "./models" 
        
        print("Đang load model từ ổ cứng...")
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_path, 
            torch_dtype="auto", 
            device_map="auto"
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

    def _call_ai(self, messages, stream=False):
        text = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.tokenizer([text], return_tensors="pt").to(self.model.device)
        
        if stream:
            # Dùng TextStreamer để in trực tiếp
            streamer = TextStreamer(self.tokenizer, skip_prompt=True, skip_special_tokens=True)
            
            # Thay output_ids bằng _ vì chúng ta không cần giữ giá trị trả về
            _ = self.model.generate(
                **inputs, 
                max_new_tokens=512, 
                do_sample=True,
                temperature=0.1,
                top_p=0.9,
                streamer=streamer
            )
            return "" # Streamer đã in rồi nên trả về rỗng
        else:
            # Chế độ bình thường (không stream)
            output_ids = self.model.generate(
                **inputs, 
                max_new_tokens=512, 
                do_sample=True, 
                temperature=0.1
            )
            return self.tokenizer.batch_decode(output_ids, skip_special_tokens=True)[0].split("assistant")[-1].strip()
        
    def _generate_query(self, user_question):
        # Chỉ dẫn tạo Query bằng tiếng Việt có dấu
        system_prompt = (
        "Bạn là một máy chuyển đổi ngôn ngữ sang JSON MongoDB.\n"
        # "Nếu người dùng nhập 'Xin chào', 'hello', 'hi' thì chào lại ngắn gọn và yêu cầu người dùng hỏi về chủ đề thang máy.\n"
        "DANH MỤC THIẾT BỊ HỢP LỆ: ['T1', 'T2', 'T3']\n\n" # Thêm dòng này
        "QUY TẮC BẮT BUỘC:\n"
        "1. CHỈ được sử dụng ID từ danh mục trên. Nếu người dùng nói 'tất cả' hoặc '3 thang máy', hãy dùng: {\"device_id\": {\"$in\": [\"T1\", \"T2\", \"T3\"]}}.\n"
        "2. Tuyệt đối KHÔNG tự chế tên như 'ThangMau', 'Thang1'...\n"
        "3. CHỈ sử dụng 'device_id' và 'timestamp' ($gte, $lt) để lọc.\n"
        "4. Phản hồi CHỈ bao gồm mã JSON thuần túy.\n\n"
        "VÍ DỤ:\n"
        "Câu hỏi: Tình trạng cả 3 thang máy lúc 2h ngày 1/1\n"
        "Trả về: {\"device_id\": {\"$in\": [\"T1\", \"T2\", \"T3\"]}, \"timestamp\": {\"$gte\": \"2026-01-01T02:00:00\", \"$lt\": \"2026-01-01T02:59:59\"}}"
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

    def _humanize_response(self, user_question, data, stream=False):
        # Chỉ dẫn phản hồi bằng tiếng Việt có dấu
        system_prompt = (
        "Bạn là chuyên gia kỹ thuật thang máy. Nhiệm vụ của bạn là đọc kỹ dữ liệu JSON được cung cấp và trả lời câu hỏi.\n"
        "QUY TẮC:\n"
        "1. Phải kiểm tra tất cả các trường: 'voltage' (điện áp), 'current' (dòng điện), 'floor' (tầng).\n"
        "2. Nếu trong dữ liệu có số, bạn KHÔNG ĐƯỢC nói là không có thông tin.\n"
        "3. Trả lời đầy đủ các thông số người dùng hỏi dựa trên con số cụ thể trong dữ liệu."
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Câu hỏi: {user_question}\nDữ liệu từ hệ thống: {data}"}
        ]
        return self._call_ai(messages, stream=stream)

    def ask(self, user_question, stream=False):
        # 1. AI tạo Query (Chạy ngầm)
        raw_query = self._generate_query(user_question) 
        
        # 2. Làm sạch Query
        query_dict = {}
        if isinstance(raw_query, dict) and raw_query:
            if 'device_id' in raw_query:
                query_dict['device_id'] = raw_query['device_id']
            if 'timestamp' in raw_query:
                ts = raw_query['timestamp']
                if isinstance(ts, dict):
                    new_ts = {op: (datetime.fromisoformat(str(val).replace('Z', '')) if isinstance(val, str) else val) 
                             for op, val in ts.items()}
                    query_dict['timestamp'] = new_ts
                elif isinstance(ts, str):
                    query_dict['timestamp'] = datetime.fromisoformat(ts.replace('Z', ''))
        
        if not query_dict:
            return "Tôi không xác định được thiết bị hoặc thời gian bạn cần tra cứu."

        # --- SỬA THỨ TỰ IN TẠI ĐÂY ---
        print(f"\n[Hệ thống] Truy vấn thực tế: {query_dict}")
        
        # 3. Truy xuất dữ liệu từ MongoDB
        try:
            cursor = self.collection.find(query_dict).sort("timestamp", -1).limit(10)
            data_found = list(cursor)
            
            clean_data = []
            for d in data_found:
                item = {
                    "device_id": d.get("device_id"),
                    "voltage": d.get("voltage"),
                    "current": d.get("current"),
                    "floor": d.get("floor"),
                    "status": d.get("status"),
                    "timestamp": d.get("timestamp").strftime("%d/%m/%Y %H:%M:%S") if isinstance(d.get("timestamp"), datetime) else d.get("timestamp")
                }
                clean_data.append(item)
                
            if not clean_data:
                msg = "Hệ thống không tìm thấy dữ liệu phù hợp."
                print(f"AI Agent: {msg}") # In bình thường nếu không có data
                return msg
                
        except Exception as e:
            error_msg = f"Lỗi truy vấn: {e}"
            print(error_msg)
            return error_msg

        # --- CHUẨN BỊ STREAM ---
        print("AI Agent: ", end="", flush=True) 
        
        # 4. AI phân tích và trả lời (TextStreamer sẽ nối tiếp vào dòng "AI Agent:")
        return self._humanize_response(user_question, clean_data, stream=stream)