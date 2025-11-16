import ErrorBoundary from './components/ErrorBoundary';
import DashboardLayout from './components/DashboardLayout';

function App() {
  return (
    <ErrorBoundary>
      <DashboardLayout />
    </ErrorBoundary>
  );
}

export default App;

