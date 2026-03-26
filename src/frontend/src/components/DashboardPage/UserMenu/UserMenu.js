import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Settings, Moon, Sun, Info, LogOut, Eye, EyeOff } from 'lucide-react'; // Thêm icon Eye
import './UserMenu.scss';

const UserMenu = ({ isLoggedIn, onLogout, isDarkMode, toggleDarkMode, isCameraHidden, toggleCameraPrivacy }) => {
    const navigate = useNavigate();
    const [isOpen, setIsOpen] = useState(false);

    useEffect(() => {
        const checkLogin = sessionStorage.getItem("isLoggedIn");
        if (!isLoggedIn && checkLogin !== "true") {
            navigate("/");
        }
    }, [isLoggedIn, navigate]);

    const handleLogout = () => {
        if (onLogout) {
            onLogout();
        } else {
            sessionStorage.clear();
            window.location.replace("/");
        }
    };

    return (
        <div className="user-menu-container">
            <button className="menu-icon-btn" onClick={() => setIsOpen(!isOpen)}>
                <Settings size={28} />
            </button>

            {isOpen && (
                <div className="menu-popup">
                    <div className="menu-header">Cài đặt hệ thống</div>
                    
                    {/* CHUYỂN ĐỔI GIAO DIỆN (DARK/LIGHT) */}
                    <div className="menu-item-group theme-switch-row">
                        <div className="label-group">
                            {isDarkMode ? <Moon className="theme-icon" /> : <Sun className="theme-icon" />}
                            <span>{isDarkMode ? "Chế độ tối" : "Chế độ sáng"}</span>
                        </div>
                        <label className="pill-switch-wrapper">
                            <input type="checkbox" checked={isDarkMode} onChange={toggleDarkMode} />
                            <span className="slider round">
                                <Moon size={15} style={{ opacity: isDarkMode ? 1 : 1, color: isDarkMode ? '#f1c40f' : '#ccc' }} />
                                <Sun size={15} style={{ opacity: !isDarkMode ? 1 : 1, color: !isDarkMode ? '#f39c12' : '#ccc' }} />
                            </span>
                        </label>
                    </div>

                    {/* --- CHỨC NĂNG CHE CAMERA (MỚI) --- */}
                    <div className="menu-item-group theme-switch-row">
                        <div className="label-group">
                            {isCameraHidden ? <EyeOff className="theme-icon" /> : <Eye className="theme-icon" />}
                            <span>{isCameraHidden ? "Đang che" : "Che camera"}</span>
                        </div>
                        <label className="pill-switch-wrapper camera-switch">
                            <input type="checkbox" checked={isCameraHidden} onChange={toggleCameraPrivacy} />
                            <span className="slider round">
                                {/* Icon hiển thị bên trong nút gạt */}
                                <EyeOff size={15} style={{ opacity: isCameraHidden ? 1 : 1 }} />
                                <Eye size={15} style={{ opacity: !isCameraHidden ? 1 : 1 }} />
                            </span>
                        </label>
                    </div>

                    <div className="menu-divider"></div>

                    <div className="menu-item" onClick={() => alert("Tác giả: Bùi Minh Tài (Tai BUG)")}>
                        <Info size={20} />
                        <span>Thông tin tác giả</span>
                    </div>

                    <div className="menu-item logout" onClick={handleLogout}>
                        <LogOut size={20} />
                        <span>Đăng xuất</span>
                    </div>
                </div>
            )}
        </div>
    );
};

export default UserMenu;