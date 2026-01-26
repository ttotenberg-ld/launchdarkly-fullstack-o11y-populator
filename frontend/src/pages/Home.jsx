import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../services/api';
import ProductCard from '../components/products/ProductCard';

export default function Home() {
  const [featuredProducts, setFeaturedProducts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadProducts() {
      try {
        const result = await api.listProducts();
        if (result.success && result.data.products) {
          setFeaturedProducts(result.data.products.slice(0, 4));
        }
      } catch (err) {
        console.error('Failed to load products:', err);
      } finally {
        setLoading(false);
      }
    }
    loadProducts();
  }, []);

  return (
    <div className="home-page" data-testid="home-page">
      {/* Hero Section */}
      <section className="hero" data-testid="hero-section">
        <div className="hero-content">
          <h1>Welcome to LD Store</h1>
          <p>Discover our collection of feature flags, progressive rollouts, and experimentation tools.</p>
          <Link to="/products" className="btn-primary btn-lg" data-testid="shop-now-button">
            Shop Now
          </Link>
        </div>
      </section>

      {/* Featured Products */}
      <section className="featured-section">
        <div className="section-header">
          <h2>Featured Products</h2>
          <Link to="/products" className="view-all-link">View All</Link>
        </div>
        
        {loading ? (
          <div className="loading-grid">
            {[1, 2, 3, 4].map(i => (
              <div key={i} className="product-card-skeleton" />
            ))}
          </div>
        ) : (
          <div className="product-grid" data-testid="featured-products">
            {featuredProducts.map(product => (
              <ProductCard key={product.id} product={product} />
            ))}
          </div>
        )}
      </section>

      {/* Features Section */}
      <section className="features-section">
        <h2>Why Choose LD Store?</h2>
        <div className="features-grid">
          <div className="feature-card">
            <div className="feature-icon">🚀</div>
            <h3>Fast Delivery</h3>
            <p>Get your feature flags deployed in seconds, not days.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">🎯</div>
            <h3>Precise Targeting</h3>
            <p>Target specific users or segments with surgical precision.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">📊</div>
            <h3>Real-time Analytics</h3>
            <p>Monitor your rollouts with comprehensive observability.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">🔒</div>
            <h3>Enterprise Security</h3>
            <p>SOC 2 compliant with role-based access control.</p>
          </div>
        </div>
      </section>
    </div>
  );
}
