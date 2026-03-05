import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer # SỬA: Dùng IteratorStreamer
import json, re
from pymongo import MongoClient
import urllib.parse
from datetime import datetime, timedelta
import os
import warnings
from threading import Thread # THÊM: Để chạy stream song song

# --- TẮT CẢNH BÁO ---
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
warnings.filterwarnings("ignore", category=UserWarning)

class ElevatorAI:
    def __init__(self):
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"--- Đang khởi động AI trên thiết bị: {device.upper()} ---")

        # 1. Khởi tạo Model
        self.model_path = "/media/minhthong/DATA/University/Nam_tu/TTTN/models"
        
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
            # SỬA: Dùng TextIteratorStreamer để đẩy dữ liệu ra Web thay vì in tại chỗ
            streamer = TextIteratorStreamer(self.tokenizer, skip_prompt=True, skip_special_tokens=True)
            generation_kwargs = dict(
                **inputs, 
                streamer=streamer, 
                max_new_tokens=1024, # Tăng lên để báo cáo không bị cụt
                do_sample=True, 
                temperature=0.2, 
                top_p=0.9
            )
            thread = Thread(target=self.model.generate, kwargs=generation_kwargs)
            thread.start()
            return streamer 
        else:
            # Chế độ bình thường (không stream) - GIỮ NGUYÊN
            output_ids = self.model.generate(
                **inputs, 
                max_new_tokens=1024, 
                do_sample=True, 
                temperature=0.2,
                top_p=0.9
            )
            return self.tokenizer.batch_decode(output_ids, skip_special_tokens=True)[0].split("assistant")[-1].strip()
    
    def _generate_query(self, user_question):
        now = datetime.now()
        current_year = now.year

        processed_question = user_question
        date_pattern = r'(\d{1,2})[/-](\d{1,2})(?!\d|/|-)'
        if re.search(date_pattern, user_question):
            # Nếu tìm thấy ngày/tháng mà không có năm đi kèm, ta nối thêm năm hiện tại
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
        
        raw_res = self._call_ai(messages)
        print(f"--- AI RAW RESPONSE: {raw_res} ---")

        try:
            # Làm sạch phản hồi từ AI
            clean_res = re.sub(r'```json|```', '', raw_res).strip()
            match = re.search(r'\{.*\}', clean_res, re.DOTALL)
            
            if match:
                json_str = match.group(0).replace("'", '"')
                result = json.loads(json_str)
                
                # --- LỚP BẢO VỆ: CHỈ GIỮ LẠI CÁC TRƯỜNG HỢP LỆ CHO MONGODB ---
                if "camera_id" in result and "timestamp" in result:
                    return {
                        "camera_id": "CAM_01", # Ép cứng ID tại đây cho an toàn tuyệt đối
                        "timestamp": result["timestamp"]
                    }
                
                # Trường hợp AI trả về out_of_scope dạng JSON
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
            "- [YÊU CẦU HÀNH ĐỘNG]: Phải liệt kê TẤT CẢ các mã số người có hành vi 'nằm trên sàn' hoặc 'xác định bất thường' vào chung một đoạn văn ngắn gọn duy nhất yêu cầu nguời quản lý phải kiểm tra gấp."        
        )

        user_content = (
            f"DỮ LIỆU GỐC (CẤM IN LẠI):\n- Trạng thái: {status_label}\n- Chi tiết: {context_data}\n\n"
            f"HÃY XUẤT BÁO CÁO THEO CẤU TRÚC CHÍNH XÁC NHƯ SAU:\n\n"
            f"DỮ LIỆU ĐƯỢC TRUY XUẤT VÀO NGÀY {formatted_date}, BẮT ĐẦU TỪ {start_t} TỚI {end_t}.\n\n"
            f"[TRẠNG THÁI AN NINH]: {status_label}\n\n"
            f"[THÔNG TIN CHI TIẾT]\n"
            f"{{Điền danh sách chi tiết các cá nhân ở đây}}\n\n"
            f"[YÊU CẦU HÀNH ĐỘNG]\n\n"
            # f"YÊU CẦU CAN THIỆP KHẨN CẤP NGAY ĐỐI VỚI: "
        )

        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_content}]
        return self._call_ai(messages, stream=stream)
    
    def ask(self, user_question, stream=False):
        # 1. Lấy Query từ AI - GIỮ NGUYÊN
        query_dict = self._generate_query(user_question)

        # CHỐT CHẶN AN TOÀN - GIỮ NGUYÊN
        if not isinstance(query_dict, dict):
            if isinstance(query_dict, str) and "out_of_scope" in query_dict:
                query_dict = {"error": "out_of_scope"}
            else:
                query_dict = {"error": "unknown_type"}

        # Xử lý trường hợp lỗi khi gọi Stream
        def error_generator(msg):
            yield msg

        # 2. Xử lý trường hợp câu hỏi ngoài phạm vi 
        if query_dict.get("error") == "out_of_scope" or "message" in query_dict or "query" in query_dict:
            q_lower = user_question.lower()
            greetings = ["chào", "hi", "hello", "xin chào", "hey"]
            
            # 1. Kiểm tra nếu là lời chào
            if any(word in q_lower for word in greetings):
                res = ("Xin chào! Tôi là trợ lý AI giám sát an ninh thang máy.\n"
                       "Tôi đã sẵn sàng hỗ trợ. Bạn cần tôi trích xuất dữ liệu camera hay kiểm tra sự cố vào mốc thời gian nào?")
            
            # 2. Nếu không phải chào hỏi (ví dụ hỏi thời tiết, linh tinh) thì mới hiện danh sách quy định
            else:
                res = ("Tôi là trợ lý AI giám sát camera thang máy. Hiện tại tôi không có dữ liệu về các vấn đề ngoài lề .\n"
                       "Tôi chỉ chuyên trách các mục sau:\n"
                       "- Tình hình an ninh/sự cố.\n"
                       "- Các hành vi bất thường (nằm, ngồi, ngã).\n"
                       "- Truy xuất dữ liệu theo ngày/giờ cụ thể.\n\n"
                       "Vui lòng đặt câu hỏi liên quan đến an ninh thang máy.")
            
            return error_generator(res) if stream else res
        
        if "timestamp" not in query_dict:
            res = "Tôi không xác định được mốc thời gian bạn cần. Vui lòng nói rõ hơn (ví dụ: sáng nay, hôm qua)."
            return error_generator(res) if stream else res
        
        translate_behavior = {
            "sitting": "đang ngồi", "standing": "đang đứng", "lying": "đang nằm trên sàn", "fallen": "bị ngã", "unknown": "không xác định"
        }

        try:
            # 1. Truy vấn theo khung giờ cụ thể người dùng yêu cầu
            cursor = self.collection.find(query_dict).sort("timestamp", 1)
            data_found = list(cursor)
            
            if not data_found:
                # Trích xuất thông tin thời gian từ query để xử lý thông báo
                gte_str = query_dict.get('timestamp', {}).get('$gte', '')
                lt_str = query_dict.get('timestamp', {}).get('$lt', '')
                
                date_raw = gte_str.split('T')[0] if 'T' in gte_str else gte_str
                
                # Đảo định dạng ngày sang DD-MM-YYYY để hiển thị
                try:
                    parts = date_raw.split("-")
                    date_display = f"{parts[2]}-{parts[1]}-{parts[0]}" if len(parts) == 3 else date_raw
                except:
                    date_display = date_raw

                # --- BỔ SUNG: KIỂM TRA DỮ LIỆU TOÀN BỘ NGÀY ---
                day_check_query = {
                    "camera_id": query_dict.get("camera_id", "CAM_01"),
                    "timestamp": {
                        "$gte": f"{date_raw}T00:00:00",
                        "$lt": f"{date_raw}T23:59:59"
                    }
                }
                # Chỉ tìm 1 bản ghi bất kỳ trong ngày đó để xác nhận sự tồn tại của dữ liệu
                has_any_data_that_day = self.collection.find_one(day_check_query)

                if has_any_data_that_day:
                    # Trường hợp: Có dữ liệu trong ngày nhưng không có trong khung giờ yêu cầu
                    start_t = gte_str.split('T')[1][:5] if 'T' in gte_str else "giờ bắt đầu"
                    end_t = lt_str.split('T')[1][:5] if 'T' in lt_str else "giờ kết thúc"
                    
                    res = f"Trong ngày {date_display}, hệ thống có dữ liệu nhưng không ghi nhận hoạt động nào trong khung giờ từ {start_t} đến {end_t}."
                else:
                    # Trường hợp: Hoàn toàn không có dữ liệu cho cả ngày đó
                    res = f"Hệ thống không tìm thấy bất kỳ dữ liệu camera nào trong ngày {date_display}."
                
                return error_generator(res) if stream else res   
            
            # --- GIỮ NGUYÊN TOÀN BỘ LOGIC XỬ LÝ DATA PHÍA DƯỚI ---
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
                    level = p.get("level", "normal")
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
                vi_behavior = translate_behavior.get(info['behavior'], info['behavior'])
                if info['warning_start'] == info['first_seen'] or info['warning_start'] is None:
                    detail = f"Người {p_id:02d} ({vi_behavior}): Ghi nhận từ {info['first_seen']} đến {info['last_seen']}."
                else:
                    detail = f"Người {p_id:02d} ({vi_behavior}): Xuất hiện từ {info['first_seen']}, chính thức xác định bất thường từ {info['warning_start']} đến {info['last_seen']}."
                actual_details.append(detail)

            summary = {
                "date": record_date,
                "time_range": {"start": first_ts_str.split('T')[-1], "end": data_found[-1]['timestamp'].split('T')[-1]},
                "details": actual_details,
                "is_emergency": any(item['is_warning'] for item in warns_info.values())
            }

        except Exception as e:
            print(f"[Error] Lỗi truy xuất: {e}")
            res = "Đã xảy ra lỗi trong quá trình truy xuất dữ liệu an ninh."
            return error_generator(res) if stream else res
        
        print(f"[Debug] Dữ liệu gửi cho AI phản hồi: {summary}")
        return self._humanize_response(user_question, summary, stream=stream)

