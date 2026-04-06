import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useFlags } from 'launchdarkly-react-client-sdk';
import { LDObserve } from '@launchdarkly/observability';
import { api } from '../services/api';
import ProductCard from '../components/products/ProductCard';

export default function Products() {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchParams] = useSearchParams();
  const searchQuery = searchParams.get('q');
  const flags = useFlags();
  const layoutVariant = flags['product-card-layout'] || 'standard';

  useEffect(() => {
    async function loadProducts() {
      setLoading(true);
      setError(null);
      try {
        let result;
        if (searchQuery) {
          result = await api.search(searchQuery);
        } else {
          result = await api.listProducts();
        }

        if (result.success) {
          const items = result.data.products || result.data.results || [];
          setProducts(items);

          // Funnel metric: record search submission + result count.
          if (searchQuery) {
            LDObserve.recordCount({
              name: 'app.search.submitted_total',
              value: 1,
              attributes: {
                had_results: items.length > 0 ? 'true' : 'false',
                layout_variant: layoutVariant,
              },
            });
            LDObserve.recordHistogram({
              name: 'app.search.result_count',
              value: items.length,
              attributes: { layout_variant: layoutVariant },
            });
          }
        } else {
          setError('Failed to load products');
        }
      } catch (err) {
        console.error('Failed to load products:', err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    loadProducts();
  }, [searchQuery, layoutVariant]);

  return (
    <div className="products-page" data-testid="products-page">
      <div className="page-header">
        <h1>{searchQuery ? `Search: "${searchQuery}"` : 'All Products'}</h1>
        <p>{products.length} products found</p>
      </div>

      {loading && (
        <div className="loading-grid" data-testid="products-loading">
          {[1, 2, 3, 4, 5, 6].map(i => (
            <div key={i} className="product-card-skeleton" />
          ))}
        </div>
      )}

      {error && (
        <div className="error-message" data-testid="products-error">
          <p>{error}</p>
          <button onClick={() => window.location.reload()}>Try Again</button>
        </div>
      )}

      {!loading && !error && (
        <div className="product-grid" data-testid="product-grid">
          {products.map(product => (
            <ProductCard key={product.id} product={product} />
          ))}
          {products.length === 0 && (
            <div className="empty-state" data-testid="no-products">
              <p>No products found.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
