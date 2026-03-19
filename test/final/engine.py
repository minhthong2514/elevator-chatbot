import json, re, os, warnings, ast
from datetime import datetime, timedelta
import urllib.parse
from pymongo import MongoClient
from llama_cpp import Llama
import torch

# Tắt cảnh báo
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
warnings.filterwarnings("ignore", category=UserWarning)

class ElevatorAI:
    def __init__(self):
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"--- Đang khởi động AI trên thiết bị: {device.upper()} ---")

        # 1. Khởi tạo Model GGUF
        self.model_path = "/home/tai/Ung_dung/Code/Python/Thuc_tap/models-gguf/qwen2.5-1.5b-instruct-q4_0.gguf"
        
        if not os.path.exists(self.model_path):
            print(f"LỖI: Không tìm thấy file GGUF tại {self.model_path}")
        
        self.llm = Llama(
            model_path=self.model_path,
            n_ctx=2048,
            n_gpu_layers=-1,      # Đẩy toàn bộ vào GPU Jetson
            verbose=False,
            n_threads=4
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
        
        print("Trợ lý AI GGUF đã sẵn sàng kết nối cơ sở dữ liệu.")

    def _call_ai_query(self, messages):
        """Inference GGUF cho việc trích xuất JSON - Ép độ chính xác cao"""
        prompt = ""
        for msg in messages:
            prompt += f"<|im_start|>{msg['role']}\n{msg['content']}<|im_end|>\n"
        prompt += "<|im_start|>assistant\n"

        output = self.llm(
            prompt,
            max_tokens=150,
            stop=["<|im_end|>", "<|endoftext|>"],
            echo=False,
            temperature=0.1, 
            top_p=0.9
        )
        return output['choices'][0]['text'].strip()

    def _call_ai(self, messages, stream=False):
        """Inference GGUF cho việc viết báo cáo"""
        prompt = ""
        for msg in messages:
            prompt += f"<|im_start|>{msg['role']}\n{msg['content']}<|im_end|>\n"
        prompt += "<|im_start|>assistant\n"

        if stream:
            stream_output = self.llm(
                prompt,
                max_tokens=1024,
                stop=["<|im_end|>", "<|endoftext|>"],
                stream=True,
                temperature=0.5,
                top_p=0.9
            )
            def gen():
                for chunk in stream_output:
                    token = chunk['choices'][0]['text']
                    if token: yield token
            return gen()
        else:
            output = self.llm(
                prompt,
                max_tokens=1024,
                stop=["<|im_end|>", "<|endoftext|>"],
                echo=False,
                temperature=0.5,
                top_p=0.9
            )
            return output['choices'][0]['text'].strip()
    
    def _generate_query(self, user_question):
        """Trích xuất JSON - Cải tiến Prompt tổng quát hóa Intent của người dùng"""
        now = datetime.now()
        current_year = now.year

        processed_question = user_question.lower()
        print(f"[Input] {processed_question}")
        
        # Chuẩn hóa ngày tháng
        date_pattern = r'(\d{1,2})[/-](\d{1,2})(?!\d|/|-)'
        if re.search(date_pattern, processed_question):
            processed_question = re.sub(date_pattern, rf'\1/\2/{current_year}', processed_question)

        today_date = now.strftime("%Y-%m-%d")
        yesterday_date = (now - timedelta(days=1)).strftime("%Y-%m-%d")
        now_full = now.strftime("%Y-%m-%dT%H:%M:%S")

        # SYSTEM PROMPT MỚI: TẬP TRUNG VÀO NGỮ CẢNH (INTENT) THAY VÌ TỪ KHÓA CỨNG
        system_prompt = (
            f"BẠN LÀ MÁY TRÍCH XUẤT THÔNG TIN CAMERA. GIỜ HỆ THỐNG: {now_full}.\n"
            f"Hôm nay: {today_date}. Hôm qua: {yesterday_date}.\n\n"
            "NHIỆM VỤ:\n"
            "1. Chuyển đổi yêu cầu người dùng sang JSON để truy vấn database.\n"
            "2. PHẠM VI HỢP LỆ: Mọi câu hỏi liên quan đến tình hình thang máy, an ninh, hoạt động của con người, "
            "thời gian camera ghi hình, sự cố, hoặc kiểm tra dữ liệu cũ.\n"
            "3. VÍ DỤ CÁCH HỎI TỔNG QUÁT:\n"
            "   - 'Có chuyện gì không?' -> Intent: Kiểm tra an ninh.\n"
            "   - 'Thang máy sao rồi?' -> Intent: Tình trạng camera.\n"
            "   - 'Ai đã vào?' -> Intent: Kiểm tra nhân viên.\n"
            "   - 'Ngày 3/3 có gì lạ?' -> Intent: Truy xuất dữ liệu ngày cụ thể.\n\n"
            "QUY TẮC TRẢ VỀ:\n"
            "- LUÔN trả về JSON: {\"camera_id\": \"CAM_01\", \"timestamp\": {\"$gte\": \"...\", \"$lt\": \"...\"}}\n"
            "- CHỈ trả về {\"error\": \"out_of_scope\"} khi người dùng hỏi về: thời tiết, nấu ăn, kiến thức chung không liên quan camera.\n"
            "- KHÔNG GIẢI THÍCH, CHỈ XUẤT JSON."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Yêu cầu: {processed_question}"}
        ]
        
        raw_res = self._call_ai_query(messages)
        print(f"--- AI RAW RESPONSE (QUERY): {raw_res} ---")

        try:
            # Xử lý chuỗi thô (Giữ nguyên logic fix của bạn)
            clean_res = re.sub(r'```json|```', '', raw_res).strip()
            if clean_res.startswith('{{') and clean_res.endswith('}}'):
                clean_res = clean_res[1:-1]
            clean_res = clean_res.replace('“', '"').replace('”', '"').replace('‘', "'").replace('’', "'")
            
            start_idx = clean_res.find('{')
            end_idx = clean_res.rfind('}')
            
            if start_idx != -1 and end_idx != -1:
                json_str = clean_res[start_idx:end_idx+1]
                
                try:
                    result = json.loads(json_str)
                except Exception:
                    try:
                        result = ast.literal_eval(json_str)
                    except:
                        json_str_fixed = json_str.replace('{{', '{').replace('}}', '}')
                        try:
                            result = json.loads(json_str_fixed)
                        except:
                            return {"error": "out_of_scope"}

                if isinstance(result, dict):
                    if result.get("error") == "out_of_scope":
                        return {"error": "out_of_scope"}
                    
                    # Trích xuất timestamp linh hoạt hơn
                    if "timestamp" in result:
                        raw_ts = result["timestamp"]
                        clean_ts = {str(k).strip(): v for k, v in raw_ts.items()}
                        return {
                            "camera_id": str(result.get("camera_id", "CAM_01")),
                            "timestamp": clean_ts
                        }
                    # Nếu AI chỉ trả về camera_id (do hỏi chung chung)
                    elif "camera_id" in result:
                        return {
                            "camera_id": result["camera_id"],
                            "timestamp": {"$gte": f"{today_date}T00:00:00", "$lt": f"{today_date}T23:59:59"}
                        }
                
            return {"error": "out_of_scope"}
        except Exception as e:
            print(f"Lỗi phân tách JSON: {e}")
            return {"error": "out_of_scope"}
        
    def _humanize_response(self, user_question, summary, stream=False):
        """Giữ nguyên cấu trúc báo cáo đanh thép"""
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
            "BỐI CẢNH QUAN TRỌNG: Hệ thống chỉ truy xuất các trường hợp có dấu hiệu bất thường. "
            "DO ĐÓ: TẤT CẢ nhân viên xuất hiện trong 'DỮ LIỆU GỐC' đều được coi là đối tượng vi phạm hoặc liên quan trực tiếp đến sự cố.\n"
            "QUY TẮC CẤM:\n"
            "1. CẤM in lại tiêu đề 'DỮ LIỆU GỐC', 'NHIỆM VỤ', 'QUY TẮC'.\n"
            "2. CẤM viết lại các câu hướng dẫn, câu ví dụ hay nội dung trong ngoặc đơn.\n"
            "3. CẤM các từ ngữ lịch sự thừa thãi như: 'Xin vui lòng', 'Cần được', 'Hãy', 'Trân trọng', 'Cảm ơn'.\n"
            "4. CẤM liệt kê danh sách xuống dòng ở mục YÊU CẦU HÀNH ĐỘNG.\n"
            f"LƯU Ý THỜI GIAN: Hôm nay là {formatted_date}.\n"
            "QUY TẮC VIẾT:\n"
            "- [TRẠNG THÁI AN NINH]: Viết giá trị trạng thái ngay sau dấu hai chấm.\n"
            "- [CHI TIẾT SỰ KIỆN]: Liệt kê mỗi người một dòng: ghi rõ hành vi, mốc thời gian và chốt trạng thái (BÌNH THƯỜNG hoặc NGUY HIỂM).\n"
            "- [YÊU CẦU HÀNH ĐỘNG]: Phải liệt kê RÕ TÊN TẤT CẢ những người có tên trong danh sách chi tiết vào chung một đoạn văn ngắn gọn duy nhất yêu cầu người quản lý phải kiểm tra gấp vì toàn bộ danh sách này đều bị hệ thống đánh dấu bất thường."
        )

        user_content = (
            f"DỮ LIỆU GỐC (CẤM IN LẠI):\n- Trạng thái: {status_label}\n- Chi tiết: {context_data}\n\n"
            f"HÃY XUẤT BÁO CÁO THEO CẤU TRÚC CHÍNH XÁC NHƯ SAU:\n\n"
            f"DỮ LIỆU ĐƯỢC TRUY XUẤT VÀO NGÀY {formatted_date}, BẮT ĐẦU TỪ {start_t} TỚI {end_t}.\n\n"
            f"[TRẠNG THÁI AN NINH]: {status_label}\n\n"
            f"[THÔNG TIN CHI TIẾT]\n"
            f"(Liệt kê danh sách tại đây)\n\n"
            f"[YÊU CẦU HÀNH ĐỘNG]\n"
            f"(Viết yêu cầu tại đây)"
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
                ts_query = query_dict.get('timestamp', {})
                gte_str = ts_query.get('$gte', '')
                lt_str = ts_query.get('$lt', '')
                
                # Tách ngày và giờ
                try:
                    date_part = gte_str.split('T')[0]
                    display_date = datetime.strptime(date_part, "%Y-%m-%d").strftime("%d-%m-%Y")
                    
                    time_start = gte_str.split('T')[1][:5] if 'T' in gte_str else "00:00"
                    time_end = lt_str.split('T')[1][:5] if 'T' in lt_str else "23:59"
                    
                    if time_start == "00:00" and time_end == "23:59":
                        res = f"Hệ thống hoàn toàn không có dữ liệu camera trong ngày {display_date}."
                    else:
                        res = f"Hệ thống không có dữ liệu camera trong khung giờ từ {time_start} đến {time_end} trong ngày {display_date}."
                except:
                    res = "Hệ thống không có dữ liệu camera trong khoảng thời gian này."
                
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
