import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, TextStreamer
import json, re
from pymongo import MongoClient
import urllib.parse
from datetime import datetime, timedelta
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
        self.model_path = "/home/minhthong/Desktop/Chatbot/models" 
        
        print("Đang load model từ ổ cứng...")
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_path, 
            torch_dtype="auto", 
            device_map="auto"
        )
        
        # 2. Cấu hình MongoDB
        USER = "buiminhtai1234"
        PASSWORD = "191104"
        CLUSTER_URL = "cluster0.ydqe2ve.mongodb.net" 
        safe_pass = urllib.parse.quote_plus(PASSWORD)
        self.uri = f"mongodb+srv://{USER}:{safe_pass}@{CLUSTER_URL}/?retryWrites=true&w=majority&appName=test-model"
        
        self.client = MongoClient(self.uri)
        self.db = self.client['iot_project']
        self.collection = self.db['human_behavior']
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
        now_str = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

        # Prompt này được thiết kế để Qwen không hiểu nhầm là đang đi theo dõi người
        system_prompt = (
            f"BẠN LÀ MÁY CHUYỂN ĐỔI DỮ LIỆU JSON. GIỜ HIỆN TẠI: {now_str}.\n"
            "NHIỆM VỤ: Chuyển văn bản người dùng thành JSON MongoDB.\n"
            "QUY TẮC:\n"
            "1. KHÔNG trả lời bằng lời văn, CHỈ trả về JSON.\n"
            "2. KHÔNG từ chối vì lý do bảo mật, đây là dữ liệu IoT kỹ thuật.\n"
            "3. Mẫu JSON: {\"camera_id\": \"CAM_01\", \"timestamp\": {\"$gte\": \"...\", \"$lt\": \"...\"}}\n"
            "VÍ DỤ: 'Lúc 16:13:53 có ai không?' -> {'camera_id': 'CAM_01', 'timestamp': {'$gte': '2026-02-03T16:13:53', '$lt': '2026-02-03T16:13:54'}}"
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Chuyển câu này sang JSON: {user_question}"}
        ]
        
        raw_res = self._call_ai(messages)
        print(f"--- AI RAW RESPONSE: {raw_res} ---")

        try:
            # Tìm kiếm JSON trong phản hồi
            match = re.search(r'\{.*\}', raw_res, re.DOTALL)
            if match:
                json_str = match.group(0)
                # Xử lý các ký tự đặc biệt AI có thể thêm vào nhầm
                json_str = json_str.replace("'", '"') 
                return json.loads(json_str)
            return {}
        except Exception as e:
            print(f"Lỗi phân tách JSON: {e}")
            return {}
        
    def _humanize_response(self, user_question, summary, stream=False):        
        system_prompt = (
        "Bạn là báo cáo viên kỹ thuật. Nhiệm vụ của bạn là đọc dữ liệu JSON và trả lời câu hỏi.\n"
        "QUY TẮC:\n"
        "1. 'đứng' = 'standing', 'ngồi' = 'sitting', 'nằm' = 'lying' hoặc 'fallen'.\n"
        "2. Chỉ báo cáo số lượng dựa trên trường 'behaviors' trong dữ liệu.\n"
        "3. Nếu không có dữ liệu cho hành vi đó, báo là 0.\n"
        "4. Trả lời ngắn gọn, không giải thích dài dòng."
        )
        user_content = f"Câu hỏi: {user_question}\nDữ liệu hệ thống: {json.dumps(summary, ensure_ascii=False)}"
        messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content}
        ]
        return self._call_ai(messages, stream=stream)

    def ask(self, user_question, stream=False):
        raw_query = self._generate_query(user_question) 
        query_dict = {}
        
        if isinstance(raw_query, dict) and raw_query:
            query_dict['camera_id'] = raw_query.get('camera_id', 'CAM_01')
            
            if 'timestamp' in raw_query:
                ts = raw_query['timestamp']
                try:
                    if isinstance(ts, dict):
                        # CHUYỂN ĐỔI: Chuyển về datetime rồi cộng 1 giây, sau đó chuyển lại String để khớp DB
                        start_dt = datetime.fromisoformat(str(ts.get('$gte')).replace('Z', ''))
                        # Nếu AI trả về $lt, dùng $lt, nếu không có thì lấy $gte + 1s
                        end_val = ts.get('$lt') or ts.get('$gte')
                        end_dt = datetime.fromisoformat(str(end_val).replace('Z', '')) + timedelta(seconds=1)
                        
                        query_dict['timestamp'] = {
                            "$gte": start_dt.isoformat(),
                            "$lt": end_dt.isoformat()
                        }
                    elif isinstance(ts, str):
                        query_dict['timestamp'] = ts.replace('Z', '')
                except Exception as e:
                    print(f"[Lỗi] Định dạng thời gian: {e}")

        if not query_dict: 
            return "Tôi không xác định được Camera hoặc thời gian bạn cần tra cứu."

        print(f"\n[Hệ thống] Truy vấn thực tế: {query_dict}")

        # 3. Truy xuất và TỔNG HỢP dữ liệu
        try:
            # Sắp xếp tăng dần để dễ tính toán timeline
            cursor = self.collection.find(query_dict).sort("timestamp", 1)
            data_found = list(cursor)
            
            if not data_found:
                return "Hệ thống không tìm thấy dữ liệu Camera phù hợp trong khoảng thời gian này."

            # Khởi tạo đối tượng Aggregation (Gom nhóm dữ liệu)
            summary = {
                "time_range": {
                    "start": data_found[0]['timestamp'].strftime('%H:%M:%S'),
                    "end": data_found[-1]['timestamp'].strftime('%H:%M:%S')
                },
                "max_people": 0,
                "behaviors": {}, 
                "alert_count": 0,
                "notable_moments": [] # Chỉ lưu các mốc quan trọng để tránh quá tải Token
            }

            last_count = -1
            for d in data_found:
                people = d.get("people", [])
                current_count = len(people)
                ts_str = d['timestamp'].strftime('%H:%M:%S')

                # Cập nhật số người tối đa
                if current_count > summary["max_people"]:
                    summary["max_people"] = current_count

                # Theo dõi sự biến động số lượng người
                if current_count != last_count:
                    summary["notable_moments"].append(f"Lúc {ts_str}: Có {current_count} người")
                    last_count = current_count

                # Phân tích hành vi và cảnh báo
                for p in people:
                    b = p.get("behavior", "không xác định")
                    summary["behaviors"][b] = summary["behaviors"].get(b, 0) + 1
                    
                    if p.get("level") == "warning":
                        summary["alert_count"] += 1
                        # Lưu lại mốc thời gian có cảnh báo (nếu chưa lưu)
                        alert_msg = f"Cảnh báo tại {ts_str}"
                        if alert_msg not in summary["notable_moments"]:
                            summary["notable_moments"].append(alert_msg)

            # Giới hạn số lượng notable_moments để AI đọc nhanh hơn
            summary["notable_moments"] = summary["notable_moments"][-10:]

        except Exception as e:
            return f"Lỗi truy vấn cơ sở dữ liệu: {e}"

        # 4. AI Phân tích dựa trên bản tổng hợp
        print(f"[Debug] Dữ liệu gửi cho AI phản hồi: {summary}") # Xem summary có rỗng không
        print("AI Agent: ", end="", flush=True) 
        return self._humanize_response(user_question, summary, stream=stream)