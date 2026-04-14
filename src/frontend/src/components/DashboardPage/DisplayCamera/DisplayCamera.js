// file này cấu hình hiển thị camera của user
import React, { useState } from 'react';
import { EyeOff } from 'lucide-react'; // Dùng icon của lucide cho đồng bộ
import './DisplayCamera.scss'; 

const DisplayCamera = ({ isCameraHidden }) => {
    const videoUrl = process.env.REACT_APP_FASTAPI_URL;

    // const videoUrl = "http://localhost:8000/video_feed"; 
    const [streamError, setStreamError] = useState(false);

    return (
        <div className="camera-container">
            <div className="video-box">
                <div className="camera-stream-wrapper">
                    <img 
                        src={videoUrl} 
                        alt="Elevator Camera Stream" 
                        className="camera-stream"
                        onError={() => setStreamError(true)}
                        onLoad={() => setStreamError(false)}
                    />
                </div>

                {/* MỚI: Lớp phủ màn đen khi chế độ che camera được bật */}
                <div className={`camera-privacy-overlay ${isCameraHidden ? 'active' : ''}`}>
                    <div className="overlay-content">
                        <EyeOff size={48} className="privacy-icon" />
                        <p>CHẾ ĐỘ RIÊNG TƯ ĐANG BẬT</p>
                        <span>Camera tạm thời bị che</span>
                    </div>
                </div>
            </div>
            
            <div className="status-text">
                <span className={`status-dot ${streamError ? 'error' : 'live'}`}></span>
                Trạng thái: 
                <span className={streamError ? 'error' : 'live'}>
                    {streamError ? ' Mất kết nối' : ' Đang kết nối trực tiếp'}
                </span>
            </div>
        </div>
    );
};

export default DisplayCamera;