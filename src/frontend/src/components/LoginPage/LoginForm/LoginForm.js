import React, { useState } from 'react';
import { FaEye, FaEyeSlash } from 'react-icons/fa';
import Header from '../Header/Header.js'; 
import './LoginForm.scss';

// --- 1. COMPONENT CON: KHUNG ĐĂNG NHẬP ---
const LoginCard = ({ handleLogin, username, setUsername, password, setPassword }) => {
  const [showPassword, setShowPassword] = useState(false);

  return (
    <div className="login-card">
      <div className="login-header">
        <h2>ELEVATOR MONITORING</h2>
      </div>

      <form onSubmit={handleLogin}>
        <div className="input-group">
          <label>Tên đăng nhập</label>
          <input 
            type="text" 
            placeholder="Nhập username..." 
            value={username} 
            onChange={(e) => setUsername(e.target.value)}
            required 
          />
        </div>
        
        <div className="input-group">
          <label>Mật khẩu</label>
          <div className="password-wrapper">
            <input 
              type={showPassword ? "text" : "password"} 
              placeholder="Nhập mật khẩu..." 
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required 
            />
            <span className="eye-icon" onClick={() => setShowPassword(!showPassword)}>
              {showPassword ? <FaEyeSlash /> : <FaEye />}
            </span>
          </div>
        </div>

        <button type="submit" className="login-btn">
          ĐĂNG NHẬP HỆ THỐNG
        </button>
      </form>

      {/* Đã xóa phần Divider và nút Create Account */}
      <div className="login-footer">
        <span>© 2026 Elevator Monitor System</span>
      </div>
    </div>
  );
};

// --- 2. COMPONENT CHA ---
const LoginForm = (props) => {
  return (
    <div className="login-page-wrapper">
      <Header />
      <div className="login-body-content">
        <div className="login-card-container">
          <LoginCard {...props} />
        </div>
      </div>
    </div>
  );
};

export default LoginForm;