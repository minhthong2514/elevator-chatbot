import React from 'react';
import { FaVideo, FaPlus, FaEdit, FaTrash, FaChartLine, FaSignOutAlt } from 'react-icons/fa';
import './AdminSiderbar.scss';

const AdminSidebar = ({ activeTab, setActiveTab, onLogout }) => {
  return (
    <div className="admin-sidebar">
      <div className="sidebar-header">
        <img src="/imgs/bug-removebg-preview.png" alt="Logo" />
        <span>ADMIN PANEL</span>
      </div>
      
      <nav className="sidebar-nav">
        {/* GIÁM SÁT */}
        <div 
          className={`nav-item ${activeTab === 'monitor' ? 'active' : ''}`} 
          onClick={() => setActiveTab('monitor')}
        >
          <FaVideo /> <span>Giám sát</span>
        </div>
        
        {/* THÊM */}
        <div 
          className={`nav-item ${activeTab === 'add' ? 'active' : ''}`} 
          onClick={() => setActiveTab('add')}
        >
          <FaPlus /> <span>Thêm</span>
        </div>

        {/* SỬA */}
        <div 
          className={`nav-item ${activeTab === 'edit' ? 'active' : ''}`} 
          onClick={() => setActiveTab('edit')}
        >
          <FaEdit /> <span>Sửa</span>
        </div>

        {/* XÓA */}
        <div 
          className={`nav-item ${activeTab === 'delete' ? 'active' : ''}`} 
          onClick={() => setActiveTab('delete')}
        >
          <FaTrash /> <span>Xóa</span>
        </div>

        {/* THỐNG KÊ */}
        <div 
          className={`nav-item ${activeTab === 'analytics' ? 'active' : ''}`} 
          onClick={() => setActiveTab('analytics')}
        >
          <FaChartLine /> <span>Thống kê</span>
        </div>
      </nav>

      <div className="sidebar-footer" onClick={onLogout}>
        <FaSignOutAlt /> <span>Đăng xuất</span>
      </div>
    </div>
  );
};

export default AdminSidebar;