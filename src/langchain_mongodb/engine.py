import torch
import os
import warnings
import urllib.parse
import re
import json
from datetime import datetime, timezone

from pymongo import MongoClient
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
from langchain_huggingface import HuggingFacePipeline, HuggingFaceEmbeddings
from langchain_mongodb import MongoDBAtlasVectorSearch
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda, RunnableParallel

# Tắt các cảnh báo không cần thiết
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
warnings.filterwarnings("ignore", category=UserWarning)

class ElevatorAI:
    def __init__(self):
        # 1. Khởi tạo Model & Tokenizer cho LLM
        self.model_path = "/media/minhthong/DATA/University/Nam_tu/TTTN/models"
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                torch_dtype="auto",
                device_map="auto"
            )
            print("--- Model và Tokenizer đã sẵn sàng ---")
        except Exception as e:
            print(f"Lỗi khởi tạo Model: {e}")
            raise e
        
        # Pipelines cho LangChain
        query_pipe = pipeline(
            "text-generation",
            model=self.model,
            tokenizer=self.tokenizer,
            max_new_tokens=150,
            temperature=0.1,
            do_sample=False,
            top_p=0.9,
            return_full_text=False
        )
        self.llm_query = HuggingFacePipeline(pipeline=query_pipe)

        report_pipe = pipeline(
            "text-generation",
            model=self.model,
            tokenizer=self.tokenizer,
            max_new_tokens=512,
            temperature=0.3,
            do_sample=True,
            top_p=0.9,
            return_full_text=False
        )
        self.llm_report = HuggingFacePipeline(pipeline=report_pipe)

        # 2. Khởi tạo Embedding Model
        try:
            # Lưu ý: Model này tạo ra vector 384 chiều, khớp với cấu hình Index của bạn
            self.embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
            print("--- Embedding Model đã sẵn sàng ---")
        except Exception as e:
            print(f"Lỗi khởi tạo Embeddings: {e}")
            raise e
        
        # 3. Kết nối MongoDB
        USER = "buiminhtai1234"
        PASSWORD = "191104"
        CLUSTER_URL = "cluster0.ydqe2ve.mongodb.net"
        self.uri = f"mongodb+srv://{USER}:{urllib.parse.quote_plus(PASSWORD)}@{CLUSTER_URL}/?retryWrites=true&w=majority&appName=test-model"
        
        try:
            self.client = MongoClient(self.uri, serverSelectionTimeoutMS=5000)
            self.db = self.client['iot_project']
            self.collection = self.db['human_behavior']
            
            # Khởi tạo Vector Store
            self.vector_store = MongoDBAtlasVectorSearch(
                collection=self.collection,
                embedding=self.embeddings,
                index_name="vector_index", 
                relevance_score_fn="cosine"
            )
            
            self.client.admin.command('ping')
            print("--- Đã kết nối MongoDB Atlas Hybrid Search thành công ---")
        except Exception as e:
            print(f"Lỗi kết nối MongoDB: {e}")
            raise e

    def _generate_query(self, user_question):
        """Trích xuất JSON filter từ câu hỏi"""
        try:
            now = datetime.now()
            current_year = now.year
            processed_question = user_question
            
            # Xử lý ngày tháng nếu thiếu năm
            date_pattern = r'(\d{1,2})[/-](\d{1,2})(?!\d|/|-)'
            if re.search(date_pattern, user_question):
                processed_question = re.sub(date_pattern, rf'\1/\2/{current_year}', user_question)

            today_date = now.strftime("%Y-%m-%d")
            
            system_prompt = (
                f"BẠN LÀ MÁY TRÍCH XUẤT JSON. NGÀY HÔM NAY: {today_date}.\n"
                "NHIỆM VỤ: Chuyển câu hỏi thành JSON filter.\n"
                "QUY TẮC:\n"
                "1. 'timestamp' PHẢI LÀ: {{ \"$gte\": \"YYYY-MM-DDT00:00:00\", \"$lt\": \"YYYY-MM-DDT23:59:59\" }}\n"
                "2. 'action': Chỉ lấy từ khóa hành vi (ngã, nằm, sự cố).\n"
                "CHỈ TRẢ VỀ JSON THUẦN."
            )

            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("user", "{question}")
            ])
            
            chain = prompt | self.llm_query | StrOutputParser()
            raw_res = chain.invoke({"question": processed_question})
            
            # Làm sạch JSON
            clean_raw = re.sub(r'```[a-z]*|```', '', raw_res).strip()
            json_match = re.findall(r'(\{.*\})', clean_raw, re.DOTALL)

            if json_match:
                result = json.loads(json_match[-1].replace("'", '"'))
                if "timestamp" in result:
                    for k in ["$gte", "$lt"]:
                        if k in result["timestamp"]:
                            val = result["timestamp"][k].split('.')[0].replace('Z', '')
                            result["timestamp"][k] = val
                
                action = result.get("action", "")
                if isinstance(action, list):
                    action = " ".join(action)
                
                action = str(action).lower()
                for word in ["tình trạng", "an ninh", "trong ngày"]:
                    action = action.replace(word, "")
                result["action"] = action.strip()
                
                print(f"[DEBUG AI] JSON trích xuất: {result}")
                return result

            return {"error": "out_of_scope"}
        except Exception as e:
            print(f"[DEBUG AI] Lỗi Parse JSON: {e}")
            return {"error": "out_of_scope"}

    def _retrieve_context(self, user_question):
        """Truy vấn dữ liệu sử dụng Hybrid Search (Vector + Filter)"""
        try:
            query_dict = self._generate_query(user_question)
            if "error" in query_dict: return "OUT_OF_SCOPE"

            ts_filter = query_dict.get("timestamp")
            
            # Quan trọng: filter của Vector Search trong MongoDB Atlas cần đúng cấu trúc
            # Chú ý: Đảm bảo trường 'camera_id' và 'timestamp' đã được index dạng 'filter' trong Atlas
            search_filter = {
                "camera_id": {"$eq": "CAM_01"},
                "timestamp": {"$gte": ts_filter["$gte"], "$lt": ts_filter["$lt"]}
            }
            
            semantic_query = query_dict.get("action") or "người nằm, ngã, sự cố"
            print(f"[DEBUG DB] Lọc: {search_filter} | Truy vấn ngữ nghĩa: '{semantic_query}'")

            # 1. Thực hiện Vector Search (Tận dụng trường embedding)
            docs = []
            try:
                # similarity_search_with_score giúp ta biết độ tương đồng (score)
                docs_with_score = self.vector_store.similarity_search_with_score(
                    query=semantic_query,
                    k=20,
                    pre_filter=search_filter
                )
                
                if docs_with_score:
                    # Lọc ra các document có score tốt (ví dụ > 0.6)
                    docs = [doc for doc, score in docs_with_score if score > 0.5]
                    print(f"[DEBUG DB] Vector Search thành công. Tìm thấy {len(docs)} bản ghi tương đồng.")
                    for i, (doc, score) in enumerate(docs_with_score[:3]):
                        print(f"   - Top {i+1} score: {score:.4f} | Nội dung: {doc.page_content[:50]}...")
            except Exception as e:
                print(f"[DEBUG DB] Lỗi kỹ thuật Vector Search: {e}")

            # 2. Fallback: Nếu Vector Search không ra kết quả (rỗng)
            if not docs:
                print("[DEBUG DB] Vector Search không ra kết quả (Có thể do Pre-filter hoặc Vector Index chưa nạp xong).")
                print("[DEBUG DB] Đang dùng find() dự phòng...")
                
                # Cấu trúc query cho find() thông thường
                find_query = {
                    "camera_id": "CAM_01",
                    "timestamp": {"$gte": ts_filter["$gte"], "$lt": ts_filter["$lt"]}
                }
                cursor = self.collection.find(find_query).sort("timestamp", 1).limit(50)
                results = list(cursor)
                if not results: return "NO_DATA"
                
                from langchain_core.documents import Document
                docs = []
                for res in results:
                    people_data = res.get('people', [])
                    behaviors = [f"ID {p.get('person_id')}: {p.get('behavior')} ({p.get('level')})" for p in people_data]
                    content = "; ".join(behaviors) if behaviors else "Bình thường"
                    docs.append(Document(page_content=content, metadata=res))

            context_parts = []
            warn_ids = set()

            # Xử lý dữ liệu
            for doc in docs:
                ts = doc.metadata.get('timestamp', 'N/A')
                people_list = doc.metadata.get('people', [])
                
                if isinstance(people_list, list) and len(people_list) > 0:
                    behaviors = []
                    for p in people_list:
                        behaviors.append(f"ID {p.get('person_id')}: {p.get('behavior')}")
                        if p.get('level') == 'warning':
                            warn_ids.add(p.get('person_id'))
                    content = "; ".join(behaviors)
                else:
                    content = doc.page_content

                context_parts.append(f"- Lúc {ts}: {content}")

            return {
                "text": "\n".join(context_parts),
                "is_emergency": len(warn_ids) > 0,
                "bad_actors": list(warn_ids)
            }

        except Exception as e:
            print(f"[DEBUG DB] Lỗi Retrieval: {e}")
            return {"error": "system_error"}

    def ask(self, user_question, stream=False):
        try:
            def error_gen(msg): yield msg
            
            context_data = self._retrieve_context(user_question)
            if context_data == "OUT_OF_SCOPE": return error_gen("Vui lòng hỏi về tình hình an ninh hoặc hành vi trong camera.") if stream else "Vui lòng hỏi về tình hình an ninh hoặc hành vi trong camera."
            if context_data == "NO_DATA": return error_gen("Không tìm thấy dữ liệu camera trong thời gian này.") if stream else "Không tìm thấy dữ liệu camera trong thời gian này."

            status = "CẢNH BÁO NGUY HIỂM" if context_data['is_emergency'] else "BÌNH THƯỜNG"
            system_prompt = (
                "Bạn là trợ lý AI giám sát camera an ninh chuyên nghiệp.\n"
                "Nhiệm vụ: Tóm tắt dữ liệu hành vi người trong thang máy và đưa ra nhận định.\n"
                "Nếu có hành vi 'lying' (nằm) hoặc 'ngã', hãy nhấn mạnh yêu cầu kiểm tra khẩn cấp."
            )
            user_content = f"DỮ LIỆU:\n{context_data['text']}\n\nKẾT LUẬN: {status}\nID ĐÁNG NGỜ: {list(context_data['bad_actors'])}\nCÂU HỎI: {user_question}"

            prompt = ChatPromptTemplate.from_messages([("system", system_prompt), ("user", user_content)])
            chain = prompt | self.llm_report | StrOutputParser()
            
            return chain.stream({}) if stream else chain.invoke({})
        except Exception as e:
            return error_gen(f"Lỗi hệ thống: {e}") if stream else f"Lỗi hệ thống: {e}"