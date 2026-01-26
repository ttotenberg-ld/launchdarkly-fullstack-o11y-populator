import React from 'react';

const Header = ({ title, user, isAutoPlaying, onAutoPlayToggle }) => {
  return (
    <header className="header">
      <div className="header-left">
        <h1 className="header-title">{title}</h1>
      </div>
      
      <div className="header-right">
        <div className="auto-play-toggle">
          <span style={{ fontSize: '14px', color: 'var(--ld-gray-600)' }}>
            Auto-play
          </span>
          <div 
            className={`toggle-switch ${isAutoPlaying ? 'active' : ''}`}
            onClick={onAutoPlayToggle}
            role="button"
            tabIndex={0}
            aria-label="Toggle auto-play"
          />
        </div>
        
        <div className="user-avatar">
          {user?.name?.charAt(0) || 'D'}
        </div>
      </div>
    </header>
  );
};

export default Header;
