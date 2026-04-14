// file này là file main 

import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import './index.scss';

import LoginForm from './components/LoginPage/LoginForm/LoginForm';
import UserMenu from './components/DashboardPage/UserMenu/UserMenu';
import DisplayCamera from './components/DashboardPage/DisplayCamera/DisplayCamera';
import NavButton from './components/DashboardPage/NavButton/NavButton';
import Chatbot from './components/DashboardPage/Chatbot/Chatbot'; 

// --- SỬA LẠI PHẦN IMPORT Ở ĐÂY ---
import AdminSidebar from './components/AdminDashboard/AdminSiderbar/AdminSiderbar'; 
import AdminContent from './components/AdminDashboard/AdminContent/AdminContent'; // File nội dung mới tạo


function AppContent() {
  const navigate = useNavigate();
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [userRank, setUserRank] = useState('user');
  const [isRegistering, setIsRegistering] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [activeTab, setActiveTab] = useState('camera');
  const [adminTab, setAdminTab] = useState('monitor'); 

  const BASE_URL = process.env.REACT_APP_API_BASE_URL;
  const projectName = "ELEVATOR MONITOR CHATBOT";
  const [isDarkMode, setIsDarkMode] = useState(() => localStorage.getItem("mode") === "dark");
  const [isCameraHidden, setIsCameraHidden] = useState(false);

  useEffect(() => {
    const savedLogin = sessionStorage.getItem("isLoggedIn") === "true";
    if (savedLogin) {
      setIsLoggedIn(true);
      setUsername(sessionStorage.getItem("username") || "");
      setUserRank(sessionStorage.getItem("userRank") || "user");
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
  
  const handleLogin = async (e) => {
    e.preventDefault();
    try {
      const response = await fetch(`${BASE_URL}/api/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });
      const data = await response.json();

      if (data.success) {
        setIsLoggedIn(true);
        setUserRank(data.rank);
        sessionStorage.setItem("isLoggedIn", "true");
        sessionStorage.setItem("username", data.username);
        sessionStorage.setItem("userRank", data.rank);
        
        if (data.rank === 'admin') navigate("/admin-dashboard");
        else navigate("/dashboard");
      } else {
        alert("Sai tài khoản!");
      }
    } catch (err) {
      alert("Lỗi server!");
    }
  };

  const handleLogout = () => {
    setIsLoggedIn(false);
    sessionStorage.clear();
    navigate("/"); 
  };

  return (
    <div className={`App ${isDarkMode ? 'dark-mode' : 'light-mode'}`}>
      {isLoggedIn && userRank !== 'admin' && (
        <div className="global-header">
          <img src="/imgs/bug-removebg-preview.png" alt="Logo" className="dashboard-logo" />
        </div>
      )}  

      <Routes>
        <Route path="/" element={
          isLoggedIn ? <Navigate to={userRank === 'admin' ? "/admin-dashboard" : "/dashboard"} replace /> : 
          <LoginForm 
            isRegistering={isRegistering} setIsRegistering={setIsRegistering}
            handleLogin={handleLogin} username={username} setUsername={setUsername}
            password={password} setPassword={setPassword}
          />
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

        {/* --- ROUTE ADMIN: QUẢN LÝ TABS --- */}
        <Route path="/admin-dashboard" element={
          isLoggedIn && userRank === 'admin' ? (
            <div className="admin-layout" style={{ display: 'flex', width: '100%' }}>
              <AdminSidebar 
                activeTab={adminTab} 
                setActiveTab={setAdminTab} 
                onLogout={handleLogout} 
              />
              <div className="admin-main-content" style={{ flex: 1, backgroundColor: 'rgba(180, 180, 180, 1)' }}>
                {/* Ở đây AdminContent sẽ dựa vào giá trị của adminTab để hiển thị:
                  - monitor
                  - add-user
                  - edit-user (Phần mới thêm)
                */}
                <AdminContent activeTab={adminTab} setAdminTab={setAdminTab} />
              </div>
            </div>
          ) : <Navigate to="/" replace />
        } />
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