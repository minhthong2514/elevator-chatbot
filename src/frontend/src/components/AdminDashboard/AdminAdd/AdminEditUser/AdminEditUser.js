import React, { useState } from 'react';
import './AdminEditUser.scss';
import { Mail, Lock, ShieldCheck, Save, XCircle } from 'lucide-react';

const AdminEditUser = () => {
  // ĐỊNH NGHĨA BASE_URL (Sửa lỗi Line 3:37)
  const BASE_URL = process.env.REACT_APP_API_BASE_URL || "http://localhost:5000";

  // ĐỊNH NGHĨA formData (Sửa lỗi Line 8, 9, 10)
  const [formData, setFormData] = useState({
    username: '', // Dùng để tìm kiếm user cần sửa
    email: '',
    password: '',
    rank: 'user'
  });

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleUpdate = async (e) => {
    e.preventDefault();
    try {
      const response = await fetch(`${BASE_URL}/api/update-user`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });
      const data = await response.json();
      if (data.success) {
        alert("Cập nhật thành công!");
      } else {
        alert(data.message || "Không tìm thấy Username!");
      }
    } catch (err) {
      alert("Lỗi kết nối server!");
    }
  };

  return (
    <div className="admin-edit-user-container">
      <div className="edit-card">
        <h2 className="edit-title">Chỉnh sửa thông tin</h2>
        <form className="edit-form" onSubmit={handleUpdate}>
          <div className="input-group">
            <label>Tên đăng nhập (Username cần sửa)</label>
            <input type="text" name="username" value={formData.username} onChange={handleChange} placeholder="Nhập đúng tên đăng nhập" required />
          </div>

          <div className="input-group">
            <label><Mail size={16}/> Email mới</label>
            <input type="email" name="email" value={formData.email} onChange={handleChange} placeholder="tai.new@gmail.com" required />
          </div>

          <div className="input-group">
            <label><Lock size={16}/> Mật khẩu mới</label>
            <input type="password" name="password" value={formData.password} onChange={handleChange} placeholder="••••••••" required />
          </div>

          <div className="input-group">
            <label><ShieldCheck size={16}/> Rank hệ thống</label>
            <select name="rank" value={formData.rank} onChange={handleChange}>
              <option value="user">User</option>
              <option value="admin">Admin</option>
            </select>
          </div>

          <div className="button-group">
            <button type="submit" className="btn-save"><Save size={18}/> Lưu thay đổi</button>
            <button type="button" className="btn-cancel" onClick={() => setFormData({username:'', email:'', password:'', rank:'user'})}>
                <XCircle size={18}/> Hủy
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default AdminEditUser;