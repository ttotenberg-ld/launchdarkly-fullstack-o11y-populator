import { Outlet } from 'react-router-dom';
import Navbar from './Navbar';
import Footer from './Footer';
import PromoBanner from './PromoBanner';
import FeedbackWidget from '../FeedbackWidget';
import ChatWidget from '../ChatWidget';

export default function Layout() {
  return (
    <div className="app-layout">
      <PromoBanner />
      <Navbar />
      <main className="main-content">
        <Outlet />
      </main>
      <Footer />
      <FeedbackWidget />
      <ChatWidget />
    </div>
  );
}
