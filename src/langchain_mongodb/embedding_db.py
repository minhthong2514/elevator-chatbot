import urllib.parse
from pymongo import MongoClient
from langchain_huggingface import HuggingFaceEmbeddings
from tqdm import tqdm

def vectorize_existing_data():
    # 1. Cấu hình kết nối (Thay đổi thông tin của bạn tại đây)
    USER = "buiminhtai1234"
    PASSWORD = "191104"
    CLUSTER_URL = "cluster0.ydqe2ve.mongodb.net"
    uri = f"mongodb+srv://{USER}:{urllib.parse.quote_plus(PASSWORD)}@{CLUSTER_URL}/?retryWrites=true&w=majority&appName=test-model"
    
    client = MongoClient(uri)
    db = client['iot_project']
    collection = db['human_behavior']

    # 2. Khởi tạo Model Embedding (Phải khớp với model trong engine.py)
    print("Đang tải model embedding...")
    embeddings_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

    # 3. Tìm các document chưa có trường 'embedding'
    query = {"embedding": {"$exists": False}}
    docs_to_update = list(collection.find(query))
    
    if not docs_to_update:
        print("Không có dữ liệu mới cần tạo embedding.")
        return

    print(f"Tìm thấy {len(docs_to_update)} bản ghi cần xử lý...")

    for doc in tqdm(docs_to_update):
        # Tạo chuỗi văn bản mô tả từ dữ liệu JSON
        # Ví dụ: "Tại CAM_01 lúc 2026-03-03... phát hiện hành vi lying (warning)"
        behaviors = []
        for p in doc.get('people', []):
            behaviors.append(f"người ID {p.get('person_id')} hành vi {p.get('behavior')} mức {p.get('level')}")
        
        content_text = f"Camera {doc.get('camera_id')} lúc {doc.get('timestamp')}: " + ", ".join(behaviors)
        
        # Chuyển văn bản thành Vector
        vector = embeddings_model.embed_query(content_text)
        
        # Cập nhật vào MongoDB
        collection.update_one(
            {"_id": doc["_id"]},
            {"$set": {"embedding": vector}}
        )

    print("Hoàn thành số hóa dữ liệu!")

if __name__ == "__main__":
    vectorize_existing_data()