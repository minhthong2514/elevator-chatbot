import React from 'react';
import { Camera, MessageSquare } from 'lucide-react';
import './NavButton.scss';

const NavButton = ({ activeTab, setActiveTab }) => {

    // --- XỬ LÝ CHUYỂN TAB ---
    const toggleTab = () => {
        setActiveTab(activeTab === 'camera' ? 'chatbot' : 'camera');
    };

    return (
        <div className="nav-switch-wrapper">
            {/* KHUNG CHUYỂN ĐỔI (PILL SWITCH) */}
            <div 
                className={`pill-switch ${activeTab === 'chatbot' ? 'is-chatbot' : ''}`} 
                onClick={toggleTab}
            >
                {/* ICON CAMERA */}
                <div className={`icon-box ${activeTab === 'camera' ? 'active' : ''}`}>
                    <Camera size={20} strokeWidth={activeTab === 'camera' ? 2.5 : 2} />
                </div>

                {/* ICON CHATBOT */}
                <div className={`icon-box ${activeTab === 'chatbot' ? 'active' : ''}`}>
                    <MessageSquare size={20} strokeWidth={activeTab === 'chatbot' ? 2.5 : 2} />
                </div>

                {/* VIÊN THUỐC DI CHUYỂN (THUMB) */}
                <div className="switch-thumb"></div>
            </div>

            {/* NHÃN HIỂN THỊ TRẠNG THÁI */}
            <span className="switch-label">
                {activeTab === 'camera' ? 'GIÁM SÁT' : 'TRỢ LÝ AI'}
            </span>
        </div>
    );
};

export default NavButton;