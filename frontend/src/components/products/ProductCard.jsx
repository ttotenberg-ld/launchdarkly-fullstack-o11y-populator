import { Link } from 'react-router-dom';
import { useCart } from '../../context/CartContext';
import { useState } from 'react';

export default function ProductCard({ product }) {
  const { addToCart } = useCart();
  const [added, setAdded] = useState(false);

  const handleAddToCart = (e) => {
    e.preventDefault();
    e.stopPropagation();
    addToCart(product, 1);
    setAdded(true);
    setTimeout(() => setAdded(false), 1500);
  };

  return (
    <Link 
      to={`/products/${product.id}`} 
      className="product-card"
      data-testid="product-card"
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
