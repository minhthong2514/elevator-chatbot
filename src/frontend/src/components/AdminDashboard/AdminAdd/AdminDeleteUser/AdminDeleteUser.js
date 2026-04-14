import React, { useState } from 'react';
import './AdminDeleteUser.scss'; // Nhớ tạo file scss tương ứng
import { UserX, Trash2, AlertTriangle } from 'lucide-react';

const AdminDeleteUser = () => {
  const [username, setUsername] = useState('');
  const BASE_URL = process.env.REACT_APP_API_BASE_URL;

  const handleDelete = async (e) => {
  e.preventDefault();
  
  // 1. Kiểm tra xem username có bị trống không
  if (!username.trim()) {
    alert("Vui lòng nhập Username cần xóa!");
    return;
  }

  const confirmDelete = window.confirm(`Bạn có chắc muốn XÓA vĩnh viễn "${username}"?`);
  
  if (confirmDelete) {
    try {
      // Đảm bảo BASE_URL là http://localhost:5000 (không có dấu gạch chéo thừa ở cuối)
      const response = await fetch(`${BASE_URL}/api/delete-user/${username.trim()}`, {
        method: 'DELETE', // Phải là DELETE viết hoa
        headers: {
          'Content-Type': 'application/json'
        }
      });

      const data = await response.json();

      if (data.success) {
        alert("Thành công: " + data.message);
        setUsername(''); 
      } else {
        alert("Thất bại: " + data.message);
      }
    } catch (err) {
      console.error("Chi tiết lỗi:", err);
      alert("Lỗi kết nối Server! Tài kiểm tra lại Terminal Backend xem có báo lỗi đỏ không nhé.");
    }
  }
};


  return (
    <div className="admin-delete-user-container">
      <div className="delete-card">
        <h2 className="delete-title"><UserX size={24}/> Xóa tài khoản</h2>
        {/* <div className="warning-box">
          <AlertTriangle size={20} />
          <span>Hành động này không thể hoàn tác. Dữ liệu người dùng sẽ bị xóa vĩnh viễn.</span>
        </div> */}
        
        <form className="delete-form" onSubmit={handleDelete}>
          <div className="input-group">
            <label>Nhập Username cần xóa</label>
            <input 
              type="text" 
              value={username} 
              onChange={(e) => setUsername(e.target.value)} 
              placeholder="Ví dụ: nhanvien01" 
              required 
            />
          </div>

          <button type="submit" className="btn-delete">
            <Trash2 size={18}/> XÁC NHẬN XÓA
          </button>
        </form>
      </div>
    </div>
  );
};

export default AdminDeleteUser;