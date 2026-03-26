import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import './index.scss';

import LoginForm from './components/LoginPage/LoginForm/LoginForm';
import UserMenu from './components/DashboardPage/UserMenu/UserMenu';
import DisplayCamera from './components/DashboardPage/DisplayCamera/DisplayCamera';
import NavButton from './components/DashboardPage/NavButton/NavButton';
import Chatbot from './components/DashboardPage/Chatbot/Chatbot'; 

// KHÔNG CẦN IMPORT API_ENDPOINTS NỮA

function AppContent() {
  const navigate = useNavigate();
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [isRegistering, setIsRegistering] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [activeTab, setActiveTab] = useState('camera');

  // LẤY TRỰC TIẾP TỪ BIẾN MÔI TRƯỜNG
  const BASE_URL = process.env.REACT_APP_API_BASE_URL;
  const projectName = "ELEVATOR MONITOR CHATBOT";

  const [isDarkMode, setIsDarkMode] = useState(() => localStorage.getItem("mode") === "dark");
  const [isCameraHidden, setIsCameraHidden] = useState(false);

  useEffect(() => {
    console.log(process.env.REACT_APP_FASTAPI_URL)
    const savedLogin = sessionStorage.getItem("isLoggedIn") === "true";
    if (savedLogin) {
      setIsLoggedIn(true);
      setUsername(sessionStorage.getItem("username") || "");
    }
  }, []);

  useEffect(() => {
    document.body.className = isDarkMode ? 'dark-mode' : 'light-mode';
  }, [isDarkMode]);

  const toggleDarkMode = () => {
    setIsDarkMode((prev) => {
      const newMode = !prev;
      localStorage.setItem("mode", newMode ? "dark" : "light");
      return newMode;
    });
  };

  const toggleCameraPrivacy = () => {
    setIsCameraHidden(!isCameraHidden);
  };

  const handleUsernameChange = (val) => {
    const noSpaceValue = val.replace(/\s/g, ''); 
    setUsername(noSpaceValue);
  };

  // --- XỬ LÝ ĐĂNG KÝ TRỰC TIẾP VỚI BASE_URL ---
  const handleRegister = async (e) => {
    e.preventDefault();
    if (!username) return alert("Vui lòng nhập tên đăng nhập!");

    try {
      const response = await fetch(`${BASE_URL}/api/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password, rank: 'user' })
      });
      const data = await response.json();
      if (data.success) {
        alert("Đăng ký thành công!");
        setIsRegistering(false);
        setUsername(''); setPassword('');
      } else {
        alert(data.message || "Đăng ký thất bại!");
      }
    } catch (err) {
      alert("Lỗi kết nối đến Server!");
    }
  };

  // --- XỬ LÝ ĐĂNG NHẬP TRỰC TIẾP VỚI BASE_URL ---
  const handleLogin = async (e) => {
    e.preventDefault();
    if (!username) return alert("Vui lòng nhập tên đăng nhập!");

    try {
      // Gọi trực tiếp URL nối chuỗi ở đây
      const response = await fetch(`${BASE_URL}/api/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });
      const data = await response.json();
      if (data.success) {
        setIsLoggedIn(true);
        sessionStorage.setItem("isLoggedIn", "true");
        sessionStorage.setItem("username", username);
        if (data.cameraUrl) sessionStorage.setItem("cameraUrl", data.cameraUrl);
        navigate("/dashboard");
      } else {
        alert(data.message || "Sai tên đăng nhập hoặc mật khẩu!");
      }
    } catch (err) {
      console.error("Login Error:", err);
      alert("Server chưa hoạt động hoặc lỗi địa chỉ API!");
    }
  };

  const handleLogout = () => {
    setIsLoggedIn(false);
    setUsername("");
    sessionStorage.clear();
    navigate("/"); 
  };

  return (
    <div className={`App ${isDarkMode ? 'dark-mode' : 'light-mode'}`}>
      {isLoggedIn && (
        <div className="global-header">
          <img src="/imgs/bug-removebg-preview.png" alt="Logo" className="dashboard-logo" />
        </div>
      )}  

      <Routes>
        <Route path="/" element={
          isLoggedIn ? <Navigate to="/dashboard" replace /> : (
            <LoginForm 
              isRegistering={isRegistering} setIsRegistering={setIsRegistering}
              handleLogin={handleLogin} handleRegister={handleRegister}
              username={username} setUsername={handleUsernameChange}
              password={password} setPassword={setPassword}
            />
          )
        } />
        
        <Route path="/dashboard" element={
          isLoggedIn ? (
            <div className="dashboard-layout">
              <h2 className="camera-title-fixed">{projectName}</h2>
              <NavButton activeTab={activeTab} setActiveTab={setActiveTab} />
              <UserMenu 
                isLoggedIn={isLoggedIn} username={username} onLogout={handleLogout} 
                isDarkMode={isDarkMode} toggleDarkMode={toggleDarkMode}
                isCameraHidden={isCameraHidden} toggleCameraPrivacy={toggleCameraPrivacy}
              />
              <div className="content-container">
                {activeTab === 'camera' ? 
                  <DisplayCamera isCameraHidden={isCameraHidden} /> : 
                  <Chatbot />
                }
              </div>
            </div>
          ) : <Navigate to="/" replace />
        } />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  );
}
 
function App() {
  return (
    <BrowserRouter>
      <AppContent />
    </BrowserRouter>
  );
}

export default App;