// file này là logo ở phần login 
import React from 'react';
import './Header.scss';

function Header() {
  return (
    <header className="fb-header"> 
      {/* LOGO CHÍNH CỦA HỆ THỐNG */}
      <h1 className="fb-logo">Elevator</h1>
    </header>
  );
}

export default Header;