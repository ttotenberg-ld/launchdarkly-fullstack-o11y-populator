import { Link } from 'react-router-dom';
import { useState } from 'react';
import { useFlags } from 'launchdarkly-react-client-sdk';
import { LDObserve } from '@launchdarkly/observability';
import { useCart } from '../../context/CartContext';

/**
 * ProductCard with three layout variants driven by the `product-card-layout`
 * LD flag.  The variant the user actually saw is tagged on the cart_item_added
 * metric so flag → cart-add conversion is attributable in LD.
 *
 * Variants:
 *   - standard → image, name, price, Add to Cart button (control)
 *   - detailed → adds rating, stock count, free-shipping badge
 *   - minimal  → image + name only; price hidden until hover
 */
export default function ProductCard({ product }) {
  const { addToCart } = useCart();
  const flags = useFlags();
  const layoutVariant = flags['product-card-layout'] || 'standard';
  const [added, setAdded] = useState(false);
  const [priceHovered, setPriceHovered] = useState(false);

  const handleAddToCart = (e) => {
    e.preventDefault();
    e.stopPropagation();
    addToCart(product, 1);
    setAdded(true);
    setTimeout(() => setAdded(false), 1500);

    // Funnel metric: track that an item was added, tagged with the visible
    // layout variant so we can correlate layout → add-to-cart conversion.
    LDObserve.recordCount({
      name: 'app.cart.item_added_total',
      value: 1,
      attributes: {
        product_id: String(product.id),
        product_price: String(product.price ?? 0),
        layout_variant: layoutVariant,
      },
    });
  };

  // Minimal variant: image + name only, price hidden until hover.
  if (layoutVariant === 'minimal') {
    return (
      <Link
        to={`/products/${product.id}`}
        className="product-card product-card-minimal"
        data-testid="product-card"
        data-layout-variant="minimal"
      >
        <div className="product-card-image" data-testid="product-card-image">
          <div className="product-image-placeholder">
            {product.name?.charAt(0) || 'P'}
          </div>
        </div>
        <div
          className="product-card-content"
          onMouseEnter={() => setPriceHovered(true)}
          onMouseLeave={() => setPriceHovered(false)}
        >
          <h3 className="product-card-name" data-testid="product-card-name">
            {product.name}
          </h3>
          <p
            className="product-card-price"
            data-testid="product-card-price"
            style={{
              opacity: priceHovered ? 1 : 0,
              transition: 'opacity 150ms ease',
              minHeight: '1.2em',
            }}
          >
            ${product.price?.toFixed(2)}
          </p>
          <button
            className={`btn-primary btn-sm btn-full ${added ? 'success' : ''}`}
            onClick={handleAddToCart}
            disabled={product.stock === 0}
            data-testid="add-to-cart"
          >
            {added ? 'Added!' : 'Add to Cart'}
          </button>
        </div>
      </Link>
    );
  }

  // Detailed variant: adds rating, stock count, free-shipping badge.
  if (layoutVariant === 'detailed') {
    // Deterministic pseudo-rating so the same product always shows the
    // same stars (no UI churn between renders).
    const rating = 3.5 + ((Number(String(product.id).replace(/\D/g, '')) || 0) % 15) / 10;
    const ratingStars = '★'.repeat(Math.round(rating)) + '☆'.repeat(5 - Math.round(rating));

    return (
      <Link
        to={`/products/${product.id}`}
        className="product-card product-card-detailed"
        data-testid="product-card"
        data-layout-variant="detailed"
      >
        <div className="product-card-image" data-testid="product-card-image">
          <div className="product-image-placeholder">
            {product.name?.charAt(0) || 'P'}
          </div>
          <span
            style={{
              position: 'absolute',
              top: '8px',
              right: '8px',
              background: '#059669',
              color: '#fff',
              fontSize: '11px',
              fontWeight: 700,
              padding: '3px 8px',
              borderRadius: '10px',
            }}
          >
            FREE SHIPPING
          </span>
        </div>
        <div className="product-card-content">
          <h3 className="product-card-name" data-testid="product-card-name">
            {product.name}
          </h3>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: '13px',
              color: '#f59e0b',
              marginBottom: '4px',
            }}
          >
            <span>{ratingStars}</span>
            <span style={{ color: 'var(--ld-gray-600)' }}>
              {rating.toFixed(1)}
            </span>
          </div>
          <p className="product-card-price" data-testid="product-card-price">
            ${product.price?.toFixed(2)}
          </p>
          {product.stock !== undefined && (
            <p
              className={`product-card-stock ${product.stock > 0 ? 'in-stock' : 'out-of-stock'}`}
              style={{
                fontWeight: product.stock > 0 && product.stock < 10 ? 700 : 400,
                color: product.stock > 0 && product.stock < 10 ? '#dc2626' : undefined,
              }}
            >
              {product.stock === 0
                ? 'Out of stock'
                : product.stock < 10
                  ? `Only ${product.stock} left!`
                  : `${product.stock} in stock`}
            </p>
          )}
          <button
            className={`btn-primary btn-sm btn-full ${added ? 'success' : ''}`}
            onClick={handleAddToCart}
            disabled={product.stock === 0}
            data-testid="add-to-cart"
          >
            {added ? 'Added!' : 'Add to Cart'}
          </button>
        </div>
      </Link>
    );
  }

  // Standard variant (control) — unchanged layout.
  return (
    <Link
      to={`/products/${product.id}`}
      className="product-card"
      data-testid="product-card"
      data-layout-variant="standard"
    >
      <div className="product-card-image" data-testid="product-card-image">
        <div className="product-image-placeholder">
          {product.name?.charAt(0) || 'P'}
        </div>
      </div>

      <div className="product-card-content">
        <h3 className="product-card-name" data-testid="product-card-name">
          {product.name}
        </h3>
        <p className="product-card-price" data-testid="product-card-price">
          ${product.price?.toFixed(2)}
        </p>

        {product.stock !== undefined && (
          <p className={`product-card-stock ${product.stock > 0 ? 'in-stock' : 'out-of-stock'}`}>
            {product.stock > 0 ? `${product.stock} in stock` : 'Out of stock'}
          </p>
        )}

        <button
          className={`btn-primary btn-sm btn-full ${added ? 'success' : ''}`}
          onClick={handleAddToCart}
          disabled={product.stock === 0}
          data-testid="add-to-cart"
        >
          {added ? 'Added!' : 'Add to Cart'}
        </button>
      </div>
    </Link>
  );
}
