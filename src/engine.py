import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer 
import json, re
from pymongo import MongoClient
import urllib.parse
from datetime import datetime, timedelta
import os
import warnings
from threading import Thread 

# Tắt các cảnh báo không cần thiết để log sạch hơn
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
warnings.filterwarnings("ignore", category=UserWarning)

class ElevatorAI:
    def __init__(self):
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"--- Đang khởi động AI trên thiết bị: {device.upper()} ---")

        # 1. Khởi tạo Model
        self.model_path = "/home/tai/Ung_dung/Code/Python/Thuc_tap/models"
        
        print("Đang nạp model với cấu hình tối ưu tốc độ...")
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
        
        # Tối ưu: Sử dụng float16 trên CUDA để tăng tốc độ tính toán
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_path, 
            torch_dtype=torch.float16 if device == "cuda" else torch.float32, 
            device_map="auto",
            low_cpu_mem_usage=True,
            trust_remote_code=True
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

    def _call_ai_query(self, messages):
        """
        Inference tốc độ cao để trích xuất JSON.
        Sử dụng greedy decoding (do_sample=False) để ra kết quả tức thì.
        """
        text = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.tokenizer([text], return_tensors="pt").to(self.model.device)
        
        with torch.no_grad():
            output_ids = self.model.generate(
                **inputs, 
                max_new_tokens=150, 
                do_sample=False,  # Tối ưu: Tắt sampling để nhanh hơn cho JSON
                temperature=0.2, 
                top_p=0.9,
                use_cache=True    # Tối ưu: Bật KV Cache
            )
        return self.tokenizer.batch_decode(output_ids, skip_special_tokens=True)[0].split("assistant")[-1].strip()

    def _call_ai(self, messages, stream=False):
        """
        Hàm gọi AI cho việc viết báo cáo (Humanize).
        Duy trì cấu hình bản cũ nhưng bật use_cache.
        """
        text = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.tokenizer([text], return_tensors="pt").to(self.model.device)
        
        if stream:
            streamer = TextIteratorStreamer(self.tokenizer, skip_prompt=True, skip_special_tokens=True)
            generation_kwargs = dict(
                **inputs, 
                streamer=streamer, 
                max_new_tokens=1024,
                do_sample=True, 
                temperature=0.5, 
                top_p=0.9,
                use_cache=True # Tối ưu: Bật KV Cache
            )
            thread = Thread(target=self.model.generate, kwargs=generation_kwargs)
            thread.start()
            return streamer 
        else:
            with torch.no_grad():
                output_ids = self.model.generate(
                    **inputs, 
                    max_new_tokens=1024, 
                    do_sample=True, 
                    temperature=0.5,
                    top_p=0.9,
                    use_cache=True # Tối ưu: Bật KV Cache
                )
            return self.tokenizer.batch_decode(output_ids, skip_special_tokens=True)[0].split("assistant")[-1].strip()
    
    def _generate_query(self, user_question):
        now = datetime.now()
        current_year = now.year

        processed_question = user_question
        date_pattern = r'(\d{1,2})[/-](\d{1,2})(?!\d|/|-)'
        if re.search(date_pattern, user_question):
            processed_question = re.sub(date_pattern, rf'\1/\2/{current_year}', user_question)

        today_date = now.strftime("%Y-%m-%d")
        yesterday_date = (now - timedelta(days=1)).strftime("%Y-%m-%d")
        now_full = now.strftime("%Y-%m-%dT%H:%M:%S")
        day_of_week = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"][now.weekday()]

        system_prompt = (
            f"BẠN LÀ CHUYÊN VIÊN TRÍCH XUẤT DỮ LIỆU CAMERA TRONG THANG MÁY.\n"
            f"GIỜ HỆ THỐNG: {now_full}.\n"
            f"THÔNG TIN LỊCH: Hôm nay là {day_of_week}, ngày {today_date}. Ngày hôm qua là {yesterday_date}.\n\n"

            "QUY TẮC PHÂN LOẠI (BẮT BUỘC TUÂN THỦ):\n"
            "1. CHỈ tạo JSON khi câu hỏi chứa từ khóa chuyên môn: camera, an ninh, sự cố, thang máy, kiểm tra người (ngã, nằm, ngồi, đột nhập), báo cáo.\n"
            "2. MỌI CÂU HỎI KHÁC (Chào hỏi, thời tiết, tán gẫu, hỏi đáp kiến thức...): CẤM phân tích thời gian, CẤM tạo JSON truy vấn. PHẢI TRẢ VỀ DUY NHẤT: {\"error\": \"out_of_scope\"}.\n"
            "3. CẤM tự chế thêm trường (key) như 'query', 'topic', 'message'. Chỉ được phép trả về 'camera_id' và 'timestamp'.\n\n"

            "VÍ DỤ NGOÀI LỀ (PHẢI TRẢ VỀ OUT_OF_SCOPE):\n"
            "- 'xin chào', 'hello', 'hi' -> {\"error\": \"out_of_scope\"}\n"
            "- 'thời tiết hôm nay', 'bạn là ai', 'ăn cơm chưa' -> {\"error\": \"out_of_scope\"}\n"
            "- 'thời tiết ngày 3/3 thế nào' -> {\"error\": \"out_of_scope\"}\n\n"

            "VÍ DỤ TRUY VẤN HỢP LỆ (TRẢ VỀ JSON):\n"
            f"- 'tình hình thang máy ngày 3/3' -> {{\"camera_id\": \"CAM_01\", \"timestamp\": {{\" $gte\": \"{current_year}-03-03T00:00:00\", \"$lt\": \"{current_year}-03-03T23:59:59\"}}}}\n"
            f"- 'an ninh hôm qua thế nào' -> {{\"camera_id\": \"CAM_01\", \"timestamp\": {{\" $gte\": \"{yesterday_date}T00:00:00\", \"$lt\": \"{yesterday_date}T23:59:59\"}}}}\n\n"

            "YÊU CẦU ĐỊNH DẠNG:\n"
            "1. CAMERA ID: Luôn là \"CAM_01\".\n"
            f"2. NĂM MẶC ĐỊNH: Luôn dùng {current_year}.\n"
            "3. CHỈ TRẢ VỀ JSON THUẦN TÚY, KHÔNG DÙNG DẤU NHÁY ``` CŨNG KHÔNG GIẢI THÍCH."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Chuyển câu sau sang JSON: {processed_question}"}
        ]
        
        raw_res = self._call_ai_query(messages)
        print(f"--- AI RAW RESPONSE (QUERY): {raw_res} ---")

        try:
            clean_res = re.sub(r'```json|```', '', raw_res).strip()
            match = re.search(r'\{.*\}', clean_res, re.DOTALL)
            
            if match:
                json_str = match.group(0).replace("'", '"')
                result = json.loads(json_str)
                
                if "camera_id" in result and "timestamp" in result:
                    return {
                        "camera_id": "CAM_01",
                        "timestamp": result["timestamp"]
                    }
                
                if result.get("error") == "out_of_scope":
                    return {"error": "out_of_scope"}
            
            return {"error": "out_of_scope"}
            
        except Exception as e:
            print(f"Lỗi phân tách JSON: {e}")
            return {"error": "out_of_scope"}
        
    def _humanize_response(self, user_question, summary, stream=False):
        raw_date = summary.get('date', 'N/A')
        formatted_date = "/".join(raw_date.split("-")[::-1])
        start_t = summary['time_range']['start']
        end_t = summary['time_range']['end']
        context_data = "\n".join(summary['details'])
        
        is_urgent = summary.get('is_emergency', False)
        status_label = "CẢNH BÁO NGUY HIỂM - XUẤT HIỆN HÀNH VI BẤT THƯỜNG" if is_urgent else "BÌNH THƯỜNG"

        system_prompt = (
            "BẠN LÀ TRỢ LÝ GIÁM SÁT AN NINH THANG MÁY - NGÔN NGỮ TRỰC TIẾP, ĐANH THÉP.\n"
            "NHIỆM VỤ: Lập báo cáo từ dữ liệu camera. Tuyệt đối không mâu thuẫn dữ liệu.\n"
            "QUY TẮC CẤM:\n"
            "1. CẤM viết lại các câu hướng dẫn, câu ví dụ hay nội dung trong ngoặc đơn.\n"
            "2. CẤM các từ ngữ lịch sự thừa thãi như: 'Xin vui lòng', 'Cần được', 'Hãy', 'Trân trọng', 'Cảm ơn'.\n"
            "3. CẤM liệt kê danh sách xuống dòng ở mục YÊU CẦU HÀNH ĐỘNG.\n"
            f"LƯU Ý THỜI GIAN: Hôm nay là {formatted_date}.\n"
            "QUY TẮC VIẾT:\n"
            "- [TRẠNG THÁI AN NINH]: Viết giá trị trạng thái ngay sau dấu hai chấm.\n"
            "- [CHI TIẾT SỰ KIỆN]: Liệt kê mỗi người một dòng: ghi rõ hành vi, mốc thời gian và chốt trạng thái (BÌNH THƯỜNG hoặc NGUY HIỂM).\n"
            "- [YÊU CẦU HÀNH ĐỘNG]: Phải liệt kê RÕ TÊN TẤT CẢ những người có hành vi 'warning' hoặc 'xác định bất thường' vào chung một đoạn văn ngắn gọn duy nhất yêu cầu nguời quản lý phải kiểm tra gấp."        
        )

        user_content = (
            f"DỮ LIỆU GỐC (CẤM IN LẠI):\n- Trạng thái: {status_label}\n- Chi tiết: {context_data}\n\n"
            f"HÃY XUẤT BÁO CÁO THEO CẤU TRÚC CHÍNH XÁC NHƯ SAU:\n\n"
            f"DỮ LIỆU ĐƯỢC TRUY XUẤT VÀO NGÀY {formatted_date}, BẮT ĐẦU TỪ {start_t} TỚI {end_t}.\n\n"
            f"[TRẠNG THÁI AN NINH]: {status_label}\n\n"
            f"[THÔNG TIN CHI TIẾT]\n"
            f"{{Điền danh sách chi tiết các cá nhân ở đây}}\n\n"
            f"[YÊU CẦU HÀNH ĐỘNG]\n\n"
        )

        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_content}]
        return self._call_ai(messages, stream=stream)
    
    def ask(self, user_question, stream=False):
        def error_generator(msg):
            yield msg

        q_lower = user_question.lower()
        greetings = ["chào", "hi", "hello", "xin chào", "hey"]
        out_of_scope_topics = ["thời tiết", "mưa", "nắng", "nhiệt độ", "ăn cơm", "bạn là ai"]
        
        if any(word in q_lower for word in greetings) and len(user_question.split()) < 5:
            res = ("Xin chào! Tôi là trợ lý AI giám sát an ninh thang máy.\n"
                   "Tôi đã sẵn sàng hỗ trợ. Bạn cần tôi trích xuất dữ liệu camera hay kiểm tra sự cố vào mốc thời gian nào?")
            return error_generator(res) if stream else res
            
        if any(topic in q_lower for topic in out_of_scope_topics):
            res = ("Tôi là trợ lý AI giám sát camera thang máy. Hiện tại tôi không có dữ liệu về các vấn đề ngoài lề.\n"
                   "Vui lòng đặt câu hỏi liên quan đến tình hình an ninh hoặc trích xuất dữ liệu camera.")
            return error_generator(res) if stream else res

        query_dict = self._generate_query(user_question)

        if not isinstance(query_dict, dict):
            query_dict = {"error": "out_of_scope"}

        if query_dict.get("error") == "out_of_scope" or "message" in query_dict or "query" in query_dict:
            res = ("Tôi là trợ lý AI giám sát camera thang máy. Hiện tại tôi không có dữ liệu về các vấn đề ngoài lề.\n"
                   "Vui lòng đặt câu hỏi liên quan đến an ninh thang máy.")
            return error_generator(res) if stream else res
        
        if "timestamp" not in query_dict:
            res = "Tôi không xác định được mốc thời gian. Vui lòng nói rõ ngày/giờ cần kiểm tra."
            return error_generator(res) if stream else res
        
        try:
            # Tối ưu: Chỉ fetch các trường cần thiết từ MongoDB
            cursor = self.collection.find(
                query_dict, 
                {"timestamp": 1, "people": 1}
            ).sort("timestamp", 1)
            
            data_found = list(cursor)
            
            if not data_found:
                gte_str = query_dict.get('timestamp', {}).get('$gte', '')
                date_raw = gte_str.split('T')[0] if 'T' in gte_str else gte_str
                try:
                    date_obj = datetime.strptime(date_raw, "%Y-%m-%d")
                    display_date = date_obj.strftime("%d-%m-%Y")
                except:
                    display_date = date_raw
                
                res = f"Hệ thống hoàn toàn không có dữ liệu camera trong ngày {display_date}."
                return error_generator(res) if stream else res   
            
            first_ts_str = data_found[0]['timestamp'] 
            record_date = first_ts_str.split('T')[0]
            warns_info = {} 

            for d in data_found:
                full_ts = d['timestamp']
                ts_short = full_ts.split('T')[-1] 
                people = d.get("people", [])
                for p in people:
                    p_id = p.get("person_id")
                    behavior = p.get("behavior", "unknown")
                    level = p.get("level", "warning" if p.get("level") == "warning" else "normal")
                    
                    if p_id not in warns_info:
                        warns_info[p_id] = {
                            "first_seen": ts_short,
                            "warning_start": ts_short if level == "warning" else None,
                            "last_seen": ts_short,
                            "behavior": behavior,
                            "is_warning": (level == "warning")
                        }
                    else:
                        warns_info[p_id]["last_seen"] = ts_short
                        if level == "warning":
                            warns_info[p_id]["is_warning"] = True
                            if warns_info[p_id]["warning_start"] is None:
                                warns_info[p_id]["warning_start"] = ts_short

            actual_details = []
            for p_id in sorted(warns_info.keys()):
                info = warns_info[p_id]
                display_id = str(p_id)
                if info['warning_start'] == info['first_seen'] or info['warning_start'] is None:
                    detail = f"Nhân viên {display_id}: Ghi nhận từ {info['first_seen']} đến {info['last_seen']}."
                else:
                    detail = f"Nhân viên {display_id}: Xuất hiện từ {info['first_seen']}, xác định bất thường từ {info['warning_start']} đến {info['last_seen']}."
                actual_details.append(detail)

            summary = {
                "date": record_date,
                "time_range": {"start": first_ts_str.split('T')[-1], "end": data_found[-1]['timestamp'].split('T')[-1]},
                "details": actual_details,
                "is_emergency": any(item['is_warning'] for item in warns_info.values())
            }

            print(f"[Debug] Dữ liệu gửi cho AI phản hồi: {summary}")
            return self._humanize_response(user_question, summary, stream=stream)

        except Exception as e:
            print(f"[Error] Lỗi: {e}")
            res = "Đã xảy ra lỗi trong quá trình xử lý dữ liệu."
            return error_generator(res) if stream else res