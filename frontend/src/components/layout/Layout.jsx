import { Outlet } from 'react-router-dom';
import Navbar from './Navbar';
import Footer from './Footer';
import FeedbackWidget from '../FeedbackWidget';

export default function Layout() {
  return (
    <div className="app-layout">
      <Navbar />
      <main className="main-content">
        <Outlet />
      </main>
      <Footer />
      <FeedbackWidget />
    </div>
  );
}
