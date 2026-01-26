import { useState, useEffect } from 'react';
import './Toast.css';

// Global toast management
let showToastGlobal = null;

export const useToast = () => {
  const [toasts, setToasts] = useState([]);

  useEffect(() => {
    showToastGlobal = (message, type = 'success') => {
      const id = Date.now();
      setToasts(prev => [...prev, { id, message, type }]);
      
      // Auto-remove after 3 seconds
      setTimeout(() => {
        setToasts(prev => prev.filter(toast => toast.id !== id));
      }, 3000);
    };
    
    return () => {
      showToastGlobal = null;
    };
  }, []);

  const removeToast = (id) => {
    setToasts(prev => prev.filter(toast => toast.id !== id));
  };

  return { toasts, removeToast };
};

export const showToast = (message, type = 'success') => {
  if (showToastGlobal) {
    showToastGlobal(message, type);
  }
};

export const ToastContainer = ({ toasts, removeToast }) => {
  return (
    <div className="toast-container">
      {toasts.map(toast => (
        <div 
          key={toast.id} 
          className={`toast toast-${toast.type}`}
          onClick={() => removeToast(toast.id)}
        >
          <span className="toast-icon">
            {toast.type === 'success' ? '✓' : toast.type === 'error' ? '✗' : 'ℹ'}
          </span>
          <span className="toast-message">{toast.message}</span>
        </div>
      ))}
    </div>
  );
};

