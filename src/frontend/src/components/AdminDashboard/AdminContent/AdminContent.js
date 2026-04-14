import React from 'react';
import './AdminContent.scss';
import AdminAddCamera from '../AdminAdd/AdminCamera/AdminCamera'; 
import AdminAddUser from '../AdminAdd/AdminAddUser/AdminAddUser'; 
import AdminEditUser from '../AdminAdd/AdminEditUser/AdminEditUser';
import AdminDeleteUser from '../AdminAdd/AdminDeleteUser/AdminDeleteUser'; 
import AdminChatbot from '../AdminAdd/AdminChatbot/AdminChatbot'; 

const AdminContent = ({ activeTab }) => {
  const renderContent = () => {
    switch (activeTab) {
      case 'monitor': 
        return (
          <div className="tab-body monitor-view">
             <AdminAddCamera />
          </div>
        );
      
      case 'add': 
        return (
          <div className="tab-body admin-add-layout">
            <AdminAddUser />
          </div>
        );

      case 'edit': 
        return (
          <div className="tab-body admin-edit-layout">
            <AdminEditUser />
          </div>
        );

      case 'delete': 
        return (
          <div className="tab-body admin-delete-layout">
            <AdminDeleteUser />
          </div>
        );

      case 'analytics': 
        return (
          <div className="tab-body analytics-view">
             <div className="admin-chatbot-wrapper">
                {/* Gọi AdminChatbot ở đây là CHUẨN, không bị lặp */}
                <AdminChatbot mode="analytics" />
             </div>
          </div>
        );

      default: 
        return <div className="tab-body">Chào mừng Admin</div>;
    } 
  }; 

  return (
    <div className="admin-content-container">
      <div className="admin-content-main">
        {renderContent()}
      </div>
    </div>
  );
};

export default AdminContent;