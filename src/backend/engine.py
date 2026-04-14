import json, re, os, warnings, ast
from datetime import datetime, timedelta
import urllib.parse
from pymongo import MongoClient
from llama_cpp import Llama
import torch
from dotenv import load_dotenv

load_dotenv()
# Tắt cảnh báo
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
warnings.filterwarnings("ignore", category=UserWarning)

class ElevatorAI:
    def __init__(self):
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"--- Đang khởi động AI trên thiết bị: {device.upper()} ---")

        # 1. Khởi tạo Model GGUF
        self.model_path = os.getenv("MODEL_CHATBOT_PATH")
        
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
        db_user = (os.getenv("MONGO_USER") or os.getenv("USER")).strip().replace('"', '')
        db_pass = os.getenv("PASSWORD", "").strip().replace('"', '')
        cluster_url = os.getenv("CLUSTER_URL", "").strip().replace('"', '')
        
        db_name = os.getenv("DB", "iot_project").strip().replace('"', '')
        collection_name = os.getenv("COLLECTION", "human_behavior").strip().replace('"', '')

        # Mã hóa mật khẩu an toàn cho URL
        safe_pass = urllib.parse.quote_plus(db_pass)
        
        # Xây dựng URI chuẩn
        self.uri = f"mongodb+srv://{db_user}:{safe_pass}@{cluster_url}/?retryWrites=true&w=majority&appName=test-model"
        self.client = MongoClient(self.uri, serverSelectionTimeoutMS=5000)
        self.client.admin.command('ping')
        self.db = self.client[db_name]
        self.collection = self.db[collection_name]
        print("Trợ lý AI GGUF đã sẵn sàng.")


    def _call_ai_query(self, messages):
        """Inference GGUF cho việc trích xuất JSON - Ép độ chính xác cao"""
        # ... (Giữ nguyên tuyệt đối phần này) ...
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
        # ... (Giữ nguyên tuyệt đối phần này) ...
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
        """Trích xuất JSON - Điều chỉnh mapping theo cấu trúc start_time mới"""
        now = datetime.now()
        current_year = now.year

        processed_question = user_question.lower()
        print(f"[Input] {processed_question}")
        
        date_pattern = r'(\d{1,2})[/-](\d{1,2})(?!\d|/|-)'
        if re.search(date_pattern, processed_question):
            processed_question = re.sub(date_pattern, rf'\1/\2/{current_year}', processed_question)

        today_date = now.strftime("%Y-%m-%d")
        yesterday_date = (now - timedelta(days=1)).strftime("%Y-%m-%d")
        now_full = now.strftime("%Y-%m-%dT%H:%M:%S")

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
            "- LUÔN trả về JSON: {\"camera_id\": \"CAM_01\", \"start_time\": {\"$gte\": \"...\", \"$lt\": \"...\"}}\n"
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
            clean_res = re.sub(r'```json|```', '', raw_res).strip()
            start_idx = clean_res.find('{')
            end_idx = clean_res.rfind('}')
            
            if start_idx != -1 and end_idx != -1:
                json_str = clean_res[start_idx:end_idx+1]
                result = ast.literal_eval(json_str) if "{" in json_str else json.loads(json_str)

                if isinstance(result, dict):
                    if result.get("error") == "out_of_scope":
                        return {"error": "out_of_scope"}
                    
                    query_time_key = "start_time" if "start_time" in result else "timestamp"
                    time_val = result.get(query_time_key)

                    return {
                        "camera_id": str(result.get("camera_id", "CAM_01")),
                        "start_time": time_val if time_val else {"$gte": f"{today_date}T00:00:00", "$lt": f"{today_date}T23:59:59"}
                    }
                
            return {"error": "out_of_scope"}
        except Exception:
            return {"error": "out_of_scope"}
        
    def _humanize_response(self, user_question, summary, stream=False):
        """Phân loại phản hồi linh hoạt dựa trên tình trạng an ninh"""
        raw_date = summary.get('date', 'N/A')
        formatted_date = "/".join(raw_date.split("-")[::-1])
        start_t = summary['time_range']['start']
        end_t = summary['time_range']['end']
        
        is_urgent = summary.get('is_emergency', False)
        total_p = summary.get('total_people', 0)
        total_w = summary.get('total_warnings', 0)

        # TRƯỜNG HỢP 1: BÌNH THƯỜNG - TRẢ VỀ CỰC KỲ NGẮN GỌN
        if not is_urgent:
            system_prompt = "BẠN LÀ TRỢ LÝ GIÁM SÁT AN NINH THANG MÁY. PHẢN HỒI CỰC KỲ NGẮN GỌN BẰNG TIẾNG VIỆT TRONG 2 DÒNG."
            user_content = (
                f"DỮ LIỆU ĐƯỢC TRUY XUẤT VÀO NGÀY {formatted_date}, BẮT ĐẦU TỪ {start_t} TỚI {end_t}.\n"
                f"[TRẠNG THÁI AN NINH]: BÌNH THƯỜNG (Ghi nhận {total_p} người vào, {total_w} sự cố) - HỆ THỐNG AN TOÀN."
            )
            messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_content}]
            return self._call_ai(messages, stream=stream)

        # TRƯỜNG HỢP 2: CÓ SỰ CỐ - GIỮ NGUYÊN PROMPT ĐANH THÉP
        context_data = "\n".join(summary['details'])
        status_label = f"CẢNH BÁO NGUY HIỂM ({total_p} người đã vào | {total_w} hành vi bất thường)"

        system_prompt = (
            "BẠN LÀ TRỢ LÝ GIÁM SÁT AN NINH THANG MÁY - NGÔN NGỮ TIẾNG VIỆT TRỰC TIẾP, ĐANH THÉP, CHUYÊN NGHIỆP.\n"
            "NHIỆM VỤ: Lập báo cáo từ dữ liệu camera. Tuyệt đối không mâu thuẫn dữ liệu.\n"
            "QUY TẮC QUAN TRỌNG:\n"
            "1. LUÔN LUÔN trả lời bằng TIẾNG VIỆT 100%. Dịch tất cả các từ tiếng Anh sang tiếng Việt (vd: sitting -> đang ngồi, lying -> đang nằm).\n"
            "2. CẤM sử dụng các cụm từ: 'DỮ LIỆU GỐC', 'GIAO BÁO', 'TRUY XUẤY' (phải dùng TRUY XUẤT).\n"
            "3. CẤM các từ ngữ lịch sự thừa thãi, CẤM lặp từ gây khó hiểu.\n"
            "4. CẤM liệt kê danh sách xuống dòng ở mục YÊU CẦU HÀNH ĐỘNG.\n"
            f"LƯU Ý THỜI GIAN: Hôm nay là {formatted_date}.\n"
            "QUY TẮC VIẾT:\n"
            "- [TRẠNG THÁI AN NINH]: Viết giá trị trạng thái bao gồm cả thông số người và cảnh báo ngay sau dấu hai chấm.\n"
            "- [THÔNG TIN CHI TIẾT]: Liệt kê mỗi người một dòng: ghi rõ hành vi (SỬ DỤNG TIẾNG VIỆT), mốc thời gian và chốt trạng thái (BÌNH THƯỜNG hoặc NGUY HIỂM).\n"
            "- [YÊU CẦU HÀNH ĐỘNG]: Viết một đoạn văn ngắn gọn, rõ ràng, yêu cầu kiểm tra đối tượng nghi vấn ngay lập tức. Không dùng ngôn ngữ máy móc lặp lại."
        )

        user_content = (
            f"Thông tin truy xuất:\n- Trạng thái: {status_label}\n- Chi tiết: {context_data}\n\n"
            f"HÃY XUẤT BÁO CÁO THEO CẤU TRÚC CHÍNH XÁC NHƯ SAU (BẰNG TIẾNG VIỆT):\n\n"
            f"DỮ LIỆU ĐƯỢC TRUY XUẤT VÀO NGÀY {formatted_date}, BẮT ĐẦU TỪ {start_t} TỚI {end_t}.\n\n"
            f"[TRẠNG THÁI AN NINH]: {status_label}\n\n"
            f"[THÔNG TIN CHI TIẾT]\n"
            f"(Liệt kê danh sách tại đây, đảm bảo dịch Sitting/Lying sang tiếng Việt)\n\n"
            f"[YÊU CẦU HÀNH ĐỘNG]\n"
            f"(Viết yêu cầu tại đây - Ngắn gọn, đanh thép, không lặp từ)"
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
                res = "Xin chào! Tôi là trợ lý AI giám sát an ninh thang máy. Tôi đã sẵn sàng hỗ trợ."
                return error_generator(res) if stream else res
                
            if any(topic in q_lower for topic in out_of_scope_topics):
                res = "Tôi là trợ lý AI giám sát camera thang máy. Vui lòng đặt câu hỏi liên quan đến an ninh."
                return error_generator(res) if stream else res

            query_dict = self._generate_query(user_question)

            if query_dict.get("error") == "out_of_scope":
                res = "Vui lòng đặt câu hỏi liên quan đến an ninh hoặc trích xuất dữ liệu camera."
                return error_generator(res) if stream else res
            
            if "start_time" not in query_dict:
                res = "Tôi không xác định được mốc thời gian. Vui lòng nói rõ ngày/giờ cần kiểm tra."
                return error_generator(res) if stream else res
            
            try:
                cursor = self.collection.find(query_dict, {"start_time": 1, "end_time": 1, "analysis": 1}).sort("start_time", 1)
                data_found = list(cursor)
                if not data_found: return error_generator("Không tìm thấy dữ liệu.") if stream else "Không tìm thấy dữ liệu."
                
                record_date = data_found[0]['start_time'].split('T')[0]
                max_end_time = data_found[-1]['end_time'].split('T')[-1]
                warns_info = {} 

                for doc in data_found:
                    analysis = doc.get("analysis", {})
                    for sec_key in sorted(analysis.keys()):
                        for p in analysis[sec_key]:
                            p_id = str(p.get("person_id"))
                            level = p.get("level", "normal")
                            bh = str(p.get("behavior", "normal")).lower()
                            vn_bh = "đang ngồi" if "sit" in bh else "đang nằm" if "ly" in bh else "đang đứng"

                            if p_id not in warns_info:
                                warns_info[p_id] = {
                                    "first_seen": sec_key,
                                    "last_seen": sec_key,
                                    "warning_start": sec_key if level == "warning" else None,
                                    "warning_end": sec_key if level == "warning" else None,
                                    "behavior": vn_bh,
                                    "is_warning_now": (level == "warning"),
                                    "ever_warned": (level == "warning")
                                }
                            else:
                                warns_info[p_id]["last_seen"] = sec_key
                                if level == "warning":
                                    warns_info[p_id]["ever_warned"] = True
                                    if warns_info[p_id]["warning_start"] is None:
                                        warns_info[p_id]["warning_start"] = sec_key
                                    warns_info[p_id]["warning_end"] = sec_key
                                    warns_info[p_id]["behavior"] = vn_bh
                                    warns_info[p_id]["is_warning_now"] = True
                                else:
                                    warns_info[p_id]["is_warning_now"] = False

                actual_details = []
                warning_count = 0
                for p_id in sorted(warns_info.keys(), key=lambda x: int(x) if x.isdigit() else x):
                    info = warns_info[p_id]
                    if info['ever_warned']:
                        warning_count += 1
                        # Nếu lúc cuối cùng (max_end_time) trạng thái đã là bình thường (is_warning_now = False)
                        # thì thời gian kết thúc hành vi là warning_end, không phải last_seen
                        if not info['is_warning_now'] or info['warning_end'] != max_end_time:
                            time_desc = f"bắt đầu lúc {info['warning_start']} và đã kết thúc lúc {info['warning_end']}"
                        else:
                            time_desc = f"bắt đầu lúc {info['warning_start']} và vẫn đang tiếp diễn"
                        
                        actual_details.append(f"- Nhân viên {p_id}: Phát hiện {info['behavior']} bất thường, {time_desc} - NGUY HIỂM")
                    else:
                        actual_details.append(f"- Nhân viên {p_id}: Hoạt động bình thường từ {info['first_seen']} đến {info['last_seen']}.")

                summary = {
                    "date": record_date,
                    "time_range": {"start": data_found[0]['start_time'].split('T')[-1], "end": max_end_time},
                    "total_people": len(warns_info),
                    "total_warnings": warning_count,
                    "details": actual_details,
                    "is_emergency": warning_count > 0
                }
                return self._humanize_response(user_question, summary, stream=stream)
            except Exception as e:
                return error_generator(f"Lỗi: {e}") if stream else f"Lỗi: {e}"