import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../services/api';
import { useCart } from '../context/CartContext';

export default function ProductDetail() {
  const { id } = useParams();
  const [product, setProduct] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [quantity, setQuantity] = useState(1);
  const [addedToCart, setAddedToCart] = useState(false);
  const { addToCart } = useCart();

  useEffect(() => {
    async function loadProduct() {
      setLoading(true);
      setError(null);
      try {
        const result = await api.getProduct(id);
        if (result.success) {
          setProduct(result.data.product || result.data);
        } else {
          setError('Product not found');
        }
      } catch (err) {
        console.error('Failed to load product:', err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    loadProduct();
  }, [id]);

  const handleAddToCart = () => {
    if (product) {
      addToCart(product, quantity);
      setAddedToCart(true);
      setTimeout(() => setAddedToCart(false), 2000);
    }
  };

  if (loading) {
    return (
      <div className="product-detail-page" data-testid="product-detail-loading">
        <div className="product-detail-skeleton" />
      </div>
    );
  }

  if (error || !product) {
    return (
      <div className="product-detail-page" data-testid="product-detail-error">
        <div className="error-state">
          <h2>Product Not Found</h2>
          <p>{error || 'The product you are looking for does not exist.'}</p>
          <Link to="/products" className="btn-primary">Browse Products</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="product-detail-page" data-testid="product-detail">
      <nav className="breadcrumb">
        <Link to="/">Home</Link>
        <span>/</span>
        <Link to="/products">Products</Link>
        <span>/</span>
        <span>{product.name}</span>
      </nav>

      <div className="product-detail-content">
        <div className="product-image" data-testid="product-image">
          <div className="product-image-placeholder">
            <span>{product.name?.charAt(0) || 'P'}</span>
          </div>
        </div>

        <div className="product-info">
          <h1 data-testid="product-name">{product.name}</h1>
          <p className="product-price" data-testid="product-price">
            ${product.price?.toFixed(2)}
          </p>
          
          <p className="product-description" data-testid="product-description">
            {product.description || 'A high-quality product designed to enhance your development workflow with powerful feature management capabilities.'}
          </p>

          <div className="product-stock">
            {product.stock > 0 ? (
              <span className="in-stock">In Stock ({product.stock} available)</span>
            ) : (
              <span className="out-of-stock">Out of Stock</span>
            )}
          </div>

          <div className="product-actions">
            <div className="quantity-selector">
              <label htmlFor="quantity">Quantity:</label>
              <button 
                onClick={() => setQuantity(q => Math.max(1, q - 1))}
                data-testid="decrease-quantity"
              >
                -
              </button>
              <input
                type="number"
                id="quantity"
                value={quantity}
                onChange={e => setQuantity(Math.max(1, parseInt(e.target.value) || 1))}
                min="1"
                max={product.stock || 99}
                data-testid="quantity-input"
              />
              <button 
                onClick={() => setQuantity(q => q + 1)}
                data-testid="increase-quantity"
              >
                +
              </button>
            </div>

            <button
              className={`btn-primary btn-lg ${addedToCart ? 'success' : ''}`}
              onClick={handleAddToCart}
              disabled={product.stock <= 0}
              data-testid="add-to-cart"
            >
              {addedToCart ? 'Added!' : 'Add to Cart'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
