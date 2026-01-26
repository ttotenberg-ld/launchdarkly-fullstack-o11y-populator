import { useCart } from '../../context/CartContext';

export default function CartItem({ item }) {
  const { updateQuantity, removeFromCart } = useCart();

  return (
    <div className="cart-item" data-testid="cart-item">
      <div className="cart-item-image">
        <div className="product-image-placeholder">
          {item.name?.charAt(0) || 'P'}
        </div>
      </div>
      
      <div className="cart-item-details">
        <h3 className="cart-item-name" data-testid="cart-item-name">{item.name}</h3>
        <p className="cart-item-price">${item.price?.toFixed(2)} each</p>
      </div>
      
      <div className="cart-item-quantity">
        <button
          onClick={() => updateQuantity(item.id, item.quantity - 1)}
          className="quantity-btn"
          data-testid="decrease-quantity"
        >
          -
        </button>
        <span className="quantity-value" data-testid="item-quantity">{item.quantity}</span>
        <button
          onClick={() => updateQuantity(item.id, item.quantity + 1)}
          className="quantity-btn"
          data-testid="increase-quantity"
        >
          +
        </button>
      </div>
      
      <div className="cart-item-total" data-testid="cart-item-total">
        ${(item.price * item.quantity).toFixed(2)}
      </div>
      
      <button
        onClick={() => removeFromCart(item.id)}
        className="cart-item-remove"
        data-testid="remove-item"
        aria-label="Remove item"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <line x1="18" y1="6" x2="6" y2="18"></line>
          <line x1="6" y1="6" x2="18" y2="18"></line>
        </svg>
      </button>
    </div>
  );
}
