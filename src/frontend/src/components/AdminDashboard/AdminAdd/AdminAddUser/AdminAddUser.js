import React, { useState } from 'react';
import './AdminAddUser.scss';
import { Mail, User, Calendar, ShieldCheck, UserPlus, Lock, ArrowRight, CheckCircle } from 'lucide-react';
import Cleave from 'cleave.js/react';

const AdminAddUser = () => {
  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState({
    email: '',
    fullName: '',
    dob: '', 
    role: 'user',
    username: '',
    password: '',
    confirmPassword: ''
  });   

  // Định nghĩa URL Backend (Tài có thể lấy từ .env hoặc gán trực tiếp)
  const BASE_URL = process.env.REACT_APP_API_BASE_URL;

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleNext = () => {
    if (formData.email && formData.fullName && formData.dob) {
      setStep(2);
    } else {
      alert("Vui lòng điền đủ thông tin cá nhân nhé!");
    }
  };

  // PHẦN QUAN TRỌNG: GỬI DỮ LIỆU LÊN SERVER
  const handleCreate = async (e) => {
    e.preventDefault();
    
    if (formData.password !== formData.confirmPassword) {
      alert("Mật khẩu xác nhận không khớp, kiểm tra lại nhé!");
      return;
    }

    try {
      const response = await fetch(`${BASE_URL}/api/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData) // Gửi toàn bộ 6 trường dữ liệu
      });

      const data = await response.json();

      if (data.success) {
        alert("Tài khoản đã tạo thành công ");
        // Reset form về trạng thái ban đầu sau khi tạo thành công
        setFormData({
          email: '', fullName: '', dob: '', role: 'user',
          username: '', password: '', confirmPassword: ''
        });
        setStep(1); 
      } else {
        alert(data.message || "Lỗi khi tạo tài khoản!");
      }
    } catch (err) {
      console.error("Lỗi kết nối:", err);
      alert("Không thể kết nối tới Server. Tài kiểm tra Backend đã chạy chưa nhé!");
    }
  };

  return (
    <div className="admin-add-user-container">
      <div className="form-card">
        <div className="step-bar">
          <div className={`step ${step >= 1 ? 'active' : ''}`}>1</div>
          <div className={`line ${step === 2 ? 'active' : ''}`}></div>
          <div className={`step ${step === 2 ? 'active' : ''}`}>2</div>
        </div>

        <h2 className="form-title">
          {step === 1 ? "THÔNG TIN CÁ NHÂN" : "THIẾT LẬP TÀI KHOẢN"}
        </h2>

        <form onSubmit={handleCreate}>
          {step === 1 ? (
            <div className="tab-animation">
              <div className="input-group">
                <label><Mail size={16}/> Địa chỉ Gmail</label>
                <input type="email" name="email" value={formData.email} onChange={handleChange} placeholder="example@gmail.com" required />
              </div>

              <div className="input-group">
                <label><User size={16}/> Tên của bạn</label>
                <input type="text" name="fullName" value={formData.fullName} onChange={handleChange} placeholder="Nhập họ và tên" required />
              </div>

              <div className="input-group">
                <label><Calendar size={16}/> Ngày tháng năm sinh</label>
                <Cleave
                  name="dob"
                  placeholder="DD/MM/YYYY"
                  options={{ 
                    date: true, 
                    datePattern: ['d', 'm', 'Y'], 
                    delimiter: '/' 
                  }}
                  value={formData.dob}
                  onChange={handleChange}
                  className="cleave-input"
                  required
                />
              </div>

              <div className="input-group">
                <label><ShieldCheck size={16}/> Chức danh</label>
                <select name="role" value={formData.role} onChange={handleChange}>
                  <option value="user">Nhân viên (User)</option>
                  <option value="admin">Quản trị viên (Admin)</option>
                </select>
              </div>

              <div className="button-footer">
                <button type="button" className="btn-next" onClick={handleNext}>
                  TIẾP THEO <ArrowRight size={18} />
                </button>
              </div>
            </div>
          ) : (
            <div className="tab-animation">
              <div className="input-group">
                <label><UserPlus size={16}/> Tên đăng nhập</label>
                <input type="text" name="username" value={formData.username} onChange={handleChange} placeholder="VD: tai123" required />
              </div>

              <div className="input-group">
                <label><Lock size={16}/> Mật khẩu</label>
                <input type="password" name="password" value={formData.password} onChange={handleChange} placeholder="••••••••" required />
              </div>

              <div className="input-group">
                <label><Lock size={16}/> Xác nhận lại mật khẩu</label>
                <input type="password" name="confirmPassword" value={formData.confirmPassword} onChange={handleChange} placeholder="••••••••" required />
              </div>

              <div className="button-footer space-between">
                <button type="button" className="btn-back" onClick={() => setStep(1)}>Quay lại</button>
                <button type="submit" className="btn-submit">
                  TẠO TÀI KHOẢN <CheckCircle size={18} />
                </button>
              </div>
            </div>
          )}
        </form>
      </div>
    </div>
  );
};

export default AdminAddUser;