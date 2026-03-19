import pymongo
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
import urllib.parse

def test_mongodb_connection():
    # 1. Cấu hình chuỗi kết nối
    # Local: "mongodb://localhost:27017/"
    # Atlas: "mongodb+srv://<user>:<password>@cluster.mongodb.net/"
    USER = "buiminhtai1234"
    PASSWORD = "191104"
    CLUSTER_URL = "cluster0.ydqe2ve.mongodb.net" 
    safe_pass = urllib.parse.quote_plus(PASSWORD)
    CONNECTION_STRING = f"mongodb+srv://{USER}:{safe_pass}@{CLUSTER_URL}/?retryWrites=true&w=majority&appName=test-model"

    print("--- Đang khởi tạo kết nối tới MongoDB ---")
    
    # Khởi tạo client với timeout là 5 giây để không phải chờ quá lâu nếu lỗi
    client = pymongo.MongoClient(CONNECTION_STRING, serverSelectionTimeoutMS=5000)

    try:
        # 2. Sử dụng lệnh 'ping' để xác thực kết nối với server
        # Đây là cách chuẩn nhất để biết server có phản hồi hay không
        client.admin.command('ping')
        print("✅ Kết nối thành công!")

        # 3. Hiển thị thông tin server
        print(f"🔹 Thông tin Server: {client.address}")

        # 4. Liệt kê các database hiện có
        print("🔹 Danh sách Databases trên hệ thống:")
        db_names = client.list_database_names()
        for db in db_names:
            print(f"   - {db}")

    except ServerSelectionTimeoutError:
        print("❌ Lỗi: Không thể kết nối tới Server (Timeout). Hãy kiểm tra IP hoặc Port.")
    except ConnectionFailure:
        print("❌ Lỗi: Kết nối thất bại. Hãy kiểm tra lại thông tin đăng nhập.")
    except Exception as e:
        print(f"❌ Đã xảy ra lỗi không xác định: {e}")
    finally:
        # Đóng kết nối
        client.close()
        print("--- Đã ngắt kết nối ---")

if __name__ == "__main__":
    test_mongodb_connection()