import React from 'react';
import './AdminCamera.scss';
import DisplayCamera from '../../../DashboardPage/DisplayCamera/DisplayCamera'; 

const AdminAddCamera = () => {
  return (
    <div className="admin-camera-display-wrapper">
      <div className="admin-camera-view">
        <DisplayCamera isCameraHidden={false} />
      </div>
    </div>
  );
};

export default AdminAddCamera;