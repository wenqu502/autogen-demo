import React from 'react';
import { NavLink } from 'react-router-dom';

const Sidebar = () => {
  return (
    <div className="sidebar">
      <h2>AutoGen Studio</h2>
      <nav>
        <NavLink to="/" className={({ isActive }) => isActive ? 'active' : ''}>
          首页
        </NavLink>
        <NavLink to="/agents" className={({ isActive }) => isActive ? 'active' : ''}>
          智能体设置
        </NavLink>
        <NavLink to="/chat" className={({ isActive }) => isActive ? 'active' : ''}>
          对话界面
        </NavLink>
      </nav>
    </div>
  );
};

export default Sidebar;
