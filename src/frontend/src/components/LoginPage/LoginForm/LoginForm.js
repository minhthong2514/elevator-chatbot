import React, { useState } from 'react';
import { FaEye, FaEyeSlash } from 'react-icons/fa';
import Header from '../Header/Header.js'; 
import './LoginForm.scss';

// --- 1. COMPONENT CON: KHUNG ĐĂNG NHẬP/ĐĂNG KÝ ---
const LoginCard = ({ 
  isRegistering, setIsRegistering, handleLogin, handleRegister, 
  username, setUsername, password, setPassword 
}) => {
  const [showPassword, setShowPassword] = useState(false);

  // Xử lý gửi form chung
  const onSubmit = (e) => {
    isRegistering ? handleRegister(e) : handleLogin(e);
  };

  // Reset dữ liệu khi chuyển đổi chế độ
  const toggleMode = () => {
    setIsRegistering(!isRegistering);
    setUsername('');
    setPassword('');
  };

  return (
    <div className="login-card">
      <h2>ELEVATOR MONITORING</h2>
      <form onSubmit={onSubmit}>
        <input 
          type="text" 
          placeholder="Username" 
          value={username} 
          onChange={(e) => setUsername(e.target.value)}
          required 
        />
        
        <div className="password-group">
          <input 
            type={showPassword ? "text" : "password"} 
            placeholder="Password" 
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required 
          />
          <span className="eye-icon" onClick={() => setShowPassword(!showPassword)}>
            {showPassword ? <FaEyeSlash /> : <FaEye />}
          </span>
        </div>

        <button type="submit" className="login-btn">
          {isRegistering ? 'Sign in' : 'Login'}
        </button>
      </form>

      <div className="divider"></div>

      <button type="button" className="create-btn" onClick={toggleMode}>
        {isRegistering ? 'Already have an account?' : 'Create an Account'}
      </button>
    </div>
  );
};

// --- 2. COMPONENT CHA: BỐ CỤC TRANG ---
const LoginForm = (props) => {
  return (
    <div className="fb-app-wrapper">
      <Header />
      
      <div className="fb-body">
        <div className="login-form-section">
          <div className="login-form-container">
            <LoginCard {...props} />
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginForm;