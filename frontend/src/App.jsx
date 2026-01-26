import ErrorBoundary from './components/infrastructure/ErrorBoundary';
import DashboardLayout from './components/infrastructure/DashboardLayout';
import { useToast, ToastContainer } from './components/infrastructure/Toast';

function App() {
  const { toasts, removeToast } = useToast();

  return (
    <ErrorBoundary>
      <ToastContainer toasts={toasts} removeToast={removeToast} />
      <DashboardLayout />
    </ErrorBoundary>
  );
}

export default App;

